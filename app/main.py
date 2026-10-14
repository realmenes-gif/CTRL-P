"""
Arranque de Ctrl-P en Android.
Si algo falla al abrir, el detalle se guarda en un archivo y se muestra en pantalla
en lugar de cerrar la app sin explicacion.
"""

import os
import sys
import time
import traceback

_RUTAS = []

# En Android la carpeta "personal" (HOME) apunta a /data, donde la app no puede escribir.
# Se usa la carpeta privada de la app para la configuracion y los temporales.
if os.environ.get("ANDROID_PRIVATE") or os.environ.get("ANDROID_ARGUMENT") is not None:
    _priv = os.environ.get("ANDROID_PRIVATE") or os.path.dirname(os.path.abspath(__file__))
    os.environ["HOME"] = _priv
    _tmp = os.path.join(_priv, "tmp")
    try:
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
    except Exception:
        pass


def _rutas_registro():
    if _RUTAS:
        return _RUTAS
    candidatas = [
        "/storage/emulated/0/Download/CtrlP_error_inicio.txt",
        "/storage/emulated/0/Documents/CtrlP_error_inicio.txt",
        os.path.join(os.environ.get("ANDROID_PRIVATE") or os.path.dirname(os.path.abspath(__file__)),
                     "CtrlP_error_inicio.txt"),
    ]
    _RUTAS.extend(candidatas)
    return _RUTAS


def _escribir(texto, modo="a"):
    escritas = []
    for r in _rutas_registro():
        try:
            os.makedirs(os.path.dirname(r), exist_ok=True)
            with open(r, modo, encoding="utf-8") as f:
                f.write(texto)
            escritas.append(r)
        except Exception:
            pass
    return escritas


def paso(texto):
    _escribir(f"{time.strftime('%H:%M:%S')}  {texto}\n")
    if texto == "inicio de sesion en pantalla":
        # Abrio bien: no dejar el archivo de diagnostico en Descargas ni en Documentos.
        for r in _rutas_registro()[:2]:
            try:
                os.remove(r)
            except Exception:
                pass


_escribir(f"Ctrl-P · arranque {time.strftime('%Y-%m-%d %H:%M:%S')}\nPython {sys.version}\n", "w")

# Errores nativos (cierres sin traceback de Python) tambien quedan en el archivo.
_fh = None
try:
    import faulthandler
    for _r in _rutas_registro():
        try:
            _fh = open(_r, "a", encoding="utf-8")
            faulthandler.enable(_fh, all_threads=True)
            break
        except Exception:
            _fh = None
except Exception:
    pass


def _mostrar_error(texto):
    """Pantalla minima con el error, para poder mandar una captura."""
    from kivy.app import App
    from kivy.core.window import Window
    from kivy.metrics import dp
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    Window.clearcolor = (0.93, 0.95, 0.97, 1)

    class Error(App):
        title = "Ctrl-P · error al abrir"

        def build(self):
            sv = ScrollView(do_scroll_x=False)
            lb = Label(text="[b]Ctrl-P no pudo abrir.[/b] Mandá una captura de esta pantalla.\n\n" + texto,
                       markup=True, color=(0.1, 0.12, 0.16, 1), font_size=dp(13), halign="left", valign="top",
                       size_hint_y=None, padding=(dp(16), dp(16)))
            lb.bind(width=lambda w, v: setattr(w, "text_size", (v - dp(32), None)),
                    texture_size=lambda w, v: setattr(w, "height", v[1] + dp(32)))
            sv.add_widget(lb)
            return sv

    Error().run()


def _texto_error():
    tb = traceback.format_exc()
    if len(tb) > 6000:
        tb = tb[:1500] + "\n...\n" + tb[-4500:]
    return tb


if __name__ == "__main__":
    try:
        paso("importando la app")
        import ctrlp_app
        paso("app importada; abriendo ventana")
        ctrlp_app.ARRANQUE = paso
        ctrlp_app.CtrlPApp().run()
        paso("app cerrada normalmente")
    except Exception:
        tb = _texto_error()
        donde = _escribir("\n===== ERROR AL ABRIR\n" + tb + "\n")
        try:
            _mostrar_error(tb + "\n\nGuardado en:\n" + "\n".join(donde))
        except Exception:
            _escribir("\n===== Tampoco se pudo mostrar la pantalla de error\n" + _texto_error() + "\n")
            raise
