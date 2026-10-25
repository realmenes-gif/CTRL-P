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
