"""
Ctrl-P Android - tabla y arbol rapidos (RecycleView: solo se dibujan las filas visibles,
asi miles de partidas se mueven fluido en la tablet).
"""

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, DictProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior

import ui_k as ui
from ui_k import rgba

ESTILOS = {
    "": ("tarjeta", False, "texto"),
    "titulo0": ("titulo0", True, "texto"),
    "titulo": ("titulo", True, "texto"),
    "subtotal": ("subtotal", True, "texto"),
    "total": ("titulo0", True, "texto"),
    "fuera": ("tarjeta", False, "texto2"),
    "sel": ("sel", False, "texto"),
    "rojo": ("tarjeta", False, "rojo"),
    "verde": ("tarjeta", False, "verde"),          # al 100 % (o mas) de lo contractual
    "titulo_verde": ("titulo", True, "verde"),
}


class _Celda(Label):
    pass


class FilaTabla(RecycleDataViewBehavior, ButtonBehavior, BoxLayout):
    indice = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(orientation="horizontal", padding=[dp(6), 0, dp(6), 0], **kw)
        with self.canvas.before:
            self._cf = Color(*rgba("tarjeta"))
            self._rf = Rectangle()
            self._cl = Color(*rgba("linea"))
            self._rl = Rectangle()
        self.bind(pos=self._fondo, size=self._fondo)
        self.celdas = []
        self.tabla = None

    def _fondo(self, *_):
        self._rf.pos, self._rf.size = self.pos, self.size
        self._rl.pos, self._rl.size = self.pos, (self.width, 1)

    def _armar(self, cols):
        self.clear_widgets()
        self.celdas = []
        for k, (_, ancho, alin) in enumerate(cols):
            c = _Celda(font_size=sp(13), font_name=ui.FAM, halign=alin, valign="middle", shorten=True,
                       shorten_from="right", color=rgba("texto"))
            if ancho:
                c.size_hint_x = None
                c.width = dp(ancho)
            c.bind(size=lambda w, *_: setattr(w, "text_size", (w.width - dp(8), w.height)))
            self.celdas.append(c)
            self.add_widget(c)

    def refresh_view_attrs(self, rv, index, data):
        self.indice = index
        self.tabla = rv.tabla
        cols = rv.tabla.cols
        if len(self.celdas) != len(cols):
            self._armar(cols)
        fondo, negrita, colr = ESTILOS.get(data.get("estilo", ""), ESTILOS[""])
        if data.get("seleccionada"):
            fondo = "sel"
        self._cf.rgba = rgba(fondo)
        vals = data.get("vals", [])
        nivel = data.get("nivel", 0)
        abierto = data.get("abierto")
        for k, c in enumerate(self.celdas):
            t = str(vals[k]) if k < len(vals) else ""
            if k == rv.tabla.col_arbol:
                flecha = "" if abierto is None else ("▼  " if abierto else "▶  ")
                t = "    " * nivel + flecha + t
            c.text = t
            c.bold = negrita
            c.color = rgba(colr)
            if data.get("colores") and k in data["colores"]:
                c.color = rgba(data["colores"][k])
        return super().refresh_view_attrs(rv, index, data)

    def on_release(self):
        if self.tabla:
            self.tabla._tocar(self.indice)


class _RV(RecycleView):
    pass


class Tabla(BoxLayout):
    """cols: [(titulo, ancho_dp o None = flexible, 'left'|'right'|'center')].
    filas: [{'id', 'vals', 'estilo', 'nivel', 'abierto' (None = sin hijos), 'padre'}]"""

    def __init__(self, cols, al_tocar=None, arbol=False, col_arbol=0, alto_fila=46, min_flexible=220, **kw):
        super().__init__(orientation="vertical", **kw)
        self.cols, self.al_tocar, self.arbol, self.col_arbol = cols, al_tocar, arbol, col_arbol
        # si las columnas no entran a lo ancho, la tabla se desliza de lado (los textos no se aprietan)
        from kivy.uix.scrollview import ScrollView
        ancho_min = sum(dp(c[1]) for c in cols if c[1]) + sum(dp(min_flexible) for c in cols if not c[1]) + dp(20)
        lado = ScrollView(do_scroll_y=False, do_scroll_x=True, bar_width=dp(6), scroll_type=["bars", "content"],
                          effect_cls="ScrollEffect")
        interior = BoxLayout(orientation="vertical", size_hint_x=None)
        lado.bind(width=lambda *_: setattr(interior, "width", max(lado.width, ancho_min)))
        lado.add_widget(interior)
        super().add_widget(lado)
        self._interior = interior
        cab = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), padding=[dp(6), 0, dp(6), 0])
        self.add_widget = self._interior.add_widget
        with cab.canvas.before:
            Color(*rgba("subtotal"))
            r = Rectangle()
        cab.bind(pos=lambda *_: setattr(r, "pos", cab.pos), size=lambda *_: setattr(r, "size", cab.size))
        for t, ancho, alin in cols:
            c = Label(text=t, font_size=sp(12), bold=True, color=rgba("texto2"), font_name=ui.FAM, halign=alin,
                      valign="middle", shorten=True)
            if ancho:
                c.size_hint_x = None
                c.width = dp(ancho)
            c.bind(size=lambda w, *_: setattr(w, "text_size", (w.width - dp(8), w.height)))
            cab.add_widget(c)
        self.add_widget(cab)
        self.rv = _RV(bar_width=dp(8), scroll_type=["bars", "content"], effect_cls="ScrollEffect")
        self.rv.bar_color = rgba("texto2", 0.6)
        self.rv.bar_inactive_color = rgba("texto2", 0.3)
        self.rv.tabla = self
        lay = RecycleBoxLayout(orientation="vertical", size_hint_y=None, default_size=(None, dp(alto_fila)),
                               default_size_hint=(1, None))
        lay.bind(minimum_height=lay.setter("height"))
        self.rv.add_widget(lay)
        self.rv.viewclass = FilaTabla
        with self.rv.canvas.before:
            Color(*rgba("tarjeta"))
            rr = Rectangle()
        self.rv.bind(pos=lambda *_: setattr(rr, "pos", self.rv.pos), size=lambda *_: setattr(rr, "size", self.rv.size))
        self.add_widget(self.rv)
        del self.add_widget
        self.todas = []
        self.sel_id = None

    # ---------------------------------------------------------------- datos
    def cargar(self, filas, conservar_abiertos=True):
        abiertos = {f["id"] for f in self.todas if f.get("abierto")} if conservar_abiertos else set()
        for f in filas:
            if f.get("abierto") is not None and f["id"] in abiertos:
                f["abierto"] = True
        self.todas = filas
        self._mostrar()

    def _mostrar(self):
        if not self.arbol:
            vis = self.todas
        else:
            vis = []
            cerrado_desde = None
            for f in self.todas:
                n = f.get("nivel", 0)
                if cerrado_desde is not None and n > cerrado_desde:
                    continue
                cerrado_desde = None
                vis.append(f)
                if f.get("abierto") is False:
                    cerrado_desde = n
        for f in vis:
            f["seleccionada"] = f.get("id") is not None and f.get("id") == self.sel_id
        self.visibles = vis
        self.rv.data = vis
        self.rv.refresh_from_data()

    def desplegar(self, abrir):
        for f in self.todas:
            if f.get("abierto") is not None:
                f["abierto"] = abrir
        self._mostrar()

    def _tocar(self, i):
        if i >= len(self.visibles):
            return
        f = self.visibles[i]
        if f.get("abierto") is not None and self.arbol:
            f["abierto"] = not f["abierto"]
            self._mostrar()
            return
        if f.get("id") is not None:
            self.sel_id = f["id"]
            self._mostrar()
        if self.al_tocar:
            self.al_tocar(f)

    def seleccionar(self, iid, ver=True):
        self.sel_id = iid
        # abrir los padres
        por_id = {f.get("id"): f for f in self.todas}
        f = por_id.get(iid)
        while f is not None and f.get("padre"):
            pa = por_id.get(f["padre"])
            if pa is not None and pa.get("abierto") is False:
                pa["abierto"] = True
            f = pa
        self._mostrar()
        if ver:
            Clock.schedule_once(lambda *_: self.ver(iid), 0.05)

    def ver(self, iid):
        idx = next((k for k, f in enumerate(self.visibles) if f.get("id") == iid), None)
        if idx is None or not self.visibles:
            return
        alto_total = len(self.visibles) * self.rv.children[0].default_size[1]
        if alto_total <= self.rv.height:
            return
        y = idx * self.rv.children[0].default_size[1]
        self.rv.scroll_y = max(0, min(1, 1 - (y - self.rv.height / 3) / (alto_total - self.rv.height)))

    def poner_valor(self, iid, col, texto):
        for f in self.todas:
            if f.get("id") == iid:
                v = list(f["vals"])
                v[col] = texto
                f["vals"] = v
        self._mostrar()


def partidas_completas(p):
    """Partidas al 100 % (o mas) de su cantidad: van en verde en la lista de partidas."""
    ej = {i: sum(v.values()) for i, v in p.ejecutado().items()}
    return {it["id"] for it in p.items() if it["tipo"] == "P" and (it["cantidad"] or 0) > 1e-9
            and ej.get(it["id"], 0.0) >= it["cantidad"] * (1 - 5e-5)}


def filas_presupuesto(p, columnas, q="", con_fuera=False, marcas=None, completas=None):
    """Filas del arbol del presupuesto. columnas: funcion(it) -> lista de valores."""
    import ctrlp_core as core
    filas = []
    qn = core.clave_texto(q)
    items = p.items()
    completas = completas or set()
    if qn:
        for it in items:
            if it["tipo"] == "P" and it["vigente"] and (qn in core.clave_texto(it["descripcion"])
                                                        or qn in core.clave_texto(it["codigo"])):
                filas.append({"id": it["id"], "vals": columnas(it), "nivel": 0, "abierto": None, "padre": "",
                              "estilo": "verde" if it["id"] in completas else ""})
        return filas
    hijos = {}
    for it in items:
        hijos.setdefault(it["padre"], 0)
        hijos[it["padre"]] += 1
    nivel = {}
    fuera = []
    for it in items:
        if not it["vigente"]:
            fuera.append(it)
            continue
        n = (nivel.get(it["padre"], -1) + 1) if it["padre"] else 0
        nivel[it["id"]] = n
        es_t = it["tipo"] == "T"
        filas.append({"id": it["id"], "vals": columnas(it), "nivel": n, "padre": it["padre"] or "",
                      "abierto": (False if hijos.get(it["id"]) else None) if es_t else None,
                      "estilo": ("titulo0" if not it["padre"] else "titulo") if es_t else
                      ("verde" if it["id"] in completas else "")})
    if con_fuera and fuera:
        filas.append({"id": "__fuera", "vals": columnas(None) if False else ["", "FUERA DEL PRESUPUESTO VIGENTE (con avance)"],
                      "nivel": 0, "abierto": True, "estilo": "titulo0", "padre": ""})
        for it in fuera:
            filas.append({"id": it["id"], "vals": columnas(it), "nivel": 1, "abierto": None, "estilo": "fuera",
                          "padre": "__fuera"})
    return filas


class ArbolPartidas(BoxLayout):
    """Arbol del presupuesto con buscador, para elegir partida (Datos fijos, Registro)."""

    def __init__(self, app, al_elegir, columna_extra=None, **kw):
        super().__init__(orientation="vertical", spacing=dp(8), **kw)
        from ui_k import Boton, Campo, Fila
        self.app, self.al_elegir, self.extra = app, al_elegir, columna_extra
        self.marcas = {}
        f = Fila(alto=44, espacio=6)
        self.e_q = Campo("", pista="Buscar partida", al_cambiar=lambda *_: self._programar())
        f.add_widget(self.e_q)
        f.add_widget(Boton("Desplegar", ancho=96, tam=12, al_tocar=lambda: self.tabla.desplegar(True)))
        f.add_widget(Boton("Agrupar", ancho=86, tam=12, al_tocar=lambda: self.tabla.desplegar(False)))
        self.add_widget(f)
        cols = [("Código", 74, "left"), ("Descripción", None, "left")]
        if columna_extra:
            cols.append((columna_extra, 50, "center"))
        self.tabla = Tabla(cols, al_tocar=self._tocar, arbol=True, col_arbol=1, alto_fila=46)
        self.add_widget(self.tabla)

    def _programar(self):
        Clock.unschedule(self._cargar_ev)
        Clock.schedule_once(self._cargar_ev, 0.3)

    def _cargar_ev(self, *_):
        self.cargar()

    def cargar(self):
        p = self.app.p
        if not p:
            self.tabla.cargar([])
            return
        ex = bool(self.extra)

        def cols(it):
            v = [it["codigo"], it["descripcion"]]
            if ex:
                v.append(self.marcas.get(it["id"], "") if it["tipo"] == "P" else "")
            return v
        self.tabla.cargar(filas_presupuesto(p, cols, self.e_q.text, completas=partidas_completas(p)))
        if self.tabla.sel_id:
            self.tabla.seleccionar(self.tabla.sel_id)

    def _tocar(self, f):
        p = self.app.p
        it = p.item(f["id"]) if p and f.get("id") else None
        if it and it["tipo"] == "P":
            self.al_elegir(it)

    def ver(self, iid):
        self.tabla.seleccionar(iid)

    def poner_marca(self, iid, texto):
        self.marcas[iid] = texto
        if self.extra:
            self.tabla.poner_valor(iid, 2, texto)
