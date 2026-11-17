"""Tabla virtual de Registro de avance.

Solo se dibujan las filas que se ven (como una tabla de un programa de inventario): abrir una partida con cientos
de filas o deslizarla no crea miles de controles. Hay una sola casilla de escritura real, que se pone encima de la
celda que se toca.

La página sigue usando sus propios cálculos: las celdas son objetos livianos (Celda / CeldaEntrada) con
configure()/cget()/bind() como una etiqueta de tk, así recalcular() y el pintado de filas no cambian.
"""
import bisect
import tkinter as tk
import tkinter.font as tkf

import customtkinter as ctk

from ctrlp_ui import col, TF


class Celda:
    """Texto de una celda (lo que antes era un tk.Label)."""
    __slots__ = ("text", "fg", "cursor", "negrita", "_clic", "_tabla")

    def __init__(self, tabla, text=""):
        self.text, self.fg, self.cursor, self.negrita, self._clic, self._tabla = text, None, "", None, None, tabla

    def configure(self, **kw):
        cambio = False
        if "text" in kw and kw["text"] != self.text:
            self.text = kw["text"]
            cambio = True
        if "fg" in kw and kw["fg"] != self.fg:
            self.fg = kw["fg"]
            cambio = True
        if "cursor" in kw:
            self.cursor = kw["cursor"]
        if "font" in kw:
            nb = "bold" in str(kw["font"])
            if nb != self.negrita:
                self.negrita = nb
                cambio = True
        if cambio:
            self._tabla.marcar()
    config = configure

    def cget(self, k):
        return {"text": self.text, "fg": self.fg, "cursor": self.cursor}.get(k, "")

    def bind(self, _sec, fn, add=None):
        self._clic = fn


class CeldaEntrada:
    """Lo que antes era la casilla tk.Entry de «Del día»: estado (normal/disabled) y color de borde."""
    __slots__ = ("state", "borde", "_tabla")

    def __init__(self, tabla, state="normal"):
        self.state, self.borde, self._tabla = state, None, tabla

    def configure(self, **kw):
        cambio = False
        if "state" in kw and kw["state"] != self.state:
            self.state = kw["state"]
            cambio = True
        if "highlightbackground" in kw and kw["highlightbackground"] != self.borde:
            self.borde = kw["highlightbackground"]
            cambio = True
        if cambio:
            self._tabla.marcar()
    config = configure

    def cget(self, k):
        return self.state if k == "state" else (self.borde or "")


class TablaVirtual(tk.Frame):
    """Columnas: listas de dicts {id, titulo, ancho, alinear ('w'|'e'), tipo ('txt'|'entrada'|'obs'|'fecha'),
    clic (opcional, al tocar el título), resaltar (título destacado)}.
    izq: columnas fijas; der: columnas que se deslizan en horizontal (en «Día» van todas en der)."""

    def __init__(self, master, izq, der, al_editar=None):
        super().__init__(master, bg=col("tarjeta"), highlightthickness=1, highlightbackground=col("borde"))
        self.izq, self.der = izq, der
        self.filas = {}                 # r (número de fila) -> dict
        self._orden = []                # r visibles, en orden
        self._y = []                    # y inicial de cada fila visible
        self._alto_total = 0
        self._yoff = 0
        self._xoff = 0
        self._pend = None
        self.activa = None              # (r, columna) de la casilla que se escribe
        self.al_editar = al_editar
        self.fuente = TF(10)
        self.fuente_b = TF(10, "bold")
        self.fuente_t = TF(9, "bold")
        f = tkf.Font(root=self, font=self.fuente)
        self._ls = f.metrics("linespace")
        self.alto_res = self._ls + 14
        self.alto_hoja = self._ls + 20
        self.alto_tit = self._ls + 16
        self._medir = f
        self._medir_b = tkf.Font(root=self, font=self.fuente_b)
        esc = ctk.ScalingTracker.get_widget_scaling(self)
        self.esc = esc
        # partes
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.cv_i = tk.Canvas(self, bg=col("tarjeta"), highlightthickness=0, bd=0)
        self.cv_d = tk.Canvas(self, bg=col("tarjeta"), highlightthickness=0, bd=0)
        self.sb_h = ctk.CTkScrollbar(self, orientation="horizontal", height=12, command=self._xview,
                                     button_color=col("borde"))
        self.sb_v = ctk.CTkScrollbar(self, orientation="vertical", width=12, command=self._yview,
                                     button_color=col("borde"))
        self.cv_i.grid(row=1, column=0, sticky="ns")
        self.cv_d.grid(row=1, column=1, sticky="nsew")
        self.sb_v.grid(row=1, column=2, sticky="ns")
        self._sb_h_vis = False
        for cv in (self.cv_i, self.cv_d):
            cv.bind("<Configure>", lambda _: self.marcar(), add="+")
            cv.bind("<MouseWheel>", self._rueda)
            cv.bind("<Shift-MouseWheel>", self._rueda_h)
            cv.bind("<Button-4>", lambda e: self._mover(-3))
            cv.bind("<Button-5>", lambda e: self._mover(3))
            cv.bind("<Button-1>", self._clic)
            cv.bind("<Motion>", self._movimiento)
        # la casilla de escritura (una sola)
        self.editor = tk.Entry(self, justify="right", font=self.fuente_b, relief="flat", bg=col("campo"),
                               fg=col("texto"), insertbackground=col("texto"), highlightthickness=1,
                               highlightbackground=col("acento"), highlightcolor=col("acento"))
        self.editor.bind("<Return>", lambda e: self.mover_activa(1) or "break")
        self.editor.bind("<KP_Enter>", lambda e: self.mover_activa(1) or "break")
        self.editor.bind("<Down>", lambda e: self.mover_activa(1) or "break")
        self.editor.bind("<Up>", lambda e: self.mover_activa(-1) or "break")
        self.editor.bind("<MouseWheel>", self._rueda)
        self._calcular_anchos_base()

    # ------------------------------------------------------------ filas
    def fila_resumen(self, r, texto, fondo, bold, celdas, enlace=None):
        self.filas[r] = {"r": r, "tipo": "res", "texto": texto, "fondo": fondo, "bold": bold, "c": celdas,
                         "vis": True, "enlace": enlace}

    def fila_hoja(self, r, texto, bold, contractual, ant, fila, celdas, por_fecha, fg_contr):
        self.filas[r] = {"r": r, "tipo": "hoja", "texto": texto, "fondo": col("tarjeta"), "bold": bold,
                         "contr": contractual, "fg_contr": fg_contr, "ant": ant, "f": fila, "c": celdas,
                         "fechas": por_fecha, "vis": True, "enlace": None}

    def enlace(self, r, texto, cmd):
        if r in self.filas:
            self.filas[r]["enlace"] = (texto, cmd)

    def ocultar(self, r0, r1, ocultar):
        for r, f in self.filas.items():
            if r0 <= r < r1:
                f["vis"] = not ocultar
        if self.activa and not self.filas.get(self.activa[0], {}).get("vis", True):
            self.soltar_activa()
        self.listo(anchos=False)

    def listo(self, anchos=True):
        """Después de agregar filas (anchos) o abrir/cerrar niveles: recalcula posiciones y dibuja."""
        self._orden = sorted(r for r, f in self.filas.items() if f["vis"])
        y = 0
        self._y = []
        for r in self._orden:
            self._y.append(y)
            y += self.alto_hoja if self.filas[r]["tipo"] == "hoja" else self.alto_res
        self._alto_total = y
        if anchos or not hasattr(self, "ancho_der"):
            self._ajustar_anchos()
        self.marcar()

    # ------------------------------------------------------------ anchos
    def _calcular_anchos_base(self):
        num = self._medir_b.measure("-0,000,000.00") + int(16 * self.esc)
        for c in self.izq + self.der:
            if c.get("ancho"):
                continue
            if c["tipo"] in ("entrada",):
                c["ancho"] = max(num, int(100 * self.esc))
            elif c["tipo"] == "obs":
                c["ancho"] = int(180 * self.esc)
            elif c["tipo"] == "fecha":
                c["ancho"] = max(int(84 * self.esc), self._medir.measure("0,000,000.00") + int(12 * self.esc))
            elif c["id"] == 0:
                c["ancho"] = int(200 * self.esc)
            else:
                c["ancho"] = num

    def _ajustar_anchos(self):
        c0 = next((c for c in self.izq + self.der if c["id"] == 0), None)
        if c0 is not None:
            # se mide el texto más largo (aprox. por cantidad de letras) y no cada fila: medir es lento
            largos = sorted({f["texto"] for f in self.filas.values()}, key=len, reverse=True)[:12]
            w = max([self._medir_b.measure(t) + self._medir_b.measure("▾ ") for t in largos] + [100])
            enl = max([self._medir.measure(t) + 16 for t in {f["enlace"][0] for f in self.filas.values() if f["enlace"]}]
                      + [0])
            c0["ancho"] = min(int(420 * self.esc), w + enl + int(24 * self.esc))
        x = 0
        for c in self.izq:
            c["x"] = x
            x += c["ancho"]
        self.ancho_izq = x
        self.cv_i.configure(width=x if self.izq else 0)
        if not self.izq:
            self.cv_i.grid_remove()
        x = 0
        for c in self.der:
            c["x"] = x
            x += c["ancho"]
        self.ancho_der = x

    # ------------------------------------------------------------ desplazamiento
    def _vis_alto(self):
        return max(1, self.cv_d.winfo_height() - self.alto_tit)

    def _yview(self, *a):
        h = self._vis_alto()
        maxo = max(0, self._alto_total - h)
        if a[0] == "moveto":
            self._yoff = int(float(a[1]) * self._alto_total)
        elif a[0] == "scroll":
            n = int(a[1])
            self._yoff += n * (h if a[2] == "pages" else self.alto_hoja)
        self._yoff = min(max(0, self._yoff), maxo)
        self.marcar()

    def _xview(self, *a):
        w = max(1, self.cv_d.winfo_width())
        maxo = max(0, self.ancho_der - w)
        if a[0] == "moveto":
            self._xoff = int(float(a[1]) * self.ancho_der)
        elif a[0] == "scroll":
            self._xoff += int(a[1]) * (w if a[2] == "pages" else int(60 * self.esc))
        self._xoff = min(max(0, self._xoff), maxo)
        self.marcar()

    def xview_moveto(self, f):
        self._xview("moveto", f)

    def xfrac(self):
        return self._xoff / max(1, self.ancho_der)

    def _mover(self, filas):
        self._yview("scroll", filas, "units")

    def _rueda(self, e):
        self._mover(-3 if e.delta > 0 else 3)
        return "break"

    def _rueda_h(self, e):
        self._xview("scroll", -1 if e.delta > 0 else 1, "units")
        return "break"

    def ver_fila(self, r):
        if r not in self._orden:
            return
        i = self._orden.index(r)
        y0 = self._y[i]
        y1 = y0 + (self.alto_hoja if self.filas[r]["tipo"] == "hoja" else self.alto_res)
        h = self._vis_alto()
        if y0 < self._yoff:
            self._yoff = y0
        elif y1 > self._yoff + h:
            self._yoff = y1 - h
        self.marcar()

    def ver_columna(self, cid):
        c = next((c for c in self.der if c["id"] == cid), None)
        if c is None:
            return
        w = max(1, self.cv_d.winfo_width())
        if c["x"] < self._xoff or c["x"] + c["ancho"] > self._xoff + w:
            self._xoff = max(0, min(c["x"] + c["ancho"] - w + int(40 * self.esc), self.ancho_der - w))
        self.marcar()

    # ------------------------------------------------------------ dibujo
    def marcar(self):
        if self._pend is None:
            try:
                self._pend = self.after_idle(self._dibujar)
            except tk.TclError:
                pass

    def _dibujar(self):
        self._pend = None
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        h = self._vis_alto()
        maxo = max(0, self._alto_total - h)
        self._yoff = min(max(0, self._yoff), maxo)
        wd = max(1, self.cv_d.winfo_width())
        self._xoff = min(max(0, self._xoff), max(0, self.ancho_der - wd))
        # barras
        tot = max(1, self._alto_total)
        self.sb_v.set(self._yoff / tot, min(1.0, (self._yoff + h) / tot))
        hace_falta = self.ancho_der > wd + 1
        if hace_falta and not self._sb_h_vis:
            self.sb_h.grid(row=0, column=1, sticky="ew")
            self._sb_h_vis = True
        elif not hace_falta and self._sb_h_vis:
            self.sb_h.grid_remove()
            self._sb_h_vis = False
        if self._sb_h_vis:
            self.sb_h.set(self._xoff / max(1, self.ancho_der), min(1.0, (self._xoff + wd) / max(1, self.ancho_der)))
        # filas visibles
        i0 = max(0, bisect.bisect_right(self._y, self._yoff) - 1)
        filas = []
        for i in range(i0, len(self._orden)):
            if self._y[i] > self._yoff + h:
                break
            filas.append((self._orden[i], self._y[i] - self._yoff + self.alto_tit))
        for cv, cols, xo in ((self.cv_i, self.izq, 0), (self.cv_d, self.der, self._xoff)):
            cv.delete("all")
            if not cols:
                continue
            ancho_cv = max(cv.winfo_width(), 1)
            for r, y in filas:
                self._dibujar_fila(cv, cols, xo, ancho_cv, self.filas[r], y)
            self._dibujar_titulos(cv, cols, xo, ancho_cv)
        self._poner_editor(filas)

    def _dibujar_titulos(self, cv, cols, xo, ancho_cv):
        cv.create_rectangle(0, 0, ancho_cv, self.alto_tit, fill=col("subtotal"), width=0)
        for c in cols:
            x = c["x"] - xo
            if x + c["ancho"] < 0 or x > ancho_cv:
                continue
            if c.get("resaltar"):
                cv.create_rectangle(x, 0, x + c["ancho"], self.alto_tit, fill=col("sel"), width=0)
            fg = col("acento") if c.get("resaltar") or c["tipo"] == "entrada" else col("texto2")
            if c["alinear"] == "w":
                cv.create_text(x + 8, self.alto_tit / 2, text=c["titulo"], anchor="w", font=self.fuente_t, fill=fg)
            else:
                cv.create_text(x + c["ancho"] - 8, self.alto_tit / 2, text=c["titulo"], anchor="e",
                               font=self.fuente_t, fill=fg)
        cv.create_line(0, self.alto_tit - 1, ancho_cv, self.alto_tit - 1, fill=col("linea"))

    def _dibujar_fila(self, cv, cols, xo, ancho_cv, f, y):
        hoja = f["tipo"] == "hoja"
        alto = self.alto_hoja if hoja else self.alto_res
        cv.create_rectangle(0, y, ancho_cv, y + alto, fill=f["fondo"], width=0)
        fuente = self.fuente_b if f["bold"] else self.fuente
        ym = y + alto / 2
        for c in cols:
            x = c["x"] - xo
            if x + c["ancho"] < 0 or x > ancho_cv:
                continue
            cid, tipo = c["id"], c["tipo"]
            if cid == 0:
                cel0 = f["c"].get(0)
                cv.create_text(x + 8, ym, text=cel0.text if cel0 is not None else f["texto"], anchor="w",
                               font=fuente, fill=col("texto"))
                if f["enlace"]:
                    cv.create_text(x + c["ancho"] - 8, ym, text=f["enlace"][0], anchor="e", font=TF(9, "bold"),
                                   fill=col("acento"))
                continue
            if tipo == "fecha":
                if hoja:
                    v = f["fechas"].get(cid)
                    if v:
                        cv.create_text(x + c["ancho"] - 8, ym, text=v, anchor="e", font=self.fuente,
                                       fill=col("texto2"))
                continue
            if hoja and tipo in ("entrada", "obs"):
                fl = f["f"]
                ent = fl["entry"]
                deshab = ent is not None and ent.state == "disabled"
                if tipo == "obs" and fl.get("obs_bloq"):
                    deshab = True
                x0, x1, y0, y1 = x + 6, x + c["ancho"] - 6, y + 4, y + alto - 4
                borde = (ent.borde if (tipo == "entrada" and ent is not None and ent.borde) else col("campo_borde"))
                cv.create_rectangle(x0, y0, x1, y1, fill=col("suave") if deshab else col("campo"), outline=borde)
                txt = (fl["v"] if tipo == "entrada" else fl["obs"]).get()
                if txt:
                    if tipo == "entrada":
                        cv.create_text(x1 - 6, ym, text=txt, anchor="e", font=self.fuente_b,
                                       fill=col("texto2") if deshab else col("texto"))
                    else:
                        cv.create_text(x0 + 6, ym, text=txt, anchor="w", font=self.fuente,
                                       fill=col("texto2") if deshab else col("texto"))
                continue
            if hoja and cid == 1:
                txt, fg = f["contr"], f["fg_contr"]
            elif hoja and cid == 2:
                txt, fg = f["ant"], col("texto")
            else:
                cel = f["c"].get(cid)
                if cel is None:
                    continue
                txt, fg = cel.text, cel.fg or col("texto")
                if cel.negrita:
                    fuente_c = self.fuente_b
                else:
                    fuente_c = fuente if not hoja else self.fuente
            if txt:
                if hoja and cid in (1, 2):
                    fuente_c = self.fuente
                cv.create_text(x + c["ancho"] - 8, ym, text=txt, anchor="e", font=fuente_c, fill=fg)
        if hoja:
            cv.create_line(0, y + alto - 1, ancho_cv, y + alto - 1, fill=col("linea"))

    # ------------------------------------------------------------ clics y escritura
    def _donde(self, e):
        """(fila r, columna) bajo el mouse; columna None si es el título."""
        cv = e.widget
        cols, xo = (self.izq, 0) if cv is self.cv_i else (self.der, self._xoff)
        x = e.x + xo
        c = next((c for c in cols if c["x"] <= x < c["x"] + c["ancho"]), None)
        if e.y < self.alto_tit:
            return None, c
        y = e.y - self.alto_tit + self._yoff
        i = bisect.bisect_right(self._y, y) - 1
        if i < 0 or i >= len(self._orden):
            return None, None
        return self._orden[i], c

    def _movimiento(self, e):
        r, c = self._donde(e)
        mano = False
        if c is not None:
            if r is None:
                mano = bool(c.get("clic"))
            else:
                f = self.filas[r]
                if c["id"] == 0:
                    cel = f["c"].get(0)
                    mano = bool(f["enlace"]) or bool(cel is not None and cel._clic)
                elif f["tipo"] == "hoja" and c["tipo"] in ("entrada", "obs"):
                    mano = False
        cur = "hand2" if mano else ""
        if e.widget.cget("cursor") != cur:
            e.widget.configure(cursor=cur)

    def _clic(self, e):
        r, c = self._donde(e)
        if c is None:
            return
        if r is None:
            if c.get("clic"):
                c["clic"]()
            return
        f = self.filas[r]
        if c["id"] == 0:
            if f["enlace"]:
                x = e.x + (0 if e.widget is self.cv_i else self._xoff)
                ancho_enl = self._medir.measure(f["enlace"][0]) + 20       # solo al hacer clic
                if x > c["x"] + c["ancho"] - ancho_enl:
                    f["enlace"][1]()
                    return
            cel = f["c"].get(0)
            if cel is not None and cel._clic:
                cel._clic(e)
            return
        if f["tipo"] == "hoja" and c["tipo"] in ("entrada", "obs"):
            self.activar(r, c["id"])

    def _editable(self, r, cid):
        f = self.filas.get(r)
        if not f or f["tipo"] != "hoja" or not f["vis"]:
            return False
        ent = f["f"]["entry"]
        if ent is not None and ent.state == "disabled":
            return False
        if self._col(cid)["tipo"] == "obs" and f["f"].get("obs_bloq"):
            return False
        return True

    def _col(self, cid):
        return next(c for c in self.izq + self.der if c["id"] == cid)

    def activar(self, r, cid, seleccionar=False):
        """Pone la casilla de escritura en esa celda. Con un clic el cursor queda al final; al bajar con
        Enter/flechas se selecciona todo (escribir reemplaza, como en Excel)."""
        if not self._editable(r, cid):
            return
        self._limpiar_cero()
        self.activa = (r, cid)
        fl = self.filas[r]["f"]
        tipo = self._col(cid)["tipo"]
        self.editor.configure(textvariable=fl["v"] if tipo == "entrada" else fl["obs"],
                              justify="right" if tipo == "entrada" else "left",
                              font=self.fuente_b if tipo == "entrada" else self.fuente)
        self.ver_fila(r)
        if any(c["id"] == cid for c in self.der):
            self.ver_columna(cid)
        self._dibujar()
        self.editor.focus_set()
        self.editor.icursor("end")
        if seleccionar:
            self.editor.select_range(0, "end")
        else:
            self.editor.select_clear()

    def soltar_activa(self):
        self._limpiar_cero()
        self.activa = None
        self.editor.place_forget()

    def _limpiar_cero(self):
        """Un 0 escrito no es avance: la casilla queda vacía."""
        if not self.activa:
            return
        try:
            t = self.editor.get().strip().replace(",", "")
            if t and abs(float(t)) < 1e-12 and self._col(self.activa[1])["tipo"] == "entrada":
                self.editor.delete(0, "end")
        except (ValueError, tk.TclError, StopIteration):
            pass

    def mover_activa(self, d):
        """Enter / ↓ baja a la siguiente casilla que se puede escribir; ↑ sube."""
        if not self.activa:
            return
        r, cid = self.activa
        i = self._orden.index(r) if r in self._orden else -1
        j = i + d
        while 0 <= j < len(self._orden):
            if self._editable(self._orden[j], cid):
                self.activar(self._orden[j], cid, seleccionar=True)
                return
            j += d

    def _poner_editor(self, filas):
        if not self.activa:
            self.editor.place_forget()
            return
        r, cid = self.activa
        c = self._col(cid)
        en_der = c in self.der
        cv = self.cv_d if en_der else self.cv_i
        y = next((y for rr, y in filas if rr == r), None)
        x = c["x"] - (self._xoff if en_der else 0)
        if y is None or (en_der and (x + c["ancho"] < 0 or x > cv.winfo_width())):
            self.editor.place_forget()
            return
        alto = self.alto_hoja
        self.editor.place(in_=cv, x=x + 6, y=y + 4, width=c["ancho"] - 12, height=alto - 8)
        self.editor.lift()

    # ------------------------------------------------------------ fecha por columna
    def columna_fecha_en(self, cid):
        return any(c["id"] == cid for c in self.der)
