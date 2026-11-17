"""
Ctrl-P Android - Tarjeta liviana
================================
El mismo principio que la tabla virtual de la computadora: la tarjeta de un edificio (nombre, total y una
casilla por nivel) se DIBUJA en el canvas en lugar de armarse con una etiqueta y un cuadro de texto por renglón.
Al tocar una casilla aparece UN solo cuadro de texto encima (el editor); al salir, el valor vuelve al dibujo.
Un proyecto grande pasa de ~1000 controles a unas decenas, y la pantalla se arma al instante.
"""

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, PopMatrix, PushMatrix, Rectangle, RoundedRectangle, Translate
from kivy.metrics import dp, sp
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.widget import Widget

import ui_k as ui
from ui_k import Campo, es_cero, rgba

_TEX = {}


def _textura(texto, tam, negrita, color, ancho_max=None, partir=False):
    k = (texto, tam, negrita, tuple(color), ancho_max, partir)
    t = _TEX.get(k)
    if t is None:
        kw = dict(text=texto, font_size=sp(tam), bold=negrita, color=color, font_name=ui.FAM)
        cl = CoreLabel(**kw)
        cl.refresh()
        t = cl.texture
        if ancho_max and t.width > ancho_max and partir:    # no entra: en dos renglones
            cl = CoreLabel(text_size=(ancho_max, None), max_lines=2, **kw)
            cl.refresh()
            t = cl.texture
        elif ancho_max and t.width > ancho_max:             # no entra: se acorta con «…»
            cl = CoreLabel(text_size=(ancho_max, None), shorten=True, shorten_from="right", max_lines=1, **kw)
            cl.refresh()
            t = cl.texture
        if len(_TEX) > 3000:
            _TEX.clear()
        _TEX[k] = t
    return t


class TarjetaLiviana(Widget):
    """filas: dicts {etiq, st (lista [texto, original]), sub (renglón de tipo, más chico), negrita,
    fijo (no editable por sí mismo), grupo (índice del renglón que suma los tipos)}."""

    RELLENO, CAB, ESP = 14, 34, 6

    def __init__(self, titulo, total, total_color, filas, al_cambiar=None, al_final=None, **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(**kw)
        self.titulo, self.total, self.total_color = titulo, total, total_color
        self.filas = filas
        self.al_cambiar, self.al_final = al_cambiar, al_final
        self.editor, self.i_ed = None, None
        self.height = dp(self.RELLENO * 2 + self.CAB) + sum(dp((42 if f.get("sub") else 46) + self.ESP)
                                                             for f in filas)
        self._sumar_todos()
        self._pend = False
        self.bind(size=self.marcar)
        self.bind(pos=self._mover)
        self.marcar()

    # ------------------------------------------------------------ geometría (coordenadas locales, y hacia arriba)
    def _cajas(self):
        """[(y_renglon, alto_renglon, caja_x, caja_ancho, caja_alto)] por fila."""
        out, y = [], self.height - dp(self.RELLENO + self.CAB + self.ESP)
        for f in self.filas:
            alto = dp(42 if f.get("sub") else 46)
            y -= alto
            ca, ch = dp(130 if f.get("sub") else 150), dp(40 if f.get("sub") else 44)
            out.append((y, alto, self.width - dp(self.RELLENO) - ca, ca, ch))
            y -= dp(self.ESP)
        return out

    def editable(self, i):
        f = self.filas[i]
        return not f.get("fijo") and not f.get("_sumado")

    # ------------------------------------------------------------ dibujo
    def marcar(self, *_):
        if not self._pend:
            self._pend = True
            Clock.schedule_once(self._dibujar, -1)

    def _mover(self, *_):
        if hasattr(self, "_tr"):
            self._tr.xy = self.pos
        if self.editor is not None:
            self._poner_editor()

    def _dibujar(self, *_):
        self._pend = False
        w, h = self.width, self.height
        if w <= 1:
            return
        R = dp(self.RELLENO)
        cv = self.canvas.before          # el editor (hijo) se dibuja en self.canvas, encima
        cv.clear()
        with cv:
            PushMatrix()
            self._tr = Translate(self.x, self.y)
            Color(*rgba("tarjeta"))
            RoundedRectangle(pos=(0, 0), size=(w, h), radius=[dp(14)])
            Color(*rgba("borde"))
            Line(rounded_rectangle=(0, 0, w, h, dp(14)), width=1)
            ct = rgba(self.total_color)
            t_tot = _textura(self.total, 15, True, ct)
            t_tit = _textura(self.titulo, 16, True, rgba("texto"), max(10, int(w - 2 * R - t_tot.width - dp(10))))
            yc = h - R - dp(self.CAB) / 2
            Color(1, 1, 1, 1)
            Rectangle(texture=t_tit, pos=(R, yc - t_tit.height / 2), size=t_tit.size)
            Rectangle(texture=t_tot, pos=(w - R - t_tot.width, yc - t_tot.height / 2), size=t_tot.size)
            for i, (f, (y, alto, cx, ca, ch)) in enumerate(zip(self.filas, self._cajas())):
                sub = f.get("sub")
                xl = R + (dp(26) if sub else 0)
                te = _textura(f["etiq"], 13 if sub else 14, bool(f.get("negrita")) and not sub,
                              rgba("texto2" if sub else "texto"), max(10, int(cx - xl - dp(8))), partir=True)
                Color(1, 1, 1, 1)
                Rectangle(texture=te, pos=(xl, y + (alto - te.height) / 2), size=te.size)
                by = y + (alto - ch) / 2
                Color(*rgba("campo"))
                Rectangle(pos=(cx, by), size=(ca, ch))
                Color(*rgba("campo_borde"))
                Line(rounded_rectangle=(cx, by, ca, ch, dp(8)), width=1)
                if i == self.i_ed:
                    continue
                txt = f["st"][0]
                if txt:
                    tv = _textura(txt, 14, False, rgba("texto") if self.editable(i) else rgba("texto2"),
                                  max(10, int(ca - dp(20))))
                else:
                    tv = _textura("Sin asignar", 14, False, rgba("texto2", 0.8))
                Color(1, 1, 1, 1)
                Rectangle(texture=tv, pos=(cx + ca - dp(10) - tv.width, by + (ch - tv.height) / 2), size=tv.size)
            PopMatrix()

    # ------------------------------------------------------------ sumas de los tipos de hito
    def _sumar(self, g):
        from ui_k import leer_num, txt_num
        nums = [leer_num(f["st"][0]) for f in self.filas if f.get("grupo") == g]
        if any(isinstance(x, float) for x in nums):
            self.filas[g]["st"][0] = txt_num(round(sum(x for x in nums if isinstance(x, float)), 6))
            self.filas[g]["_sumado"] = True
        else:
            self.filas[g]["_sumado"] = False

    def _sumar_todos(self):
        for g in {f["grupo"] for f in self.filas if f.get("grupo") is not None}:
            self._sumar(g)

    # ------------------------------------------------------------ edición: un solo cuadro de texto
    def on_touch_down(self, touch):
        if self.editor is not None and self.editor.collide_point(*touch.pos):
            return self.editor.on_touch_down(touch)
        if not self.collide_point(*touch.pos):
            return False
        lx, ly = touch.x - self.x, touch.y - self.y
        for i, (y, alto, cx, ca, ch) in enumerate(self._cajas()):
            if y <= ly <= y + alto and cx - dp(30) <= lx <= cx + ca:
                if self.editable(i):
                    # que Kivy no le quite el foco al editor al soltar este mismo toque
                    FocusBehavior.ignored_touch.append(touch)
                    self.abrir(i)
                    return True
                return False
        return False

    def on_touch_move(self, touch):
        if self.editor is not None:
            return self.editor.on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.editor is not None:
            return self.editor.on_touch_up(touch)

    def _poner_editor(self):
        y, alto, cx, ca, ch = self._cajas()[self.i_ed]
        self.editor.pos = (self.x + cx, self.y + y + (alto - ch) / 2)

    def abrir(self, i):
        if TarjetaLiviana._activa is not None and TarjetaLiviana._activa is not self:
            TarjetaLiviana._activa.cerrar()
        if self.editor is not None:
            self.cerrar()
        f = self.filas[i]
        sub = f.get("sub")
        ed = Campo(f["st"][0], pista="Sin asignar", ancho=130 if sub else 150, alto=40 if sub else 44,
                   alinear="right", numerico=True)
        ed.text_validate_unfocus = False
        self.editor, self.i_ed = ed, i
        TarjetaLiviana._activa = self
        self.add_widget(ed)
        self._poner_editor()
        ed.bind(focus=lambda w, v: (not v) and Clock.schedule_once(lambda *_: self._salio(w), 0))
        ed.bind(on_text_validate=lambda *_: self._siguiente())
        self.marcar()
        Clock.schedule_once(lambda *_: setattr(ed, "focus", True), 0)

    _activa = None

    def _guardar_editor(self):
        ed, i = self.editor, self.i_ed
        if ed is None:
            return
        t = "" if es_cero(ed.text) else ed.text
        f = self.filas[i]
        if t != f["st"][0]:
            f["st"][0] = t
            if f.get("grupo") is not None:
                self._sumar(f["grupo"])
            if self.al_cambiar:
                self.al_cambiar()

    def cerrar(self):
        ed = self.editor
        if ed is None:
            return
        self._guardar_editor()
        self.editor, self.i_ed = None, None
        if TarjetaLiviana._activa is self:
            TarjetaLiviana._activa = None
        self.remove_widget(ed)
        self.marcar()

    def _salio(self, ed):
        if self.editor is ed and not ed.focus:
            self.cerrar()

    def _siguiente(self):
        """Enter: pasa a la siguiente casilla editable (y a la tarjeta siguiente al llegar al final)."""
        i = self.i_ed
        sig = next((j for j in range(i + 1, len(self.filas)) if self.editable(j)), None)
        if sig is not None:
            self.abrir(sig)
        else:
            self.cerrar()
            if self.al_final:
                self.al_final(self)

    def primera(self):
        sig = next((j for j in range(len(self.filas)) if self.editable(j)), None)
        if sig is not None:
            self.abrir(sig)
            return True
        return False


class RenglonLiviano(Widget):
    """Renglón dibujado: título (ancho fijo), texto gris y un botón a la derecha (ej. «+ Tramo»).
    Reemplaza a Fila + 2 etiquetas + botón en las listas largas de ubicaciones."""

    def __init__(self, titulo, info, boton, al_tocar=None, deshabilitado=False, ancho_titulo=200, alto=44,
                 ancho_boton=110, **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(height=dp(alto), **kw)
        self.titulo, self.info, self.boton = titulo, info, boton
        self.al_tocar, self.deshab = al_tocar, deshabilitado
        self.a_t, self.a_b = dp(ancho_titulo), dp(ancho_boton)
        self._apretado = False
        self.bind(size=self._dibujar, pos=self._mover)

    def _mover(self, *_):
        if hasattr(self, "_tr"):
            self._tr.xy = self.pos
        else:
            self._dibujar()

    def _dibujar(self, *_):
        w, h = self.width, self.height
        if w <= 1:
            return
        cv = self.canvas
        cv.clear()
        with cv:
            PushMatrix()
            self._tr = Translate(self.x, self.y)
            Color(1, 1, 1, 1)
            tt = _textura(self.titulo, 14, True, rgba("texto"), int(self.a_t - dp(8)), partir=True)
            Rectangle(texture=tt, pos=(0, (h - tt.height) / 2), size=tt.size)
            ti = _textura(self.info, 12, False, rgba("texto2"), max(10, int(w - self.a_t - self.a_b - dp(16))))
            Rectangle(texture=ti, pos=(self.a_t + dp(8), (h - ti.height) / 2), size=ti.size)
            bx = w - self.a_b
            a = 0.5 if self.deshab else 1
            Color(*rgba("suave_h" if self._apretado else "suave", a))
            RoundedRectangle(pos=(bx, 0), size=(self.a_b, h), radius=[dp(10)])
            Color(*rgba("borde", a))
            Line(rounded_rectangle=(bx, 0, self.a_b, h, dp(10)), width=1)
            Color(1, 1, 1, 1)
            tb = _textura(self.boton, 14, True, rgba("texto", a))
            Rectangle(texture=tb, pos=(bx + (self.a_b - tb.width) / 2, (h - tb.height) / 2), size=tb.size)
            PopMatrix()

    def on_touch_down(self, touch):
        if self.deshab or not self.collide_point(*touch.pos) or touch.x < self.right - self.a_b:
            return False
        touch.grab(self)
        self._apretado = True
        self._dibujar()
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        self._apretado = False
        self._dibujar()
        if self.collide_point(*touch.pos) and self.al_tocar:
            self.al_tocar()
        return True


class TarjetaUbicacionK(Widget):
    """Tarjeta de Ubicaciones entera dibujada: nombre, botones (Editar/Eliminar), resumen (+ tramo) y niveles."""

    def __init__(self, titulo, info, chips, botones=(), boton_info=None, **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(height=dp(120), **kw)
        self.titulo, self.info, self.chips = titulo, info, [f"  {c}  " for c in chips]
        self.botones, self.boton_info = list(botones), boton_info
        self._zonas, self._apretado = [], None
        self.bind(width=self._dibujar, pos=self._mover)

    def _mover(self, *_):
        if hasattr(self, "_tr"):
            self._tr.xy = self.pos

    def _boton(self, x1, y, txt, ancho, cmd, k):
        a, h = dp(ancho), dp(38)
        x0 = x1 - a
        Color(*rgba("suave_h" if self._apretado == k else "suave"))
        RoundedRectangle(pos=(x0, y), size=(a, h), radius=[dp(10)])
        Color(*rgba("borde"))
        Line(rounded_rectangle=(x0, y, a, h, dp(10)), width=1)
        t = _textura(txt, 14, True, rgba("texto"))
        Color(1, 1, 1, 1)
        Rectangle(texture=t, pos=(x0 + (a - t.width) / 2, y + (h - t.height) / 2), size=t.size)
        self._zonas.append((x0, y, x1, y + h, cmd, k))
        return x0

    def _dibujar(self, *_):
        w = self.width
        if w <= 1:
            return
        P, E, A, S = dp(16), dp(6), dp(28), dp(6)
        # alto: cabecera 40 + resumen 40 (o una línea) + píldoras
        tex = [_textura(t, 12, True, rgba("texto")) for t in self.chips]
        pos, x, fila = [], 0, 0
        for t in tex:
            an = t.width + dp(16)
            if x and x + an > w - 2 * P:
                x, fila = 0, fila + 1
            pos.append((x, fila, an))
            x += an + S
        n_f = fila + 1 if tex else 0
        h_chips = n_f * A + max(0, n_f - 1) * S
        h_info = dp(40)
        alto = P + dp(40) + E + h_info + ((E + h_chips) if tex else 0) + P
        self.height = alto
        self._zonas = []
        cv = self.canvas
        cv.clear()
        with cv:
            PushMatrix()
            self._tr = Translate(self.x, self.y)
            Color(*rgba("tarjeta"))
            RoundedRectangle(pos=(0, 0), size=(w, alto), radius=[dp(14)])
            Color(*rgba("borde"))
            Line(rounded_rectangle=(0, 0, w, alto, dp(14)), width=1)
            y = alto - P - dp(40)
            x = w - P
            for k, (txt, an, cmd) in enumerate(self.botones):
                x = self._boton(x, y + dp(1), txt, an, cmd, ("b", k)) - dp(8)
            tt = _textura(self.titulo, 18, True, rgba("texto"), max(10, int(x - P - dp(8))))
            Color(1, 1, 1, 1)
            Rectangle(texture=tt, pos=(P, y + (dp(40) - tt.height) / 2), size=tt.size)
            y -= E + h_info
            ti = _textura(self.info, 13, False, rgba("texto2"))
            Color(1, 1, 1, 1)
            Rectangle(texture=ti, pos=(P, y + (h_info - ti.height) / 2), size=ti.size)
            if self.boton_info:
                txt, an, cmd = self.boton_info
                self._boton(w - P, y + dp(1), txt, an, cmd, ("i", 0))
            if tex:
                ytop = y - E
                for t, (cx, f, an) in zip(tex, pos):
                    cy = ytop - (f + 1) * A - f * S
                    Color(*rgba("suave"))
                    RoundedRectangle(pos=(P + cx, cy), size=(an, A), radius=[dp(14)])
                    Color(1, 1, 1, 1)
                    Rectangle(texture=t, pos=(P + cx + (an - t.width) / 2, cy + (A - t.height) / 2), size=t.size)
            PopMatrix()

    def _zona(self, touch):
        lx, ly = touch.x - self.x, touch.y - self.y
        return next((z for z in self._zonas if z[0] <= lx <= z[2] and z[1] <= ly <= z[3]), None)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        z = self._zona(touch)
        if not z:
            return False
        touch.grab(self)
        self._apretado = z[5]
        self._dibujar()
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        z = self._zona(touch)
        k = self._apretado
        self._apretado = None
        self._dibujar()
        if z and z[5] == k and z[4]:
            z[4]()
        return True
