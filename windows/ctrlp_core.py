"""
Ctrl-P - nucleo de datos
========================
Archivo de proyecto .ctrlp (SQLite comprimido en ZIP), modelo de datos,
calculos de avance (topes por ubicacion, porcentajes, montos), copias de
seguridad por sesion, historial en Excel, importacion y actualizacion de
presupuesto, informes y exportaciones, e intercambio entre computadoras.
"""

import base64
import datetime as dt
import difflib
import hashlib
import hmac
import json
import os
import re
import shutil
import sqlite3
import tempfile
import unicodedata
import uuid
import zipfile

APP = "Ctrl-P"
EXT = ".ctrlp"
ESQUEMA = 6
EPS = 1e-9

# Administrador: su contrasena va como huella PBKDF2 (nunca la clave). Las contrasenas de los
# demas usuarios se guardan cifradas con la clave publica del administrador; solo su clave
# privada (protegida con la contrasena del administrador) puede leerlas.
ADMIN = "CARLOS - CONSORCIO"
ADMIN_HUELLA = ("7Se83VaqumlDOCo1Di6NpQ==", "wnxgcHhH652if6fhFNHyVKiHylzWL/GzgXIKWXaxrdQ=", 200000)
ADMIN_PUBLICA = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAn+x93dm7rL1Kgx1rxASP
HsBTRjyBKm1sv4ZZtaEmxICpLhpB0JeamVHO4/IzgPJulvyocQ2cEupar82PkODg
Mwyv49iSiHyXA/IXMwDVfHK0bbl3ZU/5KjtbrOHIILi/GACrZxsBqg8ArsRDSW0o
5lq9lc5gI0Mi55nNfniCGsTA+Ebd0M+yIeuILZ21iPfOE6+h966fWnvUQUf63od0
Sa2M+UuB94CMgjBbQvZnnKVJJIh7lHtiseVCq6V6yJtS+8gRYWrV51ECcz4/eNKO
mXwTjGa8oN5rDIThmPrhECcoCDu0vpOXT3Uc5g/+yUHG18j88MLxj/DYKNOjUX7p
yQIDAQAB
-----END PUBLIC KEY-----"""
ADMIN_PRIVADA = b"""-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIFLTBXBgkqhkiG9w0BBQ0wSjApBgkqhkiG9w0BBQwwHAQIPBfY7ou/rEsCAggA
MAwGCCqGSIb3DQIJBQAwHQYJYIZIAWUDBAEqBBDtLIAff1RCRhMmjxeq3hUvBIIE
0LDRfL1inAKrdXYOUokYXgPUwV+EunWGm9AqSjNHt4zLGbWVPWtzf58Ovdq5EJGd
jmg9d+LSZWgTjkK7Q6kRiLtU1v9OleCD6VzM6YfbwAyEhEac2EBrsvOZAWBFRJp+
yDNmWXb7xzucWi6Ld+6rhchWyEg2N7+GRBeEzuPOTWdEvuh2nyarYE5u5viIgdLq
tD4976HYENk/DFWDTan471FgTbvbEGZqnB26ep4LsNykVB8e6QN86UbHo6Ya6ugX
esCrzYxMvU9yVnkBCYmG3cf11nVQoxWjd3+3aa24JIiNVcmOqytNH0fVOAkGudeP
sSMu+iuUH0M38CdQTIpRBi1KjJ2C/ybLKDHnqGWqXg8f56oIeZBKzPSu7UrMhiIl
EylX9aKuYTwXi2egKph6bKns6Odz/feNxqAUuAszXW7fN50Dxs1wsHIdM6e4KXNO
d+qQVfetxeqOXl2Mq0M/5jiWJlr++q0iBZVK8YXixraY3qYXOa5gdpFRLVg9F6YS
Oz5b1cTXSyGx3KBambc1uozjP7gv6pe4igBsBisbyUSnkuAim94x3OXSwD0Q2Y5F
yNjcSTmoQnIIS4lCbG0iUN8OgH/szyhUMtfV/Puj2inleAH+Y/oMyq/dANS6FSTK
Vh3cURn+cTbQ7Tj2mVVVVTcSdbui1d02B8f6LSdv+uAEb5sKcjVJn3ibWGh652pF
zC1hFNGWR6UdYLKkosSJTfPDzVjX94FIZXDG5U8iP4nNzIUAiY436ke3opOilQqh
Y1FVrhKiIPcZTv498mW9AaDasZZBJCmSGIdkSHRDY28XFF6y4owHKke4i5FS88Xd
2ZkJ23J4oBKvTOkPeYu3d1hZewauao6RZ6yLaiEgStHbDjaTSdL06M9HInqccBCU
V+q0USntCo5AH8I68+QbjRy0jZGF+AMAfGe9x6pYD4vsQVjm8YIrBWyxpZmK8MFX
mRPjCruUncw9XQ7tKxaLf+KrRX25kRDFUB8ococPf344RymFdGTUSejSsyYEwmzO
uInctVdKL/MfgGs7h2UAjSgEmMc8Lm0FOaVMEdonwkvcBfMDvtdF52W4+Aq9XQ9C
VSxo1KkzoWpuQqUW2SlvPTRatKKpUuZsf86Dubh7zCXeAWNZjnBCjHMzHs1JPWjh
68SpHbT98TADYJfzi8jnU6VuRTh+IGNaibAy61afVKfpd5rY0d948uxm5iq1nmz0
ara458Iq4ReLzlJRfx8SH3FjQlo54/rJQTDRrsRXZa67frF+k3OAegC4T+CVq2SO
E+YQ8lbHGGoJeALwR2bSNAorshOfQccVDgk2ThaWwkZDvKU0jq/zsvhRcLrKqx4G
vHvVH1+l/jS7EbgD41jXMsCZ8tXfF1R459RXeGITnDLZLeiwQh7B3l9ZPDEDsH7/
2jyddQgYD1m1qgVShUUnXQ4/9GiYahJ8UNNkPGw4LCZ1U1M7KaFgk5zNCRyysmYg
KB6AJMfe4bvyW2ZpZC8TzG7xSoF1tb5JFufWGYA9ihToZpKHo/GvsZPpHbTm1zs+
3LkoVAqD8mljTTKhMQAx+EAOCbctY5pUHX5HH2gDIsYAX7TNZYhkqeS8YF4GIYIL
EmKSzA9Noc92ZD5dQXEwNFjixeKO6OYHv96kM6bKRccX
-----END ENCRYPTED PRIVATE KEY-----"""


class ErrorCtrlP(Exception):
    """Error con mensaje pensado para mostrarse al usuario."""


# =========================================================================
#  Utilidades
# =========================================================================
def ahora():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hoy_iso():
    return dt.date.today().isoformat()


def nuevo_id():
    return uuid.uuid4().hex[:16]


def mayus(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().upper()


def sin_acentos(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def clave_texto(s):
    """Normaliza para comparar textos: mayusculas, sin acentos, espacios simples."""
    return re.sub(r"\s+", " ", sin_acentos(s)).strip().upper()


def norm_codigo(c):
    if c is None:
        return ""
    if isinstance(c, float) and c.is_integer():
        c = int(c)
    return str(c).strip().rstrip(".").strip()


def a_numero(v):
    """Convierte celdas de Excel a numero (acepta textos con comas). None si no es numero."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("US$", "").replace("$", "").replace(" ", "")
    if not s:
        return None
    if re.fullmatch(r"-?[\d,]*\.?\d+", s):
        try:
            return float(s.replace(",", ""))
        except ValueError:
            return None
    return None


def fecha_iso(d):
    if isinstance(d, dt.date):
        return d.isoformat()
    return str(d)


def iso_a_fecha(s):
    return dt.date.fromisoformat(s)


def fecha_txt(iso):
    """2026-10-08 -> 08/10/2026"""
    try:
        d = iso_a_fecha(iso)
        return d.strftime("%d/%m/%Y")
    except Exception:
        return iso or ""


def txt_a_iso(txt):
    """08/10/2026 -> 2026-10-08 (acepta tambien 8-10-26 y ISO)."""
    t = (txt or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        dt.date.fromisoformat(t)
        return t
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", t)
    if not m:
        raise ErrorCtrlP(f"Fecha no válida: «{txt}». Usá el formato dd/mm/aaaa.")
    d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    try:
        return dt.date(y, mth, d).isoformat()
    except ValueError:
        raise ErrorCtrlP(f"Fecha no válida: «{txt}».")


def dia_anterior(iso):
    return (iso_a_fecha(iso) - dt.timedelta(days=1)).isoformat()


def r6(x):
    return round(float(x or 0.0), 6)


# =========================================================================
#  Usuarios
# =========================================================================
def nombre_usuario(nombre, empresa):
    n, e = mayus(nombre), mayus(empresa)
    if not n:
        raise ErrorCtrlP("Escribí tu nombre.")
    if not e:
        raise ErrorCtrlP("Escribí tu empresa.")
    return f"{n} - {e}"


def _huella(clave, sal_b64, it):
    return hashlib.pbkdf2_hmac("sha256", (clave or "").encode("utf-8"), base64.b64decode(sal_b64), it)


def _rec_valido(rec):
    return isinstance(rec, dict) and all(k in rec for k in ("sal", "huella", "iter"))


def usuarios_registrados(extra=None):
    """Usuarios con contrasena conocidos en esta PC (+ los de un proyecto si se pasan)."""
    regs = {k: v for k, v in leer_config().get("usuarios", {}).items() if _rec_valido(v)}
    for k, v in (extra or {}).items():
        if _rec_valido(v) and (k not in regs or (v.get("modificado", "") > regs[k].get("modificado", ""))):
            regs[k] = v
    regs.pop(ADMIN, None)
    return regs


def es_admin(u):
    return u == ADMIN


def requiere_clave(nombre, empresa, extra=None):
    try:
        u = nombre_usuario(nombre, empresa)
    except ErrorCtrlP:
        return False
    return u == ADMIN or u in usuarios_registrados(extra)


def verificar_usuario(nombre, empresa, clave="", extra=None):
    """Devuelve el nombre de usuario completo o lanza ErrorCtrlP."""
    u = nombre_usuario(nombre, empresa)
    if u == ADMIN:
        sal, huella, it = ADMIN_HUELLA
        if not hmac.compare_digest(_huella(clave, sal, it), base64.b64decode(huella)):
            raise ErrorCtrlP("Contraseña incorrecta.")
        return u
    rec = usuarios_registrados(extra).get(u)
    if rec and not hmac.compare_digest(_huella(clave, rec["sal"], rec["iter"]), base64.b64decode(rec["huella"])):
        raise ErrorCtrlP("Contraseña incorrecta.")
    return u


def _cifrar_para_admin(clave):
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        pub = serialization.load_pem_public_key(ADMIN_PUBLICA)
        c = pub.encrypt(clave.encode("utf-8"), padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                                            algorithm=hashes.SHA256(), label=None))
        return base64.b64encode(c).decode()
    except Exception:
        return ""


def llave_admin(clave):
    """Clave privada del administrador (para ver contrasenas). None si no se puede abrir."""
    try:
        from cryptography.hazmat.primitives import serialization
        return serialization.load_pem_private_key(ADMIN_PRIVADA, (clave or "").encode("utf-8"))
    except Exception:
        return None


def ver_clave(llave, cifrada):
    if not llave or not cifrada:
        return ""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        return llave.decrypt(base64.b64decode(cifrada), padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)).decode("utf-8")
    except Exception:
        return ""


def _nuevo_rec(clave):
    sal = base64.b64encode(os.urandom(16)).decode()
    it = 200000
    return {"sal": sal, "huella": base64.b64encode(_huella(clave, sal, it)).decode(), "iter": it,
            "cifrada": _cifrar_para_admin(clave), "creado": ahora(), "modificado": ahora()}


def _validar_clave(clave):
    if len(clave or "") < 4:
        raise ErrorCtrlP("La contraseña debe tener al menos 4 caracteres.")


def registrar_usuario(nombre, empresa, clave, extra=None):
    """Crea un usuario con contrasena (los nombres no se repiten)."""
    u = nombre_usuario(nombre, empresa)
    _validar_clave(clave)
    if u == ADMIN or u in usuarios_registrados(extra):
        raise ErrorCtrlP(f"Ya existe el usuario {u}. Elegí otro nombre.")
    cfg = leer_config()
    cfg.setdefault("usuarios", {})[u] = _nuevo_rec(clave)
    guardar_config(cfg)
    return u


def cambiar_clave(u, nueva, extra=None):
    """Cambia la contrasena de un usuario registrado (no del administrador)."""
    if u == ADMIN:
        raise ErrorCtrlP("La contraseña del administrador viene incluida en el programa.")
    _validar_clave(nueva)
    cfg = leer_config()
    rec = _nuevo_rec(nueva)
    ant = usuarios_registrados(extra).get(u)
    if ant:
        rec["creado"] = ant.get("creado", rec["creado"])
    cfg.setdefault("usuarios", {})[u] = rec
    guardar_config(cfg)
    return rec


def quitar_clave(u):
    """El usuario vuelve a entrar solo con su nombre (lo hace el administrador)."""
    cfg = leer_config()
    cfg.get("usuarios", {}).pop(u, None)
    borrados = cfg.setdefault("usuarios_quitados", {})
    borrados[u] = ahora()
    guardar_config(cfg)


# =========================================================================
#  Configuracion local (ultimo usuario, apariencia, recientes)
# =========================================================================
def carpeta_config():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    p = os.path.join(base, "Ctrl-P")
    os.makedirs(p, exist_ok=True)
    return p


def leer_config():
    try:
        with open(os.path.join(carpeta_config(), "config.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar_config(cfg):
    try:
        ruta = os.path.join(carpeta_config(), "config.json")
        with open(ruta + ".tmp", "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(ruta + ".tmp", ruta)
    except Exception:
        pass


def config_poner(**kw):
    """Actualiza solo esas claves de la configuracion (sin pisar usuarios ni recientes)."""
    cfg = leer_config()
    cfg.update(kw)
    guardar_config(cfg)
    return cfg


def agregar_reciente(ruta, nombre):
    cfg = leer_config()
    rec = [r for r in cfg.get("recientes", []) if os.path.normcase(r.get("ruta", "")) != os.path.normcase(ruta)]
    rec.insert(0, {"ruta": ruta, "nombre": nombre, "abierto": ahora()})
    cfg["recientes"] = rec[:8]
    guardar_config(cfg)


# =========================================================================
#  Esquema
# =========================================================================
SQL_ESQUEMA = """
CREATE TABLE IF NOT EXISTS meta(clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS versiones(num INTEGER PRIMARY KEY, fecha TEXT, archivo TEXT, usuario TEXT, total REAL);
CREATE TABLE IF NOT EXISTS items(
    id TEXT PRIMARY KEY, orden INTEGER, tipo TEXT, nivel INTEGER, padre TEXT,
    codigo TEXT, descripcion TEXT, unidad TEXT, cantidad REAL, pu REAL, total REAL,
    vigente INTEGER DEFAULT 1, fila_excel INTEGER);
CREATE TABLE IF NOT EXISTS edificios(id TEXT PRIMARY KEY, nombre TEXT, es_area INTEGER, orden INTEGER);
CREATE TABLE IF NOT EXISTS niveles(id TEXT PRIMARY KEY, edificio TEXT, nombre TEXT, orden INTEGER);
CREATE TABLE IF NOT EXISTS contractual(item TEXT, nivel TEXT, cantidad REAL, PRIMARY KEY(item, nivel));
CREATE TABLE IF NOT EXISTS ubic_fija(item TEXT PRIMARY KEY, nivel TEXT);
CREATE TABLE IF NOT EXISTS avances(
    id TEXT PRIMARY KEY, item TEXT, nivel TEXT, fecha TEXT, cantidad REAL, obs TEXT,
    usuario TEXT, creado TEXT, modificado TEXT, mod_usuario TEXT, origen TEXT,
    hito TEXT DEFAULT '', tramo TEXT DEFAULT '', marca TEXT DEFAULT '', equipo TEXT DEFAULT '',
    UNIQUE(item, nivel, fecha, equipo, tramo, hito, marca));
CREATE INDEX IF NOT EXISTS ix_av_fecha ON avances(fecha);
CREATE TABLE IF NOT EXISTS usuarios(nombre TEXT PRIMARY KEY, datos TEXT);
CREATE TABLE IF NOT EXISTS detalle(item TEXT PRIMARY KEY, tramos INTEGER DEFAULT 0, hitos INTEGER DEFAULT 0,
    hitos_bloq INTEGER DEFAULT 0, equipos INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS equipos(id TEXT PRIMARY KEY, item TEXT, nivel TEXT, nombre TEXT, contractual REAL,
    orden INTEGER, creado TEXT, usuario TEXT);
CREATE TABLE IF NOT EXISTS hitos(id TEXT PRIMARY KEY, item TEXT, orden INTEGER, nombre TEXT, pct REAL,
    tipo TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS tipo_cant(item TEXT, nivel TEXT, tipo TEXT, cantidad REAL, PRIMARY KEY(item, nivel, tipo));
CREATE TABLE IF NOT EXISTS tramos(id TEXT PRIMARY KEY, item TEXT, nivel TEXT, nombre TEXT, contractual REAL,
    plano TEXT, geom TEXT, orden INTEGER, creado TEXT, usuario TEXT, equipo TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS planos(id TEXT PRIMARY KEY, nivel TEXT, nombre TEXT, tipo TEXT, datos BLOB,
    ancho INTEGER, alto INTEGER, escala REAL, unidad TEXT, creado TEXT, usuario TEXT, orden INTEGER,
    alcance TEXT DEFAULT 'nivel', nombre_alcance TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS marcas(id TEXT PRIMARY KEY, plano TEXT, item TEXT, nivel TEXT, hito TEXT, tramo TEXT,
    tipo TEXT, geom TEXT, medida REAL, factor REAL, altura TEXT, nota TEXT, fecha TEXT, cantidad REAL,
    anulada INTEGER DEFAULT 0, usuario TEXT, creado TEXT, equipo TEXT DEFAULT '', ref TEXT DEFAULT '',
    visual INTEGER DEFAULT 0, huecos TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS plano_ubic(plano TEXT, nivel TEXT, PRIMARY KEY(plano, nivel));
CREATE TABLE IF NOT EXISTS hojas(id TEXT PRIMARY KEY, plano TEXT, item TEXT, creado TEXT, usuario TEXT,
    UNIQUE(plano, item));
CREATE TABLE IF NOT EXISTS estilos(item TEXT PRIMARY KEY, datos TEXT);
CREATE TABLE IF NOT EXISTS historial(
    id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, fecha TEXT, usuario TEXT, version TEXT,
    que TEXT, actividad TEXT, ubicacion TEXT, anterior TEXT, nuevo TEXT, exportado INTEGER DEFAULT 0);
"""


# =========================================================================
#  Proyecto
# =========================================================================
ACUM = "ACUM"   # ref de las marcas hechas con «Marcar por acumulado»


NIVEL_UNICO = "ÚNICO"          # nivel interno de un area sin nivel
NOMBRE_GENERAL = "(GENERAL)"   # como se muestra ese nivel cuando el area tiene tramos


def nombre_nivel(e, n):
    """Nombre visible de un nivel: en un area con tramos, la ubicacion general se llama «(GENERAL)»."""
    if e["es_area"] and n["nombre"] == NIVEL_UNICO:
        return NOMBRE_GENERAL
    return n["nombre"]


class Proyecto:
    """Proyecto abierto. Trabaja sobre una copia de la base en una carpeta temporal
    y guarda el .ctrlp (ZIP con la base) cada vez que se llama a guardar()."""

    # ---- revision (para deshacer): cada cambio que marca el proyecto como sucio sube la revision
    @property
    def sucio(self):
        return self.__dict__.get("_sucio", False)

    @sucio.setter
    def sucio(self, v):
        if v:
            self.rev = self.__dict__.get("rev", 0) + 1
        self._sucio = v

    rev = 0
    TABLAS_DESHACER = ("avances", "marcas", "hojas", "tramos", "plano_ubic")

    def instantanea(self, datos_de=()):
        """Copia de lo que tocan los planos, para deshacer. datos_de: planos cuya imagen hay que guardar (al eliminar)."""
        snap = {"rev": self.__dict__.get("rev", 0), "tablas": {}, "datos": {}}
        for tb in self.TABLAS_DESHACER:
            snap["tablas"][tb] = [dict(r) for r in self.con.execute(f"SELECT * FROM {tb}")]
        cols = [c[1] for c in self.con.execute("PRAGMA table_info(planos)") if c[1] != "datos"]
        snap["planos"] = {r["id"]: dict(r) for r in self.con.execute(f"SELECT {', '.join(cols)} FROM planos")}
        for pid in datos_de or ():
            r = self.con.execute("SELECT datos FROM planos WHERE id=?", (pid,)).fetchone()
            if r:
                snap["datos"][pid] = r[0]
        return snap

    def restaurar(self, snap, descripcion=""):
        for tb, filas in snap["tablas"].items():
            self.con.execute(f"DELETE FROM {tb}")
            for f in filas:
                self.con.execute(f"INSERT INTO {tb}({', '.join(f)}) VALUES({', '.join('?' * len(f))})", list(f.values()))
        actuales = {r[0] for r in self.con.execute("SELECT id FROM planos")}
        for pid in actuales - set(snap["planos"]):
            self.con.execute("DELETE FROM planos WHERE id=?", (pid,))
        for pid, f in snap["planos"].items():
            if pid in actuales:
                self.con.execute(f"UPDATE planos SET {', '.join(k + '=?' for k in f if k != 'id')} WHERE id=?",
                                 [v for k, v in f.items() if k != "id"] + [pid])
            elif pid in snap["datos"]:
                g = dict(f, datos=snap["datos"][pid])
                self.con.execute(f"INSERT INTO planos({', '.join(g)}) VALUES({', '.join('?' * len(g))})", list(g.values()))
        self.registrar("Deshacer", "", "", descripcion, "")
        self._cache = None
        self.sucio = True
        self.rev = snap["rev"]

    def __init__(self, ruta, usuario, version_trabajo="", _crear=False):
        self.ruta = os.path.abspath(ruta)
        self.usuario = usuario
        self.version_trabajo = version_trabajo
        self.tmp = tempfile.mkdtemp(prefix="ctrlp_")
        self.db_path = os.path.join(self.tmp, "proyecto.db")
        if not _crear:
            self._extraer(self.ruta, self.db_path)
        self.con = sqlite3.connect(self.db_path)
        self.con.row_factory = sqlite3.Row
        self._migrar()
        self.con.executescript(SQL_ESQUEMA)
        self.con.execute("INSERT OR IGNORE INTO plano_ubic SELECT id, nivel FROM planos")
        # hojas de marcado de versiones anteriores (una por plano y actividad ya marcada)
        for r in self.con.execute("SELECT plano, item, MIN(creado), usuario FROM marcas GROUP BY plano, item").fetchall():
            self.con.execute("INSERT OR IGNORE INTO hojas VALUES(?,?,?,?,?)", (nuevo_id(), r[0], r[1], r[2], r[3]))
        self.con.execute("UPDATE planos SET alcance='nivel' WHERE alcance IS NULL OR alcance='' OR alcance='especifico'")
        for r in self.con.execute("SELECT plano, COUNT(*) FROM plano_ubic GROUP BY plano HAVING COUNT(*) > 1").fetchall():
            self.con.execute("UPDATE planos SET alcance='general' WHERE id=? AND alcance='nivel'", (r[0],))
        if _crear:
            self.set_meta("creado", ahora())
        if self.get_meta("esquema", "1") != str(ESQUEMA):
            self.set_meta("esquema", str(ESQUEMA))
        self.sucio = False
        self._cache = None

    def _migrar(self):
        """Proyectos de versiones anteriores: agrega columnas y rehace la tabla de avances."""
        def cols(t):
            return [r[1] for r in self.con.execute(f"PRAGMA table_info({t})")]
        av = cols("avances")
        if av and "equipo" not in av:
            comunes = [c for c in ("id", "item", "nivel", "fecha", "cantidad", "obs", "usuario", "creado", "modificado",
                                   "mod_usuario", "origen", "hito", "tramo", "marca") if c in av]
            lista = ",".join(comunes)
            self.con.executescript(f"""
                ALTER TABLE avances RENAME TO avances_vieja;
                DROP INDEX IF EXISTS ix_av_fecha;
                CREATE TABLE avances(
                    id TEXT PRIMARY KEY, item TEXT, nivel TEXT, fecha TEXT, cantidad REAL, obs TEXT,
                    usuario TEXT, creado TEXT, modificado TEXT, mod_usuario TEXT, origen TEXT,
                    hito TEXT DEFAULT '', tramo TEXT DEFAULT '', marca TEXT DEFAULT '', equipo TEXT DEFAULT '',
                    UNIQUE(item, nivel, fecha, equipo, tramo, hito, marca));
                INSERT INTO avances({lista}) SELECT {lista} FROM avances_vieja;
                DROP TABLE avances_vieja;
            """)
        for tabla, col, tipo in (("detalle", "equipos", "INTEGER DEFAULT 0"), ("tramos", "equipo", "TEXT DEFAULT ''"),
                                 ("marcas", "equipo", "TEXT DEFAULT ''"), ("marcas", "ref", "TEXT DEFAULT ''"),
                                 ("marcas", "visual", "INTEGER DEFAULT 0"), ("planos", "alcance", "TEXT DEFAULT 'nivel'"),
                                 ("planos", "nombre_alcance", "TEXT DEFAULT ''"), ("marcas", "huecos", "TEXT DEFAULT ''"),
                                 ("hitos", "tipo", "TEXT DEFAULT ''")):
            c = cols(tabla)
            if c and col not in c:
                self.con.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")
        self.con.commit()

    # ---------------------------------------------------------------- archivo
    @staticmethod
    def _extraer(ruta, destino):
        try:
            with zipfile.ZipFile(ruta) as z:
                if "proyecto.db" not in z.namelist():
                    raise ErrorCtrlP("El archivo no es un proyecto de Ctrl-P válido.")
                with z.open("proyecto.db") as src, open(destino, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        except zipfile.BadZipFile:
            raise ErrorCtrlP("El archivo está dañado o no es un proyecto de Ctrl-P.")
        except FileNotFoundError:
            raise ErrorCtrlP(f"No se encontró el archivo:\n{ruta}")

    def _escribir_zip(self, destino):
        self.con.commit()
        tmp_zip = destino + ".guardando"
        # copia consistente de la base
        copia = os.path.join(self.tmp, "export.db")
        if os.path.exists(copia):
            os.remove(copia)
        bk = sqlite3.connect(copia)
        self.con.backup(bk)
        bk.close()
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.write(copia, "proyecto.db")
            z.writestr("info.json", json.dumps({
                "app": APP, "esquema": ESQUEMA, "proyecto": self.get_meta("nombre", ""),
                "guardado": ahora(), "usuario": self.usuario}, ensure_ascii=False))
        os.remove(copia)
        os.replace(tmp_zip, destino)

    def guardar_en(self, nueva):
        """Pasa a trabajar sobre otro archivo (el master): lo escribe completo y desde ahi se guarda siempre ahi.
        El historial en Excel se copia junto al nuevo archivo si alli no hay uno."""
        nueva = os.path.abspath(nueva if nueva.lower().endswith(EXT) else nueva + EXT)
        hist_ant = self.ruta_historial()
        anterior = self.ruta
        self.ruta = nueva
        try:
            self._escribir_zip(nueva)
        except Exception:
            self.ruta = anterior
            raise
        if os.path.isfile(hist_ant) and not os.path.exists(self.ruta_historial()):
            try:
                shutil.copy2(hist_ant, self.ruta_historial())
            except OSError:
                pass
        self.registrar("Proyecto guardado como master", "", "", anterior, nueva)
        agregar_reciente(self.ruta, self.get_meta("nombre"))
        return self.guardar()

    def guardar(self):
        """Guarda el .ctrlp y agrega al historial en Excel. Devuelve un aviso (o "")."""
        self._escribir_zip(self.ruta)
        self.sucio = False
        return self.volcar_historial_excel()

    def cerrar(self):
        try:
            self.con.close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------------------------------------------------------------- crear / abrir
    @classmethod
    def crear(cls, ruta, usuario, analisis, datos):
        """Crea un proyecto nuevo a partir del analisis de importacion."""
        if not ruta.lower().endswith(EXT):
            ruta += EXT
        p = cls(ruta, usuario, version_trabajo="", _crear=True)
        for k in ("nombre", "propietario", "contratista", "moneda"):
            p.set_meta(k, datos.get(k, ""))
        p.set_meta("solo_agregar", "0")
        p.set_meta("version_presupuesto", "1")
        p._insertar_items(analisis["items"])
        total = sum(i["total"] for i in analisis["items"] if i["tipo"] == "P")
        p.con.execute("INSERT INTO versiones VALUES(1,?,?,?,?)",
                      (ahora(), os.path.basename(analisis.get("archivo", "")), usuario, total))
        p.registrar("Proyecto creado", "", "", "", f"Presupuesto V1 · {len(analisis['items'])} filas")
        p.version_trabajo = "creación"
        p.guardar()
        agregar_reciente(p.ruta, p.get_meta("nombre"))
        return p

    @classmethod
    def abrir(cls, ruta, usuario, decidir_copia=None):
        """Abre un .ctrlp haciendo la copia de seguridad de la sesion.
        decidir_copia() -> True (nueva copia) / False (seguir con la de hoy); se llama
        solo si ya hay una copia de hoy."""
        ruta = os.path.abspath(ruta)
        if not os.path.isfile(ruta):
            raise ErrorCtrlP(f"No se encontró el archivo:\n{ruta}")
        version = cls._copia_sesion(ruta, decidir_copia)
        p = cls(ruta, usuario, version_trabajo=version)
        agregar_reciente(p.ruta, p.get_meta("nombre"))
        return p

    @staticmethod
    def carpeta_respaldos(ruta):
        base, _ = os.path.splitext(os.path.abspath(ruta))
        return base + " - respaldos"

    @classmethod
    def _copia_sesion(cls, ruta, decidir_copia):
        carpeta = cls.carpeta_respaldos(ruta)
        os.makedirs(carpeta, exist_ok=True)
        stem = os.path.splitext(os.path.basename(ruta))[0]
        hoy = hoy_iso()
        existentes = sorted(f for f in os.listdir(carpeta) if f.startswith(f"{stem}_{hoy}_") and f.endswith(EXT))
        if existentes:
            nueva = decidir_copia() if decidir_copia else False
            if not nueva:
                return os.path.splitext(existentes[-1])[0][len(stem) + 1:]
            n = max(int(re.search(r"_(\d+)\.ctrlp$", f).group(1)) for f in existentes) + 1
        else:
            n = 1
        etiqueta = f"{hoy}_{n:02d}"
        shutil.copy2(ruta, os.path.join(carpeta, f"{stem}_{etiqueta}{EXT}"))
        return etiqueta

    # ---------------------------------------------------------------- meta
    def get_meta(self, k, defecto=""):
        r = self.con.execute("SELECT valor FROM meta WHERE clave=?", (k,)).fetchone()
        return r[0] if r else defecto

    def set_meta(self, k, v):
        self.con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, str(v)))
        self.sucio = True

    @property
    def nombre(self):
        return self.get_meta("nombre", "PROYECTO")

    @property
    def solo_agregar(self):
        return self.get_meta("solo_agregar", "0") == "1"

    @property
    def version_presupuesto(self):
        return int(self.get_meta("version_presupuesto", "1") or 1)

    def cambiar_datos(self, datos):
        for k in ("nombre", "propietario", "contratista", "moneda"):
            if k in datos:
                ant = self.get_meta(k)
                nuevo = datos[k].strip() if k != "nombre" else mayus(datos[k])
                if nuevo != ant:
                    self.set_meta(k, nuevo)
                    self.registrar(f"Dato del proyecto: {k}", "", "", ant, nuevo)

    # ---------------------------------------------------------------- historial
    def registrar(self, que, actividad="", ubicacion="", anterior="", nuevo="", usuario=None, fecha=None,
                  version=None, uid=None):
        self.con.execute(
            "INSERT INTO historial(uid,fecha,usuario,version,que,actividad,ubicacion,anterior,nuevo,exportado)"
            " VALUES(?,?,?,?,?,?,?,?,?,0)",
            (uid or nuevo_id(), fecha or ahora(), usuario or self.usuario,
             version if version is not None else self.version_trabajo,
             que, actividad, ubicacion, "" if anterior is None else str(anterior),
             "" if nuevo is None else str(nuevo)))
        self.sucio = True

    def ruta_historial(self):
        base, _ = os.path.splitext(self.ruta)
        return base + " - historial.xlsx"

    def volcar_historial_excel(self):
        filas = self.con.execute("SELECT * FROM historial WHERE exportado=0 ORDER BY id").fetchall()
        if not filas:
            return ""
        ruta = self.ruta_historial()
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            if os.path.exists(ruta):
                wb = openpyxl.load_workbook(ruta)
                ws = wb.active
            else:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Historial"
                enc = ["Fecha y hora", "Usuario", "Versión", "Qué se modificó", "Actividad", "Ubicación",
                       "Valor anterior", "Valor nuevo"]
                ws.append(enc)
                for c in ws[1]:
                    c.font = Font(bold=True, color="FFFFFF")
                    c.fill = PatternFill("solid", fgColor="4C6F9F")
                    c.alignment = Alignment(vertical="center")
                for col, w in zip("ABCDEFGH", (19, 26, 18, 34, 60, 24, 18, 18)):
                    ws.column_dimensions[col].width = w
                ws.freeze_panes = "A2"
                ws.auto_filter.ref = "A1:H1"
            for f in filas:
                ws.append([f["fecha"], f["usuario"], f["version"], f["que"], f["actividad"], f["ubicacion"],
                           f["anterior"], f["nuevo"]])
            ws.auto_filter.ref = f"A1:H{ws.max_row}"
            wb.save(ruta)
        except PermissionError:
            return ("El historial en Excel está abierto en otro programa; los cambios se agregarán "
                    "la próxima vez que guardes.")
        except Exception as e:
            return f"No se pudo actualizar el historial en Excel: {e}"
        self.con.execute("UPDATE historial SET exportado=1 WHERE exportado=0")
        self.con.commit()
        self._escribir_zip(self.ruta)
        return ""

    # ---------------------------------------------------------------- presupuesto
    def _insertar_items(self, items):
        for it in items:
            self.con.execute(
                "INSERT INTO items(id,orden,tipo,nivel,padre,codigo,descripcion,unidad,cantidad,pu,total,vigente,fila_excel)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?)",
                (it["id"], it["orden"], it["tipo"], it["nivel"], it["padre"], it["codigo"], it["descripcion"],
                 it["unidad"], it["cantidad"], it["pu"], it["total"], it.get("fila")))
        self._cache = None
        self.sucio = True

    def items(self, solo_vigentes=False):
        q = "SELECT * FROM items" + (" WHERE vigente=1" if solo_vigentes else "") + " ORDER BY vigente DESC, orden"
        return [dict(r) for r in self.con.execute(q)]

    def item(self, iid):
        r = self.con.execute("SELECT * FROM items WHERE id=?", (iid,)).fetchone()
        return dict(r) if r else None

    def partidas(self):
        return [i for i in self.items() if i["tipo"] == "P"]

    def total_presupuesto(self):
        r = self.con.execute("SELECT SUM(total) FROM items WHERE tipo='P' AND vigente=1").fetchone()
        return float(r[0] or 0.0)

    def etiqueta_item(self, it):
        return f"{it['codigo']} {it['descripcion']}".strip()

    # ---------------------------------------------------------------- ubicaciones
    def edificios(self):
        return [dict(r) for r in self.con.execute("SELECT * FROM edificios ORDER BY es_area, orden, nombre")]

    def niveles_de(self, edificio_id):
        return [dict(r) for r in self.con.execute("SELECT * FROM niveles WHERE edificio=? ORDER BY orden",
                                                    (edificio_id,))]

    def area_simple(self, e, niveles=None):
        """Area sin nivel que es una sola ubicacion (sin subdivisiones)."""
        if not e["es_area"]:
            return False
        niveles = self.niveles_de(e["id"]) if niveles is None else niveles
        return not niveles or (len(niveles) == 1 and niveles[0]["nombre"] == NIVEL_UNICO)

    def ubicaciones(self):
        """Lista de ubicaciones en orden: dict(nivel, edificio, ed_nombre, nv_nombre, es_area, etiqueta).
        Un area exterior con subdivisiones (tramos) se maneja como un edificio: cada tramo es una ubicacion."""
        res = []
        for e in self.edificios():
            nvs = self.niveles_de(e["id"])
            simple = self.area_simple(e, nvs)
            for n in nvs:
                nn = nombre_nivel(e, n)
                et = e["nombre"] if simple else f"{e['nombre']} {nn}"
                res.append({"nivel": n["id"], "edificio": e["id"], "ed_nombre": e["nombre"],
                            "nv_nombre": "" if simple else nn, "es_area": simple,
                            "exterior": bool(e["es_area"]), "etiqueta": et})
        return res

    def etiqueta_ubicacion(self, nivel_id):
        for u in self.ubicaciones():
            if u["nivel"] == nivel_id:
                return u["etiqueta"]
        return "(ubicación eliminada)"

    def crear_edificio(self, nombre, niveles, es_area=False, tramos=None):
        nombre = mayus(nombre)
        if not nombre:
            raise ErrorCtrlP("Escribí el nombre.")
        if any(e["nombre"] == nombre for e in self.edificios()):
            raise ErrorCtrlP(f"Ya existe «{nombre}».")
        eid = nuevo_id()
        orden = len(self.edificios())
        self.con.execute("INSERT INTO edificios VALUES(?,?,?,?)", (eid, nombre, 1 if es_area else 0, orden))
        if es_area:
            niveles = [t for t in (tramos or []) if mayus(t)] or [NIVEL_UNICO]
            if any(mayus(t) in (NIVEL_UNICO, NOMBRE_GENERAL) for t in (tramos or [])):
                raise ErrorCtrlP(f"«{NOMBRE_GENERAL}» no se puede usar como nombre de tramo.")
        nombres = [mayus(n) for n in niveles if mayus(n)]
        if not nombres:
            raise ErrorCtrlP("Agregá al menos un nivel.")
        if len(set(nombres)) != len(nombres):
            raise ErrorCtrlP("Hay niveles con el mismo nombre.")
        for k, n in enumerate(nombres):
            self.con.execute("INSERT INTO niveles VALUES(?,?,?,?)", (nuevo_id(), eid, n, k))
        self.registrar("Ubicación creada", "", nombre, "",
                       ", ".join(nombres) if not es_area else
                       ("Área sin nivel" if nombres == [NIVEL_UNICO] else "Área con tramos: " + ", ".join(nombres)))
        return eid

    def agregar_subdivision(self, eid, nombre):
        """Agrega un tramo (subdivision) a un area exterior. Si el area todavia es una sola ubicacion sin uso,
        esa ubicacion pasa a ser el primer tramo; si ya tenia avance o contractual, queda como «(GENERAL)»."""
        e = self.con.execute("SELECT * FROM edificios WHERE id=?", (eid,)).fetchone()
        if e is None or not e["es_area"]:
            raise ErrorCtrlP("Los tramos se agregan a las áreas sin nivel.")
        nombre = mayus(nombre)
        if not nombre:
            raise ErrorCtrlP("Escribí el nombre del tramo.")
        if nombre in (NIVEL_UNICO, NOMBRE_GENERAL):
            raise ErrorCtrlP(f"«{nombre}» no se puede usar como nombre de tramo.")
        nvs = self.niveles_de(eid)
        if any(n["nombre"] == nombre for n in nvs):
            raise ErrorCtrlP(f"Ya existe el tramo «{nombre}» en {e['nombre']}.")
        unico = [n for n in nvs if n["nombre"] == NIVEL_UNICO]
        if len(nvs) == 1 and unico and not self._nivel_en_uso(unico[0]["id"]):
            self.con.execute("UPDATE niveles SET nombre=? WHERE id=?", (nombre, unico[0]["id"]))
            nid = unico[0]["id"]
        else:
            nid = nuevo_id()
            self.con.execute("INSERT INTO niveles VALUES(?,?,?,?)", (nid, eid, nombre, len(nvs)))
        self.registrar("Tramo agregado", "", f"{e['nombre']} {nombre}", "", nombre)
        self.sucio = True
        return nid

    def renombrar_edificio(self, eid, nombre):
        nombre = mayus(nombre)
        ant = self.con.execute("SELECT nombre FROM edificios WHERE id=?", (eid,)).fetchone()[0]
        if nombre == ant:
            return
        if any(e["nombre"] == nombre and e["id"] != eid for e in self.edificios()):
            raise ErrorCtrlP(f"Ya existe «{nombre}».")
        self.con.execute("UPDATE edificios SET nombre=? WHERE id=?", (nombre, eid))
        self.registrar("Ubicación renombrada", "", nombre, ant, nombre)

    def guardar_niveles(self, eid, nombres_por_id):
        """nombres_por_id: lista de (nivel_id o None, nombre) en el orden final."""
        e = self.con.execute("SELECT * FROM edificios WHERE id=?", (eid,)).fetchone()
        actuales = {n["id"]: n for n in self.niveles_de(eid)}
        finales = [(i, mayus(n)) for i, n in nombres_por_id if mayus(n)]
        if e["es_area"]:
            # area exterior: se reciben solo los tramos; la ubicacion general («ÚNICO») se conserva
            # si tiene avance o contractual, o si no queda ningun tramo
            gen = [n for n in actuales.values() if n["nombre"] == NIVEL_UNICO]
            otros = [(i, n) for i, n in finales if not (gen and i == gen[0]["id"])]
            if any(n in (NIVEL_UNICO, NOMBRE_GENERAL) for _, n in otros):
                raise ErrorCtrlP(f"«{NOMBRE_GENERAL}» no se puede usar como nombre de tramo.")
            if gen and (self._nivel_en_uso(gen[0]["id"]) or not otros):
                finales = [(gen[0]["id"], NIVEL_UNICO)] + otros
            else:
                finales = otros or [(None, NIVEL_UNICO)]
        if len({n for _, n in finales}) != len(finales):
            raise ErrorCtrlP("Hay niveles con el mismo nombre.")
        quedan = {i for i, _ in finales if i}
        for nid, n in actuales.items():
            if nid not in quedan and self._nivel_en_uso(nid):
                raise ErrorCtrlP(f"El nivel {n['nombre']} tiene avance o cantidades contractuales; no se puede quitar.")
        for nid, n in actuales.items():
            if nid not in quedan:
                self.con.execute("DELETE FROM niveles WHERE id=?", (nid,))
                self.registrar("Nivel eliminado", "", f"{e['nombre']} {n['nombre']}", n["nombre"], "")
        for k, (nid, n) in enumerate(finales):
            if nid and nid in actuales:
                if actuales[nid]["nombre"] != n:
                    self.registrar("Nivel renombrado", "", e["nombre"], actuales[nid]["nombre"], n)
                self.con.execute("UPDATE niveles SET nombre=?, orden=? WHERE id=?", (n, k, nid))
            else:
                self.con.execute("INSERT INTO niveles VALUES(?,?,?,?)", (nuevo_id(), eid, n, k))
                self.registrar("Nivel agregado", "", f"{e['nombre']} {n}", "", n)
        self.sucio = True

    def _nivel_en_uso(self, nid):
        a = self.con.execute("SELECT COUNT(*) FROM avances WHERE nivel=?", (nid,)).fetchone()[0]
        c = self.con.execute("SELECT COUNT(*) FROM contractual WHERE nivel=?", (nid,)).fetchone()[0]
        return a + c > 0

    def eliminar_edificio(self, eid):
        for n in self.niveles_de(eid):
            if self._nivel_en_uso(n["id"]):
                raise ErrorCtrlP("Esta ubicación tiene avance o cantidades contractuales; no se puede eliminar.")
        nombre = self.con.execute("SELECT nombre FROM edificios WHERE id=?", (eid,)).fetchone()[0]
        self.con.execute("DELETE FROM niveles WHERE edificio=?", (eid,))
        self.con.execute("DELETE FROM edificios WHERE id=?", (eid,))
        self.registrar("Ubicación eliminada", "", nombre, nombre, "")

    # ---------------------------------------------------------------- contractual
    def contractual_de(self, iid):
        return {r["nivel"]: r["cantidad"] for r in self.con.execute(
            "SELECT nivel, cantidad FROM contractual WHERE item=?", (iid,))}

    def todo_contractual(self):
        res = {}
        for r in self.con.execute("SELECT item, nivel, cantidad FROM contractual"):
            res.setdefault(r["item"], {})[r["nivel"]] = r["cantidad"]
        return res

    def set_contractual(self, iid, nivel, cantidad):
        """cantidad None = sin asignar."""
        ant = self.con.execute("SELECT cantidad FROM contractual WHERE item=? AND nivel=?", (iid, nivel)).fetchone()
        ant = ant[0] if ant else None
        if cantidad is not None and cantidad < 0:
            raise ErrorCtrlP("La cantidad contractual no puede ser negativa.")
        if (ant is None and cantidad is None) or (ant is not None and cantidad is not None and abs(ant - cantidad) < EPS):
            return False
        it = self.item(iid)
        if cantidad is None:
            self.con.execute("DELETE FROM contractual WHERE item=? AND nivel=?", (iid, nivel))
        else:
            self.con.execute("INSERT OR REPLACE INTO contractual VALUES(?,?,?)", (iid, nivel, float(cantidad)))
        self.registrar("Cantidad contractual", self.etiqueta_item(it), self.etiqueta_ubicacion(nivel),
                       "" if ant is None else f"{ant:,.2f}", "" if cantidad is None else f"{cantidad:,.2f}")
        self._cache = None
        return True

    def cant_tipos_de(self, iid):
        """Cantidad contractual de cada tipo de hito por ubicacion: {(nivel, tipo): cantidad}."""
        return {(r["nivel"], r["tipo"]): r["cantidad"]
                for r in self.con.execute("SELECT * FROM tipo_cant WHERE item=?", (iid,))}

    def set_cant_tipo(self, iid, nivel, tipo, cantidad):
        """Cantidad contractual de un tipo (ej. TABIQUE TIPO 1) en una ubicacion. None = sin asignar."""
        ant = self.cant_tipos_de(iid).get((nivel, tipo))
        if cantidad is not None and cantidad < 0:
            raise ErrorCtrlP("La cantidad no puede ser negativa.")
        if (ant is None and cantidad is None) or (ant is not None and cantidad is not None and abs(ant - cantidad) < EPS):
            return False
        if cantidad is None:
            self.con.execute("DELETE FROM tipo_cant WHERE item=? AND nivel=? AND tipo=?", (iid, nivel, tipo))
        else:
            self.con.execute("INSERT OR REPLACE INTO tipo_cant VALUES(?,?,?,?)", (iid, nivel, tipo, float(cantidad)))
        self.registrar(f"Cantidad contractual · {tipo}", self.etiqueta_item(self.item(iid)), self.etiqueta_ubicacion(nivel),
                       "" if ant is None else f"{ant:,.2f}", "" if cantidad is None else f"{cantidad:,.2f}")
        self._cache = None
        self.sucio = True
        return True

    def ubic_fija_de(self, iid):
        r = self.con.execute("SELECT nivel FROM ubic_fija WHERE item=?", (iid,)).fetchone()
        return r[0] if r else None

    def set_ubic_fija(self, iid, nivel):
        """Partida que en el presupuesto ya pertenece a una sola ubicacion (presupuesto separado)."""
        ant = self.ubic_fija_de(iid)
        if ant == nivel:
            return
        it = self.item(iid)
        if nivel is None:
            self.con.execute("DELETE FROM ubic_fija WHERE item=?", (iid,))
        else:
            otros = [r[0] for r in self.con.execute(
                "SELECT DISTINCT nivel FROM avances WHERE item=? AND nivel<>?", (iid, nivel))]
            if otros:
                raise ErrorCtrlP("La partida ya tiene avance en otras ubicaciones.")
            self.con.execute("INSERT OR REPLACE INTO ubic_fija VALUES(?,?)", (iid, nivel))
            self.con.execute("DELETE FROM contractual WHERE item=? AND nivel<>?", (iid, nivel))
            self.con.execute("INSERT OR REPLACE INTO contractual VALUES(?,?,?)", (iid, nivel, it["cantidad"]))
        self.registrar("Ubicación fija de la partida", self.etiqueta_item(it), "",
                       self.etiqueta_ubicacion(ant) if ant else "", self.etiqueta_ubicacion(nivel) if nivel else "")
        self._cache = None

    def sugerir_ubicaciones(self):
        """Partidas cuya descripcion menciona una ubicacion (para presupuestos separados).
        Devuelve lista de (item, nivel, etiqueta). El usuario debe confirmar."""
        ubs = self.ubicaciones()
        res = []
        for it in self.partidas():
            if self.ubic_fija_de(it["id"]):
                continue
            d = " " + clave_texto(it["descripcion"]) + " "
            candidatos = []
            for u in ubs:
                ed = clave_texto(u["ed_nombre"])
                if not re.search(rf"(?<![A-Z0-9]){re.escape(ed)}(?![A-Z0-9])", d):
                    continue
                if u["es_area"]:
                    candidatos.append(u)
                elif re.search(rf"(?<![A-Z0-9]){re.escape(clave_texto(u['nv_nombre']))}(?![A-Z0-9])", d):
                    candidatos.append(u)
            if len(candidatos) == 1:
                res.append((it, candidatos[0]["nivel"], candidatos[0]["etiqueta"]))
        return res

    def descuadres(self):
        """Partidas cuya suma contractual no coincide con la cantidad de la partida (o la suma de sus
        equipos con el contractual de su nivel)."""
        cont = self.todo_contractual()
        eqs, _ = self.estructura_topes()
        res = []
        for it in self.partidas():
            if not it["vigente"]:
                continue
            if it["id"] in cont:
                s = sum(cont[it["id"]].values())
                if abs(s - (it["cantidad"] or 0)) > 0.005:
                    res.append((it, s))
                    continue
            por_nv = {}
            for nv, c in eqs.get(it["id"], {}).values():
                if c is not None:
                    por_nv[nv] = por_nv.get(nv, 0.0) + c
            base = cont.get(it["id"], {})
            if any(abs(v - base[nv]) > 0.005 for nv, v in por_nv.items() if nv in base):
                res.append((it, sum(base.values())))
        return res

    # ---------------------------------------------------------------- usuarios del proyecto
    def usuarios_proyecto(self):
        res = {}
        for r in self.con.execute("SELECT nombre, datos FROM usuarios"):
            try:
                res[r["nombre"]] = json.loads(r["datos"])
            except Exception:
                pass
        return res

    def sincronizar_usuarios(self):
        """Une los usuarios con contrasena de esta PC y los del proyecto (en ambos sentidos)."""
        cfg = leer_config()
        quitados = cfg.get("usuarios_quitados", {})
        loc = {k: v for k, v in cfg.get("usuarios", {}).items() if _rec_valido(v)}
        pro = {k: v for k, v in self.usuarios_proyecto().items() if _rec_valido(v) and k != ADMIN}
        cambio_cfg = False
        for k, v in pro.items():
            if k in quitados and quitados[k] >= v.get("modificado", ""):
                self.con.execute("DELETE FROM usuarios WHERE nombre=?", (k,))
                self.sucio = True
                continue
            if k not in loc or v.get("modificado", "") > loc[k].get("modificado", ""):
                loc[k] = v
                cambio_cfg = True
        for k, v in loc.items():
            if k not in pro or v.get("modificado", "") > pro[k].get("modificado", ""):
                self.con.execute("INSERT OR REPLACE INTO usuarios VALUES(?,?)", (k, json.dumps(v)))
                self.sucio = True
        if cambio_cfg:
            cfg["usuarios"] = loc
            guardar_config(cfg)

    # ---------------------------------------------------------------- detalles de la actividad
    def detalle_de(self, iid):
        r = self.con.execute("SELECT * FROM detalle WHERE item=?", (iid,)).fetchone()
        if r:
            d = dict(r)
            d["equipos"] = d.get("equipos") or 0
            return d
        return {"item": iid, "tramos": 0, "hitos": 0, "hitos_bloq": 0, "equipos": 0}

    def _set_detalle(self, iid, **kw):
        d = self.detalle_de(iid)
        d.update(kw)
        self.con.execute("INSERT OR REPLACE INTO detalle(item,tramos,hitos,hitos_bloq,equipos) VALUES(?,?,?,?,?)",
                         (iid, int(d["tramos"]), int(d["hitos"]), int(d["hitos_bloq"]), int(d["equipos"])))
        self._cache = None
        self.sucio = True

    def hitos_de(self, iid):
        if not self.detalle_de(iid)["hitos"]:
            return []
        return [dict(r) for r in self.con.execute("SELECT * FROM hitos WHERE item=? ORDER BY orden", (iid,))]

    def tramos_de(self, iid, nivel=None, equipo=None):
        if not self.detalle_de(iid)["tramos"]:
            return []
        q, a = "SELECT * FROM tramos WHERE item=?", [iid]
        if nivel:
            q += " AND nivel=?"
            a.append(nivel)
        if equipo is not None:
            q += " AND COALESCE(equipo,'')=?"
            a.append(equipo or "")
        res = [dict(r) for r in self.con.execute(q + " ORDER BY nivel, orden, nombre", a)]
        for t in res:
            t["equipo"] = t.get("equipo") or ""
        return res

    # ---- equipos (independientes en cada partida)
    def equipos_de(self, iid, nivel=None):
        if not self.detalle_de(iid)["equipos"]:
            return []
        q, a = "SELECT * FROM equipos WHERE item=?", [iid]
        if nivel:
            q += " AND nivel=?"
            a.append(nivel)
        return [dict(r) for r in self.con.execute(q + " ORDER BY nivel, orden, nombre", a)]

    def equipo(self, eid):
        r = self.con.execute("SELECT * FROM equipos WHERE id=?", (eid,)).fetchone()
        return dict(r) if r else None

    def nombre_equipo(self, eid):
        r = self.con.execute("SELECT nombre FROM equipos WHERE id=?", (eid,)).fetchone()
        return r[0] if r else ""

    def activar_equipos(self, iid, si):
        d = self.detalle_de(iid)
        if bool(d["equipos"]) == bool(si):
            return False
        if not si and self._avance_con(iid, "equipo"):
            raise ErrorCtrlP("Esta partida ya tiene avance registrado por equipos; no se puede quitar la opción.")
        self._set_detalle(iid, equipos=1 if si else 0)
        self.registrar("Más detalles: desglose por equipos", self.etiqueta_item(self.item(iid)), "",
                       "no" if si else "sí", "sí" if si else "no")
        return True

    def crear_equipo(self, iid, nivel, nombre, contractual=None):
        nombre = mayus(nombre)
        if not nombre:
            raise ErrorCtrlP("Escribí el nombre del equipo.")
        if any(e["nombre"] == nombre for e in self.equipos_de(iid, nivel)):
            raise ErrorCtrlP(f"Ya existe el equipo «{nombre}» en esta ubicación.")
        if contractual is not None and contractual < 0:
            raise ErrorCtrlP("La cantidad no puede ser negativa.")
        if not self.detalle_de(iid)["equipos"]:
            self._set_detalle(iid, equipos=1)
        eid = nuevo_id()
        orden = self.con.execute("SELECT COUNT(*) FROM equipos WHERE item=? AND nivel=?", (iid, nivel)).fetchone()[0]
        self.con.execute("INSERT INTO equipos VALUES(?,?,?,?,?,?,?,?)",
                         (eid, iid, nivel, nombre, contractual, orden, ahora(), self.usuario))
        self.registrar("Equipo creado", self.etiqueta_item(self.item(iid)), self.etiqueta_ubicacion(nivel), "",
                       nombre + (f" · {contractual:,.2f}" if contractual else ""))
        self._cache = None
        self.sucio = True
        return eid

    def editar_equipo(self, eid, nombre=None, contractual="igual"):
        e = self.equipo(eid)
        it = self.item(e["item"])
        ub = self.etiqueta_ubicacion(e["nivel"])
        if nombre is not None:
            nombre = mayus(nombre)
            if not nombre:
                raise ErrorCtrlP("Escribí el nombre del equipo.")
            if nombre != e["nombre"]:
                if any(x["nombre"] == nombre and x["id"] != eid for x in self.equipos_de(e["item"], e["nivel"])):
                    raise ErrorCtrlP(f"Ya existe el equipo «{nombre}» en esta ubicación.")
                self.con.execute("UPDATE equipos SET nombre=? WHERE id=?", (nombre, eid))
                self.registrar("Equipo renombrado", self.etiqueta_item(it), ub, e["nombre"], nombre)
        if contractual != "igual":
            if contractual is not None and contractual < 0:
                raise ErrorCtrlP("La cantidad no puede ser negativa.")
            a = e["contractual"]
            if (a is None) != (contractual is None) or (a is not None and abs(a - contractual) > EPS):
                self.con.execute("UPDATE equipos SET contractual=? WHERE id=?", (contractual, eid))
                self.registrar("Cantidad del equipo", self.etiqueta_item(it), ub,
                               "" if a is None else f"{e['nombre']}: {a:,.2f}",
                               "" if contractual is None else f"{e['nombre']}: {contractual:,.2f}")
        self._cache = None
        self.sucio = True

    def eliminar_equipo(self, eid):
        e = self.equipo(eid)
        if self.con.execute("SELECT COUNT(*) FROM avances WHERE equipo=? AND cantidad<>0", (eid,)).fetchone()[0]:
            raise ErrorCtrlP("El equipo tiene avance; no se puede eliminar.")
        if self.con.execute("SELECT COUNT(*) FROM tramos WHERE equipo=?", (eid,)).fetchone()[0]:
            raise ErrorCtrlP("El equipo tiene tramos; quitá o mové los tramos primero.")
        self.con.execute("DELETE FROM equipos WHERE id=?", (eid,))
        self.registrar("Equipo eliminado", self.etiqueta_item(self.item(e["item"])),
                       self.etiqueta_ubicacion(e["nivel"]), e["nombre"], "")
        self.sucio = True

    def tramo(self, tid):
        r = self.con.execute("SELECT * FROM tramos WHERE id=?", (tid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["equipo"] = d.get("equipo") or ""
        return d

    def _avance_con(self, iid, campo, valor=None):
        q = f"SELECT COUNT(*) FROM avances WHERE item=? AND {campo}<>''"
        a = [iid]
        if valor is not None:
            q = f"SELECT COUNT(*) FROM avances WHERE item=? AND {campo}=? AND cantidad<>0"
            a.append(valor)
        return self.con.execute(q, a).fetchone()[0] > 0

    def activar_tramos(self, iid, si):
        d = self.detalle_de(iid)
        if bool(d["tramos"]) == bool(si):
            return False
        if not si and self._avance_con(iid, "tramo"):
            raise ErrorCtrlP("Esta partida ya tiene avance registrado por tramos; no se puede quitar la opción.")
        self._set_detalle(iid, tramos=1 if si else 0)
        self.registrar("Más detalles: por tramos", self.etiqueta_item(self.item(iid)), "",
                       "no" if si else "sí", "sí" if si else "no")
        return True

    def activar_hitos(self, iid, si):
        d = self.detalle_de(iid)
        if bool(d["hitos"]) == bool(si):
            return False
        if not si and self._avance_con(iid, "hito"):
            raise ErrorCtrlP("Esta partida ya tiene avance registrado por hitos; no se puede quitar la opción.")
        if si and self.con.execute("SELECT COUNT(*) FROM avances WHERE item=? AND hito='' AND cantidad<>0",
                                   (iid,)).fetchone()[0]:
            raise ErrorCtrlP("Esta partida ya tiene avance registrado sin hitos. Para pagarla por hitos, "
                             "ese avance tendría que reconocerse al 100 %; no se puede activar.")
        self._set_detalle(iid, hitos=1 if si else 0)
        self.registrar("Más detalles: pago por hitos", self.etiqueta_item(self.item(iid)), "",
                       "no" if si else "sí", "sí" if si else "no")
        return True

    def guardar_hitos(self, iid, lista):
        """lista: [(id|None, nombre, pct[, tipo])]. Sin tipos, los porcentajes deben sumar 100.
        Con tipos (ej. tres tipos de tabique), cada tipo tiene sus hitos y cada tipo suma 100."""
        d = self.detalle_de(iid)
        if d["hitos_bloq"]:
            raise ErrorCtrlP("Los porcentajes de los hitos están bloqueados. Desbloquealos primero.")
        lista = [(x[0], (x[1] or "").strip(), x[2], mayus((x[3] if len(x) > 3 else "") or "").strip()) for x in lista]
        lista = [x for x in lista if x[1] or x[2]]
        if any(not n for _, n, _, _ in lista):
            raise ErrorCtrlP("Cada hito necesita un nombre.")
        if any(p is None or p <= 0 for _, _, p, _ in lista):
            raise ErrorCtrlP("Cada hito necesita un porcentaje mayor que cero.")
        tipos = []
        for x in lista:
            if x[3] not in tipos:
                tipos.append(x[3])
        if len(tipos) > 1 and "" in tipos:
            raise ErrorCtrlP("Cada tipo necesita un nombre.")
        for tp in tipos:
            grupo = [x for x in lista if x[3] == tp]
            suma = sum(p for _, _, p, _ in grupo)
            if abs(suma - 100) > 0.005:
                raise ErrorCtrlP(f"Los porcentajes {'del tipo «' + tp + '» ' if tp else ''}suman {suma:,.2f} %; "
                                 "deben sumar 100 %.")
            if len({mayus(n) for _, n, _, _ in grupo}) != len(grupo):
                raise ErrorCtrlP(f"Hay hitos con el mismo nombre{' en el tipo «' + tp + '»' if tp else ''}.")
        # los hitos de un mismo tipo quedan juntos, en el orden en que aparece cada tipo
        lista = [x for tp in tipos for x in lista if x[3] == tp]
        actuales = {h["id"]: dict(h) for h in self.con.execute("SELECT * FROM hitos WHERE item=?", (iid,))}
        quedan = {x[0] for x in lista if x[0]}
        it = self.item(iid)
        for hid, h in actuales.items():
            if hid not in quedan:
                if self._avance_con(iid, "hito", hid):
                    raise ErrorCtrlP(f"El hito «{self.etiqueta_hito(h)}» tiene avance; no se puede quitar.")
        cambios = False
        # cantidades por tipo: si un tipo cambia de nombre se van con él; si el tipo desaparece, se quitan
        nuevos_tipos = {x[3] for x in lista}
        destino = {}
        for x in lista:
            if x[0] in actuales:
                destino.setdefault(actuales[x[0]].get("tipo") or "", set()).add(x[3])
        for tp_v in {h.get("tipo") or "" for h in actuales.values()}:
            if not tp_v or tp_v in nuevos_tipos:
                continue
            dst = destino.get(tp_v, set())
            if len(dst) == 1 and next(iter(dst)):
                self.con.execute("UPDATE OR REPLACE tipo_cant SET tipo=? WHERE item=? AND tipo=?", (next(iter(dst)), iid, tp_v))
            else:
                self.con.execute("DELETE FROM tipo_cant WHERE item=? AND tipo=?", (iid, tp_v))
        for hid, h in actuales.items():
            if hid not in quedan:
                self.con.execute("DELETE FROM hitos WHERE id=?", (hid,))
                self.registrar("Hito quitado", self.etiqueta_item(it), "", self.etiqueta_hito(h), "")
                cambios = True
        for k, (hid, n, p, tp) in enumerate(lista):
            nuevo = {"nombre": n, "pct": p, "tipo": tp}
            if hid and hid in actuales:
                h = actuales[hid]
                h["tipo"] = h.get("tipo") or ""
                if h["nombre"] != n or abs(h["pct"] - p) > 1e-9 or h["orden"] != k or h["tipo"] != tp:
                    if h["nombre"] != n or abs(h["pct"] - p) > 1e-9 or h["tipo"] != tp:
                        self.registrar("Hito modificado", self.etiqueta_item(it), "", self.etiqueta_hito(h),
                                       self.etiqueta_hito(nuevo))
                    self.con.execute("UPDATE hitos SET nombre=?, pct=?, orden=?, tipo=? WHERE id=?", (n, p, k, tp, hid))
                    cambios = True
            else:
                self.con.execute("INSERT INTO hitos(id,item,orden,nombre,pct,tipo) VALUES(?,?,?,?,?,?)",
                                 (nuevo_id(), iid, k, n, p, tp))
                self.registrar("Hito agregado", self.etiqueta_item(it), "", "", self.etiqueta_hito(nuevo))
                cambios = True
        self._cache = None
        self.sucio = True
        return cambios

    @staticmethod
    def etiqueta_hito(h, con_pct=True):
        """«Tipo · Hito (50.00 %)»; sin tipo, «Hito (50.00 %)»."""
        tp = (h.get("tipo") if hasattr(h, "get") else h["tipo"]) or ""
        txt = (f"{tp} · " if tp else "") + h["nombre"]
        return txt + (f" ({h['pct']:.2f} %)" if con_pct else "")

    def tipos_hito(self, iid):
        """[(tipo, [hitos])] en orden; sin tipos, un solo grupo con tipo ''."""
        res = []
        for h in self.hitos_de(iid):
            h["tipo"] = h.get("tipo") or ""
            if not res or res[-1][0] != h["tipo"]:
                res.append((h["tipo"], []))
            res[-1][1].append(h)
        return res

    def bloquear_hitos(self, iid, si):
        d = self.detalle_de(iid)
        if bool(d["hitos_bloq"]) == bool(si):
            return
        self._set_detalle(iid, hitos_bloq=1 if si else 0)
        self.registrar("Porcentajes de hitos " + ("bloqueados" if si else "desbloqueados"),
                       self.etiqueta_item(self.item(iid)), "", "", "")

    def crear_tramo(self, iid, nivel, nombre, contractual=None, plano=None, geom=None, equipo=""):
        nombre = mayus(nombre)
        if not nombre:
            raise ErrorCtrlP("Escribí el nombre del tramo.")
        if any(t["nombre"] == nombre for t in self.tramos_de(iid, nivel)):
            raise ErrorCtrlP(f"Ya existe el tramo «{nombre}» en esta ubicación.")
        if not self.detalle_de(iid)["tramos"]:
            self._set_detalle(iid, tramos=1)
        tid = nuevo_id()
        orden = self.con.execute("SELECT COUNT(*) FROM tramos WHERE item=? AND nivel=?", (iid, nivel)).fetchone()[0]
        self.con.execute("INSERT INTO tramos(id,item,nivel,nombre,contractual,plano,geom,orden,creado,usuario,equipo)"
                         " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (tid, iid, nivel, nombre, contractual, plano, json.dumps(geom) if geom else None, orden,
                          ahora(), self.usuario, equipo or ""))
        self.registrar("Tramo creado", self.etiqueta_item(self.item(iid)), self.etiqueta_ubicacion(nivel), "",
                       nombre + (f" · {contractual:,.2f}" if contractual else ""))
        self._cache = None
        self.sucio = True
        return tid

    def editar_tramo(self, tid, nombre=None, contractual="igual", equipo=None):
        t = self.tramo(tid)
        it = self.item(t["item"])
        if equipo is not None and (equipo or "") != (t.get("equipo") or ""):
            if self.con.execute("SELECT COUNT(*) FROM avances WHERE tramo=? AND cantidad<>0", (tid,)).fetchone()[0]:
                raise ErrorCtrlP(f"El tramo {t['nombre']} ya tiene avance; no se puede cambiar de equipo.")
            self.con.execute("UPDATE tramos SET equipo=? WHERE id=?", (equipo or "", tid))
            self.registrar("Tramo cambiado de equipo", self.etiqueta_item(it), self.etiqueta_ubicacion(t["nivel"]),
                           self.nombre_equipo(t.get("equipo")) or "(sin equipo)", self.nombre_equipo(equipo) or "(sin equipo)")
        if nombre is not None:
            nombre = mayus(nombre)
            if not nombre:
                raise ErrorCtrlP("Escribí el nombre del tramo.")
            if nombre != t["nombre"]:
                if any(x["nombre"] == nombre and x["id"] != tid for x in self.tramos_de(t["item"], t["nivel"])):
                    raise ErrorCtrlP(f"Ya existe el tramo «{nombre}» en esta ubicación.")
                self.con.execute("UPDATE tramos SET nombre=? WHERE id=?", (nombre, tid))
                self.registrar("Tramo renombrado", self.etiqueta_item(it), self.etiqueta_ubicacion(t["nivel"]),
                               t["nombre"], nombre)
        if contractual != "igual":
            if contractual is not None and contractual < 0:
                raise ErrorCtrlP("La cantidad no puede ser negativa.")
            a = t["contractual"]
            if (a is None) != (contractual is None) or (a is not None and abs(a - contractual) > EPS):
                self.con.execute("UPDATE tramos SET contractual=? WHERE id=?", (contractual, tid))
                self.registrar("Cantidad del tramo", self.etiqueta_item(it), self.etiqueta_ubicacion(t["nivel"]),
                               "" if a is None else f"{t['nombre']}: {a:,.2f}",
                               "" if contractual is None else f"{t['nombre']}: {contractual:,.2f}")
        self._cache = None
        self.sucio = True

    def eliminar_tramo(self, tid):
        t = self.tramo(tid)
        if self.con.execute("SELECT COUNT(*) FROM avances WHERE tramo=? AND cantidad<>0", (tid,)).fetchone()[0]:
            raise ErrorCtrlP("El tramo tiene avance; no se puede eliminar.")
        self.con.execute("DELETE FROM tramos WHERE id=?", (tid,))
        self.registrar("Tramo eliminado", self.etiqueta_item(self.item(t["item"])),
                       self.etiqueta_ubicacion(t["nivel"]), t["nombre"], "")
        self.sucio = True

    def nombre_hito(self, hid):
        r = self.con.execute("SELECT nombre, pct, tipo FROM hitos WHERE id=?", (hid,)).fetchone()
        return self.etiqueta_hito(dict(r)) if r else ""

    def nombre_tramo(self, tid):
        r = self.con.execute("SELECT nombre FROM tramos WHERE id=?", (tid,)).fetchone()
        return r[0] if r else ""

    # ---------------------------------------------------------------- avances
    def avances_del_dia(self, iid, fecha):
        """Registros manuales del dia: {(nivel, tramo, hito): registro}."""
        return {(r["nivel"], r["equipo"] or "", r["tramo"] or "", r["hito"] or ""): dict(r) for r in self.con.execute(
            "SELECT * FROM avances WHERE item=? AND fecha=? AND marca=''", (iid, fecha))}

    def puede_editar_avance(self, av):
        """En modo 'Solo agregar avance' no se modifican registros anteriores a la exportacion."""
        if not self.solo_agregar or av is None:
            return True
        return (av.get("creado") or "") > self.get_meta("exportado_en", "")

    def _ubic_detalle(self, nivel, tramo, hito, equipo=""):
        ub = self.etiqueta_ubicacion(nivel)
        if equipo:
            ub += f" · equipo {self.nombre_equipo(equipo)}"
        if tramo:
            ub += f" · tramo {self.nombre_tramo(tramo)}"
        if hito:
            ub += f" · {self.nombre_hito(hito)}"
        return ub

    def guardar_avance(self, iid, nivel, fecha, cantidad, obs="", hito="", tramo="", marca="", equipo=""):
        """cantidad None o 0 sin registro previo = no hace nada. Nunca se borra: se edita."""
        obs = (obs or "").strip()
        hito, tramo, marca, equipo = hito or "", tramo or "", marca or "", equipo or ""
        if tramo and not equipo:
            t = self.tramo(tramo)
            equipo = (t or {}).get("equipo") or ""
        ex = self.con.execute("SELECT * FROM avances WHERE item=? AND nivel=? AND fecha=? AND hito=? AND tramo=? "
                              "AND marca=? AND equipo=?", (iid, nivel, fecha, hito, tramo, marca, equipo)).fetchone()
        it = self.item(iid)
        ub = self._ubic_detalle(nivel, tramo, hito, equipo)
        if marca:
            ub += " · plano"
        if ex is None:
            if cantidad is None or (abs(cantidad) < EPS and not obs):
                return False
            self.con.execute(
                "INSERT INTO avances(id,item,nivel,fecha,cantidad,obs,usuario,creado,modificado,mod_usuario,origen,"
                "hito,tramo,marca,equipo) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (nuevo_id(), iid, nivel, fecha, float(cantidad), obs, self.usuario, ahora(), ahora(),
                 self.usuario, self.version_trabajo, hito, tramo, marca, equipo))
            self.registrar(f"Avance registrado ({fecha_txt(fecha)})", self.etiqueta_item(it), ub, "",
                           f"{cantidad:,.2f} {it['unidad']}" + (f" · {obs}" if obs else ""))
        else:
            ex = dict(ex)
            if not self.puede_editar_avance(ex):
                raise ErrorCtrlP("Este archivo es de «Solo agregar avance»: no se pueden modificar registros anteriores.")
            if cantidad is None:
                cantidad = 0.0
            cambios = []
            if abs((ex["cantidad"] or 0) - cantidad) > EPS:
                cambios.append(("cantidad", f"{ex['cantidad']:,.2f}", f"{cantidad:,.2f}"))
            if (ex["obs"] or "") != obs:
                cambios.append(("observación", ex["obs"] or "", obs))
            if not cambios:
                return False
            self.con.execute("UPDATE avances SET cantidad=?, obs=?, modificado=?, mod_usuario=? WHERE id=?",
                             (float(cantidad), obs, ahora(), self.usuario, ex["id"]))
            for campo, a, n in cambios:
                self.registrar(f"Avance editado ({fecha_txt(fecha)}): {campo}", self.etiqueta_item(it), ub, a, n)
        self._cache = None
        self.sucio = True
        return True

    def fechas_con_avance(self):
        return [r[0] for r in self.con.execute("SELECT DISTINCT fecha FROM avances ORDER BY fecha")]

    def ejecutado(self, hasta=None, desde=None):
        """{item: {nivel: cantidad equivalente}} entre desde y hasta (incluidas).
        Con hitos, cada cantidad vale su porcentaje (cantidad x % del hito)."""
        q = ("SELECT a.item, a.nivel, SUM(a.cantidad * COALESCE(h.pct / 100.0, 1.0)) s "
             "FROM avances a LEFT JOIN hitos h ON h.id = a.hito WHERE 1=1")
        args = []
        if desde:
            q += " AND a.fecha>=?"
            args.append(desde)
        if hasta:
            q += " AND a.fecha<=?"
            args.append(hasta)
        q += " GROUP BY a.item, a.nivel"
        res = {}
        for r in self.con.execute(q, args):
            res.setdefault(r["item"], {})[r["nivel"]] = r["s"] or 0.0
        return res

    def ejecutado_hojas(self, iid, hasta=None, desde=None, marcas=None, excluir_fecha=None):
        """Cantidades sin ponderar por (nivel, tramo, hito) para una partida.
        marcas: None = todo, True = solo lo marcado en planos, False = solo lo manual."""
        q = "SELECT nivel, equipo, tramo, hito, SUM(cantidad) s FROM avances WHERE item=?"
        args = [iid]
        if desde:
            q += " AND fecha>=?"
            args.append(desde)
        if hasta:
            q += " AND fecha<=?"
            args.append(hasta)
        if excluir_fecha:
            q += " AND fecha<>?"
            args.append(excluir_fecha)
        if marcas is True:
            q += " AND marca<>''"
        elif marcas is False:
            q += " AND marca=''"
        res = {}
        for r in self.con.execute(q + " GROUP BY nivel, equipo, tramo, hito", args):
            res[(r["nivel"], r["equipo"] or "", r["tramo"] or "", r["hito"] or "")] = r["s"] or 0.0
        return res

    def ejecutado_desglose(self, hasta=None, desde=None):
        """{item: {(nivel, equipo, tramo): cantidad equivalente}} para aplicar los topes en cadena."""
        q = ("SELECT a.item, a.nivel, a.equipo, a.tramo, SUM(a.cantidad * COALESCE(h.pct / 100.0, 1.0)) s "
             "FROM avances a LEFT JOIN hitos h ON h.id = a.hito WHERE 1=1")
        args = []
        if desde:
            q += " AND a.fecha>=?"
            args.append(desde)
        if hasta:
            q += " AND a.fecha<=?"
            args.append(hasta)
        res = {}
        for r in self.con.execute(q + " GROUP BY a.item, a.nivel, a.equipo, a.tramo", args):
            res.setdefault(r["item"], {})[(r["nivel"], r["equipo"] or "", r["tramo"] or "")] = r["s"] or 0.0
        return res

    def ejecutado_contractual(self, hasta=None):
        """Como ejecutado(hasta), pero en las partidas repartidas por ubicacion (con cantidad contractual por
        ubicacion) solo cuentan las ubicaciones que tienen cantidad, y cada una hasta su cantidad
        (con los topes de equipos y tramos). Las partidas sin repartir quedan igual."""
        ex = self.ejecutado(hasta=hasta)
        cont = self.todo_contractual()
        dg = self.ejecutado_desglose(hasta=hasta)
        eqs, trs = self.estructura_topes()
        cant = {r["id"]: r["cantidad"] for r in self.con.execute("SELECT id, cantidad FROM items")}
        res = {}
        for iid, nvs in ex.items():
            c = cont.get(iid)
            if not c:
                res[iid] = dict(nvs)
                continue
            d = dg.get(iid, {})
            out = {}
            for nv in nvs:
                if nv not in c:
                    continue
                sub = {k: v for k, v in d.items() if k[0] == nv}
                out[nv] = cobrable_desglose(c[nv], {nv: c[nv]}, eqs.get(iid, {}), trs.get(iid, {}), sub)[0]
            tope = cant.get(iid) or 0.0
            suma = sum(out.values())
            if suma > tope + EPS and suma > EPS:
                out = {k: v * tope / suma for k, v in out.items()}
            res[iid] = out
        return res

    def ejecutado_periodo(self, desde, hasta, solo_contractual=False):
        """Ejecutado entre desde y hasta. Con solo_contractual, la diferencia de los acumulados con tope."""
        if not solo_contractual:
            return self.ejecutado(hasta=hasta, desde=desde)
        t = self.ejecutado_contractual(hasta=hasta)
        a = self.ejecutado_contractual(hasta=dia_anterior(desde))
        res = {}
        for iid in set(t) | set(a):
            nvs = set(t.get(iid, {})) | set(a.get(iid, {}))
            res[iid] = {nv: t.get(iid, {}).get(nv, 0.0) - a.get(iid, {}).get(nv, 0.0) for nv in nvs}
        return res

    def estructura_topes(self):
        """Cantidades asignadas de equipos y tramos de todas las partidas que tienen ese detalle."""
        det = {r["item"]: dict(r) for r in self.con.execute("SELECT * FROM detalle")}
        eq, tr = {}, {}
        for r in self.con.execute("SELECT * FROM equipos"):
            if (det.get(r["item"]) or {}).get("equipos"):
                eq.setdefault(r["item"], {})[r["id"]] = (r["nivel"], r["contractual"])
        for r in self.con.execute("SELECT * FROM tramos"):
            if (det.get(r["item"]) or {}).get("tramos"):
                tr.setdefault(r["item"], {})[r["id"]] = (r["nivel"], r["equipo"] or "", r["contractual"])
        return eq, tr

    def factor_hito(self, hid):
        if not hid:
            return 1.0
        r = self.con.execute("SELECT pct FROM hitos WHERE id=?", (hid,)).fetchone()
        return (r[0] / 100.0) if r else 1.0

    def observaciones(self, desde=None, hasta=None):
        q = "SELECT item, nivel, fecha, obs, tramo, hito, equipo FROM avances WHERE obs<>''"
        args = []
        if desde:
            q += " AND fecha>=?"
            args.append(desde)
        if hasta:
            q += " AND fecha<=?"
            args.append(hasta)
        res = {}
        for r in self.con.execute(q + " ORDER BY fecha", args):
            extra = " · ".join(x for x in (self.nombre_equipo(r["equipo"]) if r["equipo"] else "",
                                           self.nombre_tramo(r["tramo"]) if r["tramo"] else "",
                                           self.nombre_hito(r["hito"]) if r["hito"] else "") if x)
            res.setdefault((r["item"], r["nivel"]), []).append(
                f"{fecha_txt(r['fecha'])}: " + (f"[{extra}] " if extra else "") + r["obs"])
        return res

    # ---------------------------------------------------------------- planos
    def planos(self, nivel=None):
        q = ("SELECT id, nivel, nombre, tipo, ancho, alto, escala, unidad, creado, usuario, orden, alcance, nombre_alcance "
             "FROM planos")
        a = []
        if nivel:
            q += " WHERE id IN (SELECT plano FROM plano_ubic WHERE nivel=?)"
            a.append(nivel)
        res = [dict(r) for r in self.con.execute(q + " ORDER BY orden, nombre", a)]
        for pl in res:
            pl["niveles"] = self.plano_niveles(pl["id"])
        return res

    def plano_niveles(self, pid):
        orden = {u["nivel"]: k for k, u in enumerate(self.ubicaciones())}
        nv = [r[0] for r in self.con.execute("SELECT nivel FROM plano_ubic WHERE plano=?", (pid,))]
        return sorted(nv, key=lambda x: orden.get(x, 9999))

    def vincular_plano(self, pid, niveles, alcance=None, nombre_alcance=None):
        niveles = [n for n in niveles if n]
        if alcance:
            if alcance == "nivel" and len(niveles) != 1:
                raise ErrorCtrlP("Un plano por nivel pertenece a una sola ubicación (edificio-nivel).")
            if alcance == "edificio":
                eds = {self.edificio_de_nivel(n) for n in niveles}
                if len(eds) != 1:
                    raise ErrorCtrlP("Un plano por edificio cubre los niveles de un solo edificio.")
                e = self.con.execute("SELECT nombre FROM edificios WHERE id=?", (eds.pop(),)).fetchone()
                nombre_alcance = e[0] if e else ""
            if alcance == "general" and not (nombre_alcance or "").strip():
                nombre_alcance = "GENERAL"
            self.con.execute("UPDATE planos SET alcance=?, nombre_alcance=? WHERE id=?",
                             (alcance, mayus(nombre_alcance or ""), pid))
        if not niveles:
            raise ErrorCtrlP("El plano debe estar vinculado al menos a una ubicación.")
        actuales = set(self.plano_niveles(pid))
        usadas = {r[0] for r in self.con.execute("SELECT DISTINCT nivel FROM marcas WHERE plano=? AND anulada=0", (pid,))}
        quitar = actuales - set(niveles)
        if quitar & usadas:
            raise ErrorCtrlP("No se puede desvincular una ubicación que ya tiene marcas en este plano.")
        for n in quitar:
            self.con.execute("DELETE FROM plano_ubic WHERE plano=? AND nivel=?", (pid, n))
        for n in set(niveles) - actuales:
            self.con.execute("INSERT OR IGNORE INTO plano_ubic VALUES(?,?)", (pid, n))
        self.con.execute("UPDATE planos SET nivel=? WHERE id=?", (niveles[0], pid))
        if set(niveles) != actuales:
            pl = self.plano(pid)
            self.registrar("Plano vinculado a ubicaciones", "", "", ", ".join(self.etiqueta_ubicacion(n) for n in actuales),
                           f"{pl['nombre']}: " + ", ".join(self.etiqueta_ubicacion(n) for n in niveles))
        self.sucio = True

    def etiqueta_plano_ubic(self, pid):
        pl = self.con.execute("SELECT alcance, nombre_alcance FROM planos WHERE id=?", (pid,)).fetchone()
        if pl and pl[0] in ("general", "edificio") and pl[1]:
            return pl[1] + (" (todo el edificio)" if pl[0] == "edificio" else "")
        nv = self.plano_niveles(pid)
        return ", ".join(self.etiqueta_ubicacion(n) for n in nv[:3]) + (f" +{len(nv) - 3}" if len(nv) > 3 else "")

    # ---- hojas de marcado (plano de la libreria + actividad)
    def hojas_de(self, iid=None, pid=None):
        q, a = "SELECT * FROM hojas WHERE 1=1", []
        if iid:
            q += " AND item=?"
            a.append(iid)
        if pid:
            q += " AND plano=?"
            a.append(pid)
        res = []
        for r in self.con.execute(q + " ORDER BY creado", a):
            d = dict(r)
            m = self.con.execute("SELECT COUNT(*), MAX(fecha) FROM marcas WHERE plano=? AND item=? AND anulada=0",
                                 (d["plano"], d["item"])).fetchone()
            d["n_marcas"], d["ultima"] = m[0], m[1]
            res.append(d)
        return res

    def hoja(self, pid, iid):
        r = self.con.execute("SELECT * FROM hojas WHERE plano=? AND item=?", (pid, iid)).fetchone()
        return dict(r) if r else None

    def crear_hoja(self, pid, iid):
        h = self.hoja(pid, iid)
        if h:
            return h["id"]
        hid = nuevo_id()
        self.con.execute("INSERT INTO hojas VALUES(?,?,?,?,?)", (hid, pid, iid, ahora(), self.usuario))
        pl = self.plano(pid)
        self.registrar("Hoja de marcado iniciada", self.etiqueta_item(self.item(iid)), self.etiqueta_plano_ubic(pid), "",
                       pl["nombre"])
        self.sucio = True
        return hid

    # ---- colores por edificio (para marcar en planos generales)
    PALETA_EDIFICIOS = ["#2563EB", "#EA580C", "#16A34A", "#9333EA", "#DB2777", "#0891B2", "#CA8A04", "#4F46E5",
                        "#DC2626", "#65A30D", "#0D9488", "#C026D3"]

    def colores_edificios(self):
        try:
            guard = json.loads(self.get_meta("colores_edificios", "{}") or "{}")
        except Exception:
            guard = {}
        res = {}
        usados = set(guard.values())
        libres = [c for c in self.PALETA_EDIFICIOS if c not in usados]
        for k, e in enumerate(self.edificios()):
            if e["id"] in guard:
                res[e["id"]] = guard[e["id"]]
            else:
                res[e["id"]] = libres.pop(0) if libres else self.PALETA_EDIFICIOS[k % len(self.PALETA_EDIFICIOS)]
        return res

    def poner_color_edificio(self, eid, colr):
        c = self.colores_edificios()
        c[eid] = colr
        self.set_meta("colores_edificios", json.dumps(c))

    def edificio_de_nivel(self, nivel):
        r = self.con.execute("SELECT edificio FROM niveles WHERE id=?", (nivel,)).fetchone()
        return r[0] if r else None

    # ---- estilos de marcado por actividad
    ESTILO_BASE = {"linea": {"grosor": 6.0, "alpha": 85},
                   "area": {"alpha": 35, "borde": 3.0, "alpha_borde": 90},
                   "punto": {"forma": "Círculo", "tamano": 16.0, "alpha": 90, "borde": 2.0},
                   "c_per": None, "c_ant": None}

    def estilo_de(self, iid):
        import copy
        e = copy.deepcopy(self.ESTILO_BASE)
        r = self.con.execute("SELECT datos FROM estilos WHERE item=?", (iid,)).fetchone()
        if r:
            try:
                d = json.loads(r[0])
                for k, v in d.items():
                    if isinstance(v, dict) and isinstance(e.get(k), dict):
                        e[k].update(v)
                    else:
                        e[k] = v
            except Exception:
                pass
        return e

    def guardar_estilo(self, iid, estilo):
        self.con.execute("INSERT OR REPLACE INTO estilos VALUES(?,?)", (iid, json.dumps(estilo)))
        self.sucio = True

    # ---- registros manuales para ubicar en los planos
    def acumulado_plano(self, corte, item=None):
        """Para «Marcar por acumulado»: por actividad y ubicacion (equipo, tramo, hito), lo acumulado hasta el corte,
        lo ya marcado en planos (de cualquier forma) hasta esa fecha y lo que falta marcar."""
        clave = "item, nivel, COALESCE(equipo,''), COALESCE(tramo,''), COALESCE(hito,'')"
        filtro, a = ("", [corte]) if not item else (" AND item=?", [corte, item])
        acum = {tuple(r[:5]): r[5] for r in self.con.execute(
            f"SELECT {clave}, SUM(cantidad) FROM avances WHERE fecha<=?{filtro} GROUP BY {clave}", a)}
        marc = {tuple(r[:5]): r[5] for r in self.con.execute(
            f"SELECT {clave}, SUM(cantidad) FROM marcas WHERE anulada=0 AND fecha<=?{filtro} GROUP BY {clave}", a)}
        res = []
        for k, v in acum.items():
            if v <= EPS:
                continue
            m = marc.get(k, 0.0)
            res.append({"item": k[0], "nivel": k[1], "equipo": k[2], "tramo": k[3], "hito": k[4], "acumulado": v,
                        "marcado": m, "pendiente": max(v - m, 0.0)})
        return res

    def cortes_acumulado(self):
        """{(item, nivel, equipo, tramo, hito): ultima fecha de corte marcada por acumulado}."""
        return {tuple(r[:5]): r[5] for r in self.con.execute(
            "SELECT item, nivel, COALESCE(equipo,''), COALESCE(tramo,''), COALESCE(hito,''), MAX(fecha) FROM marcas "
            "WHERE anulada=0 AND ref=? GROUP BY 1, 2, 3, 4, 5", (ACUM,))}

    def pendientes_plano(self, pid, desde=None, hasta=None, item=None):
        """Registros manuales (no marcados en planos) de las ubicaciones del plano, con lo que falta ubicar."""
        niveles = self.plano_niveles(pid)
        if not niveles:
            return []
        q = (f"SELECT * FROM avances WHERE marca='' AND cantidad>0 AND nivel IN ({','.join('?' * len(niveles))})")
        a = list(niveles)
        if desde:
            q += " AND fecha>=?"
            a.append(desde)
        if hasta:
            q += " AND fecha<=?"
            a.append(hasta)
        if item:
            q += " AND item=?"
            a.append(item)
        res = []
        cortes = self.cortes_acumulado()
        for r in self.con.execute(q + " ORDER BY fecha", a):
            r = dict(r)
            ub = self.con.execute("SELECT COALESCE(SUM(cantidad),0) FROM marcas WHERE ref=? AND anulada=0 AND visual=1",
                                  (r["id"],)).fetchone()[0]
            r["ubicado"] = ub
            r["pendiente"] = max(r["cantidad"] - ub, 0.0)
            corte = cortes.get((r["item"], r["nivel"], r["equipo"] or "", r["tramo"] or "", r["hito"] or ""))
            if corte and corte >= r["fecha"]:
                r["pendiente"] = 0.0      # ya quedo dentro de una marca por acumulado
            res.append(r)
        return res

    def plano(self, pid, con_datos=False):
        r = self.con.execute("SELECT * FROM planos WHERE id=?", (pid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        if not con_datos:
            d.pop("datos", None)
        return d

    def agregar_plano(self, nivel, nombre, tipo, datos, ancho, alto, alcance="nivel", nombre_alcance=""):
        nombre = (nombre or "").strip() or "PLANO"
        pid = nuevo_id()
        orden = self.con.execute("SELECT COUNT(*) FROM planos").fetchone()[0]
        self.con.execute("INSERT INTO planos(id,nivel,nombre,tipo,datos,ancho,alto,escala,unidad,creado,usuario,orden,"
                         "alcance,nombre_alcance) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (pid, nivel, nombre, tipo, sqlite3.Binary(datos), ancho, alto, None, "m", ahora(),
                          self.usuario, orden, alcance, mayus(nombre_alcance)))
        self.con.execute("INSERT OR IGNORE INTO plano_ubic VALUES(?,?)", (pid, nivel))
        self.registrar("Plano cargado", "", self.etiqueta_ubicacion(nivel), "",
                       f"{nombre} ({len(datos) / 1048576:,.1f} MB)")
        self.sucio = True
        return pid

    def calibrar_plano(self, pid, escala, unidad="m"):
        pl = self.plano(pid)
        self.con.execute("UPDATE planos SET escala=?, unidad=? WHERE id=?", (escala, unidad, pid))
        self.registrar("Plano calibrado", "", self.etiqueta_ubicacion(pl["nivel"]),
                       "" if not pl["escala"] else f"{pl['escala']:.6g} {pl['unidad']}/px",
                       f"{pl['nombre']}: {escala:.6g} {unidad}/px")
        self.sucio = True

    def renombrar_plano(self, pid, nombre):
        pl = self.plano(pid)
        nombre = (nombre or "").strip()
        if nombre and nombre != pl["nombre"]:
            self.con.execute("UPDATE planos SET nombre=? WHERE id=?", (nombre, pid))
            self.registrar("Plano renombrado", "", self.etiqueta_ubicacion(pl["nivel"]), pl["nombre"], nombre)
            self.sucio = True

    def eliminar_plano(self, pid, conservar=True):
        """Con marcas: conservar=True deja sus cantidades como registros manuales; False las anula."""
        if self.solo_agregar:
            raise ErrorCtrlP("En un archivo de «Solo agregar avance» no se pueden eliminar planos.")
        pl = self.plano(pid)
        self._limpiar_marcas(self.marcas(pid), conservar)
        self.con.execute("DELETE FROM planos WHERE id=?", (pid,))
        self.con.execute("DELETE FROM plano_ubic WHERE plano=?", (pid,))
        self.con.execute("DELETE FROM hojas WHERE plano=?", (pid,))
        self.con.execute("UPDATE tramos SET plano=NULL, geom=NULL WHERE plano=?", (pid,))
        self.registrar("Plano eliminado", "", "", pl["nombre"],
                       "avances conservados sin marcar" if conservar else "marcas y su avance anulados")
        self.sucio = True

    def marcas(self, pid, incluir_anuladas=False, nivel=None, item=None):
        q = "SELECT * FROM marcas WHERE plano=?" + ("" if incluir_anuladas else " AND anulada=0")
        a = [pid]
        if nivel:
            q += " AND nivel=?"
            a.append(nivel)
        if item:
            q += " AND item=?"
            a.append(item)
        res = []
        for r in self.con.execute(q + " ORDER BY fecha, creado", a):
            d = dict(r)
            d["geom"] = json.loads(d["geom"]) if d["geom"] else []
            d["huecos"] = json.loads(d["huecos"]) if d.get("huecos") else []
            res.append(d)
        return res

    def marca(self, mid):
        r = self.con.execute("SELECT * FROM marcas WHERE id=?", (mid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["geom"] = json.loads(d["geom"]) if d["geom"] else []
        d["huecos"] = json.loads(d["huecos"]) if d.get("huecos") else []
        return d

    def agregar_marca(self, pid, iid, tipo, geom, medida, factor, cantidad, fecha, hito="", tramo="",
                      altura="", nota="", equipo="", nivel=None, ref="", modo="avance", huecos=None):
        """modo: 'avance' (la marca es avance propio), 'ubicar' (solo marca: ubica cantidad ya registrada en
        el registro manual 'ref') o 'reemplazar' (la medida del plano reemplaza lo que faltaba ubicar de 'ref')."""
        pl = self.plano(pid)
        nivel = nivel or pl["nivel"]
        if cantidad is None or cantidad <= 0:
            raise ErrorCtrlP("La cantidad debe ser mayor que cero.")
        if tramo and not equipo:
            equipo = (self.tramo(tramo) or {}).get("equipo") or ""
        reg = None
        if modo == "acumulado":
            ref = ACUM
        if ref and ref != ACUM:
            reg = self.con.execute("SELECT * FROM avances WHERE id=?", (ref,)).fetchone()
            if reg is None:
                raise ErrorCtrlP("El registro a ubicar ya no existe.")
            reg = dict(reg)
            hito, tramo, equipo, nivel = reg["hito"] or "", reg["tramo"] or "", reg["equipo"] or "", reg["nivel"]
        if nivel not in self.plano_niveles(pid):
            raise ErrorCtrlP(f"{self.etiqueta_ubicacion(nivel)} no está en el alcance de este plano.")
        self.crear_hoja(pid, iid)
        mid = nuevo_id()
        visual = 1 if modo in ("ubicar", "acumulado") else 0
        self.con.execute("INSERT INTO marcas(id,plano,item,nivel,hito,tramo,tipo,geom,medida,factor,altura,nota,fecha,"
                         "cantidad,anulada,usuario,creado,equipo,ref,visual,huecos) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?)",
                         (mid, pid, iid, nivel, hito or "", tramo or "", tipo, json.dumps(geom), medida,
                          factor, (altura or "").strip(), (nota or "").strip(), fecha, float(cantidad),
                          self.usuario, ahora(), equipo or "", ref or "", visual, json.dumps(huecos) if huecos else ""))
        if modo == "acumulado":
            self.registrar("Avance acumulado marcado en plano", self.etiqueta_item(self.item(iid)),
                           self._ubic_detalle(nivel, tramo, hito, equipo), "",
                           f"{cantidad:,.2f} del acumulado al {fecha_txt(fecha)}")
        elif modo == "ubicar":
            self.registrar("Avance ubicado en plano", self.etiqueta_item(self.item(iid)),
                           self._ubic_detalle(nivel, tramo, hito, equipo), "",
                           f"{cantidad:,.2f} del registro del {fecha_txt(reg['fecha']) if reg else fecha_txt(fecha)}")
        else:
            if modo == "reemplazar" and reg:
                pend = [x for x in self.pendientes_plano(pid, item=iid) if x["id"] == ref]
                falta = pend[0]["pendiente"] if pend else reg["cantidad"]
                self.guardar_avance(iid, reg["nivel"], reg["fecha"], max(reg["cantidad"] - falta, 0.0), reg["obs"],
                                    reg["hito"], reg["tramo"], equipo=reg["equipo"])
            self.guardar_avance(iid, nivel, fecha, cantidad, nota, hito, tramo, marca=mid, equipo=equipo)
        self.sucio = True
        return mid

    def editar_marca(self, mid, cantidad=None, fecha=None, nota=None, altura=None, hito=None, tramo=None,
                     equipo=None, geom=None, medida=None, factor=None, huecos=None):
        m = self.marca(mid)
        m["equipo"] = m.get("equipo") or ""
        if huecos is not None:
            self.con.execute("UPDATE marcas SET huecos=? WHERE id=?", (json.dumps(huecos) if huecos else "", mid))
            self.sucio = True
        if geom is not None or medida is not None or factor is not None:
            ex0 = self.con.execute("SELECT * FROM avances WHERE marca=?", (mid,)).fetchone()
            if ex0 is not None and not self.puede_editar_avance(dict(ex0)):
                    raise ErrorCtrlP("Este archivo es de «Solo agregar avance»: no se pueden modificar marcas anteriores.")
            self.con.execute("UPDATE marcas SET geom=?, medida=?, factor=? WHERE id=?",
                             (json.dumps(geom if geom is not None else m["geom"]),
                              m["medida"] if medida is None else medida, m["factor"] if factor is None else factor, mid))
            if geom is not None:
                self.registrar("Marca de plano movida o reformada", self.etiqueta_item(self.item(m["item"])),
                               self.etiqueta_ubicacion(m["nivel"]), "", "")
            self.sucio = True
        if m.get("visual"):
            n_c = m["cantidad"] if cantidad is None else cantidad
            self.con.execute("UPDATE marcas SET cantidad=?, nota=?, altura=? WHERE id=?",
                             (n_c, m["nota"] if nota is None else nota.strip(), m["altura"] if altura is None else altura.strip(),
                              mid))
            self.registrar("Marca de plano editada", self.etiqueta_item(self.item(m["item"])),
                           self.etiqueta_ubicacion(m["nivel"]), f"{m['cantidad']:,.2f}", f"{n_c:,.2f}")
            self.sucio = True
            return
        ex = self.con.execute("SELECT * FROM avances WHERE marca=?", (mid,)).fetchone()
        if ex is not None and not self.puede_editar_avance(dict(ex)):
            raise ErrorCtrlP("Este archivo es de «Solo agregar avance»: no se pueden modificar marcas anteriores.")
        n = {"cantidad": m["cantidad"] if cantidad is None else cantidad,
             "fecha": m["fecha"] if fecha is None else fecha,
             "nota": m["nota"] if nota is None else nota.strip(),
             "altura": m["altura"] if altura is None else altura.strip(),
             "hito": m["hito"] if hito is None else hito,
             "tramo": m["tramo"] if tramo is None else tramo,
             "equipo": m["equipo"] if equipo is None else equipo}
        if n["tramo"] and equipo is None:
            n["equipo"] = (self.tramo(n["tramo"]) or {}).get("equipo") or n["equipo"]
        if n["cantidad"] < 0:
            raise ErrorCtrlP("La cantidad no puede ser negativa.")
        clave_cambia = (n["fecha"] != m["fecha"] or n["hito"] != m["hito"] or n["tramo"] != m["tramo"]
                        or n["equipo"] != m["equipo"])
        if clave_cambia and ex is not None:
            # se deja en cero el registro anterior (nunca se borra) y se crea el nuevo
            self.guardar_avance(m["item"], m["nivel"], m["fecha"], 0.0, "", m["hito"], m["tramo"], marca=mid,
                                equipo=m["equipo"])
            self.con.execute("UPDATE avances SET marca=? WHERE id=?", (mid + "~" + nuevo_id()[:4], ex["id"]))
        self.con.execute("UPDATE marcas SET cantidad=?, fecha=?, nota=?, altura=?, hito=?, tramo=?, equipo=? WHERE id=?",
                         (n["cantidad"], n["fecha"], n["nota"], n["altura"], n["hito"], n["tramo"], n["equipo"], mid))
        self.guardar_avance(m["item"], m["nivel"], n["fecha"], n["cantidad"], n["nota"], n["hito"], n["tramo"],
                            marca=mid, equipo=n["equipo"])
        self.sucio = True

    def anular_marca(self, mid):
        m = self.marca(mid)
        if m.get("visual"):
            self.con.execute("UPDATE marcas SET anulada=1 WHERE id=?", (mid,))
            self.registrar("Marca de plano anulada (solo ubicación)", self.etiqueta_item(self.item(m["item"])),
                           self.etiqueta_ubicacion(m["nivel"]), f"{m['cantidad']:,.2f}", "")
            self.sucio = True
            return
        ex = self.con.execute("SELECT * FROM avances WHERE marca=?", (mid,)).fetchone()
        if ex is not None and not self.puede_editar_avance(dict(ex)):
            raise ErrorCtrlP("Este archivo es de «Solo agregar avance»: no se pueden anular marcas anteriores.")
        self.guardar_avance(m["item"], m["nivel"], m["fecha"], 0.0, "", m["hito"], m["tramo"], marca=mid,
                            equipo=m.get("equipo") or "")
        self.con.execute("UPDATE marcas SET anulada=1 WHERE id=?", (mid,))
        self.registrar("Marca de plano anulada", self.etiqueta_item(self.item(m["item"])),
                       self.etiqueta_ubicacion(m["nivel"]), f"{m['cantidad']:,.2f} · {fecha_txt(m['fecha'])}", "0")
        self.sucio = True

    def quitar_del_plano(self, mid):
        """Borra la marca del plano pero conserva su cantidad como registro manual (queda «sin marcar»)."""
        m = self.marca(mid)
        if m.get("visual"):
            return self.anular_marca(mid)
        ex = self.con.execute("SELECT * FROM avances WHERE marca=?", (mid,)).fetchone()
        if ex is not None and not self.puede_editar_avance(dict(ex)):
            raise ErrorCtrlP("Este archivo es de «Solo agregar avance»: no se pueden quitar marcas anteriores.")
        eq = m.get("equipo") or ""
        if ex is not None and (ex["cantidad"] or 0) > EPS:
            man = self.con.execute("SELECT * FROM avances WHERE item=? AND nivel=? AND fecha=? AND hito=? AND tramo=? "
                                   "AND marca='' AND equipo=?",
                                   (m["item"], m["nivel"], ex["fecha"], m["hito"] or "", m["tramo"] or "", eq)).fetchone()
            base = (man["cantidad"] or 0) if man is not None else 0.0
            obs = (man["obs"] or "") if man is not None else (ex["obs"] or "")
            self.guardar_avance(m["item"], m["nivel"], ex["fecha"], base + ex["cantidad"], obs, m["hito"], m["tramo"],
                                equipo=eq)
            self.guardar_avance(m["item"], m["nivel"], ex["fecha"], 0.0, "", m["hito"], m["tramo"], marca=mid, equipo=eq)
        self.con.execute("UPDATE marcas SET anulada=1 WHERE id=?", (mid,))
        self.registrar("Marca quitada del plano (el avance se conserva sin marcar)",
                       self.etiqueta_item(self.item(m["item"])), self.etiqueta_ubicacion(m["nivel"]),
                       f"{m['cantidad']:,.2f} · {fecha_txt(m['fecha'])}", "sin marcar")
        self.sucio = True

    def _limpiar_marcas(self, marcas, conservar):
        for m in marcas:
            if conservar:
                self.quitar_del_plano(m["id"])
            else:
                self.anular_marca(m["id"])

    def eliminar_hoja(self, hid, conservar=True):
        h = self.con.execute("SELECT * FROM hojas WHERE id=?", (hid,)).fetchone()
        if not h:
            return
        self._limpiar_marcas(self.marcas(h["plano"], item=h["item"]), conservar)
        self.con.execute("DELETE FROM hojas WHERE id=?", (hid,))
        self.registrar("Hoja de plano eliminada", self.etiqueta_item(self.item(h["item"])), "",
                       (self.plano(h["plano"]) or {}).get("nombre", ""), "avance conservado" if conservar else "avance anulado")
        self.sucio = True


# =========================================================================
#  Calculos
# =========================================================================
def cobrable(cantidad_partida, contractual, ejecutado_por_nivel):
    """Aplica los topes. Devuelve (cobrable, excedente, cobrable_por_nivel).
    - Ubicacion con contractual: tope = su contractual.
    - Ubicaciones sin contractual: comparten lo libre de la partida (total - asignado).
    - Nunca mas que la cantidad de la partida."""
    total = cantidad_partida or 0.0
    asignado = sum(contractual.values())
    libre = max(total - asignado, 0.0)
    cob = exc = 0.0
    por_nivel = {}
    sin_asig = []
    for nv, e in ejecutado_por_nivel.items():
        if nv in contractual:
            c = min(e, contractual[nv])
            por_nivel[nv] = max(c, 0.0) if e >= 0 else e
            cob += por_nivel[nv]
            exc += max(e - contractual[nv], 0.0)
        else:
            sin_asig.append((nv, e))
    suma_sin = sum(e for _, e in sin_asig)
    x = min(suma_sin, libre)
    cob += x
    exc += max(suma_sin - x, 0.0)
    # reparto proporcional de lo cobrable sin asignar (para informes por ubicacion)
    for nv, e in sin_asig:
        por_nivel[nv] = (e / suma_sin * x) if suma_sin > EPS else 0.0
    if cob > total + EPS:
        exc += cob - total
        f = total / cob if cob > EPS else 0
        por_nivel = {k: v * f for k, v in por_nivel.items()}
        cob = total
    return cob, exc, por_nivel


def _cobro_nodo(cap, hijos):
    """Topes en cadena. hijos: lista de (asignado|None, valor) donde valor es un numero (ejecutado)
    o una lista de hijos. Solo hay tope si se asigna; si no, el tope es lo disponible de arriba.
    Devuelve el cobrable del nodo (sin pasar 'cap' si cap no es None)."""
    asign = sum(a for a, _ in hijos if a is not None)
    libre = None if cap is None else max(cap - asign, 0.0)
    total = 0.0
    sin = 0.0
    for a, v in hijos:
        c = _cobro_nodo(a, v) if isinstance(v, list) else (min(v, a) if (a is not None and v > 0) else v)
        if a is not None:
            total += c
        else:
            if isinstance(v, list):
                c = _cobro_nodo(libre, v)
            sin += c
    if libre is not None and sin > libre:
        sin = libre
    total += sin
    if cap is not None and total > cap:
        total = cap
    return total


def cobrable_desglose(cantidad_partida, cont_nivel, equipos, tramos, ejec):
    """Cobrable de una partida con topes partida › nivel › equipo › tramo.
    cont_nivel {nivel: c}; equipos {eid: (nivel, c|None)}; tramos {tid: (nivel, eid, c|None)};
    ejec {(nivel, equipo, tramo): cantidad equivalente}. Devuelve (cobrable, excedente)."""
    niveles = {}
    for (nv, eq, tr), v in ejec.items():
        niveles.setdefault(nv, {"directo": 0.0, "eq": {}, "tr": {}})
        n = niveles[nv]
        if tr and tr in tramos:
            if eq and eq in equipos:
                n["eq"].setdefault(eq, {"directo": 0.0, "tr": {}})["tr"][tr] = n["eq"].get(eq, {}).get("tr", {}).get(tr, 0.0) + v
            else:
                n["tr"][tr] = n["tr"].get(tr, 0.0) + v
        elif eq and eq in equipos:
            n["eq"].setdefault(eq, {"directo": 0.0, "tr": {}})["directo"] += v
        else:
            n["directo"] += v
    # niveles con contractual pero sin avance no cambian nada (ejecutado 0)
    hijos_p = []
    total_ej = 0.0
    for nv, n in niveles.items():
        hijos_n = [(None, n["directo"])]
        total_ej += n["directo"]
        for tr, v in n["tr"].items():
            hijos_n.append((tramos[tr][2], v))
            total_ej += v
        for eq, e in n["eq"].items():
            hijos_e = [(None, e["directo"])]
            total_ej += e["directo"]
            for tr, v in e["tr"].items():
                hijos_e.append((tramos[tr][2], v))
                total_ej += v
            hijos_n.append((equipos[eq][1], hijos_e))
        hijos_p.append((cont_nivel.get(nv), hijos_n))
    cob = _cobro_nodo(cantidad_partida or 0.0, hijos_p)
    return cob, max(total_ej - cob, 0.0)


def pct(a, b):
    return (a / b) if b and abs(b) > EPS else None


# --- filtros de Informes
FILTROS = [("completo", "Presupuesto completo"), ("avance", "Con avance"), ("historial", "Con historial"),
           ("100", "Al 100 %")]


def completa(r):
    """Actividad que llego al 100 % (o mas) de su cantidad contractual (se muestra en verde)."""
    cant = r.get("cantidad") or 0.0
    return cant > EPS and r.get("tot", 0.0) >= cant * (1 - 5e-5)


def pasa_filtro(r, filtro):
    if filtro is True:
        filtro = "historial"
    if filtro == "avance":
        return abs(r.get("per", 0.0)) > EPS
    if filtro == "historial":
        return abs(r.get("per", 0.0)) > EPS or abs(r.get("tot", 0.0)) > EPS
    if filtro == "100":
        return completa(r)
    return True


class Calculo:
    """Calculo completo para un corte: ant (antes de 'desde'), per (desde..hasta), tot (hasta)."""

    def __init__(self, proyecto, desde, hasta, solo_contractual=False):
        self.p = proyecto
        self.desde, self.hasta = desde, hasta
        self.solo = bool(solo_contractual)
        self.items = proyecto.items()
        self.por_id = {i["id"]: i for i in self.items}
        self.cont = proyecto.todo_contractual()
        self.ubic = proyecto.ubicaciones()
        self.ub_por_nivel = {u["nivel"]: u for u in self.ubic}
        self.ex_tot = proyecto.ejecutado(hasta=hasta)
        self.ex_ant = proyecto.ejecutado(hasta=dia_anterior(desde))
        self.dg_tot = proyecto.ejecutado_desglose(hasta=hasta)
        self.dg_ant = proyecto.ejecutado_desglose(hasta=dia_anterior(desde))
        self.top_eq, self.top_tr = proyecto.estructura_topes()
        self.ex_tot_bruto, self.ex_ant_bruto = self.ex_tot, self.ex_ant
        if self.solo:
            # Solo lo contractual: en partidas repartidas, fuera las ubicaciones sin cantidad y lo que pasa de ella
            self.ex_tot = proyecto.ejecutado_contractual(hasta=hasta)
            self.ex_ant = proyecto.ejecutado_contractual(hasta=dia_anterior(desde))
            for dg in (self.dg_tot, self.dg_ant):
                for iid in list(dg):
                    c = self.cont.get(iid)
                    if c:
                        dg[iid] = {k: v for k, v in dg[iid].items() if k[0] in c}
        self.total_presu = proyecto.total_presupuesto()
        self.res = {}
        for it in self.items:
            if it["tipo"] == "P":
                self.res[it["id"]] = self._partida(it)
        self._titulos()

    def _partida(self, it):
        c = self.cont.get(it["id"], {})
        et = self.ex_tot.get(it["id"], {})
        ea = self.ex_ant.get(it["id"], {})
        eqs, trs = self.top_eq.get(it["id"], {}), self.top_tr.get(it["id"], {})
        cob_t, exc_t = cobrable_desglose(it["cantidad"], c, eqs, trs, self.dg_tot.get(it["id"], {}))
        cob_a, exc_a = cobrable_desglose(it["cantidad"], c, eqs, trs, self.dg_ant.get(it["id"], {}))
        tot = sum(et.values())
        ant = sum(ea.values())
        if self.solo and c:
            # lo que queda fuera (sin cantidad o sobre la cantidad) se informa como excedente
            cob_t, cob_a = min(cob_t, tot), min(cob_a, ant)
            exc_t = max(sum(self.ex_tot_bruto.get(it["id"], {}).values()) - cob_t, 0.0)
            exc_a = max(sum(self.ex_ant_bruto.get(it["id"], {}).values()) - cob_a, 0.0)
        pu = it["pu"] or 0.0
        cant = it["cantidad"] or 0.0
        return {
            "cantidad": cant, "unidad": it["unidad"], "pu": pu, "total": it["total"] or 0.0,
            "ant": ant, "per": tot - ant, "tot": tot, "saldo": cant - tot,
            "p_ant": pct(ant, cant), "p_per": pct(tot - ant, cant), "p_tot": pct(tot, cant),
            "cob_ant": cob_a, "cob_tot": cob_t, "cob_per": cob_t - cob_a,
            "exc_tot": exc_t, "exc_per": exc_t - exc_a,
            "m_ant": cob_a * pu, "m_tot": cob_t * pu, "m_per": (cob_t - cob_a) * pu,
            "m_saldo": (it["total"] or 0.0) - cob_t * pu,
            "m_exc": exc_t * pu,
            "nv_tot": et, "nv_ant": ea, "cont": c,
        }

    def _titulos(self):
        # suma de montos de descendientes (por orden y nivel de jerarquia)
        hijos = {}
        for it in self.items:
            if it["padre"]:
                hijos.setdefault(it["padre"], []).append(it["id"])

        def suma(iid):
            if iid in self.res and self.por_id[iid]["tipo"] == "P":
                return self.res[iid]
            acc = {k: 0.0 for k in ("total", "m_ant", "m_tot", "m_per", "m_saldo", "m_exc")}
            for h in hijos.get(iid, []):
                r = suma(h)
                if not self.por_id[h]["vigente"]:
                    continue
                for k in acc:
                    acc[k] += r.get(k, 0.0)
            self.res[iid] = acc
            return acc

        for it in self.items:
            if it["tipo"] == "T" and not it["padre"]:
                suma(it["id"])
        for it in self.items:
            if it["tipo"] == "T" and it["id"] not in self.res:
                suma(it["id"])

    def visibles(self, filtro="completo"):
        """Ids a mostrar con el filtro: las partidas que pasan y todos sus titulos (etapas y subetapas)."""
        if filtro is True:
            filtro = "historial"
        elif not filtro:
            filtro = "completo"
        res = set()
        for it in self.items:
            if it["tipo"] != "P":
                continue
            r = self.res[it["id"]]
            if not it["vigente"] and abs(r["tot"]) < EPS and abs(r["per"]) < EPS:
                continue
            if pasa_filtro(r, filtro):
                res.add(it["id"])
                pid = it["padre"]
                while pid and pid not in res:
                    res.add(pid)
                    pid = (self.por_id.get(pid) or {}).get("padre")
        if filtro == "completo":
            res |= {it["id"] for it in self.items if it["tipo"] == "T"}
        return res

    def totales(self):
        t = {k: 0.0 for k in ("m_ant", "m_tot", "m_per", "m_saldo", "m_exc")}
        for it in self.items:
            if it["tipo"] == "P" and it["vigente"]:
                for k in t:
                    t[k] += self.res[it["id"]][k]
        tp = self.total_presu
        t.update({"total": tp, "p_ant": pct(t["m_ant"], tp), "p_per": pct(t["m_per"], tp),
                  "p_tot": pct(t["m_tot"], tp), "p_saldo": pct(tp - t["m_tot"], tp)})
        return t

    def detalle_ubicaciones(self, iid):
        """Filas por ubicacion para una partida: lista de grupos por edificio."""
        r = self.res[iid]
        it = self.por_id[iid]
        fija = self.p.ubic_fija_de(iid)
        hojas = self.hojas(iid)
        grupos = []
        for e in self.p.edificios():
            filas = []
            nvs_e = self.p.niveles_de(e["id"])
            simple = self.p.area_simple(e, nvs_e)
            for n in nvs_e:
                nv = n["id"]
                if fija and nv != fija:
                    continue
                c = r["cont"].get(nv)
                if self.solo and r["cont"] and c is None:
                    continue            # solo lo contractual: la ubicacion sin cantidad no se muestra
                a = r["nv_ant"].get(nv, 0.0)
                t = r["nv_tot"].get(nv, 0.0)
                filas.append({"nivel": nv, "nombre": e["nombre"] if simple else nombre_nivel(e, n),
                              "contractual": c, "ant": a, "per": t - a, "tot": t,
                              "p_nivel": pct(t, c) if c is not None else None,
                              "saldo": (c - t) if c is not None else None,
                              "hojas": hojas.get(nv, [])})
            if not filas:
                continue
            asign = [f["contractual"] for f in filas if f["contractual"] is not None]
            sc = sum(asign) if asign else None
            st = sum(f["tot"] for f in filas)
            grupos.append({"edificio": e["id"], "nombre": e["nombre"], "es_area": simple, "filas": filas,
                           "contractual": sc, "ant": sum(f["ant"] for f in filas),
                           "per": sum(f["per"] for f in filas), "tot": st,
                           "p_edificio": pct(st, sc) if sc else None,
                           "saldo": (sc - st) if sc is not None else None,
                           "p_general": pct(st, it["cantidad"])})
        return grupos


def _hojas_calc(self, iid):
    """Detalle sin ponderar por equipo, tramo e hito de cada nivel: {nivel: [hoja]}."""
    p = self.p
    hitos = p.hitos_de(iid)
    tramos = {t["id"]: t for t in p.tramos_de(iid)}
    equipos = {e["id"]: e for e in p.equipos_de(iid)}
    if not hitos and not tramos and not equipos:
        return {}
    tot = p.ejecutado_hojas(iid, hasta=self.hasta)
    ant = p.ejecutado_hojas(iid, hasta=dia_anterior(self.desde))
    claves = set(tot) | set(ant)
    for t in tramos.values():
        for h in (hitos or [{"id": ""}]):
            claves.add((t["nivel"], t["equipo"], t["id"], h["id"]))
    for e in equipos.values():
        for h in (hitos or [{"id": ""}]):
            claves.add((e["nivel"], e["id"], "", h["id"]))
    nomh = {h["id"]: h for h in hitos}
    res = {}
    for nv, eq, tr, hi in claves:
        a, t_ = ant.get((nv, eq, tr, hi), 0.0), tot.get((nv, eq, tr, hi), 0.0)
        f = (nomh[hi]["pct"] / 100.0) if hi in nomh else 1.0
        tt = tramos.get(tr)
        ee = equipos.get(eq)
        partes = []
        if equipos:
            partes.append(f"Equipo {ee['nombre']}" if ee else "Sin equipo")
        if tramos:
            partes.append(f"Tramo {tt['nombre']}" if tt else ("Sin tramo" if (not equipos or ee) else ""))
        if hi in nomh:
            partes.append(p.etiqueta_hito(nomh[hi]))
        eq_con_tr = {x["equipo"] for x in tramos.values()}
        base = tt["contractual"] if tt else (ee["contractual"] if ee and ee["id"] not in eq_con_tr else None)
        res.setdefault(nv, []).append({
            "equipo": eq, "tramo": tr, "hito": hi, "nombre": " · ".join(x for x in partes if x) or "General",
            "factor": f, "ant": a, "per": t_ - a, "tot": t_, "contractual": base,
            "orden": ((ee["orden"] if ee else -1), (tt["orden"] if tt else -1), (nomh[hi]["orden"] if hi in nomh else -1))})
    for nv in res:
        res[nv].sort(key=lambda h: h["orden"])
        res[nv] = [h for h in res[nv] if abs(h["tot"]) > EPS or h["contractual"] or h["tramo"] or h["equipo"]]
    if getattr(self, "solo", False) and self.cont.get(iid):
        # solo lo contractual: el detalle de cada ubicacion se ajusta a lo que cuenta en esa ubicacion
        for nv, filas in res.items():
            for clave, bruto, neto in (("tot", self.ex_tot_bruto, self.ex_tot), ("ant", self.ex_ant_bruto, self.ex_ant)):
                b = bruto.get(iid, {}).get(nv, 0.0)
                n = neto.get(iid, {}).get(nv, 0.0)
                f = (n / b) if abs(b) > EPS else 0.0
                for h in filas:
                    h[clave] = h[clave] * f
            for h in filas:
                h["per"] = h["tot"] - h["ant"]
    return res


Calculo.hojas = _hojas_calc


def buckets(desde, hasta, modo):
    """Intervalos para el detalle por dia o por semana: lista de (etiqueta, d0, d1)."""
    d0, d1 = iso_a_fecha(desde), iso_a_fecha(hasta)
    res = []
    if modo == "dia":
        d = d0
        while d <= d1 and len(res) < 400:
            res.append((d.strftime("%d/%m"), d.isoformat(), d.isoformat()))
            d += dt.timedelta(days=1)
    elif modo == "semana":
        d = d0
        while d <= d1 and len(res) < 200:
            fin = min(d + dt.timedelta(days=6 - d.weekday()), d1)
            res.append((f"{d.strftime('%d/%m')}–{fin.strftime('%d/%m')}", d.isoformat(), fin.isoformat()))
            d = fin + dt.timedelta(days=1)
    return res


# =========================================================================
#  Importacion de presupuesto
# =========================================================================
CAMPOS = [("codigo", "Código / Ítem"), ("descripcion", "Descripción"), ("unidad", "Unidad"),
          ("cantidad", "Cantidad"), ("pu", "Precio unitario"), ("total", "Total")]

_PISTAS = {
    "codigo": ["ITEM", "CODIGO", "COD.", "NO."],
    "descripcion": ["DESCRIPCION", "CONCEPTO", "ACTIVIDAD"],
    "unidad": ["UNIDAD", "UND", "U.M", "UM"],
    "cantidad": ["CANTIDAD", "CANT"],
    "pu": ["COSTO UNITARIO", "PRECIO UNITARIO", "P.U", "PU", "UNITARIO"],
    "total": ["COSTO TOTAL", "PRECIO TOTAL", "TOTAL", "MONTO", "IMPORTE"],
}


def leer_excel(ruta):
    """Lee la unica hoja del Excel. Devuelve (nombre_hoja, filas[list[list]])."""
    import openpyxl
    try:
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    except Exception as e:
        raise ErrorCtrlP(f"No se pudo abrir el Excel:\n{e}")
    if len(wb.sheetnames) != 1:
        raise ErrorCtrlP(f"El Excel debe tener una sola hoja (tiene {len(wb.sheetnames)}: "
                         f"{', '.join(wb.sheetnames[:5])}{'…' if len(wb.sheetnames) > 5 else ''}).\n"
                         "Dejá solo la hoja del presupuesto y volvé a intentarlo.")
    ws = wb[wb.sheetnames[0]]
    filas = [list(r) for r in ws.iter_rows(values_only=True)]
    hoja = wb.sheetnames[0]
    wb.close()
    # Formulas rotas (#REF!) o sin valores calculados: pedir pegar como valores
    errores = sum(1 for r in filas for v in r if isinstance(v, str) and v.strip().startswith("#")
                  and v.strip().upper().rstrip("!").lstrip("#") in ("REF", "¡REF", "VALUE", "¡VALOR", "VALOR", "N/A", "NAME?", "¿NOMBRE?", "DIV/0"))
    vacias = 0
    try:
        wbf = openpyxl.load_workbook(ruta, read_only=True, data_only=False)
        formulas = 0
        for rf, rv in zip(wbf[hoja].iter_rows(values_only=True), filas):
            for vf, vv in zip(rf, rv):
                if isinstance(vf, str) and vf.startswith("="):
                    formulas += 1
                    if vv is None:
                        vacias += 1
        wbf.close()
    except Exception:
        formulas = 0
    if errores > 5 or (formulas > 20 and vacias > formulas * 0.5):
        raise ErrorCtrlP(
            "La hoja tiene fórmulas con errores o sin valores calculados (por ejemplo #¡REF!), "
            "probablemente porque dependían de otras hojas que se borraron.\n\n"
            "Solución: en el Excel original seleccioná toda la hoja del presupuesto, copiala y pegala en un "
            "libro nuevo con «Pegado especial › Valores» (y luego «Formatos» si querés). Guardá ese libro "
            "y volvé a importarlo.")
    return hoja, filas


def detectar_columnas(filas):
    """Busca la fila de encabezados. Devuelve (mapa{campo: col}, fila_inicio_datos)."""
    mejor = (0, {}, 0)
    for r in range(min(len(filas), 80)):
        mapa = {}
        ult = r
        for rr in range(r, min(r + 3, len(filas))):
            for c, v in enumerate(filas[rr]):
                t = clave_texto(v)
                if not t or len(t) > 40:
                    continue
                for campo, pistas in _PISTAS.items():
                    if campo in mapa:
                        continue
                    if any(t == p or t.startswith(p + " ") or (len(p) > 4 and p in t) for p in pistas):
                        if campo == "total" and "UNITARIO" in t:
                            continue
                        mapa[campo] = c
                        ult = max(ult, rr)
                        break
        puntos = len(mapa)
        if puntos > mejor[0]:
            mejor = (puntos, mapa, ult + 1)
        if puntos == 6:
            break
    if mejor[0] < 4:
        return {}, 0
    return mejor[1], mejor[2]


def datos_encabezado(filas, hasta):
    res = {"nombre": "", "propietario": "", "contratista": "", "moneda": "US$"}
    for r in filas[:hasta]:
        for v in r:
            if not isinstance(v, str):
                continue
            t = v.replace("：", ":").strip()
            k = clave_texto(t)
            if k.startswith("PROYECTO:") and not res["nombre"]:
                res["nombre"] = t.split(":", 1)[1].strip().rstrip(".")
            elif k.startswith("PROPIETARIO") and ":" in t and not res["propietario"]:
                res["propietario"] = t.split(":", 1)[1].strip()
            elif k.startswith("CONTRATISTA") and ":" in t and not res["contratista"]:
                res["contratista"] = re.sub(r"\s+", " ", t.split(":", 1)[1]).strip()
            if "DOLARES" in k or "USD" in k:
                res["moneda"] = "US$"
            elif "LEMPIRAS" in k:
                res["moneda"] = "L"
    if not res["nombre"]:
        for r in filas[:hasta]:
            for v in r:
                if isinstance(v, str) and len(v.strip()) > 15:
                    res["nombre"] = v.strip()
                    break
            if res["nombre"]:
                break
    m = re.search(r"HOSPITAL [A-ZÁÉÍÓÚÑ ]+?(?: DE [A-ZÁÉÍÓÚÑ]+)", res["nombre"].upper())
    res["nombre_corto"] = m.group(0) if m else mayus(res["nombre"])[:60]
    return res


def analizar_presupuesto(filas, mapa, inicio, archivo=""):
    """Convierte las filas en items con jerarquia y detecta observaciones."""
    def celda(r, campo):
        c = mapa.get(campo)
        return r[c] if c is not None and c < len(r) else None

    items = []
    pila = []  # (nivel, id)
    total_hoja = None
    ult_nivel_codigo = 0
    orden = 0
    obs_unidad, obs_calculo = [], []
    for k in range(inicio, len(filas)):
        r = filas[k]
        cod_raw = celda(r, "codigo")
        desc = celda(r, "descripcion")
        uni = celda(r, "unidad")
        cant = a_numero(celda(r, "cantidad"))
        pu = a_numero(celda(r, "pu"))
        tot = a_numero(celda(r, "total"))
        cod = norm_codigo(cod_raw) if not isinstance(cod_raw, (int, float)) or isinstance(cod_raw, bool) else norm_codigo(cod_raw)
        desc_s = re.sub(r"\s+", " ", str(desc)).strip() if desc is not None else ""
        uni_s = str(uni).strip() if uni is not None else ""
        if not cod and not desc_s and uni is None and cant is None and tot is None:
            continue
        # fila de TOTAL: fin del presupuesto
        if clave_texto(cod).startswith("TOTAL") or (clave_texto(desc_s).startswith("TOTAL") and not uni_s and cant is None):
            total_hoja = tot
            break
        if isinstance(cod_raw, (int, float)) and not isinstance(cod_raw, bool) and not desc_s:
            continue
        es_partida = bool(uni_s) or cant is not None
        orden += 1
        iid = nuevo_id()
        if not es_partida:
            if cod:
                nv = len([s for s in cod.split(".") if s])
                ult_nivel_codigo = nv
            else:
                nv = (ult_nivel_codigo or 1) + 1
            while pila and pila[-1][0] >= nv:
                pila.pop()
            padre = pila[-1][1] if pila else None
            items.append({"id": iid, "orden": orden, "tipo": "T", "nivel": len(pila), "padre": padre,
                          "codigo": cod, "descripcion": desc_s, "unidad": "", "cantidad": None, "pu": None,
                          "total": tot, "fila": k + 1})
            pila.append((nv, iid))
        else:
            padre = pila[-1][1] if pila else None
            if not uni_s or a_numero(uni_s) is not None:
                obs_unidad.append((k + 1, cod, desc_s, uni_s))
            cant = cant or 0.0
            pu = pu or 0.0
            if tot is None:
                tot = round(cant * pu, 2)
            elif abs(cant * pu - tot) > 0.05:
                obs_calculo.append((k + 1, cod, desc_s, cant, pu, tot))
            items.append({"id": iid, "orden": orden, "tipo": "P", "nivel": len(pila), "padre": padre,
                          "codigo": cod, "descripcion": desc_s, "unidad": uni_s.upper(), "cantidad": cant,
                          "pu": pu, "total": tot, "fila": k + 1})
    partidas = [i for i in items if i["tipo"] == "P"]
    titulos = [i for i in items if i["tipo"] == "T"]
    total_imp = round(sum(i["total"] for i in partidas), 2)
    # ---- observaciones
    obs = []
    por_cod = {}
    for i in partidas:
        if i["codigo"]:
            por_cod.setdefault(i["codigo"], []).append(i)
    rep = {c: l for c, l in por_cod.items() if len(l) > 1}
    if rep:
        ej = list(rep.items())[0]
        obs.append({"tipo": "Códigos repetidos", "cantidad": len(rep),
                    "detalle": "Se distinguen por descripción y precio. Ej.: " +
                               " y ".join(f"{x['codigo']} {x['descripcion'][:40]}" for x in ej[1][:2]),
                    "filas": [(x["fila"], x["codigo"], x["descripcion"], x["unidad"], x["cantidad"], x["pu"], x["total"])
                              for l in rep.values() for x in l]})
    por_desc = {}
    for i in partidas:
        por_desc.setdefault(clave_texto(i["descripcion"]), []).append(i)
    repd = {d: l for d, l in por_desc.items() if len(l) > 1 and d}
    if repd:
        obs.append({"tipo": "Descripciones repetidas", "cantidad": len(repd),
                    "detalle": "La misma descripción aparece en partidas distintas.",
                    "filas": [(x["fila"], x["codigo"], x["descripcion"], x["unidad"], x["cantidad"], x["pu"], x["total"])
                              for l in repd.values() for x in l]})
    # codigos que no siguen su capitulo
    por_id = {i["id"]: i for i in items}
    fuera = []
    for i in partidas:
        cap = i
        while cap["padre"]:
            cap = por_id[cap["padre"]]
        if cap["tipo"] == "T" and cap["codigo"] and i["codigo"]:
            pref = cap["codigo"].split(".")[0]
            if i["codigo"].split(".")[0] != pref:
                fuera.append(i)
    if fuera:
        grupos = sorted({re.sub(r"\.[^.]*$", ".xx", f["codigo"]) for f in fuera})
        obs.append({"tipo": "Códigos fuera de su capítulo", "cantidad": len(fuera),
                    "detalle": "Se respeta el orden de la hoja. Grupos: " + ", ".join(grupos[:6]),
                    "filas": [(x["fila"], x["codigo"], x["descripcion"], x["unidad"], x["cantidad"], x["pu"], x["total"])
                              for x in fuera]})
    sin_cod = [t for t in titulos if not t["codigo"]]
    if sin_cod:
        obs.append({"tipo": "Subtítulos sin código", "cantidad": len(sin_cod),
                    "detalle": ", ".join(t["descripcion"][:45] for t in sin_cod[:4]),
                    "filas": [(t["fila"], "", t["descripcion"], "", None, None, t["total"]) for t in sin_cod]})
    if obs_unidad:
        obs.append({"tipo": "Unidades vacías o inválidas", "cantidad": len(obs_unidad),
                    "detalle": "Revisá la unidad de estas partidas en el Excel.",
                    "filas": [(f, c, d, u, None, None, None) for f, c, d, u in obs_unidad]})
    if obs_calculo:
        obs.append({"tipo": "Cantidad × precio ≠ total", "cantidad": len(obs_calculo),
                    "detalle": "Se usa el total de la hoja.",
                    "filas": [(f, c, d, "", q, p, t) for f, c, d, q, p, t in obs_calculo]})
    # identidad (codigo + descripcion + pu) repetida = conflicto real
    ident = {}
    for i in partidas:
        ident.setdefault((i["codigo"], clave_texto(i["descripcion"]), round(i["pu"], 4)), []).append(i)
    dup = [l for l in ident.values() if len(l) > 1]
    if dup:
        obs.insert(0, {"tipo": "Partidas idénticas (código + descripción + precio)", "cantidad": len(dup),
                       "detalle": "No se pueden distinguir entre sí. Conviene corregirlas en el Excel.",
                       "filas": [(x["fila"], x["codigo"], x["descripcion"], x["unidad"], x["cantidad"], x["pu"], x["total"])
                                 for l in dup for x in l]})
    capitulos = len([t for t in titulos if not t["padre"]])
    prof = max((i["nivel"] for i in items), default=0) + 1
    return {"items": items, "partidas": len(partidas), "titulos": len(titulos), "capitulos": capitulos,
            "profundidad": prof, "total_importado": total_imp, "total_hoja": total_hoja,
            "cuadra": total_hoja is None or abs(total_imp - (total_hoja or 0)) < 0.05,
            "observaciones": obs, "archivo": archivo}


# =========================================================================
#  Actualizacion de presupuesto (vinculacion)
# =========================================================================
def comparar_presupuestos(proyecto, nuevo):
    """Vincula las partidas del presupuesto nuevo con las actuales.
    Devuelve dict con listas: sin_cambios, modificadas, probables, nuevas, eliminadas."""
    actuales = [i for i in proyecto.items() if i["tipo"] == "P" and i["vigente"]]
    libres = {i["id"]: i for i in actuales}
    con_avance = {r[0] for r in proyecto.con.execute("SELECT DISTINCT item FROM avances")}
    res = {"sin_cambios": [], "modificadas": [], "probables": [], "nuevas": [], "eliminadas": []}
    pend = []

    def k3(i):
        return (i["codigo"], clave_texto(i["descripcion"]), round(i["pu"] or 0, 4))

    idx3 = {}
    for i in actuales:
        idx3.setdefault(k3(i), []).append(i)
    for n in [x for x in nuevo["items"] if x["tipo"] == "P"]:
        l = [i for i in idx3.get(k3(n), []) if i["id"] in libres]
        if l:
            a = l[0]
            del libres[a["id"]]
            if abs((a["cantidad"] or 0) - n["cantidad"]) > EPS or a["unidad"] != n["unidad"]:
                res["modificadas"].append((a, n))
            else:
                res["sin_cambios"].append((a, n))
        else:
            pend.append(n)
    pend2 = []
    for n in pend:
        l = [i for i in libres.values() if i["codigo"] == n["codigo"] and
             clave_texto(i["descripcion"]) == clave_texto(n["descripcion"])]
        if l:
            a = l[0]
            del libres[a["id"]]
            res["modificadas"].append((a, n))
        else:
            pend2.append(n)
    for n in pend2:
        mejor, puntos = None, 0.0
        dn = clave_texto(n["descripcion"])
        for a in libres.values():
            da = clave_texto(a["descripcion"])
            s = 0.0
            if da == dn and abs((a["pu"] or 0) - n["pu"]) < 0.005:
                s = 0.99
            elif a["codigo"] == n["codigo"]:
                s = difflib.SequenceMatcher(None, da, dn).ratio()
            elif da == dn:
                s = 0.9
            if s > puntos:
                mejor, puntos = a, s
        if mejor is not None and puntos >= 0.85:
            del libres[mejor["id"]]
            res["probables"].append((mejor, n, puntos))
        else:
            res["nuevas"].append(n)
    for a in libres.values():
        res["eliminadas"].append((a, a["id"] in con_avance))
    # ¿es el mismo presupuesto?
    n_act = len(actuales) or 1
    vinc = len(res["sin_cambios"]) + len(res["modificadas"]) + len(res["probables"])
    caps_act = {clave_texto(t["descripcion"]) for t in proyecto.items() if t["tipo"] == "T" and not t["padre"]}
    caps_nue = {clave_texto(t["descripcion"]) for t in nuevo["items"] if t["tipo"] == "T" and not t["padre"]}
    res["coincidencia"] = vinc / n_act
    res["coincidencia_capitulos"] = (len(caps_act & caps_nue) / len(caps_act)) if caps_act else 1.0
    res["mismo"] = res["coincidencia"] >= 0.5 and res["coincidencia_capitulos"] >= 0.5
    res["dudoso"] = res["mismo"] and (res["coincidencia"] < 0.8 or res["coincidencia_capitulos"] < 0.8)
    return res


def aplicar_actualizacion(proyecto, nuevo, comp, aceptar_probables, archivo=""):
    """Aplica el presupuesto nuevo conservando ids (y por lo tanto avances y contractuales)."""
    p = proyecto
    mapa = {}  # id_nuevo -> id_existente
    for a, n in comp["sin_cambios"] + comp["modificadas"]:
        mapa[n["id"]] = a["id"]
    for a, n, _ in comp["probables"]:
        if aceptar_probables.get(n["id"], True):
            mapa[n["id"]] = a["id"]
    titulos_act = {(t["codigo"], clave_texto(t["descripcion"])): t["id"] for t in p.items() if t["tipo"] == "T"}
    usados_t = set()
    for t in [x for x in nuevo["items"] if x["tipo"] == "T"]:
        k = (t["codigo"], clave_texto(t["descripcion"]))
        if k in titulos_act and titulos_act[k] not in usados_t:
            mapa[t["id"]] = titulos_act[k]
            usados_t.add(titulos_act[k])
    vinculados = set(mapa.values())
    viejos = {i["id"]: i for i in p.items()}
    con_avance = {r[0] for r in p.con.execute("SELECT DISTINCT item FROM avances")}
    version = p.version_presupuesto + 1
    p.con.execute("DELETE FROM items")
    for it in nuevo["items"]:
        iid = mapa.get(it["id"], it["id"])
        padre = mapa.get(it["padre"], it["padre"]) if it["padre"] else None
        p.con.execute(
            "INSERT INTO items(id,orden,tipo,nivel,padre,codigo,descripcion,unidad,cantidad,pu,total,vigente,fila_excel)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?)",
            (iid, it["orden"], it["tipo"], it["nivel"], padre, it["codigo"], it["descripcion"], it["unidad"],
             it["cantidad"], it["pu"], it["total"], it.get("fila")))
        if iid in viejos and it["tipo"] == "P":
            v = viejos[iid]
            for campo, nom in (("cantidad", "cantidad"), ("pu", "precio unitario"), ("unidad", "unidad"),
                               ("codigo", "código"), ("descripcion", "descripción")):
                if (v[campo] or "") != (it[campo] or "") and not (
                        isinstance(v[campo], float) and isinstance(it[campo], float) and abs(v[campo] - it[campo]) < EPS):
                    p.registrar(f"Actualización de presupuesto V{version}: {nom}", p.etiqueta_item(it), "",
                                v[campo], it[campo])
        elif it["tipo"] == "P":
            p.registrar(f"Actualización de presupuesto V{version}: partida nueva", p.etiqueta_item(it), "", "",
                        f"{it['cantidad']:,.2f} {it['unidad']} × {it['pu']:,.2f}")
    orden_extra = 10 ** 7
    for iid, v in viejos.items():
        if iid in vinculados:
            continue
        if v["tipo"] == "P" and iid in con_avance:
            orden_extra += 1
            p.con.execute(
                "INSERT INTO items(id,orden,tipo,nivel,padre,codigo,descripcion,unidad,cantidad,pu,total,vigente,fila_excel)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,0,?)",
                (iid, orden_extra, "P", 0, None, v["codigo"], v["descripcion"], v["unidad"], v["cantidad"],
                 v["pu"], v["total"], v["fila_excel"]))
            p.registrar(f"Actualización de presupuesto V{version}: fuera del presupuesto vigente",
                        p.etiqueta_item(v), "", "vigente", "fuera del presupuesto (tiene avance)")
        elif v["tipo"] == "P":
            p.con.execute("DELETE FROM contractual WHERE item=?", (iid,))
            p.con.execute("DELETE FROM ubic_fija WHERE item=?", (iid,))
            p.registrar(f"Actualización de presupuesto V{version}: partida retirada", p.etiqueta_item(v), "",
                        "vigente", "retirada (sin avance)")
    total = sum(i["total"] for i in nuevo["items"] if i["tipo"] == "P")
    p.con.execute("INSERT INTO versiones VALUES(?,?,?,?,?)", (version, ahora(), os.path.basename(archivo), p.usuario, total))
    p.set_meta("version_presupuesto", str(version))
    p.registrar(f"Presupuesto actualizado a V{version}", "", "", f"V{version - 1}", f"V{version} · {os.path.basename(archivo)}")
    p._cache = None
    p.sucio = True
    return version


# =========================================================================
#  Intercambio entre computadoras
# =========================================================================
def exportar_copia(proyecto, destino, solo_agregar):
    proyecto.con.commit()
    proyecto._escribir_zip(proyecto.ruta)
    tmp = tempfile.mkdtemp(prefix="ctrlp_exp_")
    try:
        db = os.path.join(tmp, "proyecto.db")
        Proyecto._extraer(proyecto.ruta, db)
        con = sqlite3.connect(db)
        for k, v in (("solo_agregar", "1" if solo_agregar else "0"), ("exportado_en", ahora()),
                     ("exportado_por", proyecto.usuario), ("export_id", nuevo_id()),
                     ("exportado_desde", os.path.basename(proyecto.ruta))):
            con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, v))
        con.commit()
        con.close()
        if not destino.lower().endswith(EXT):
            destino += EXT
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.write(db, "proyecto.db")
            z.writestr("info.json", json.dumps({"app": APP, "esquema": ESQUEMA, "proyecto": proyecto.nombre,
                                                "exportado": ahora(), "solo_agregar": solo_agregar},
                                               ensure_ascii=False))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    proyecto.registrar("Copia exportada", "", "", "", f"{os.path.basename(destino)}"
                       + (" · solo agregar avance" if solo_agregar else ""))
    return destino


def analizar_importacion(proyecto, ruta):
    """Compara un .ctrlp recibido con el proyecto abierto. No modifica nada."""
    tmp = tempfile.mkdtemp(prefix="ctrlp_imp_")
    try:
        db = os.path.join(tmp, "proyecto.db")
        Proyecto._extraer(ruta, db)
        o = sqlite3.connect(db)
        o.row_factory = sqlite3.Row
        ids_locales = {r[0] for r in proyecto.con.execute("SELECT id FROM items")}
        ids_otros = {r[0] for r in o.execute("SELECT id FROM items")}
        if not ids_otros or len(ids_locales & ids_otros) < 0.5 * len(ids_otros):
            raise ErrorCtrlP("El archivo recibido no corresponde a este proyecto.")
        faltan_items = ids_otros - ids_locales
        res = {"ruta": ruta, "archivo": os.path.basename(ruta), "nuevos": [], "modificados": [],
               "contractual": [], "ubicaciones": [], "historial": [], "aviso": "",
               "tramos": [], "hitos": [], "detalle": [], "planos": [], "marcas": [], "marcas_mod": [],
               "usuarios": {}, "equipos": [], "tipo_cant": []}
        tablas_o = {r[0] for r in o.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if faltan_items:
            res["aviso"] = (f"El archivo recibido tiene {len(faltan_items)} partidas que no están en tu presupuesto "
                            "(otra versión). Sus avances en esas partidas no se importarán.")
        # ubicaciones nuevas
        ed_loc = {r["id"] for r in proyecto.con.execute("SELECT id FROM edificios")}
        nv_loc = {r["id"] for r in proyecto.con.execute("SELECT id FROM niveles")}
        for e in o.execute("SELECT * FROM edificios"):
            if e["id"] not in ed_loc:
                res["ubicaciones"].append(("edificio", dict(e)))
        for n in o.execute("SELECT * FROM niveles"):
            if n["id"] not in nv_loc:
                res["ubicaciones"].append(("nivel", dict(n)))
        nombres_otros = {}
        for n in o.execute("SELECT n.id, e.nombre en, n.nombre nn, e.es_area FROM niveles n JOIN edificios e ON e.id=n.edificio"):
            nombres_otros[n["id"]] = (n["en"] if (n["es_area"] and n["nn"] == NIVEL_UNICO)
                                      else f"{n['en']} {n['nn']}")
        # avances
        def kav(r):
            return (r["item"], r["nivel"], r["fecha"], r.get("hito") or "", r.get("tramo") or "", r.get("marca") or "",
                    r.get("equipo") or "")
        locales = {kav(dict(r)): dict(r) for r in proyecto.con.execute("SELECT * FROM avances")}
        for r in o.execute("SELECT * FROM avances ORDER BY fecha"):
            r = dict(r)
            for c in ("hito", "tramo", "marca", "equipo"):
                r[c] = r.get(c) or ""
            if r["item"] in faltan_items:
                continue
            k = kav(r)
            r["ubicacion"] = nombres_otros.get(r["nivel"]) or proyecto.etiqueta_ubicacion(r["nivel"])
            if k not in locales:
                res["nuevos"].append(r)
            else:
                l = locales[k]
                if abs((l["cantidad"] or 0) - (r["cantidad"] or 0)) > EPS or (l["obs"] or "") != (r["obs"] or ""):
                    res["modificados"].append((l, r))
        # contractual
        cont_loc = proyecto.todo_contractual()
        for r in o.execute("SELECT * FROM contractual"):
            if r["item"] in faltan_items:
                continue
            l = cont_loc.get(r["item"], {}).get(r["nivel"])
            if l is None or abs(l - r["cantidad"]) > EPS:
                res["contractual"].append((dict(r), l, nombres_otros.get(r["nivel"], "")))
        # detalles de actividad, tramos, hitos, planos y marcas (solo lo que no existe aqui)
        if "tramos" in tablas_o:
            ids = {r[0] for r in proyecto.con.execute("SELECT id FROM tramos")}
            res["tramos"] = [dict(r) for r in o.execute("SELECT * FROM tramos") if r["id"] not in ids
                             and r["item"] not in faltan_items]
            if "equipos" in tablas_o:
                ids = {r[0] for r in proyecto.con.execute("SELECT id FROM equipos")}
                res["equipos"] = [dict(r) for r in o.execute("SELECT * FROM equipos") if r["id"] not in ids
                                  and r["item"] not in faltan_items]
            ids = {r[0] for r in proyecto.con.execute("SELECT id FROM hitos")}
            if "tipo_cant" in tablas_o:
                hay = {(r[0], r[1], r[2]) for r in proyecto.con.execute("SELECT item, nivel, tipo FROM tipo_cant")}
                res["tipo_cant"] = [dict(r) for r in o.execute("SELECT * FROM tipo_cant")
                                    if (r["item"], r["nivel"], r["tipo"]) not in hay and r["item"] not in faltan_items]
            res["hitos"] = [dict(r) for r in o.execute("SELECT * FROM hitos") if r["id"] not in ids
                            and r["item"] not in faltan_items]
            loc_det = {r["item"]: dict(r) for r in proyecto.con.execute("SELECT * FROM detalle")}
            for r in o.execute("SELECT * FROM detalle"):
                r = dict(r)
                l = loc_det.get(r["item"])
                if r["item"] in faltan_items:
                    continue
                r["equipos"] = r.get("equipos") or 0
                if l is not None:
                    l["equipos"] = l.get("equipos") or 0
                if l is None or any(int(r[k]) > int(l[k]) for k in ("tramos", "hitos", "hitos_bloq", "equipos")):
                    res["detalle"].append(r)
            ids = {r[0] for r in proyecto.con.execute("SELECT id FROM planos")}
            res["planos"] = [dict(r) for r in o.execute("SELECT * FROM planos") if r["id"] not in ids]
            if "plano_ubic" in tablas_o:
                loc = {(r[0], r[1]) for r in proyecto.con.execute("SELECT plano, nivel FROM plano_ubic")}
                res["plano_ubic"] = [tuple(r) for r in o.execute("SELECT plano, nivel FROM plano_ubic") if tuple(r) not in loc]
            if "hojas" in tablas_o:
                loc = {(r[0], r[1]) for r in proyecto.con.execute("SELECT plano, item FROM hojas")}
                res["hojas"] = [dict(r) for r in o.execute("SELECT * FROM hojas") if (r["plano"], r["item"]) not in loc]
            if "estilos" in tablas_o:
                loc = {r[0] for r in proyecto.con.execute("SELECT item FROM estilos")}
                res["estilos"] = [tuple(r) for r in o.execute("SELECT item, datos FROM estilos") if r[0] not in loc]
            loc_m = {r["id"]: dict(r) for r in proyecto.con.execute("SELECT id, anulada, cantidad, fecha FROM marcas")}
            for r in o.execute("SELECT * FROM marcas"):
                r = dict(r)
                if r["item"] in faltan_items:
                    continue
                if r["id"] not in loc_m:
                    res["marcas"].append(r)
                elif (loc_m[r["id"]]["anulada"], loc_m[r["id"]]["cantidad"], loc_m[r["id"]]["fecha"]) != (
                        r["anulada"], r["cantidad"], r["fecha"]):
                    res["marcas_mod"].append(r)
            for r in o.execute("SELECT nombre, datos FROM usuarios"):
                try:
                    res["usuarios"][r["nombre"]] = json.loads(r["datos"])
                except Exception:
                    pass
        # historial del otro
        uids = {r[0] for r in proyecto.con.execute("SELECT uid FROM historial")}
        for h in o.execute("SELECT * FROM historial ORDER BY id"):
            if h["uid"] not in uids:
                res["historial"].append(dict(h))
        o.close()
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def aplicar_importacion(proyecto, imp, usar_recibido):
    """usar_recibido: {avance_id_local: True/False} para los registros modificados."""
    p = proyecto
    origen = imp["archivo"]
    for tipo, d in imp["ubicaciones"]:
        if tipo == "edificio":
            p.con.execute("INSERT OR IGNORE INTO edificios VALUES(?,?,?,?)", (d["id"], d["nombre"], d["es_area"], d["orden"]))
        else:
            p.con.execute("INSERT OR IGNORE INTO niveles VALUES(?,?,?,?)", (d["id"], d["edificio"], d["nombre"], d["orden"]))
    def poner(tabla, d):
        cols = [r[1] for r in p.con.execute(f"PRAGMA table_info({tabla})")]
        cs = [c for c in cols if c in d]
        p.con.execute(f"INSERT OR IGNORE INTO {tabla}({','.join(cs)}) VALUES({','.join('?' * len(cs))})",
                      tuple(d[c] for c in cs))

    for d in imp.get("detalle", []):
        l = p.detalle_de(d["item"])
        p.con.execute("INSERT OR REPLACE INTO detalle(item,tramos,hitos,hitos_bloq,equipos) VALUES(?,?,?,?,?)",
                      (d["item"], max(int(d["tramos"]), int(l["tramos"])), max(int(d["hitos"]), int(l["hitos"])),
                       max(int(d["hitos_bloq"]), int(l["hitos_bloq"])),
                       max(int(d.get("equipos") or 0), int(l.get("equipos") or 0))))
    for e in imp.get("equipos", []):
        poner("equipos", e)
    for h in imp.get("hitos", []):
        poner("hitos", h)
    for c in imp.get("tipo_cant", []):
        poner("tipo_cant", c)
    for t in imp.get("tramos", []):
        poner("tramos", t)
    for pl in imp.get("planos", []):
        poner("planos", pl)
    for h in imp.get("hojas", []):
        p.con.execute("INSERT OR IGNORE INTO hojas VALUES(?,?,?,?,?)", (h["id"], h["plano"], h["item"], h["creado"], h["usuario"]))
    for pid, nv in imp.get("plano_ubic", []):
        p.con.execute("INSERT OR IGNORE INTO plano_ubic VALUES(?,?)", (pid, nv))
    for it, d in imp.get("estilos", []):
        p.con.execute("INSERT OR IGNORE INTO estilos VALUES(?,?)", (it, d))
    cols_m = [r[1] for r in p.con.execute("PRAGMA table_info(marcas)")]
    for m in imp.get("marcas", []) + imp.get("marcas_mod", []):
        cs = [c for c in cols_m if c in m]
        p.con.execute(f"INSERT OR REPLACE INTO marcas({','.join(cs)}) VALUES({','.join('?' * len(cs))})",
                      tuple(m[c] for c in cs))
    if imp.get("usuarios"):
        for k, v in imp["usuarios"].items():
            if k != ADMIN and _rec_valido(v):
                l = p.usuarios_proyecto().get(k)
                if not l or v.get("modificado", "") > l.get("modificado", ""):
                    p.con.execute("INSERT OR REPLACE INTO usuarios VALUES(?,?)", (k, json.dumps(v)))
        p.sincronizar_usuarios()
    for r in imp["nuevos"]:
        p.con.execute("INSERT OR IGNORE INTO avances(id,item,nivel,fecha,cantidad,obs,usuario,creado,modificado,"
                      "mod_usuario,origen,hito,tramo,marca,equipo) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["id"], r["item"], r["nivel"], r["fecha"], r["cantidad"], r["obs"], r["usuario"], r["creado"],
                       r["modificado"], r["mod_usuario"], origen, r["hito"], r["tramo"], r["marca"], r["equipo"]))
    for l, r in imp["modificados"]:
        if usar_recibido.get(l["id"], True):
            p.con.execute("UPDATE avances SET cantidad=?, obs=?, modificado=?, mod_usuario=?, origen=? WHERE id=?",
                          (r["cantidad"], r["obs"], r["modificado"], r["mod_usuario"], origen, l["id"]))
    for r, _l, _n in imp["contractual"]:
        p.con.execute("INSERT OR REPLACE INTO contractual VALUES(?,?,?)", (r["item"], r["nivel"], r["cantidad"]))
    for h in imp["historial"]:
        p.con.execute(
            "INSERT INTO historial(uid,fecha,usuario,version,que,actividad,ubicacion,anterior,nuevo,exportado)"
            " VALUES(?,?,?,?,?,?,?,?,?,0)",
            (h["uid"], h["fecha"], h["usuario"], f"{origen} · {h['version']}", h["que"], h["actividad"],
             h["ubicacion"], h["anterior"], h["nuevo"]))
    n_mod = sum(1 for l, _ in imp["modificados"] if usar_recibido.get(l["id"], True))
    p.registrar("Archivo importado", "", "", "",
                f"{origen}: {len(imp['nuevos'])} avances nuevos, {n_mod} modificados, "
                f"{len(imp['contractual'])} contractuales, {len(imp.get('marcas', []))} marcas de plano, "
                f"{len(imp.get('planos', []))} planos, {len(imp.get('tramos', []))} tramos")
    p._cache = None
    p.sucio = True
