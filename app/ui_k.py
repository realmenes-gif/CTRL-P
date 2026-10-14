"""
Ctrl-P Android - componentes de interfaz (Kivy)
===============================================
Misma paleta, fuente (Inter) y forma que la version de escritorio, pensado para tablet:
botones y campos grandes para el dedo, textos que siempre caben (saltan de linea),
dialogos que no bloquean (todo con funciones de respuesta).
"""

import os
import sys

from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image as KImage
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex, platform

import dibujos
from dibujos import C, fmt, fmt_pct, leer_num, txt_num  # noqa: F401  (se usan desde las paginas)

ANDROID = platform == "android"
FAM = "Roboto"
_OSC = False


# =========================================================================
#  Tema y fuentes
# =========================================================================
def recursos():
    return os.path.dirname(os.path.abspath(__file__))


def registrar_fuentes():
    global FAM
    d = os.path.join(recursos(), "fuentes")
    reg, bold = os.path.join(d, "Inter-Regular.ttf"), os.path.join(d, "Inter-Bold.ttf")
    if os.path.isfile(reg) and os.path.isfile(bold):
        LabelBase.register(name="Inter", fn_regular=reg, fn_bold=bold)
        FAM = "Inter"
    return FAM


def poner_oscuro(si):
    global _OSC
    _OSC = bool(si)


def oscuro():
    return _OSC


def col(k):
    return C[k][1 if _OSC else 0]


def rgba(k_o_hex, a=1.0):
    h = k_o_hex if k_o_hex.startswith("#") else col(k_o_hex)
    c = get_color_from_hex(h)
    return [c[0], c[1], c[2], a]


def sistema_oscuro():
    """Modo oscuro del sistema (Android); en la PC de prueba, claro."""
    if not ANDROID:
        return False
    try:
        from jnius import autoclass
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        cfg = act.getResources().getConfiguration()
        Configuration = autoclass("android.content.res.Configuration")
        return (cfg.uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
    except Exception:
        return False


# =========================================================================
#  Fondo con bordes redondeados (para cualquier widget)
# =========================================================================
class ConFondo:
    """Mezcla: pinta un rectangulo redondeado de fondo y un borde opcional."""

    def _fondo(self, color, borde=None, radio=12, ancho_borde=1):
        with self.canvas.before:
            self._c_f = Color(*color)
            self._r_f = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(radio)])
            if borde:
                self._c_b = Color(*borde)
                self._l_b = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(radio)),
                                 width=ancho_borde)
            else:
                self._l_b = None
        self._radio = radio
        self.bind(pos=self._mover_fondo, size=self._mover_fondo)

    def _mover_fondo(self, *_):
        self._r_f.pos, self._r_f.size = self.pos, self.size
        if self._l_b is not None:
            self._l_b.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(self._radio))

    def color_fondo(self, color):
        self._c_f.rgba = color


# =========================================================================
#  Textos
# =========================================================================
class Etiqueta(Label):
    """Texto que salta de linea al ancho disponible y ajusta su alto (nunca se corta)."""

    def __init__(self, texto="", tam=14, negrita=False, color="texto", alinear="left", ancho_fijo=None, una_linea=False,
                 **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(text=str(texto), font_size=sp(tam), bold=negrita, color=rgba(color), halign=alinear,
                         valign="middle", font_name=FAM, **kw)
        self._una = una_linea
        if ancho_fijo:
            self.size_hint_x = None
            self.width = dp(ancho_fijo)
        if una_linea:
            self.shorten = True
            self.shorten_from = "right"
        self.bind(width=self._tw)
        self._tw()
        self.bind(texture_size=self._alto)
        self.height = dp(18) if not self.text else max(dp(18), sp(tam) * 1.3)
        Clock.schedule_once(self._tw)

    def _tw(self, *_):
        self.text_size = (self.width, None)

    def _alto(self, *_):
        self.height = max(self.texture_size[1], dp(18)) if self.text else dp(18)


class EtiquetaNum(Label):
    """Celda de numero a la derecha, una linea."""

    def __init__(self, texto="", tam=13, negrita=False, color="texto", alinear="right", **kw):
        super().__init__(text=str(texto), font_size=sp(tam), bold=negrita, color=rgba(color), halign=alinear,
                         valign="middle", font_name=FAM, shorten=True, **kw)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))


# =========================================================================
#  Botones
# =========================================================================
class Boton(ButtonBehavior, Label, ConFondo):
    def __init__(self, texto="", primario=False, peligro=False, ancho=None, alto=44, al_tocar=None, tam=14,
                 plano=False, **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(text=texto, font_size=sp(tam), bold=True, font_name=FAM, halign="center", valign="middle", **kw)
        self.height = dp(alto)
        if ancho:
            self.size_hint_x = None
            self.width = dp(ancho)
        self.primario, self.peligro, self.plano = primario, peligro, plano
        self._colores()
        self._fondo(self._c_normal, None if (primario or peligro or plano) else rgba("borde"), radio=10)
        self.bind(size=lambda *_: setattr(self, "text_size", (self.width - dp(12), None)))
        self.bind(state=self._estado, disabled=self._estado)
        if al_tocar:
            self.bind(on_release=lambda *_: al_tocar())
        self._estado()

    def _colores(self):
        if self.primario:
            self._c_normal, self._c_toque, self.color = rgba("acento"), rgba("acento_h"), [1, 1, 1, 1]
        elif self.peligro:
            self._c_normal, self._c_toque, self.color = rgba("rojo"), rgba("rojo", 0.8), [1, 1, 1, 1]
        elif self.plano:
            self._c_normal, self._c_toque, self.color = [0, 0, 0, 0], rgba("suave"), rgba("acento")
        else:
            self._c_normal, self._c_toque, self.color = rgba("suave"), rgba("suave_h"), rgba("texto")

    def _estado(self, *_):
        c = self._c_toque if self.state == "down" else self._c_normal
        if self.disabled:
            c = [c[0], c[1], c[2], c[3] * 0.45]
        self.color_fondo(c)
        self.disabled_color = [self.color[0], self.color[1], self.color[2], 0.5]

    def poner_primario(self, si):
        self.primario = si
        self._colores()
        self._estado()


class BotonIcono(ButtonBehavior, AnchorLayout, ConFondo):
    """Boton cuadrado con un icono (PNG en memoria) o un simbolo."""

    def __init__(self, simbolo="", imagen=None, lado=44, al_tocar=None, activo=False, **kw):
        super().__init__(size_hint=(None, None), size=(dp(lado), dp(lado)), **kw)
        self._fondo(rgba("sel") if activo else rgba("suave"), radio=10)
        if imagen is not None:
            self.add_widget(imagen_kivy(imagen, lado * 0.6))
        else:
            self.add_widget(Label(text=simbolo, font_size=sp(18), bold=True, color=rgba("texto"), font_name=FAM))
        self.bind(state=lambda *_: self.color_fondo(rgba("suave_h") if self.state == "down" else
                                                     (rgba("sel") if activo else rgba("suave"))))
        if al_tocar:
            self.bind(on_release=lambda *_: al_tocar())


def imagen_kivy(pil, lado_dp=None):
    """PIL.Image -> widget Image de Kivy (sin archivos temporales)."""
    from kivy.core.image import Image as CoreImage
    import io
    b = io.BytesIO()
    pil.save(b, "PNG")
    b.seek(0)
    tex = CoreImage(b, ext="png").texture
    w = KImage(texture=tex, size_hint=(None, None), fit_mode="contain")
    if lado_dp:
        w.size = (dp(lado_dp), dp(lado_dp))
    else:
        w.size = (dp(pil.width), dp(pil.height))
    return w


def textura(pil):
    from kivy.graphics.texture import Texture
    img = pil.convert("RGBA")
    tex = Texture.create(size=img.size, colorfmt="rgba")
    tex.blit_buffer(img.tobytes(), colorfmt="rgba", bufferfmt="ubyte")
    tex.flip_vertical()
    return tex


# =========================================================================
#  Campos
# =========================================================================
class Campo(TextInput):
    mayus = BooleanProperty(False)
    numerico = BooleanProperty(False)

    def __init__(self, texto="", pista="", ancho=None, alto=44, mayus=False, numerico=False, clave=False,
                 al_cambiar=None, al_enter=None, alinear="left", negrita=False, tam=14, **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(text=str(texto or ""), hint_text=pista, multiline=False, password=clave,
                         font_size=sp(tam), font_name=FAM, write_tab=False, halign=alinear, do_wrap=False, **kw)
        self.mayus, self.numerico = mayus, numerico
        self.height = dp(alto)
        if ancho:
            self.size_hint_x = None
            self.width = dp(ancho)
        self.padding = [dp(10), (dp(alto) - sp(tam) * 1.2) / 2, dp(10), 0]
        self.background_normal = self.background_active = ""
        self.background_disabled_normal = ""
        self.background_color = rgba("campo")
        self.foreground_color = rgba("texto")
        self.disabled_foreground_color = rgba("texto2")
        self.hint_text_color = rgba("texto2", 0.8)
        self.cursor_color = rgba("acento")
        self.selection_color = rgba("acento", 0.35)
        if negrita:
            self.bold = True
        if numerico:
            self.input_type = "number"
        with self.canvas.after:
            self._c_borde = Color(*rgba("campo_borde"))
            self._borde = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)), width=1)
        self.bind(pos=self._mover, size=self._mover, focus=self._foco)
        if al_cambiar:
            self.bind(text=lambda *_: al_cambiar(self.text))
        if al_enter:
            self.bind(on_text_validate=lambda *_: al_enter())

    def _mover(self, *_):
        self._borde.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(8))

    def _foco(self, *_):
        self._c_borde.rgba = rgba("acento") if self.focus else rgba("campo_borde")
        self._borde.width = 1.6 if self.focus else 1

    def marcar(self, color_k):
        """Borde de color (rojo = error, acento = escrito)."""
        if not self.focus:
            self._c_borde.rgba = rgba(color_k) if color_k else rgba("campo_borde")

    def insert_text(self, substring, from_undo=False):
        if self.mayus:
            substring = substring.upper()
        if self.numerico:
            substring = "".join(ch for ch in substring if ch in "0123456789.-,")
        return super().insert_text(substring, from_undo=from_undo)

    def numero(self):
        return leer_num(self.text)


# =========================================================================
#  Contenedores
# =========================================================================
class Tarjeta(BoxLayout, ConFondo):
    def __init__(self, relleno=18, espacio=10, fondo="tarjeta", borde=True, radio=14, ajustar_alto=True, **kw):
        kw.setdefault("orientation", "vertical")
        if ajustar_alto:
            kw.setdefault("size_hint_y", None)
        super().__init__(padding=dp(relleno), spacing=dp(espacio), **kw)
        self._fondo(rgba(fondo), rgba("borde") if borde else None, radio=radio)
        if ajustar_alto:
            self.height = 0
            self.bind(minimum_height=self.setter("height"))

    def fila(self, titulo, control=None, ayuda="", ancho_control=None):
        """Fila tipo ajuste: titulo y ayuda a la izquierda, control a la derecha."""
        f = BoxLayout(size_hint_y=None, spacing=dp(14))
        izq = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        e1 = Etiqueta(titulo, 14, True)
        izq.add_widget(e1)
        if ayuda:
            izq.add_widget(Etiqueta(ayuda, 12, color="texto2"))
        izq.bind(minimum_height=izq.setter("height"))
        f.add_widget(izq)
        if control is not None:
            caja = AnchorLayout(anchor_x="right", anchor_y="center", size_hint=(None, None))
            caja.add_widget(control)

            def ajustar(*_):
                caja.width = control.width if control.size_hint_x is None else dp(ancho_control or 220)
                caja.height = control.height
            control.bind(size=ajustar)
            ajustar()
            f.add_widget(caja)

            def alto(*_):
                f.height = max(izq.height, caja.height)
            izq.bind(height=alto)
            caja.bind(height=alto)
            alto()
        else:
            izq.bind(height=lambda *_: setattr(f, "height", izq.height))
        self.add_widget(f)
        return f


def par(*tarjetas, espacio=16):
    """Tarjetas lado a lado con el mismo alto (el de la mas alta)."""
    f = BoxLayout(orientation="horizontal", size_hint_y=None, spacing=dp(espacio))
    for t in tarjetas:
        t.unbind(minimum_height=t.setter("height"))
        t.size_hint_y = 1
        f.add_widget(t)

    def alto(*_):
        f.height = max(t.minimum_height for t in tarjetas)
    for t in tarjetas:
        t.bind(minimum_height=alto)
    alto()
    return f


class Columna(GridLayout):
    """Columna que crece con su contenido (para poner dentro de un Desplazable)."""

    def __init__(self, espacio=12, relleno=0, **kw):
        super().__init__(cols=1, spacing=dp(espacio), padding=dp(relleno), size_hint_y=None, **kw)
        self.height = 0
        self.bind(minimum_height=self.setter("height"))


class Fila(BoxLayout):
    """Fila horizontal de alto fijo."""

    def __init__(self, alto=44, espacio=8, **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(orientation="horizontal", spacing=dp(espacio), **kw)
        self.height = dp(alto)

    def add_widget(self, w, *a, **kw):
        if isinstance(w, Etiqueta):        # textos centrados en vertical dentro de la fila
            caja = AnchorLayout(anchor_y="center")
            caja.size_hint_x = w.size_hint_x
            if w.size_hint_x is None:
                caja.width = w.width
            caja.add_widget(w)
            return super().add_widget(caja, *a, **kw)
        return super().add_widget(w, *a, **kw)


class Desplazable(ScrollView):
    def __init__(self, contenido=None, **kw):
        kw.setdefault("bar_width", dp(6))
        kw.setdefault("scroll_type", ["bars", "content"])
        kw.setdefault("effect_cls", "ScrollEffect")
        super().__init__(**kw)
        self.bar_color = rgba("texto2", 0.6)
        self.bar_inactive_color = rgba("texto2", 0.25)
        self.contenido = contenido or Columna()
        self.add_widget(self.contenido)


class Espacio(Widget):
    def __init__(self, alto=8, ancho=None, **kw):
        if ancho is None:
            super().__init__(size_hint_y=None, height=dp(alto), **kw)
        else:
            super().__init__(size_hint=(None, None), width=dp(ancho), height=dp(alto), **kw)


class Separador(Widget):
    def __init__(self, **kw):
        super().__init__(size_hint_y=None, height=dp(1), **kw)
        with self.canvas:
            Color(*rgba("borde"))
            self._r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._r, "pos", self.pos), size=lambda *_: setattr(self._r, "size", self.size))


# =========================================================================
#  Controles
# =========================================================================
class Interruptor(ButtonBehavior, Widget):
    activo = BooleanProperty(False)

    def __init__(self, activo=False, al_cambiar=None, **kw):
        super().__init__(size_hint=(None, None), size=(dp(52), dp(30)), **kw)
        self.activo = activo
        self._cb = al_cambiar
        with self.canvas:
            self._c1 = Color()
            self._riel = RoundedRectangle(radius=[dp(15)])
            self._c2 = Color(1, 1, 1, 1)
            from kivy.graphics import Ellipse
            self._bola = Ellipse()
        self.bind(pos=self._dib, size=self._dib, activo=self._dib, disabled=self._dib)
        self._dib()

    def _dib(self, *_):
        a = 0.45 if self.disabled else 1
        self._c1.rgba = rgba("acento", a) if self.activo else rgba("campo_borde", a)
        self._riel.pos, self._riel.size = self.pos, self.size
        d = self.height - dp(6)
        x = self.right - dp(3) - d if self.activo else self.x + dp(3)
        self._bola.pos, self._bola.size = (x, self.y + dp(3)), (d, d)

    def on_release(self):
        self.activo = not self.activo
        if self._cb:
            self._cb(self.activo)


class Casilla(ButtonBehavior, BoxLayout):
    """Casilla de verificacion con texto (todo el renglon se toca)."""
    activo = BooleanProperty(False)

    def __init__(self, texto, activo=False, al_cambiar=None, tam=14, negrita=True, **kw):
        super().__init__(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(36), **kw)
        self.activo = activo
        self._cb = al_cambiar
        self.caja = Widget(size_hint=(None, None), size=(dp(24), dp(24)))
        anc = AnchorLayout(size_hint_x=None, width=dp(28))
        anc.add_widget(self.caja)
        self.add_widget(anc)
        self.lbl = Etiqueta(texto, tam, negrita)
        caja_l = AnchorLayout(anchor_y="center")
        caja_l.add_widget(self.lbl)
        self.add_widget(caja_l)
        self.lbl.bind(height=lambda *_: setattr(self, "height", max(dp(36), self.lbl.height + dp(8))))
        with self.caja.canvas:
            self._cf = Color()
            self._rf = RoundedRectangle(radius=[dp(5)])
            self._cv = Color(1, 1, 1, 1)
            self._chk = Line(width=dp(1.6))
            self._cb_c = Color()
            self._borde = Line(width=1)
        self.caja.bind(pos=self._dib, size=self._dib)
        self.bind(activo=self._dib, disabled=self._dib)
        self._dib()

    def _dib(self, *_):
        c = self.caja
        a = 0.45 if self.disabled else 1
        self._cf.rgba = rgba("acento", a) if self.activo else rgba("campo", a)
        self._rf.pos, self._rf.size = c.pos, c.size
        self._cb_c.rgba = rgba("acento", a) if self.activo else rgba("campo_borde", a)
        self._borde.rounded_rectangle = (c.x, c.y, c.width, c.height, dp(5))
        if self.activo:
            self._chk.points = [c.x + c.width * .22, c.y + c.height * .52, c.x + c.width * .42, c.y + c.height * .3,
                                c.x + c.width * .78, c.y + c.height * .72]
        else:
            self._chk.points = []

    def on_release(self):
        self.activo = not self.activo
        if self._cb:
            self._cb(self.activo)


class Menu(Boton):
    """Lista desplegable: muestra el valor elegido; al tocar se abre la lista."""

    def __init__(self, opciones, valor=None, ancho=None, al_cambiar=None, alto=44, **kw):
        self.opciones = list(opciones)
        self.valor = valor if valor is not None else (self.opciones[0] if self.opciones else "")
        super().__init__(texto="", ancho=ancho, alto=alto, al_tocar=self.abrir, tam=13, **kw)
        self.bold = False
        self.halign = "left"
        self._cb = al_cambiar
        self._pintar()

    def _pintar(self):
        self.text = f"{self.valor}   ▼"

    def poner(self, v, avisar=False):
        self.valor = v
        self._pintar()
        if avisar and self._cb:
            self._cb(v)

    def abrir(self):
        dd = DropDown(auto_width=False, width=max(self.width, dp(220)), max_height=Window.height * 0.6)
        with dd.container.canvas.before:
            Color(*rgba("tarjeta"))
            r = Rectangle()
        dd.container.bind(pos=lambda *_: setattr(r, "pos", dd.container.pos),
                          size=lambda *_: setattr(r, "size", dd.container.size))
        for op in self.opciones:
            b = Boton(op, alto=44, plano=True, tam=13)
            b.bold = op == self.valor
            b.halign = "left"
            b.color = rgba("texto")
            b.bind(on_release=lambda w, op=op: dd.select(op))
            dd.add_widget(b)
        dd.bind(on_select=lambda _, v: self.poner(v, True))
        dd.open(self)


class Segmentado(BoxLayout, ConFondo):
    def __init__(self, opciones, valor=None, al_cambiar=None, ancho=None, alto=40, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(alto), padding=dp(3), spacing=dp(3), **kw)
        if ancho:
            self.size_hint_x = None
            self.width = dp(ancho)
        self._fondo(rgba("suave"), radio=10)
        self.valor = valor or opciones[0]
        self._cb = al_cambiar
        self.botones = {}
        for op in opciones:
            b = Boton(op, alto=alto - 6, tam=13, plano=True)
            b.bind(on_release=lambda w, op=op: self.poner(op, True))
            self.botones[op] = b
            self.add_widget(b)
        self._pintar()

    def _pintar(self):
        for op, b in self.botones.items():
            sel = op == self.valor
            b._c_normal = rgba("tarjeta") if sel else [0, 0, 0, 0]
            b.color = rgba("texto") if sel else rgba("texto2")
            b._estado()

    def poner(self, v, avisar=False):
        self.valor = v
        self._pintar()
        if avisar and self._cb:
            self._cb(v)


class Contador(BoxLayout):
    def __init__(self, valor=1, minimo=1, maximo=99, al_cambiar=None, **kw):
        super().__init__(orientation="horizontal", size_hint=(None, None), size=(dp(150), dp(44)), spacing=dp(6), **kw)
        self.v, self.minimo, self.maximo, self._cb = valor, minimo, maximo, al_cambiar
        self.add_widget(Boton("−", ancho=44, al_tocar=lambda: self.poner(self.v - 1)))
        self.lbl = Label(text=str(valor), font_size=sp(16), bold=True, color=rgba("texto"), font_name=FAM)
        self.add_widget(self.lbl)
        self.add_widget(Boton("+", ancho=44, al_tocar=lambda: self.poner(self.v + 1)))

    def poner(self, v):
        v = max(self.minimo, min(self.maximo, v))
        if v != self.v:
            self.v = v
            self.lbl.text = str(v)
            if self._cb:
                self._cb(v)


class Chip(Label, ConFondo):
    def __init__(self, texto, **kw):
        super().__init__(text=f"  {texto}  ", font_size=sp(12), bold=True, color=rgba("texto"), font_name=FAM,
                         size_hint=(None, None), height=dp(28), **kw)
        self._fondo(rgba("suave"), radio=14)
        self.bind(texture_size=lambda *_: setattr(self, "width", self.texture_size[0] + dp(16)))


class Flujo(BoxLayout):
    """Pone widgets de ancho fijo en renglones (como texto)."""

    def __init__(self, widgets, espacio=6, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(espacio), **kw)
        self._ws = list(widgets)
        self._esp = espacio
        self.bind(width=lambda *_: Clock.schedule_once(self._armar))
        Clock.schedule_once(self._armar)

    def _armar(self, *_):
        for w in self._ws:
            if w.parent:
                w.parent.remove_widget(w)
        self.clear_widgets()
        fila, ancho = None, 0
        for w in self._ws:
            if fila is None or ancho + w.width > self.width:
                fila = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(self._esp))
                self.add_widget(fila)
                ancho = 0
            fila.add_widget(w)
            ancho += w.width + dp(self._esp)
        if fila is not None:
            fila.add_widget(Widget())
        n = len(self.children)
        self.height = n * dp(28) + max(0, n - 1) * dp(self._esp)


# =========================================================================
#  Dialogos (no bloquean: responden con funciones)
# =========================================================================
class Dialogo(ModalView):
    def __init__(self, titulo, ancho=560, cerrar_afuera=False, **kw):
        super().__init__(size_hint=(None, None), auto_dismiss=cerrar_afuera, background_color=[0, 0, 0, 0.45],
                         background="", **kw)
        self.width = min(dp(ancho), Window.width - dp(32))
        self.caja = Tarjeta(relleno=24, espacio=12, size_hint_y=None)
        self.caja.add_widget(Etiqueta(titulo, 20, True))
        self.cuerpo = Columna(espacio=10)
        self.desp = Desplazable(self.cuerpo, size_hint_y=None, do_scroll_x=False)
        self.caja.add_widget(self.desp)
        self.pie = Fila(alto=48, espacio=10)
        self.caja.add_widget(self.pie)
        self.add_widget(self.caja)
        self.cuerpo.bind(height=self._alto)
        Window.bind(height=self._alto)
        self.bind(on_dismiss=lambda *_: Window.unbind(height=self._alto))

    def _alto(self, *_):
        maxh = Window.height - dp(60) - Window.keyboard_height
        fijo = dp(24) * 2 + dp(12) * 2 + dp(48) + dp(34)
        self.desp.height = min(self.cuerpo.height, maxh - fijo)
        self.height = self.desp.height + fijo
        self.caja.height = self.height

    def botones(self, textos, primario=None, al_elegir=None, ancho=None):
        self.pie.clear_widgets()
        self.pie.add_widget(Widget())
        for k, t in enumerate(textos):
            b = Boton(t, primario=(k == primario), ancho=ancho or max(110, 14 + 9 * len(t)))
            b.bind(on_release=lambda w, k=k: al_elegir(k) if al_elegir else self.dismiss())
            self.pie.add_widget(b)


def info(titulo, texto, al_cerrar=None):
    d = Dialogo(titulo)
    d.cuerpo.add_widget(Etiqueta(texto, 14, color="texto2"))

    def fin(_):
        d.dismiss()
        if al_cerrar:
            al_cerrar()
    d.botones(["Aceptar"], 0, fin)
    d.open()
    return d


def preguntar(titulo, texto, al_responder, si="Sí", no="Cancelar", peligro=False):
    d = Dialogo(titulo)
    d.cuerpo.add_widget(Etiqueta(texto, 14, color="texto2"))

    def fin(k):
        d.dismiss()
        al_responder(k == 1)
    d.botones([no, si], 1, fin)
    d.open()
    return d


def opciones(titulo, texto, textos, al_elegir, primario=None):
    """Varias opciones; al_elegir(indice) o None si cancela."""
    d = Dialogo(titulo)
    d.cuerpo.add_widget(Etiqueta(texto, 14, color="texto2"))

    def fin(k):
        d.dismiss()
        al_elegir(k)
    d.botones(textos, primario if primario is not None else len(textos) - 1, fin)
    d.open()
    return d


def formulario(titulo, subtitulo, campos, textos, al_aceptar, validar=None):
    """campos: [(clave, etiqueta, es_clave, inicial[, mayus])] -> al_aceptar(dict) (no se llama si cancela)."""
    d = Dialogo(titulo)
    if subtitulo:
        d.cuerpo.add_widget(Etiqueta(subtitulo, 13, color="texto2"))
    ent = {}
    for c in campos:
        k, et, es_clave, ini = c[:4]
        may = c[4] if len(c) > 4 else False
        d.cuerpo.add_widget(Etiqueta(et, 13, True))
        e = Campo(ini, clave=es_clave, mayus=may)
        ent[k] = e
        d.cuerpo.add_widget(e)
    err = Etiqueta("", 13, color="rojo")
    d.cuerpo.add_widget(err)

    def fin(k):
        if k == 0:
            d.dismiss()
            return
        vals = {kk: e.text for kk, e in ent.items()}
        if validar:
            msg = validar(vals)
            if msg:
                err.text = msg
                return
        d.dismiss()
        al_aceptar(vals)
    d.botones(textos, 1, fin)
    d.open()
    if campos:
        Clock.schedule_once(lambda *_: setattr(list(ent.values())[0], "focus", True), 0.3)
    return d


def aviso(texto, segundos=2.8):
    """Mensaje corto abajo de la pantalla."""
    ancho = min(Window.width - dp(40), dp(620))
    lbl = Label(text=texto, font_size=sp(14), bold=True, color=[1, 1, 1, 1], font_name=FAM, size_hint=(None, None),
                halign="center", valign="middle", text_size=(ancho - dp(32), None))
    lbl.texture_update()
    lbl.size = (ancho, max(dp(48), lbl.texture_size[1] + dp(24)))
    with lbl.canvas.before:
        Color(0.12, 0.15, 0.19, 0.92)
        r = RoundedRectangle(radius=[dp(12)], pos=lbl.pos, size=lbl.size)
    lbl.bind(pos=lambda *_: setattr(r, "pos", lbl.pos), size=lambda *_: setattr(r, "size", lbl.size))
    lbl.pos = ((Window.width - lbl.width) / 2, dp(30))
    Window.add_widget(lbl)
    Clock.schedule_once(lambda *_: Window.remove_widget(lbl), segundos)


# =========================================================================
#  Archivos (explorador propio: funciona igual en la tablet y en la PC de prueba)
# =========================================================================
def raiz_almacenamiento():
    if ANDROID:
        try:
            from android.storage import primary_external_storage_path
            return primary_external_storage_path()
        except Exception:
            return "/storage/emulated/0"
    return os.path.expanduser("~")


def carpeta_docs(cfg=None):
    """Carpeta por defecto: Documentos/CTRL-P DOC (se puede cambiar en Apariencia)."""
    elegida = (cfg or {}).get("carpeta_docs")
    if elegida and os.path.isdir(elegida):
        return elegida
    for base in (os.path.join(raiz_almacenamiento(), "Documents"), raiz_almacenamiento()):
        ruta = os.path.join(base, dibujos.NOMBRE_DOCS)
        try:
            os.makedirs(ruta, exist_ok=True)
            return ruta
        except OSError:
            continue
    return raiz_almacenamiento()


class Explorador(Dialogo):
    """Elegir un archivo para abrir, o carpeta y nombre para guardar."""

    def __init__(self, titulo, inicio, extensiones=(), guardar=False, nombre="", al_elegir=None, carpeta=False):
        super().__init__(titulo, ancho=760)
        self.ext = tuple(e.lower() for e in extensiones)
        self.guardar, self.cb, self.solo_carpeta = guardar, al_elegir, carpeta
        self.ruta = inicio if os.path.isdir(inicio) else raiz_almacenamiento()
        self.v_ruta = Etiqueta("", 12, color="texto2")
        arriba = Fila(alto=44)
        arriba.add_widget(Boton("↑ Subir", ancho=100, al_tocar=self.subir))
        arriba.add_widget(Boton("Documentos", ancho=130, al_tocar=lambda: self.ir(carpeta_docs())))
        arriba.add_widget(Boton("Descargas", ancho=120, al_tocar=lambda: self.ir(
            os.path.join(raiz_almacenamiento(), "Download"))))
        arriba.add_widget(Widget())
        arriba.add_widget(Boton("+ Carpeta", ancho=110, al_tocar=self.nueva_carpeta))
        self.cuerpo.add_widget(arriba)
        self.cuerpo.add_widget(self.v_ruta)
        self.lista = Columna(espacio=2)
        self.cuerpo.add_widget(self.lista)
        self.e_nombre = None
        if guardar:
            self.cuerpo.add_widget(Etiqueta("Nombre del archivo", 13, True))
            self.e_nombre = Campo(nombre)
            self.cuerpo.add_widget(self.e_nombre)
        self.botones(["Cancelar"] + (["Guardar aquí"] if guardar else (["Elegir esta carpeta"] if carpeta else [])),
                     1 if (guardar or carpeta) else None, self._fin)
        self.ir(self.ruta)

    def _fin(self, k):
        if k == 0:
            self.dismiss()
            return
        if self.solo_carpeta:
            self.dismiss()
            self.cb(self.ruta)
            return
        n = (self.e_nombre.text or "").strip()
        if not n:
            aviso("Escribí un nombre de archivo.")
            return
        if self.ext and not n.lower().endswith(self.ext):
            n += self.ext[0]
        destino = os.path.join(self.ruta, n)

        def seguir(si=True):
            if si:
                self.dismiss()
                self.cb(destino)
        if os.path.exists(destino):
            preguntar("Ya existe", f"Ya existe «{n}» en esta carpeta. ¿Reemplazarlo?", seguir, si="Reemplazar")
        else:
            seguir()

    def subir(self):
        padre = os.path.dirname(self.ruta.rstrip("/"))
        if padre and padre != self.ruta:
            self.ir(padre)

    def nueva_carpeta(self):
        def crear(v):
            try:
                os.makedirs(os.path.join(self.ruta, v["n"].strip()), exist_ok=True)
            except OSError as e:
                info("Carpeta", f"No se pudo crear la carpeta:\n{e}")
            self.ir(self.ruta)
        formulario("Nueva carpeta", "", [("n", "Nombre", False, "")], ["Cancelar", "Crear"], crear,
                   validar=lambda v: "" if v["n"].strip() else "Escribí un nombre.")

    def ir(self, ruta):
        try:
            nombres = sorted(os.listdir(ruta), key=lambda s: s.lower())
        except OSError:
            aviso("No se puede abrir esa carpeta.")
            return
        self.ruta = ruta
        self.v_ruta.text = ruta
        self.lista.clear_widgets()
        carpetas = [n for n in nombres if not n.startswith(".") and os.path.isdir(os.path.join(ruta, n))]
        archivos = [n for n in nombres if not n.startswith(".") and os.path.isfile(os.path.join(ruta, n))
                    and (not self.ext or n.lower().endswith(self.ext))]
        for n in carpetas:
            b = Boton(f"{n} /", plano=True, alto=46, tam=14)
            b.halign = "left"
            b.color = rgba("texto")
            b.bind(on_release=lambda w, n=n: self.ir(os.path.join(ruta, n)))
            self.lista.add_widget(b)
        if not self.solo_carpeta:
            for n in archivos:
                b = Boton(f"     {n}", plano=True, alto=46, tam=14)
                b.halign = "left"
                b.bold = False
                b.color = rgba("acento")
                b.bind(on_release=lambda w, n=n: self._archivo(n))
                self.lista.add_widget(b)
        if not carpetas and not archivos:
            self.lista.add_widget(Etiqueta("Carpeta vacía", 13, color="texto2"))

    def _archivo(self, n):
        if self.guardar:
            self.e_nombre.text = n
            return
        self.dismiss()
        self.cb(os.path.join(self.ruta, n))


def elegir_archivo(titulo, inicio, extensiones, al_elegir):
    Explorador(titulo, inicio, extensiones, al_elegir=al_elegir).open()


def guardar_archivo(titulo, inicio, nombre, extensiones, al_elegir):
    Explorador(titulo, inicio, extensiones, guardar=True, nombre=nombre, al_elegir=al_elegir).open()


def elegir_carpeta(titulo, inicio, al_elegir):
    Explorador(titulo, inicio, carpeta=True, al_elegir=al_elegir).open()


MIMES = {".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".pdf": "application/pdf",
         ".png": "image/png", ".jpg": "image/jpeg", ".ctrlp": "application/zip"}


def compartir_archivo(ruta, tipo=None):
    """Abre el archivo con otra app de la tablet (Excel, visor de PDF o imagenes). En la PC de prueba no hace nada."""
    if not ANDROID:
        return False
    try:
        from jnius import autoclass, cast
        tipo = tipo or MIMES.get(os.path.splitext(ruta)[1].lower(), "*/*")
        StrictMode = autoclass("android.os.StrictMode")
        Builder = autoclass("android.os.StrictMode$VmPolicy$Builder")
        StrictMode.setVmPolicy(Builder().build())
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        File = autoclass("java.io.File")
        act = PythonActivity.mActivity
        it = Intent(Intent.ACTION_VIEW)
        it.setDataAndType(Uri.fromFile(File(ruta)), tipo)
        it.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK)
        String = autoclass("java.lang.String")
        act.startActivity(Intent.createChooser(it, cast("java.lang.CharSequence", String("Abrir con"))))
        return True
    except Exception:
        return False


def ofrecer_abrir(titulo, texto, ruta):
    """Despues de exportar: avisa donde quedo y ofrece abrirlo con otra app."""
    if ANDROID:
        preguntar(titulo, texto, lambda si: si and (compartir_archivo(ruta) or
                                                     info(titulo, "No hay una app para abrir este archivo.")),
                  si="Abrir", no="Cerrar")
    else:
        info(titulo, texto)
