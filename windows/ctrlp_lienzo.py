"""
Ctrl-P - Tarjetas dibujadas (mismo principio que la tabla virtual de Registro de avance)
=====================================================================================
En Datos fijos y Ubicaciones cada edificio tenía decenas de controles (marco, etiqueta, casilla y texto de
ayuda por nivel; una píldora por nivel). Aquí la tarjeta entera es UN lienzo que dibuja los textos y casillas;
al hacer clic en una casilla aparece una sola casilla de escritura real encima. Mismo aspecto, una fracción de
los controles: la pantalla se arma y se desplaza sin trabarse.
"""

import tkinter as tk
import tkinter.font as tkf

import customtkinter as ctk

from ctrlp_ui import TF, col, leer_num as _leer, txt_num as _txt

_FUENTES = {}


def _fuente(raiz, tam, negrita=False):
    k = (tam, negrita)
    f = _FUENTES.get(k)
    if f is None:
        f = _FUENTES[k] = tkf.Font(root=raiz, font=TF(tam, "bold" if negrita else "normal"))
    return f


def _es_cero(t):
    try:
        return float(str(t).replace(",", "").strip()) == 0
    except ValueError:
        return False


def _acortar(fuente, texto, ancho):
    if ancho <= 0 or fuente.measure(texto) <= ancho:
        return texto
    while texto and fuente.measure(texto + "…") > ancho:
        texto = texto[:-1]
    return texto + "…"


class TarjetaLienzo(tk.Canvas):
    """filas: dicts {etiq, var (StringVar), sub (renglón de tipo), negrita, fijo (no editable), grupo (índice
    del renglón que suma sus tipos)}. Se pone dentro de una ui.Tarjeta."""

    def __init__(self, master, titulo, total, total_color, filas, al_final=None, ancho_caja=130):
        super().__init__(master, bg=col("tarjeta"), highlightthickness=0, bd=0, height=10)
        self.esc = ctk.ScalingTracker.get_widget_scaling(master)
        self.titulo, self.total, self.total_color = titulo, total, total_color
        self.filas, self.al_final = filas, al_final
        self.ancho_caja = ancho_caja
        self.editor, self.i_ed = None, None
        self.f_tit = _fuente(self, 11, True)
        self.f_lbl = _fuente(self, 10)
        self.f_lbl_b = _fuente(self, 10, True)
        self.f_sub = _fuente(self, 9)
        self.f_val = _fuente(self, 10)
        ls = self.f_val.metrics("linespace")
        self.h_caja = int(ls + 10 * self.esc)
        self.h_fila = int(self.h_caja + 6 * self.esc)
        self.h_sub = int(self.h_caja + 2 * self.esc)
        self.h_cab = int(self.f_tit.metrics("linespace") + 12 * self.esc)
        self._ancho = 0
        self._trazas = []
        for i, f in enumerate(filas):
            f.setdefault("_sumado", False)
            nombre = f["var"].trace_add("write", lambda *_, i=i: self._cambio(i))
            self._trazas.append((f["var"], nombre))
        for g in {f["grupo"] for f in filas if f.get("grupo") is not None}:
            self._sumar(g)
        self.configure(height=self._alto())
        self.bind("<Configure>", self._al_configurar)
        self.bind("<Button-1>", self._clic)
        self.bind("<Destroy>", self._soltar, add="+")

    # ------------------------------------------------------------ geometría
    def _alto(self):
        return self.h_cab + sum(self.h_sub if f.get("sub") else self.h_fila for f in self.filas) + int(4 * self.esc)

    def _cajas(self):
        out, y = [], self.h_cab
        w = self._ancho
        for f in self.filas:
            h = self.h_sub if f.get("sub") else self.h_fila
            ca = int((self.ancho_caja - (20 if f.get("sub") else 0)) * self.esc)
            ch = self.h_caja - (int(4 * self.esc) if f.get("sub") else 0)
            out.append((y, h, w - ca - 1, ca, ch))
            y += h
        return out

    def editable(self, i):
        f = self.filas[i]
        return not f.get("fijo") and not f.get("_sumado")

    # ------------------------------------------------------------ dibujo
    def _al_configurar(self, ev):
        if ev.width != self._ancho:
            self._ancho = ev.width
            self.dibujar()

    def dibujar(self):
        if self._ancho <= 1:
            return
        self.delete("d")
        w = self._ancho
        yc = self.h_cab // 2
        t_tot = self.create_text(w - 1, yc, text=self.total, anchor="e", font=self.f_tit,
                                 fill=col(self.total_color), tags="d")
        ancho_tot = self.f_tit.measure(self.total)
        self.create_text(0, yc, text=_acortar(self.f_tit, self.titulo, w - ancho_tot - 16), anchor="w",
                         font=self.f_tit, fill=col("texto"), tags="d")
        del t_tot
        for i, (f, (y, h, cx, ca, ch)) in enumerate(zip(self.filas, self._cajas())):
            sub = f.get("sub")
            fl = self.f_sub if sub else (self.f_lbl_b if f.get("negrita") else self.f_lbl)
            xl = int(18 * self.esc) if sub else 0
            self.create_text(xl, y + h // 2, text=_acortar(fl, f["etiq"], cx - xl - 8), anchor="w", font=fl,
                             fill=col("texto2" if sub else "texto"), tags="d")
            by = y + (h - ch) // 2
            ed = self.editable(i)
            self.create_rectangle(cx, by, cx + ca, by + ch, fill=col("campo") if ed else col("suave"),
                                  outline=col("campo_borde"), tags="d")
            if i == self.i_ed:
                continue
            txt = f["var"].get()
            if txt:
                self.create_text(cx + ca - int(6 * self.esc), by + ch // 2, text=_acortar(self.f_val, txt, ca - 10),
                                 anchor="e", font=self.f_val, fill=col("texto") if ed else col("texto2"), tags="d")
            else:
                self.create_text(cx + ca - int(6 * self.esc), by + ch // 2, text="Sin asignar", anchor="e",
                                 font=self.f_sub, fill=col("texto2"), tags="d")
        self.tag_raise("ed")

    # ------------------------------------------------------------ sumas de los tipos
    def _sumar(self, g):
        nums = [_leer(f["var"].get()) for f in self.filas if f.get("grupo") == g]
        fg = self.filas[g]
        if any(isinstance(x, float) for x in nums):
            fg["_sumado"] = True
            nuevo = _txt(round(sum(x for x in nums if isinstance(x, float)), 6))
            if fg["var"].get() != nuevo:
                fg["var"].set(nuevo)
        else:
            fg["_sumado"] = False

    def _cambio(self, i):
        g = self.filas[i].get("grupo")
        if g is not None:
            self._sumar(g)
        if self.i_ed is None or self.i_ed != i:
            self.after_idle(self.dibujar)

    def _soltar(self, ev):
        if ev.widget is not self:
            return
        for v, n in self._trazas:
            try:
                v.trace_remove("write", n)
            except tk.TclError:
                pass
        self._trazas = []
        if TarjetaLienzo._activa is self:
            TarjetaLienzo._activa = None

    # ------------------------------------------------------------ edición: una sola casilla real
    _activa = None

    def _clic(self, ev):
        for i, (y, h, cx, ca, ch) in enumerate(self._cajas()):
            if y <= ev.y < y + h and cx - 20 <= ev.x <= cx + ca:
                if self.editable(i):
                    self.abrir(i)
                return

    def abrir(self, i):
        if TarjetaLienzo._activa is not None and TarjetaLienzo._activa is not self:
            TarjetaLienzo._activa.cerrar()
        self.cerrar()
        f = self.filas[i]
        y, h, cx, ca, ch = self._cajas()[i]
        e = tk.Entry(self, textvariable=f["var"], justify="right", font=self.f_val, relief="flat", bg=col("campo"),
                     fg=col("texto"), insertbackground=col("texto"), highlightthickness=1,
                     highlightbackground=col("acento"), highlightcolor=col("acento"))
        self.editor, self.i_ed = e, i
        TarjetaLienzo._activa = self
        self.create_window(cx, y + (h - ch) // 2, window=e, anchor="nw", width=ca + 1, height=ch + 1, tags="ed")
        self.dibujar()
        e.bind("<Return>", lambda _: self._mover(1) or "break")
        e.bind("<KP_Enter>", lambda _: self._mover(1) or "break")
        e.bind("<Down>", lambda _: self._mover(1) or "break")
        e.bind("<Tab>", lambda _: self._mover(1) or "break")
        e.bind("<Up>", lambda _: self._mover(-1) or "break")
        e.bind("<Shift-Tab>", lambda _: self._mover(-1) or "break")
        e.bind("<Escape>", lambda _: self.cerrar() or "break")
        e.bind("<FocusOut>", lambda _: self.after_idle(lambda: self._salio(e)))
        e.focus_set()
        e.select_range(0, "end")
        e.icursor("end")

    def _salio(self, e):
        try:
            foco = self.focus_get()
        except (tk.TclError, KeyError):
            foco = None
        if self.editor is e and foco is not e:
            self.cerrar()

    def cerrar(self):
        e = self.editor
        if e is None:
            return
        f = self.filas[self.i_ed]
        if _es_cero(f["var"].get()):
            f["var"].set("")          # un 0 no es cantidad: la casilla queda vacía
        self.editor, self.i_ed = None, None
        if TarjetaLienzo._activa is self:
            TarjetaLienzo._activa = None
        self.delete("ed")
        try:
            e.destroy()
        except tk.TclError:
            pass
        self.dibujar()

    def _mover(self, d):
        i = self.i_ed
        rango = range(i + 1, len(self.filas)) if d > 0 else range(i - 1, -1, -1)
        sig = next((j for j in rango if self.editable(j)), None)
        if sig is not None:
            self.abrir(sig)
        else:
            self.cerrar()
            if self.al_final:
                self.al_final(self, d)

    def primera(self, d=1):
        rango = range(len(self.filas)) if d > 0 else range(len(self.filas) - 1, -1, -1)
        sig = next((j for j in rango if self.editable(j)), None)
        if sig is not None:
            self.abrir(sig)
            return True
        return False


class ChipsLienzo(tk.Canvas):
    """Píldoras (nombres de niveles) dibujadas en renglones dentro de un solo lienzo."""

    def __init__(self, master, textos, tam=11, alto=26, sep=6, relleno=12):
        super().__init__(master, bg=col("tarjeta"), highlightthickness=0, bd=0, height=1)
        self.esc = ctk.ScalingTracker.get_widget_scaling(master)
        self.textos = list(textos)
        self.f = _fuente(self, max(7, round(tam * 0.75)), True)
        self.alto, self.sep, self.relleno = int(alto * self.esc), int(sep * self.esc), int(relleno * self.esc)
        self._ancho = 0
        self.bind("<Configure>", self._conf)

    def _conf(self, ev):
        if ev.width != self._ancho:
            self._ancho = ev.width
            self.dibujar()

    def dibujar(self):
        w = self._ancho
        if w <= 1:
            return
        self.delete("all")
        x = y = 0
        A, S, R = self.alto, self.sep, self.relleno
        r = A // 2
        fondo = col("suave")
        for t in self.textos:
            ancho = self.f.measure(t) + 2 * R
            if x and x + ancho > w:
                x, y = 0, y + A + S
            # píldora: dos medios círculos y un rectángulo
            self.create_oval(x, y, x + A, y + A, fill=fondo, outline=fondo)
            self.create_oval(x + ancho - A, y, x + ancho, y + A, fill=fondo, outline=fondo)
            self.create_rectangle(x + r, y, x + ancho - r, y + A, fill=fondo, outline=fondo)
            self.create_text(x + ancho / 2, y + A / 2, text=t, font=self.f, fill=col("texto"))
            x += ancho + S
        alto = (y + A) if self.textos else 1
        if int(self.cget("height")) != alto:
            self.configure(height=alto)


class RenglonesLienzo(tk.Canvas):
    """Renglones «TÍTULO   info   + enlace» dibujados en un solo lienzo (lista de ubicaciones de Tramos/Equipos).
    renglones: [(titulo, info, texto_enlace|None, comando)]."""

    def __init__(self, master, renglones):
        super().__init__(master, bg=col("tarjeta"), highlightthickness=0, bd=0)
        self.esc = ctk.ScalingTracker.get_widget_scaling(master)
        self.renglones = renglones
        self.f_t, self.f_i, self.f_e = _fuente(self, 10, True), _fuente(self, 8), _fuente(self, 9, True)
        self.h = int(self.f_t.metrics("linespace") + 14 * self.esc)
        self._zonas = []
        self.configure(height=self.h * len(renglones), width=10)
        self.bind("<Button-1>", self._clic)
        self.bind("<Motion>", self._mano)
        self._dibujar()

    def _dibujar(self):
        self.delete("all")
        self._zonas = []
        ancho = 0
        for k, (tit, info, enl, cmd) in enumerate(self.renglones):
            y = k * self.h + self.h // 2 + int(2 * self.esc)
            self.create_text(0, y, text=tit, anchor="w", font=self.f_t, fill=col("texto"))
            x = self.f_t.measure(tit)
            self.create_text(x, y, text=f"   {info}", anchor="w", font=self.f_i, fill=col("texto2"))
            x += self.f_i.measure(f"   {info}") + int(18 * self.esc)
            if enl:
                self.create_text(x, y, text=enl, anchor="w", font=self.f_e, fill=col("acento"))
                w = self.f_e.measure(enl)
                self._zonas.append((x - 6, k * self.h, x + w + 6, (k + 1) * self.h, cmd))
                x += w + 8
            ancho = max(ancho, x)
        self.configure(width=ancho + 4)

    def _zona(self, ev):
        return next((z[4] for z in self._zonas if z[0] <= ev.x <= z[2] and z[1] <= ev.y < z[3]), None)

    def _clic(self, ev):
        cmd = self._zona(ev)
        if cmd:
            cmd()

    def _mano(self, ev):
        self.configure(cursor="hand2" if self._zona(ev) else "")


def _redondeado(cv, x0, y0, x1, y1, r, **kw):
    """Rectángulo de esquinas redondeadas (polígono suavizado)."""
    r = max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    p = [x0 + r, y0, x0 + r, y0, x1 - r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y0 + r, x1, y1 - r, x1, y1 - r,
         x1, y1, x1 - r, y1, x1 - r, y1, x0 + r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y1 - r, x0, y0 + r,
         x0, y0 + r, x0, y0]
    return cv.create_polygon(p, smooth=True, **kw)


class TarjetaUbicacion(tk.Canvas):
    """Tarjeta de un edificio/área en Ubicaciones, entera en un lienzo: nombre, botones, resumen y niveles.
    botones: [(texto, ancho, comando)] arriba a la derecha; boton_info: (texto, ancho, comando) o None."""

    def __init__(self, master, titulo, info, chips, botones=(), boton_info=None):
        super().__init__(master, bg=col("fondo"), highlightthickness=0, bd=0, height=60)
        self.esc = e = ctk.ScalingTracker.get_widget_scaling(master)
        self.titulo, self.info, self.chips = titulo, info, list(chips)
        self.botones, self.boton_info = list(botones), boton_info
        self.f_t, self.f_b, self.f_i = _fuente(self, 13, True), _fuente(self, 10), _fuente(self, 9)
        self.f_c = _fuente(self, 8, True)
        self.px, self.pt, self.hb = int(18 * e), int(14 * e), int(28 * e)
        self.hc, self.sc, self.rc = int(26 * e), int(6 * e), int(12 * e)
        self._ancho, self._zonas, self._sobre = 0, [], None
        self.bind("<Configure>", self._conf)
        self.bind("<Button-1>", self._clic)
        self.bind("<Motion>", self._mov)
        self.bind("<Leave>", lambda _: self._mov(None))

    def _conf(self, ev):
        if ev.width != self._ancho:
            self._ancho = ev.width
            self.dibujar()

    def _boton(self, x1, y, texto, ancho, cmd, k):
        x0 = x1 - int(ancho * self.esc)
        fill = col("suave_h") if self._sobre == k else col("suave")
        _redondeado(self, x0, y, x1, y + self.hb, int(8 * self.esc), fill=fill, outline=fill)
        self.create_text((x0 + x1) / 2, y + self.hb / 2, text=texto, font=self.f_b, fill=col("texto"))
        self._zonas.append((x0, y, x1, y + self.hb, cmd, k))
        return x0

    def dibujar(self):
        w = self._ancho
        if w <= 1:
            return
        self.delete("all")
        self._zonas = []
        px, e = self.px, self.esc
        y = self.pt
        # botones arriba a la derecha y nombre a la izquierda
        x = w - px
        for k, (txt, anc, cmd) in enumerate(self.botones):
            x = self._boton(x, y, txt, anc, cmd, ("b", k)) - int(6 * e)
        lt = self.f_t.metrics("linespace")
        h1 = max(self.hb, lt)
        self.create_text(px, y + h1 / 2, text=_acortar(self.f_t, self.titulo, x - px - 8), anchor="w", font=self.f_t,
                         fill=col("texto"))
        y += h1 + int(6 * e)
        # resumen (+ tramo)
        li = self.f_i.metrics("linespace")
        h2 = self.hb if self.boton_info else li
        self.create_text(px, y + h2 / 2, text=self.info, anchor="w", font=self.f_i, fill=col("texto2"))
        if self.boton_info:
            txt, anc, cmd = self.boton_info
            self._boton(w - px, y, txt, anc, cmd, ("i", 0))
        y += h2
        # niveles en píldoras
        if self.chips:
            y += int(6 * e)
            x0 = int(16 * e)
            x, A, S, R = x0, self.hc, self.sc, self.rc
            fondo = col("suave")
            for t in self.chips:
                ancho = self.f_c.measure(t) + 2 * R
                if x > x0 and x + ancho > w - x0:
                    x, y = x0, y + A + S
                _redondeado(self, x, y, x + ancho, y + A, A // 2, fill=fondo, outline=fondo)
                self.create_text(x + ancho / 2, y + A / 2, text=t, font=self.f_c, fill=col("texto"))
                x += ancho + S
            y += A
        y += self.pt
        # fondo de la tarjeta, detrás de todo
        fb = _redondeado(self, 0, 0, w - 1, y - 1, int(12 * e), fill=col("tarjeta"), outline=col("borde"))
        self.tag_lower(fb)
        if int(self.cget("height")) != y:
            self.configure(height=y)

    def _zona(self, ev):
        if ev is None:
            return None
        return next((z for z in self._zonas if z[0] <= ev.x <= z[2] and z[1] <= ev.y <= z[3]), None)

    def _clic(self, ev):
        z = self._zona(ev)
        if z and z[4]:
            z[4]()

    def _mov(self, ev):
        z = self._zona(ev)
        k = z[5] if z else None
        if k != self._sobre:
            self._sobre = k
            self.configure(cursor="hand2" if z else "")
            self.dibujar()
