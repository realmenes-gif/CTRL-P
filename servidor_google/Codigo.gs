/**
 * Ctrl-P en línea · servidor en Google Apps Script (en el Google Drive del administrador)
 * =====================================================================================
 * - Cada usuario entra con su cuenta de Google: Ctrl-P manda su «id_token» y aquí se comprueba con Google
 *   quién es (correo verificado). No se guarda ninguna contraseña.
 * - Los proyectos se guardan CIFRADOS con la clave del proyecto (el cifrado lo hace Ctrl-P en cada
 *   computadora; aquí nunca llega la clave). Sin la clave, los archivos no se pueden leer.
 * - Solo el administrador sube versiones del proyecto, acepta correos y resuelve los cambios enviados.
 * - Los demás: piden acceso, bajan la versión vigente y envían sus cambios (quedan pendientes de aprobación).
 *
 * Instalación: ver «LEEME_GOOGLE.txt» (pegar este código, poner los 2 datos de abajo e implementar
 * como «Aplicación web»: ejecutar como «Yo», acceso «Cualquier usuario»).
 */

// ===== los 2 datos a completar =====
var ADMIN_EMAIL = "PONER_AQUI_TU_GMAIL@gmail.com";            // el Gmail del administrador (CARLOS - CONSORCIO)
var CLIENT_ID = "PONER_AQUI_EL_ID_DE_CLIENTE.apps.googleusercontent.com";   // de Google Cloud (app de escritorio)
// ===================================

var CARPETA = "Ctrl-P en línea";
var VERSIONES_GUARDADAS = 15;

function doGet() {
  return _json({ ok: true, servicio: "Ctrl-P en línea", version: 1 });
}

function doPost(e) {
  try {
    var q = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    if (q.accion === "registro") return _json(_registro(q));
    var email = _quien(q.id_token);
    var admin = email === ADMIN_EMAIL.toLowerCase();
    var r = _accion(q, email, admin);
    r.ok = true;
    return _json(r);
  } catch (err) {
    return _json({ ok: false, error: String((err && err.message) || err) });
  }
}

function _json(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// ---------------------------------------------------------------- identidad (Google)
function _quien(token) {
  if (!token) throw new Error("Falta iniciar sesión con Google.");
  var cache = CacheService.getScriptCache();
  var h = Utilities.base64EncodeWebSafe(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, token));
  var guardado = cache.get("tok_" + h);
  if (guardado) return guardado;
  var resp = UrlFetchApp.fetch("https://oauth2.googleapis.com/tokeninfo?id_token=" + encodeURIComponent(token),
                               { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) throw new Error("La sesión de Google venció. Volvé a iniciar sesión.");
  var t = JSON.parse(resp.getContentText());
  if (t.aud !== CLIENT_ID) throw new Error("La sesión no es de Ctrl-P.");
  if (String(t.email_verified) !== "true" || !t.email) throw new Error("La cuenta de Google no tiene el correo verificado.");
  var email = String(t.email).toLowerCase();
  var resta = Math.min(3000, Math.max(60, Number(t.exp || 0) - Math.floor(Date.now() / 1000) - 60));
  cache.put("tok_" + h, email, resta);
  return email;
}

// ---------------------------------------------------------------- almacenamiento
function _raiz() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty("RAIZ");
  if (id) {
    try { return DriveApp.getFolderById(id); } catch (e) { /* se borró: se crea de nuevo */ }
  }
  var it = DriveApp.getRootFolder().getFoldersByName(CARPETA);
  var f = it.hasNext() ? it.next() : DriveApp.getRootFolder().createFolder(CARPETA);
  props.setProperty("RAIZ", f.getId());
  return f;
}

function _archivo(carpeta, nombre) {
  var it = carpeta.getFilesByName(nombre);
  return it.hasNext() ? it.next() : null;
}

function _leerJson(carpeta, nombre, defecto) {
  var f = _archivo(carpeta, nombre);
  if (!f) return defecto;
  return JSON.parse(f.getBlob().getDataAsString("UTF-8"));
}

function _escribirJson(carpeta, nombre, datos) {
  var txt = JSON.stringify(datos);
  var f = _archivo(carpeta, nombre);
  if (f) f.setContent(txt);
  else carpeta.createFile(nombre, txt, "application/json");
}

function _escribirBin(carpeta, nombre, b64) {
  var f = _archivo(carpeta, nombre);
  if (f) f.setTrashed(true);
  carpeta.createFile(Utilities.newBlob(Utilities.base64Decode(b64), "application/octet-stream", nombre));
}

function _leerBin(carpeta, nombre) {
  var f = _archivo(carpeta, nombre);
  if (!f) throw new Error("No se encontró el archivo en Drive (" + nombre + ").");
  return Utilities.base64Encode(f.getBlob().getBytes());
}

function _borrar(carpeta, nombre) {
  var f = _archivo(carpeta, nombre);
  if (f) f.setTrashed(true);
}

function _indice() { return _leerJson(_raiz(), "indice.json", { proyectos: {} }); }
function _guardarIndice(ind) { _escribirJson(_raiz(), "indice.json", ind); }

function _proyecto(ind, id) {
  var p = ind.proyectos[id];
  if (!p) throw new Error("El proyecto no existe en línea.");
  return p;
}

function _carpetaProyecto(p) { return DriveApp.getFolderById(p.carpeta); }

function _acceso(p, email, admin) {
  if (admin) return "admin";
  var a = (p.accesos || {})[email];
  return a ? a.estado : "";
}

function _exigirAcceso(p, email, admin) {
  var a = _acceso(p, email, admin);
  if (a !== "admin" && a !== "aprobado") {
    throw new Error(a === "pendiente" ? "Tu acceso todavía no fue aprobado por el administrador."
                                     : "No tenés acceso a este proyecto. Pedilo desde Ctrl-P.");
  }
}

function _exigirAdmin(admin) {
  if (!admin) throw new Error("Solo el administrador puede hacer esto.");
}

function _ahora() { return Utilities.formatDate(new Date(), "America/Tegucigalpa", "yyyy-MM-dd HH:mm:ss"); }

function _id() { return Utilities.getUuid().replace(/-/g, "").substring(0, 16); }

function _conCandado(fn) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try { return fn(); } finally { lock.releaseLock(); }
}

// ---------------------------------------------------------------- acciones
function _accion(q, email, admin) {
  switch (q.accion) {
    case "quien":
      return { email: email, admin: admin };

    case "proyectos": {
      var ind = _indice(), lista = [];
      Object.keys(ind.proyectos).forEach(function (id) {
        var p = ind.proyectos[id], a = _acceso(p, email, admin);
        var pend = 0, acc = 0;
        if (admin) {
          Object.keys(p.accesos || {}).forEach(function (m) { if (p.accesos[m].estado === "pendiente") acc++; });
          pend = (p.envios || []).filter(function (x) { return x.estado === "pendiente"; }).length;
        }
        lista.push({ id: id, nombre: p.nombre, version: p.version, actualizado: p.actualizado, acceso: a,
                     envios_pendientes: pend, accesos_pendientes: acc,
                     verificador: (a === "admin" || a === "aprobado") ? (p.verificador || "") : "" });
      });
      return { proyectos: lista, email: email, admin: admin };
    }

    case "pedir_acceso":
      return _conCandado(function () {
        var ind = _indice(), p = _proyecto(ind, q.proyecto);
        p.accesos = p.accesos || {};
        var a = p.accesos[email];
        if (!a || a.estado === "rechazado") {
          p.accesos[email] = { estado: "pendiente", usuario: String(q.usuario || ""), fecha: _ahora() };
          _guardarIndice(ind);
        }
        return { acceso: admin ? "admin" : p.accesos[email].estado };
      });

    case "accesos": {
      _exigirAdmin(admin);
      var p1 = _proyecto(_indice(), q.proyecto), out = [];
      Object.keys(p1.accesos || {}).forEach(function (m) {
        var a = p1.accesos[m];
        out.push({ email: m, estado: a.estado, usuario: a.usuario, fecha: a.fecha });
      });
      return { accesos: out };
    }

    case "resolver_acceso":
      _exigirAdmin(admin);
      return _conCandado(function () {
        var ind = _indice(), p = _proyecto(ind, q.proyecto);
        var a = (p.accesos || {})[String(q.email).toLowerCase()];
        if (!a) throw new Error("Ese correo no pidió acceso.");
        a.estado = q.aprobar ? "aprobado" : "rechazado";
        a.resuelto = _ahora();
        _guardarIndice(ind);
        return { estado: a.estado };
      });

    case "subir":
      _exigirAdmin(admin);
      return _conCandado(function () {
        var ind = _indice(), id = q.proyecto, p;
        if (!id) {
          id = _id();
          var carpeta = _raiz().createFolder(String(q.nombre || "Proyecto") + " · " + id);
          p = ind.proyectos[id] = { nombre: String(q.nombre || "Proyecto"), carpeta: carpeta.getId(), version: 0,
                                    accesos: {}, envios: [], creado: _ahora() };
        } else {
          p = _proyecto(ind, id);
          if (q.version_base !== undefined && q.version_base !== null && Number(q.version_base) !== p.version) {
            throw new Error("En línea hay una versión más nueva (v" + p.version + "). Sincronizá antes de subir.");
          }
          if (q.nombre) p.nombre = String(q.nombre);
        }
        if (q.verificador) p.verificador = String(q.verificador);   // texto cifrado con la clave (para avisar si se escribe mal)
        var c = _carpetaProyecto(p);
        p.version += 1;
        _escribirBin(c, "v" + p.version + ".bin", q.datos);
        p.actualizado = _ahora();
        p.tam = String(q.datos || "").length;
        var viejo = p.version - VERSIONES_GUARDADAS;
        if (viejo > 0) _borrar(c, "v" + viejo + ".bin");
        _guardarIndice(ind);
        return { proyecto: id, version: p.version, actualizado: p.actualizado };
      });

    case "version": {
      var pv = _proyecto(_indice(), q.proyecto);
      _exigirAcceso(pv, email, admin);
      return { version: pv.version, actualizado: pv.actualizado };
    }

    case "bajar": {
      var ind2 = _indice(), pb = _proyecto(ind2, q.proyecto);
      _exigirAcceso(pb, email, admin);
      var v = q.version ? Number(q.version) : pb.version;
      if (!v) throw new Error("El proyecto todavía no tiene ninguna versión subida.");
      return { version: v, actualizado: pb.actualizado, nombre: pb.nombre,
               datos: _leerBin(_carpetaProyecto(pb), "v" + v + ".bin") };
    }

    case "enviar":
      return _conCandado(function () {
        var ind = _indice(), p = _proyecto(ind, q.proyecto);
        _exigirAcceso(p, email, admin);
        var c = _carpetaProyecto(p), eid = _id();
        p.envios = p.envios || [];
        // un envio pendiente nuevo del mismo usuario reemplaza al anterior (lleva todo lo de antes)
        p.envios.forEach(function (x) {
          if (x.email === email && x.estado === "pendiente") {
            x.estado = "reemplazado";
            x.resuelto = _ahora();
            _borrar(c, "envio_" + x.id + ".bin");
          }
        });
        _escribirBin(c, "envio_" + eid + ".bin", q.datos);
        p.envios.push({ id: eid, email: email, usuario: String(q.usuario || ""), fecha: _ahora(),
                        version_base: Number(q.version_base || 0), resumen: q.resumen || {}, estado: "pendiente",
                        visto: false });
        if (p.envios.length > 300) p.envios = p.envios.slice(p.envios.length - 300);
        _guardarIndice(ind);
        return { envio: eid };
      });

    case "envios": {
      _exigirAdmin(admin);
      var pe = _proyecto(_indice(), q.proyecto);
      return { envios: (pe.envios || []).filter(function (x) { return x.estado === "pendiente"; }) };
    }

    case "envio_datos": {
      _exigirAdmin(admin);
      var pd = _proyecto(_indice(), q.proyecto);
      return { datos: _leerBin(_carpetaProyecto(pd), "envio_" + q.envio + ".bin") };
    }

    case "resolver_envio":
      _exigirAdmin(admin);
      return _conCandado(function () {
        var ind = _indice(), p = _proyecto(ind, q.proyecto);
        var x = (p.envios || []).filter(function (y) { return y.id === q.envio; })[0];
        if (!x) throw new Error("No se encontró el envío.");
        x.estado = String(q.estado || "resuelto");        // aceptado / rechazado / parcial
        x.resultado = q.resultado || {};
        x.resuelto = _ahora();
        x.version_resuelta = Number(q.version || p.version);
        x.visto = false;
        _guardarIndice(ind);
        return { estado: x.estado };
      });

    case "mis_envios":
      return _conCandado(function () {
        var ind = _indice(), p = _proyecto(ind, q.proyecto);
        var mios = (p.envios || []).filter(function (x) { return x.email === email; });
        var nuevos = mios.filter(function (x) { return !x.visto && x.estado !== "pendiente" && x.estado !== "reemplazado"; });
        var resp = { envios: mios.slice(-20), avisos: JSON.parse(JSON.stringify(nuevos)) };
        if (q.marcar_vistos && nuevos.length) {
          nuevos.forEach(function (x) { x.visto = true; });
          _guardarIndice(ind);
        }
        return resp;
      });

    default:
      throw new Error("Acción desconocida: " + q.accion);
  }
}

/**
 * Ctrl-P · errores.log automático
 * Cada Ctrl-P (computadora o tablet) manda solo lo nuevo de su errores.log cuando trae errores.
 * Queda en Drive («Ctrl-P en línea/registros», un archivo por equipo) y llega por correo al administrador.
 * No lleva claves ni datos de los proyectos. Funciona aunque la persona no haya iniciado sesión.
 */
var REGISTRO_MAX_CORREOS_DIA = 25;

function _registro(q) {
  var texto = String(q.texto || "");
  if (!texto) return { ok: true, guardado: false };
  if (texto.length > 200000) texto = texto.slice(-200000);
  var email = "";
  try { if (q.id_token) email = _quien(q.id_token); } catch (e) { email = ""; }
  var equipo = String(q.equipo || "equipo").replace(/[^\w .\-]/g, "_").slice(0, 60);
  var version = String(q.version || "").slice(0, 30);
  var plataforma = String(q.plataforma || "").slice(0, 30);
  var cab = "\n######## recibido " + _ahora() + " · " + plataforma + " · " + version + " · " + equipo +
            (email ? " · " + email : "") + "\n";
  _conCandado(function () {
    var raiz = _raiz();
    var it = raiz.getFoldersByName("registros");
    var carpeta = it.hasNext() ? it.next() : raiz.createFolder("registros");
    var nombre = plataforma + " - " + equipo + ".log";
    var f = _archivo(carpeta, nombre);
    var previo = f ? f.getBlob().getDataAsString("UTF-8") : "";
    var todo = previo + cab + texto;
    if (todo.length > 1000000) todo = todo.slice(-1000000);
    if (f) f.setContent(todo); else carpeta.createFile(nombre, todo, "text/plain");
  });
  // correo al administrador (con tope diario para no llenar el buzón)
  var props = PropertiesService.getScriptProperties();
  var hoy = Utilities.formatDate(new Date(), "America/Tegucigalpa", "yyyy-MM-dd");
  var cuenta = props.getProperty("REG_DIA") === hoy ? Number(props.getProperty("REG_N") || 0) : 0;
  if (cuenta < REGISTRO_MAX_CORREOS_DIA) {
    props.setProperty("REG_DIA", hoy);
    props.setProperty("REG_N", String(cuenta + 1));
    var cuerpo = cab + (texto.length > 60000 ? "…(completo en el adjunto)…\n" + texto.slice(-60000) : texto);
    MailApp.sendEmail({
      to: ADMIN_EMAIL,
      subject: "Ctrl-P errores · " + plataforma + " · " + version + " · " + equipo,
      body: cuerpo,
      attachments: [Utilities.newBlob(texto, "text/plain", "errores " + equipo + ".log")]
    });
  }
  return { ok: true, guardado: true };
}
