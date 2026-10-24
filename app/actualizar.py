"""
Ctrl-P Android - actualizaciones.
GitHub publica en la rama «apk» el APK y un version.json (version, nombre del APK, SHA256 y novedades).
La app lo consulta, descarga el APK, comprueba el SHA256 y se lo pasa al instalador de Android
(PackageInstaller). Android siempre pide confirmar con «Actualizar»; los datos de la app se mantienen.
"""

import hashlib
import json
import os
import urllib.error
import urllib.request

import novedades

BASE = "https://raw.githubusercontent.com/realmenes-gif/CTRL-P/apk/"


class ErrorActualizar(Exception):
    pass


def _ctx():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _num(v):
    try:
        return tuple(int(x) for x in str(v).strip().lstrip("v").split("."))
    except ValueError:
        return (0,)


def version_actual():
    return novedades.VERSION_INTERNA


def ultima_version(timeout=15):
    """Devuelve el version.json si hay una version mas nueva, o None."""
    req = urllib.request.Request(BASE + "version.json", headers={"User-Agent": "Ctrl-P", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise ErrorActualizar(f"No se pudo consultar GitHub ({e.code}).")
    except Exception as e:
        raise ErrorActualizar(f"No hay conexión para buscar actualizaciones ({getattr(e, 'reason', e)}).")
    if _num(d.get("version")) > _num(version_actual()):
        return d
    return None


def carpeta_descargas():
    try:
        from jnius import autoclass
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        c = act.getCacheDir().getAbsolutePath()
    except Exception:
        import tempfile
        c = tempfile.gettempdir()
    c = os.path.join(c, "actualizacion")
    os.makedirs(c, exist_ok=True)
    return c


def descargar(info, avance=None, cancelado=lambda: False):
    """Descarga el APK y comprueba su SHA256. avance(fraccion) se llama desde el hilo de descarga."""
    destino = os.path.join(carpeta_descargas(), "ctrlp.apk")
    req = urllib.request.Request(BASE + info["apk"], headers={"User-Agent": "Ctrl-P"})
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(req, timeout=60, context=_ctx()) as r, open(destino + ".part", "wb") as f:
            total = int(r.headers.get("Content-Length") or info.get("tamano") or 0)
            n = 0
            while True:
                if cancelado():
                    raise ErrorActualizar("Se canceló la descarga.")
                b = r.read(256 * 1024)
                if not b:
                    break
                f.write(b)
                h.update(b)
                n += len(b)
                if avance and total:
                    avance(min(n / total, 1.0))
    except ErrorActualizar:
        raise
    except Exception as e:
        raise ErrorActualizar(f"No se pudo descargar la actualización ({getattr(e, 'reason', e)}).")
    if info.get("sha256") and h.hexdigest().lower() != info["sha256"].lower():
        os.remove(destino + ".part")
        raise ErrorActualizar("La descarga llegó dañada (no coincide la comprobación SHA256). Probá de nuevo.")
    os.replace(destino + ".part", destino)
    return destino


# ------------------------------------------------------------------ Android
def puede_instalar():
    """Android 8+: la app necesita «Instalar apps desconocidas» (una sola vez)."""
    try:
        from jnius import autoclass
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        return bool(act.getPackageManager().canRequestPackageInstalls())
    except Exception:
        return True


def abrir_permiso_instalar():
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        act.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                                 Uri.parse("package:" + act.getPackageName())))
        return True
    except Exception:
        return False


_escuchando = [False]


def _al_volver(intent):
    """El instalador avisa por aqui: si pide confirmacion, se abre la pantalla «¿Actualizar?» de Android."""
    try:
        from jnius import autoclass, cast
        PackageInstaller = autoclass("android.content.pm.PackageInstaller")
        Intent = autoclass("android.content.Intent")
        if intent is None or not intent.hasExtra(PackageInstaller.EXTRA_STATUS):
            return
        st = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -999)
        if st == PackageInstaller.STATUS_PENDING_USER_ACTION:
            conf = cast("android.content.Intent", intent.getParcelableExtra(Intent.EXTRA_INTENT))
            conf.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            autoclass("org.kivy.android.PythonActivity").mActivity.startActivity(conf)
        elif st != PackageInstaller.STATUS_SUCCESS:
            msg = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) or ""
            from kivy.clock import Clock
            import ui_k as ui
            Clock.schedule_once(lambda *_: ui.info(
                "Actualización", "Android no instaló la actualización" + (f" ({msg})." if msg else ".")
                + "\n\nSi dice que la app no es compatible o hay un conflicto, desinstalá Ctrl-P e instalá el APK "
                  "de nuevo (los proyectos están en Documentos/CTRL-P DOC y no se pierden)."), 0)
    except Exception:
        pass


def instalar(ruta):
    """Pasa el APK al instalador de Android (sesion de PackageInstaller)."""
    from jnius import autoclass
    act = autoclass("org.kivy.android.PythonActivity").mActivity
    PackageInstaller = autoclass("android.content.pm.PackageInstaller")
    SessionParams = autoclass("android.content.pm.PackageInstaller$SessionParams")
    Intent = autoclass("android.content.Intent")
    PendingIntent = autoclass("android.app.PendingIntent")
    if not _escuchando[0]:
        from android import activity
        activity.bind(on_new_intent=_al_volver)
        _escuchando[0] = True
    pi = act.getPackageManager().getPackageInstaller()
    params = SessionParams(SessionParams.MODE_FULL_INSTALL)
    sid = pi.createSession(params)
    s = pi.openSession(sid)
    tam = os.path.getsize(ruta)
    out = s.openWrite("ctrlp", 0, tam)
    with open(ruta, "rb") as f:
        while True:
            b = f.read(512 * 1024)
            if not b:
                break
            out.write(bytearray(b), 0, len(b))
    s.fsync(out)
    out.close()
    it = Intent(act, act.getClass())
    it.setAction("com.consorciohospitaltocoa.ctrlp.INSTALADO")
    it.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
    flags = PendingIntent.FLAG_UPDATE_CURRENT | 33554432          # FLAG_MUTABLE (Android 12+): el sistema agrega el estado
    pend = PendingIntent.getActivity(act, 0, it, flags)
    s.commit(pend.getIntentSender())
    s.close()
