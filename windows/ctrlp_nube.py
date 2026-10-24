"""
Ctrl-P en línea (Google)
========================
- Inicio de sesión con Google (solo para saber quién es: correo). La sesión queda guardada protegida por
  Windows en %APPDATA%\\Ctrl-P y no hay que volver a entrar cada semana.
- El servidor es un Apps Script en el Google Drive del administrador (servidor_google/Codigo.gs).
- Los proyectos viajan CIFRADOS (AES-256-GCM) con la clave del proyecto. La clave nunca se guarda en
  archivos ni en el código: se pide al sincronizar y queda solo en memoria mientras el programa está abierto.
- Usuarios: bajan la versión vigente, trabajan y envían sus cambios (quedan «pendientes de aprobación").
- Administrador: acepta correos, revisa los cambios uno por uno (o todos), los aplica y sube la versión nueva.
"""

import base64
import hashlib
import json
import os
import secrets
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import ctrlp_core as core

# ---- datos del servidor (se completan al configurar Google; ver servidor_google/LEEME_GOOGLE.txt) ----
URL_SERVIDOR = ""
CLIENT_ID = ""
CLIENT_SECRET = ""
try:            # los pone GitHub al compilar, desde los secretos del repositorio (nunca en el código público)
    from nube_datos import CLIENT_ID, CLIENT_SECRET, URL_SERVIDOR
except ImportError:
    pass

ENCABEZADO = b"CTP1"
RUTA_SESION = "nube_sesion.dat"


class ErrorNube(Exception):
    pass


class ClaveIncorrecta(ErrorNube):
    pass


class NecesitaSesion(ErrorNube):
    pass


def _cfg():
    try:
        return core.leer_config()
    except Exception:
        return {}


def url_servidor():
    return os.environ.get("CTRLP_NUBE_URL") or _cfg().get("nube_url") or URL_SERVIDOR


def id_cliente():
    return _cfg().get("nube_cliente") or CLIENT_ID


def secreto_cliente():
    return _cfg().get("nube_secreto") or CLIENT_SECRET


def modo_prueba():
    """En las pruebas automaticas: la sesion es «PRUEBA:<correo>» contra el simulador (sin navegador)."""
    return os.environ.get("CTRLP_NUBE_PRUEBA", "")


def configurado():
    return bool(url_servidor() and (modo_prueba() or id_cliente()))


# ------------------------------------------------------------------ cifrado
def _derivar(clave, sal):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=200_000).derive(
        clave.encode("utf-8"))


def cifrar(datos, clave):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    sal, nonce = os.urandom(16), os.urandom(12)
    return ENCABEZADO + sal + nonce + AESGCM(_derivar(clave, sal)).encrypt(nonce, datos, ENCABEZADO)


def descifrar(blob, clave):
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not blob.startswith(ENCABEZADO) or len(blob) < 4 + 16 + 12 + 16:
        raise ErrorNube("El archivo en línea no es de Ctrl-P o está dañado.")
    sal, nonce, ct = blob[4:20], blob[20:32], blob[32:]
    try:
        return AESGCM(_derivar(clave, sal)).decrypt(nonce, ct, ENCABEZADO)
    except InvalidTag:
        raise ClaveIncorrecta("La clave del proyecto no es correcta.")


TEXTO_VERIFICADOR = b"Ctrl-P verificador de clave"


def verificador(clave):
    return base64.b64encode(cifrar(TEXTO_VERIFICADOR, clave)).decode("ascii")


def clave_correcta(clave, verif_b64):
    """True/False si se puede comprobar; None si el proyecto no trae verificador."""
    if not verif_b64:
        return None
    try:
        return descifrar(base64.b64decode(verif_b64), clave) == TEXTO_VERIFICADOR
    except ClaveIncorrecta:
        return False
    except Exception:
        return None


# ------------------------------------------------------------------ sesion guardada (protegida por Windows)
def _proteger(datos):
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class BLOB(ctypes.Structure):
                _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
            ent = BLOB(len(datos), ctypes.cast(ctypes.create_string_buffer(datos, len(datos)), ctypes.POINTER(ctypes.c_char)))
            sal = BLOB()
            if ctypes.windll.crypt32.CryptProtectData(ctypes.byref(ent), None, None, None, None, 0, ctypes.byref(sal)):
                r = ctypes.string_at(sal.pbData, sal.cbData)
                ctypes.windll.kernel32.LocalFree(sal.pbData)
                return b"DP" + r
        except Exception:
            pass
    return b"B6" + base64.b64encode(datos)


def _desproteger(datos):
    if datos.startswith(b"DP") and os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
        d = datos[2:]
        ent = BLOB(len(d), ctypes.cast(ctypes.create_string_buffer(d, len(d)), ctypes.POINTER(ctypes.c_char)))
        sal = BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(ent), None, None, None, None, 0, ctypes.byref(sal)):
            raise ErrorNube("No se pudo leer la sesión guardada.")
        r = ctypes.string_at(sal.pbData, sal.cbData)
        ctypes.windll.kernel32.LocalFree(sal.pbData)
        return r
    if datos.startswith(b"B6"):
        return base64.b64decode(datos[2:])
    raise ErrorNube("Sesión guardada desconocida.")


def _ruta_sesion():
    return os.path.join(core.carpeta_config(), RUTA_SESION)


def _leer_sesion():
    try:
        with open(_ruta_sesion(), "rb") as f:
            return json.loads(_desproteger(f.read()).decode("utf-8"))
    except Exception:
        return {}


def _guardar_sesion(d):
    with open(_ruta_sesion(), "wb") as f:
        f.write(_proteger(json.dumps(d).encode("utf-8")))


def _post(url, datos, timeout=60):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(datos).encode("ascii"),
                                 headers={"Content-Type": "application/x-www-form-urlencoded",
                                          "User-Agent": "Ctrl-P"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


class Sesion:
    """Sesion de Google: id_token vigente (se renueva solo con el refresh_token guardado)."""

    def __init__(self):
        self.id_token = None
        self.vence = 0
        self.email = _leer_sesion().get("email", "")
        self._cancelar = threading.Event()

    def tiene_sesion(self):
        return bool(modo_prueba() or _leer_sesion().get("refresh"))

    def token(self):
        if modo_prueba():
            self.email = modo_prueba()
            return "PRUEBA:" + modo_prueba()
        if self.id_token and time.time() < self.vence - 120:
            return self.id_token
        s = _leer_sesion()
        if not s.get("refresh"):
            raise NecesitaSesion("Iniciá sesión con Google.")
        try:
            r = _post("https://oauth2.googleapis.com/token", {
                "client_id": id_cliente(), "client_secret": secreto_cliente(),
                "refresh_token": s["refresh"], "grant_type": "refresh_token"}, timeout=20)
        except urllib.error.HTTPError as e:
            if e.code in (400, 401):
                self.cerrar_sesion()
                raise NecesitaSesion("La sesión de Google se cerró. Volvé a iniciar sesión.")
            raise
        self._tomar(r)
        return self.id_token

    def _tomar(self, r):
        if not r.get("id_token"):
            raise ErrorNube("Google no devolvió la identificación.")
        self.id_token = r["id_token"]
        self.vence = time.time() + int(r.get("expires_in", 3600))
        try:
            carga = self.id_token.split(".")[1]
            carga += "=" * (-len(carga) % 4)
            self.email = json.loads(base64.urlsafe_b64decode(carga)).get("email", "").lower()
        except Exception:
            pass

    def iniciar_sesion(self, al_abrir_navegador=None, espera=300):
        """Abre el navegador para elegir la cuenta de Google y espera la respuesta (en un hilo aparte)."""
        if modo_prueba():
            self.email = modo_prueba()
            return self.email
        import http.server
        import webbrowser
        verif = secrets.token_urlsafe(48)
        reto = base64.urlsafe_b64encode(hashlib.sha256(verif.encode()).digest()).decode().rstrip("=")
        estado = secrets.token_urlsafe(16)
        res = {}

        class Manejador(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if q.get("state", [""])[0] == estado:
                    res["code"] = q.get("code", [""])[0]
                    res["error"] = q.get("error", [""])[0]
                ok = bool(res.get("code"))
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(("<html><body style='font-family:sans-serif;padding:40px'><h2>Ctrl-P</h2><p>" +
                                  ("Listo, ya podés volver a Ctrl-P." if ok else "No se completó el inicio de sesión.")
                                  + "</p></body></html>").encode("utf-8"))

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), Manejador)
        srv.timeout = 1
        redir = f"http://127.0.0.1:{srv.server_address[1]}"
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
            "client_id": id_cliente(), "redirect_uri": redir, "response_type": "code",
            "scope": "openid email profile", "code_challenge": reto, "code_challenge_method": "S256",
            "state": estado, "access_type": "offline", "prompt": "consent select_account"})
        if al_abrir_navegador:
            al_abrir_navegador(url)
        webbrowser.open(url)
        self._cancelar.clear()
        limite = time.time() + espera
        try:
            while not res and time.time() < limite and not self._cancelar.is_set():
                srv.handle_request()
        finally:
            srv.server_close()
        if self._cancelar.is_set():
            raise ErrorNube("Se canceló el inicio de sesión.")
        if not res.get("code"):
            raise ErrorNube("No se completó el inicio de sesión con Google" +
                            (f" ({res['error']})." if res.get("error") else "."))
        r = _post("https://oauth2.googleapis.com/token", {
            "client_id": id_cliente(), "client_secret": secreto_cliente(), "code": res["code"],
            "code_verifier": verif, "redirect_uri": redir, "grant_type": "authorization_code"}, timeout=30)
        self._tomar(r)
        if r.get("refresh_token"):
            _guardar_sesion({"refresh": r["refresh_token"], "email": self.email})
        return self.email

    def cancelar(self):
        self._cancelar.set()

    def cerrar_sesion(self):
        self.id_token, self.vence = None, 0
        try:
            os.remove(_ruta_sesion())
        except OSError:
            pass


SESION = Sesion()


def anotar(texto):
    """Diagnostico en errores.log (sin claves ni datos del proyecto)."""
    try:
        with open(os.path.join(core.carpeta_config(), "errores.log"), "a", encoding="utf-8") as f:
            f.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} · En línea\n{texto}\n")
    except Exception:
        pass


def llamar(accion, timeout=60, **datos):
    """Llama al servidor. Devuelve el diccionario de respuesta o lanza ErrorNube."""
    if not url_servidor():
        raise ErrorNube("Ctrl-P en línea todavía no está configurado (falta el servidor de Google).")
    t0 = time.time()
    datos = dict(datos, accion=accion, id_token=SESION.token())
    t_tok = time.time() - t0
    cuerpo = json.dumps(datos).encode("utf-8")
    req = urllib.request.Request(url_servidor(), data=cuerpo, headers={"Content-Type": "application/json",
                                                                       "User-Agent": "Ctrl-P"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            texto = r.read().decode("utf-8")
    except urllib.error.URLError as e:
        anotar(f"{accion}: sin conexión tras {time.time() - t0:.1f} s ({getattr(e, 'reason', e)})")
        raise ErrorNube(f"No hay conexión con Google ({getattr(e, 'reason', e)}). Revisá internet.")
    except (TimeoutError, OSError) as e:
        anotar(f"{accion}: Google no respondió en {time.time() - t0:.1f} s ({e})")
        raise ErrorNube(f"Google no respondió a tiempo ({int(time.time() - t0)} s). Probá de nuevo en un momento.")
    dt = time.time() - t0
    if dt > 8 or len(cuerpo) > 200000:
        anotar(f"{accion}: {dt:.1f} s (sesión {t_tok:.1f} s), enviado {len(cuerpo) / 1e6:.2f} MB, "
               f"recibido {len(texto) / 1e6:.2f} MB")
    try:
        d = json.loads(texto)
    except ValueError:
        raise ErrorNube("El servidor de Google respondió algo inesperado (¿está bien implementado el Apps Script?).")
    if not d.get("ok"):
        err = d.get("error") or "Error del servidor."
        if "sesión" in err.lower() and "venció" in err.lower():
            SESION.id_token = None
        raise ErrorNube(err)
    return d


def _n(x):
    try:
        return f"{float(x):,.2f}"
    except (TypeError, ValueError):
        return str(x)


def b64(b):
    return base64.b64encode(b).decode("ascii")


def de_b64(s):
    return base64.b64decode(s)


# ------------------------------------------------------------------ vinculo del archivo local con el proyecto en linea
CLAVES_META = ("nube_proyecto", "nube_version", "nube_rol", "nube_nombre", "nube_enviado_en", "nube_enviado_huella")


def vinculo(p):
    if p is None or not p.get_meta("nube_proyecto"):
        return None
    try:
        v = int(p.get_meta("nube_version", "0") or 0)
    except ValueError:
        v = 0
    return {"proyecto": p.get_meta("nube_proyecto"), "version": v, "rol": p.get_meta("nube_rol", "usuario"),
            "nombre": p.get_meta("nube_nombre", ""), "enviado_en": p.get_meta("nube_enviado_en", ""),
            "enviado_huella": p.get_meta("nube_enviado_huella", "")}


def vincular(p, proyecto, version, rol, nombre):
    p.set_meta("nube_proyecto", proyecto)
    p.set_meta("nube_version", int(version))
    p.set_meta("nube_rol", rol)
    p.set_meta("nube_nombre", nombre)


def carpeta_en_linea():
    import ctrlp_ui as ui
    c = os.path.join(ui.carpeta_docs(), "En línea")
    os.makedirs(c, exist_ok=True)
    return c


def ruta_base(proyecto_id):
    c = os.path.join(carpeta_en_linea(), ".base")
    os.makedirs(c, exist_ok=True)
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(c, 0x02)       # oculta
        except Exception:
            pass
    return os.path.join(c, f"{proyecto_id}.ctrlp")


TABLAS_HUELLA = ("items", "edificios", "niveles", "contractual", "tipo_cant", "avances", "detalle", "equipos", "hitos",
                 "tramos", "marcas", "hojas", "plano_ubic")


def huella_archivo(p):
    """Huella del contenido del proyecto (sin fechas de guardado): para saber si cambio algo desde la ultima subida."""
    h = hashlib.sha256()
    for t in TABLAS_HUELLA:
        try:
            for r in p.con.execute(f"SELECT * FROM {t} ORDER BY 1"):
                h.update(repr(tuple(r)).encode("utf-8"))
        except Exception:
            pass
    h.update(repr(sorted((r[0], r[1]) for r in p.con.execute("SELECT id, nombre FROM planos"))).encode("utf-8"))
    return h.hexdigest()[:24]


def bytes_proyecto(p):
    """El archivo .ctrlp tal como esta ahora (guardado)."""
    p.guardar()
    with open(p.ruta, "rb") as f:
        return f.read()


# ------------------------------------------------------------------ cambios (comparar y aplicar)
def _abrir_temporal(datos, usuario):
    """Abre unos bytes .ctrlp como proyecto temporal (sin copias de seguridad). Devuelve (proyecto, carpeta)."""
    tmp = tempfile.mkdtemp(prefix="ctrlp_nube_")
    ruta = os.path.join(tmp, "base.ctrlp")
    with open(ruta, "wb") as f:
        f.write(datos)
    return core.Proyecto(ruta, usuario), tmp


def cambios_de(base_bytes, nuevo_bytes, usuario="CTRL-P"):
    """Lo que tiene «nuevo» que no tiene «base» (analizar_importacion de Ctrl-P)."""
    base, tmp = _abrir_temporal(base_bytes, usuario)
    try:
        ruta = os.path.join(tmp, "nuevo.ctrlp")
        with open(ruta, "wb") as f:
            f.write(nuevo_bytes)
        imp = core.analizar_importacion(base, ruta)
        imp["archivo"] = "en línea"
        return imp
    finally:
        try:
            base.cerrar()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


def resumen(imp):
    return {"avances": len(imp["nuevos"]), "modificados": len(imp["modificados"]),
            "contractual": len(imp["contractual"]) + len(imp.get("tipo_cant", [])),
            "marcas": len(imp.get("marcas", [])) + len(imp.get("marcas_mod", [])),
            "ubicaciones": len(imp["ubicaciones"]), "planos": len(imp.get("planos", []))}


def hay_cambios(imp):
    r = resumen(imp)
    return any(r.values()) or any(imp.get(k) for k in ("tramos", "hitos", "equipos", "detalle", "hojas", "estilos"))


def huella_cambios(imp):
    def lim(x):
        return json.dumps(x, sort_keys=True, default=str)
    partes = [lim([(r["id"], r["cantidad"], r.get("obs")) for r in imp["nuevos"]]),
              lim([(l["id"], r["cantidad"], r.get("obs")) for l, r in imp["modificados"]]),
              lim([(r["item"], r["nivel"], r["cantidad"]) for r, _l, _n in imp["contractual"]]),
              lim(imp.get("tipo_cant", [])), lim([m["id"] for m in imp.get("marcas", []) + imp.get("marcas_mod", [])]),
              lim([d["id"] for _t, d in imp["ubicaciones"]])]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:24]


def lista_cambios(p_admin, imp, usuario_envio=""):
    """Lista para aprobar: [{clave, tipo, fecha, actividad, ubicacion, valor, conflicto, usuario}].
    imp: los cambios que hizo el usuario respecto de SU version base. p_admin: el proyecto del administrador
    (para marcar conflictos: el mismo dato ya cambio en el proyecto)."""
    it = {i["id"]: i for i in p_admin.items()}

    def act(iid):
        i = it.get(iid)
        return f"{i['codigo']} {i['descripcion']}" if i else "(actividad que no está en tu presupuesto)"

    def uni(iid):
        i = it.get(iid)
        return i["unidad"] if i else ""
    actuales = {r["id"]: dict(r) for r in p_admin.con.execute("SELECT * FROM avances")}
    por_clave = {(r["item"], r["nivel"], r["fecha"], r["hito"] or "", r["tramo"] or "", r["marca"] or "",
                  r["equipo"] or ""): r for r in actuales.values()}
    marcas_ids = {m["id"] for m in imp.get("marcas", []) + imp.get("marcas_mod", [])}
    out = []
    for r in imp["nuevos"]:
        if r.get("marca") and r["marca"].split("~")[0] in marcas_ids:
            continue                                   # va junto con su marca de plano
        k = (r["item"], r["nivel"], r["fecha"], r["hito"], r["tramo"], r["marca"], r["equipo"])
        ya = por_clave.get(k)
        conflicto = bool(ya) and abs((ya["cantidad"] or 0) - (r["cantidad"] or 0)) > core.EPS
        if ya and not conflicto:
            continue                                   # ya esta igual en el proyecto
        extra = " · ".join(x for x in (p_admin.nombre_hito(r["hito"]) if r["hito"] else "",
                                       p_admin.nombre_tramo(r["tramo"]) if r["tramo"] else "") if x)
        out.append({"clave": "N" + r["id"], "tipo": "Avance nuevo" if not ya else "Avance (ya hay otro valor)",
                    "fecha": r["fecha"], "actividad": act(r["item"]), "ubicacion": r.get("ubicacion", ""),
                    "valor": (f"{_n(ya['cantidad'])} → " if ya else "") +
                             f"{_n(r['cantidad'])} {uni(r['item'])}" + (f" · {extra}" if extra else "") +
                             (f" · {r['obs']}" if r.get("obs") else ""),
                    "conflicto": conflicto, "usuario": r.get("mod_usuario") or r.get("usuario") or usuario_envio})
    for l, r in imp["modificados"]:
        cur = actuales.get(l["id"])
        conflicto = bool(cur) and (abs((cur["cantidad"] or 0) - (l["cantidad"] or 0)) > core.EPS
                                   or (cur["obs"] or "") != (l["obs"] or ""))
        out.append({"clave": "M" + l["id"], "tipo": "Avance modificado", "fecha": r["fecha"],
                    "actividad": act(r["item"]), "ubicacion": r.get("ubicacion", ""),
                    "valor": f"{_n((cur or l)['cantidad'])} → {_n(r['cantidad'])} {uni(r['item'])}",
                    "conflicto": conflicto, "usuario": r.get("mod_usuario") or usuario_envio})
    cont = p_admin.todo_contractual()
    for r, l, n in imp["contractual"]:
        cur = cont.get(r["item"], {}).get(r["nivel"])
        conflicto = (cur is None) != (l is None) or (cur is not None and l is not None and abs(cur - l) > core.EPS)
        out.append({"clave": f"C{r['item']}|{r['nivel']}", "tipo": "Cantidad contractual", "fecha": "",
                    "actividad": act(r["item"]), "ubicacion": n,
                    "valor": f"{_n(cur) if cur is not None else '—'} → {_n(r['cantidad'])}",
                    "conflicto": conflicto, "usuario": usuario_envio})
    for c in imp.get("tipo_cant", []):
        out.append({"clave": f"T{c['item']}|{c['nivel']}|{c['tipo']}", "tipo": f"Contractual · {c['tipo']}",
                    "fecha": "", "actividad": act(c["item"]), "ubicacion": p_admin.etiqueta_ubicacion(c["nivel"]),
                    "valor": _n(c["cantidad"]), "conflicto": False, "usuario": usuario_envio})
    for m in imp.get("marcas", []) + imp.get("marcas_mod", []):
        nuevo = m in imp.get("marcas", [])
        out.append({"clave": "P" + m["id"], "tipo": "Marca en plano" if nuevo else "Marca en plano (cambio)",
                    "fecha": m.get("fecha", ""), "actividad": act(m["item"]),
                    "ubicacion": p_admin.etiqueta_ubicacion(m["nivel"]),
                    "valor": ("anulada" if m.get("anulada") else f"{_n(m.get('cantidad') or 0)} {uni(m['item'])}"),
                    "conflicto": False, "usuario": m.get("usuario") or usuario_envio})
    for tipo, d in imp["ubicaciones"]:
        out.append({"clave": "U" + d["id"], "tipo": "Ubicación nueva", "fecha": "", "actividad": "",
                    "ubicacion": d["nombre"], "valor": "edificio / área" if tipo == "edificio" else "nivel / tramo",
                    "conflicto": False, "usuario": usuario_envio})
    for pl in imp.get("planos", []):
        out.append({"clave": "L" + pl["id"], "tipo": "Plano nuevo", "fecha": "", "actividad": "",
                    "ubicacion": p_admin.etiqueta_ubicacion(pl["nivel"]) if pl.get("nivel") else "",
                    "valor": pl.get("nombre", ""), "conflicto": False, "usuario": pl.get("usuario") or usuario_envio})
    for t in imp.get("tramos", []):
        out.append({"clave": "R" + t["id"], "tipo": "Tramo nuevo", "fecha": "", "actividad": act(t["item"]),
                    "ubicacion": p_admin.etiqueta_ubicacion(t["nivel"]), "valor": t.get("nombre", ""),
                    "conflicto": False, "usuario": t.get("usuario") or usuario_envio})
    for e in imp.get("equipos", []):
        out.append({"clave": "E" + e["id"], "tipo": "Equipo nuevo", "fecha": "", "actividad": act(e["item"]),
                    "ubicacion": p_admin.etiqueta_ubicacion(e["nivel"]), "valor": e.get("nombre", ""),
                    "conflicto": False, "usuario": e.get("usuario") or usuario_envio})
    for h in imp.get("hitos", []):
        out.append({"clave": "H" + h["id"], "tipo": "Hito nuevo", "fecha": "", "actividad": act(h["item"]),
                    "ubicacion": "", "valor": f"{h.get('nombre', '')} {_n(h.get('pct') or 0)} %"
                    + (f" · {h['tipo']}" if h.get("tipo") else ""), "conflicto": False, "usuario": usuario_envio})
    return out


def aplicar_seleccion(p, imp, elegidos):
    """Aplica en el proyecto del administrador solo los cambios elegidos (claves de lista_cambios), con lo que
    necesitan (ubicaciones, hitos, tramos, equipos, planos de las marcas). Devuelve cuantos se aplicaron."""
    el = set(elegidos)
    marcas = [m for m in imp.get("marcas", []) if "P" + m["id"] in el]
    marcas_mod = [m for m in imp.get("marcas_mod", []) if "P" + m["id"] in el]
    ids_marca = {m["id"] for m in marcas + marcas_mod}
    nuevos = [r for r in imp["nuevos"] if "N" + r["id"] in el or
              (r.get("marca") and r["marca"].split("~")[0] in ids_marca)]
    # lo que ya esta con otro valor (misma actividad, ubicacion y fecha): se reemplaza el valor
    reemplazar = []
    por_clave = {(r["item"], r["nivel"], r["fecha"], r["hito"] or "", r["tramo"] or "", r["marca"] or "",
                  r["equipo"] or ""): r["id"] for r in p.con.execute("SELECT * FROM avances")}
    for r in list(nuevos):
        k = (r["item"], r["nivel"], r["fecha"], r["hito"], r["tramo"], r["marca"], r["equipo"])
        if k in por_clave:
            nuevos.remove(r)
            reemplazar.append((por_clave[k], r))
    modificados = [(l, r) for l, r in imp["modificados"] if "M" + l["id"] in el]
    contractual = [(r, l, n) for r, l, n in imp["contractual"] if f"C{r['item']}|{r['nivel']}" in el]
    tipo_cant = [c for c in imp.get("tipo_cant", []) if f"T{c['item']}|{c['nivel']}|{c['tipo']}" in el]
    # dependencias
    usados_nv = ({r["nivel"] for r in nuevos} | {r["nivel"] for _i, r in reemplazar} | {r["nivel"] for _l, r in modificados}
                 | {r["nivel"] for r, _l, _n in contractual} | {c["nivel"] for c in tipo_cant}
                 | {m["nivel"] for m in marcas + marcas_mod})
    niveles_nuevos = {d["id"]: d for t, d in imp["ubicaciones"] if t == "nivel"}
    usados_ed = {niveles_nuevos[n]["edificio"] for n in usados_nv if n in niveles_nuevos}
    ubic = [(t, d) for t, d in imp["ubicaciones"]
            if "U" + d["id"] in el or (t == "nivel" and d["id"] in usados_nv) or (t == "edificio" and d["id"] in usados_ed)]
    for t, d in ubic:                                # un nivel elegido necesita su edificio
        if t == "nivel":
            usados_ed.add(d["edificio"])
    ubic = [(t, d) for t, d in imp["ubicaciones"]
            if (t, d) in ubic or (t == "edificio" and d["id"] in usados_ed)]
    usados_hito = {r["hito"] for r in nuevos + [r for _i, r in reemplazar]} | {m.get("hito") for m in marcas}
    usados_tramo = {r["tramo"] for r in nuevos + [r for _i, r in reemplazar]} | {m.get("tramo") for m in marcas}
    usados_eq = {r["equipo"] for r in nuevos + [r for _i, r in reemplazar]} | {m.get("equipo") for m in marcas}
    usados_plano = {m["plano"] for m in marcas + marcas_mod}
    hitos = [h for h in imp.get("hitos", []) if "H" + h["id"] in el or h["id"] in usados_hito]
    tramos = [t for t in imp.get("tramos", []) if "R" + t["id"] in el or t["id"] in usados_tramo]
    equipos = [e for e in imp.get("equipos", []) if "E" + e["id"] in el or e["id"] in usados_eq]
    planos = [pl for pl in imp.get("planos", []) if "L" + pl["id"] in el or pl["id"] in usados_plano]
    ids_pl = {pl["id"] for pl in planos} | usados_plano
    items_con_detalle = ({h["item"] for h in hitos} | {t["item"] for t in tramos} | {e["item"] for e in equipos})
    filtrado = dict(imp)
    filtrado.update({
        "nuevos": nuevos, "modificados": modificados, "contractual": contractual, "tipo_cant": tipo_cant,
        "ubicaciones": ubic, "marcas": marcas, "marcas_mod": marcas_mod, "hitos": hitos, "tramos": tramos,
        "equipos": equipos, "planos": planos,
        "detalle": [d for d in imp.get("detalle", []) if d["item"] in items_con_detalle],
        "hojas": [h for h in imp.get("hojas", []) if h["plano"] in ids_pl],
        "plano_ubic": [x for x in imp.get("plano_ubic", []) if x[0] in ids_pl],
        "estilos": [x for x in imp.get("estilos", []) if x[0] in {m["item"] for m in marcas}],
        "historial": [],
    })
    core.aplicar_importacion(p, filtrado, {l["id"]: True for l, _r in modificados})
    for vid, r in reemplazar:
        p.con.execute("UPDATE avances SET cantidad=?, obs=?, modificado=?, mod_usuario=?, origen=? WHERE id=?",
                      (r["cantidad"], r["obs"], r["modificado"], r.get("mod_usuario") or r["usuario"], "en línea", vid))
    p._cache = None
    p.sucio = True
    return len(nuevos) + len(reemplazar) + len(modificados) + len(contractual) + len(tipo_cant) + len(marcas) \
        + len(marcas_mod)


def pendientes_ids(p_local, base_bytes):
    """Avances del usuario que todavia no aprobo el administrador: {id de avance}."""
    imp = cambios_de(base_bytes, bytes_proyecto(p_local), p_local.usuario)
    ids = {r["id"] for r in imp["nuevos"]} | {r["id"] for _l, r in imp["modificados"]}
    return ids, imp


def rebasar(p_local, base_vieja, base_nueva, desde_local=""):
    """Pone al dia el archivo del usuario con la version nueva del administrador, conservando solo lo que el
    usuario hizo despues de «desde_local» (lo ya enviado se reemplaza por lo que el administrador aprobo).
    Devuelve los bytes del archivo nuevo."""
    imp = cambios_de(base_vieja, bytes_proyecto(p_local), p_local.usuario)

    def despues(r):
        return not desde_local or max(r.get("modificado") or "", r.get("creado") or "") > desde_local
    nuevo, tmp = _abrir_temporal(base_nueva, p_local.usuario)
    try:
        imp2 = dict(imp)
        imp2["nuevos"] = [r for r in imp["nuevos"] if despues(r)]
        imp2["modificados"] = [(l, r) for l, r in imp["modificados"] if despues(r)]
        if desde_local:
            imp2["contractual"], imp2["tipo_cant"], imp2["marcas"], imp2["marcas_mod"] = [], [], [], []
            imp2["ubicaciones"], imp2["planos"] = [], []
        imp2["historial"] = []
        ids_nuevo = {r[0] for r in nuevo.con.execute("SELECT id FROM avances")}
        imp2["nuevos"] = [r for r in imp2["nuevos"] if r["id"] not in ids_nuevo]
        imp2["modificados"] = [(l, r) for l, r in imp2["modificados"] if l["id"] in ids_nuevo]
        if hay_cambios(imp2) or imp2["nuevos"] or imp2["modificados"]:
            aplicar_seleccion(nuevo, imp2, [c["clave"] for c in lista_cambios(nuevo, imp2)])
        nuevo.guardar()
        with open(nuevo.ruta, "rb") as f:
            return f.read()
    finally:
        try:
            nuevo.cerrar()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)
