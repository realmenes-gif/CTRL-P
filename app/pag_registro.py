"""
Ctrl-P Android - Registro de avance
===================================
Igual que en la computadora: por partida y fecha, cantidad del dia en cada ubicacion (con equipos,
tramos, hitos y tipos de hitos), acumulados, % de avance, saldo, observaciones y monto cobrable.
La tabla usa RecycleView (solo dibuja lo visible) y los niveles con detalle se pliegan con un toque.
"""

import datetime as dt

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import ctrlp_core as core
import ui_k as ui
from paginas import Pagina
from tabla import ArbolPartidas
from ui_k import Boton, Campo, Etiqueta, Fila, Interruptor, Tarjeta, fmt, fmt_pct, leer_num, rgba, txt_num

# columnas: (titulo, ancho dp, alineacion)
COLS = [("Ubicación", None, "left"), ("Contractual", 96, "right"), ("Acum. ant.", 90, "right"),
        ("Del día", 110, "right"), ("Acum. total", 96, "right"), ("% avance", 82, "right"), ("Saldo", 92, "right"),
        ("Observación", 170, "left")]
MIN_UBIC = 200               # ancho minimo de la columna Ubicacion (si no entra, la tabla se desliza de lado)
ALTO_MAX_DETALLE = 80        # filas de detalle a partir de las cuales los niveles se pliegan


class _Toque(ButtonBehavior, Label):
    pass


class CampoTabla(TextInput):
    """Campo de la tabla: guarda en el modelo al escribir."""

    def __init__(self, numerico, **kw):
        super().__init__(multiline=False, write_tab=False, font_size=sp(14), font_name=ui.FAM, do_wrap=False, **kw)
        self.numerico = numerico
        self.background_normal = self.background_active = self.background_disabled_normal = ""
        self.background_color = rgba("campo")
        self.foreground_color = rgba("texto")
        self.disabled_foreground_color = rgba("texto2")
        self.cursor_color = rgba("acento")
        self.padding = [dp(8), dp(9), dp(8), 0]
        if numerico:
            self.halign = "right"
            self.bold = True
            self.input_type = "tel"
        from kivy.graphics import Line
        with self.canvas.after:
            self._cb = Color(*rgba("campo_borde"))
            self._ln = Line(width=1)
        self.bind(pos=self._borde, size=self._borde, focus=lambda *_: self.pintar(self._estado_borde))
        self._estado_borde = ""

    def _borde(self, *_):
        self._ln.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(6))

    def pintar(self, estado):
        self._estado_borde = estado
        if self.focus:
            self._cb.rgba = rgba("acento")
            self._ln.width = 1.6
        else:
            self._cb.rgba = rgba({"error": "rojo", "escrito": "acento"}.get(estado, "campo_borde"))
            self._ln.width = 1.3 if estado else 1

    def insert_text(self, s, from_undo=False):
        if self.numerico:
            s = "".join(ch for ch in s if ch in "0123456789.-,")
        return super().insert_text(s, from_undo=from_undo)


class FilaRegistro(RecycleDataViewBehavior, BoxLayout):
    indice = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(orientation="horizontal", padding=[dp(6), dp(4), dp(6), dp(4)], spacing=dp(4), **kw)
        with self.canvas.before:
            self._cf = Color(*rgba("tarjeta"))
            self._rf = Rectangle()
            self._cl = Color(*rgba("linea"))
            self._rl = Rectangle()
        self.bind(pos=self._fondo, size=self._fondo)
        self.pag = None
        self.data = None
        self._key = None
        self._armado_obs = None

    def _fondo(self, *_):
        self._rf.pos, self._rf.size = self.pos, self.size
        self._rl.pos, self._rl.size = self.pos, (self.width, 1)

    def _armar(self, con_obs):
        self.clear_widgets()
        self._armado_obs = con_obs
        self.l_ubic = _Toque(font_size=sp(13), font_name=ui.FAM, halign="left", valign="middle", color=rgba("texto"),
                             shorten=True, shorten_from="right")
        self.l_ubic.bind(size=lambda w, *_: setattr(w, "text_size", (w.width - dp(4), w.height)))
        self.l_ubic.bind(on_release=lambda *_: self.pag._toque_ubic(self.data))
        caja_u = BoxLayout(orientation="horizontal", spacing=dp(4))
        caja_u.add_widget(self.l_ubic)
        self.b_mas = Boton("", ancho=86, alto=34, tam=12, plano=True)
        self.b_mas.bind(on_release=lambda *_: self.pag._boton_mas(self.data))
        self.caja_mas = AnchorLayout(size_hint_x=None, width=0)
        caja_u.add_widget(self.caja_mas)
        self.add_widget(caja_u)
        self.lbls = {}
        for k in range(1, 8 if con_obs else 7):
            _, ancho, alin = COLS[k]
            if k == 3:
                caja = AnchorLayout(size_hint_x=None, width=dp(ancho))
                self.e_dia = CampoTabla(True, size_hint=(1, None), height=dp(38))
                self.e_dia.bind(text=lambda w, t: self.pag._escribio(self._key, "v", t) if self._key else None)
                self.l_dia = Label(font_size=sp(13), font_name=ui.FAM, halign="right", valign="middle",
                                   color=rgba("texto"))
                self.l_dia.bind(size=lambda w, *_: setattr(w, "text_size", (w.width - dp(6), w.height)))
                self.caja_dia = caja
                self.add_widget(caja)
                continue
            if k == 7:
                caja = AnchorLayout(size_hint_x=None, width=dp(ancho))
                self.e_obs = CampoTabla(False, size_hint=(1, None), height=dp(38))
                self.e_obs.bind(text=lambda w, t: self.pag._escribio(self._key, "obs", t) if self._key else None)
                self.caja_obs = caja
                self.add_widget(caja)
                continue
            lb = Label(font_size=sp(13), font_name=ui.FAM, halign=alin, valign="middle", color=rgba("texto"),
                       shorten=True)
            lb.size_hint_x = None
            lb.width = dp(ancho)
            lb.bind(size=lambda w, *_: setattr(w, "text_size", (w.width - dp(6), w.height)))
            self.lbls[k] = lb
            self.add_widget(lb)

    def _valores(self, data):
        neg = data.get("negrita", False)
        vals = data.get("vals", {})
        for k, lb in self.lbls.items():
            lb.text = vals.get(k, "")
            lb.bold = neg or (k == 7 and data.get("saldo_neg"))
            lb.color = rgba("rojo") if (k == 7 and data.get("saldo_neg")) else (
                rgba("texto2") if (k == 1 and vals.get(1) in ("—", "")) else rgba("texto"))
        self.l_dia.text = vals.get(3, "")
        self.l_dia.bold = neg

    def actualizar_valores(self):
        """Repinta solo los numeros (sin reasignar la fila): asi el campo donde se escribe no pierde el foco."""
        if not self.data:
            return
        self._valores(self.data)
        if self._key and self.pag is not None:
            f = self.pag.modelo.get(self._key)
            if f is not None:
                self.e_dia.pintar(f.get("borde", ""))

    def refresh_view_attrs(self, rv, index, data):
        self.indice = index
        self.pag = rv.pag
        con_obs = rv.pag.ver_obs
        if self._armado_obs != con_obs:
            self._armar(con_obs)
        nueva = data.get("key") if data.get("tipo") == "hoja" else None
        if nueva != self._key:
            # La fila se reutiliza para otra ubicacion: lo que se este escribiendo no debe pasar a la nueva.
            for campo in (self.e_dia, getattr(self, "e_obs", None)):
                if campo is not None and campo.focus:
                    campo.focus = False
        self._key = None          # que los campos no escriban mientras se cargan
        self.data = None
        fondo = data.get("fondo", "tarjeta")
        self._cf.rgba = rgba(fondo)
        neg = data.get("negrita", False)
        self.l_ubic.text = data.get("texto", "")
        self.l_ubic.bold = neg
        self.l_ubic.color = rgba("texto")
        mas = data.get("mas")
        self.caja_mas.clear_widgets()
        if mas:
            self.b_mas.text = mas
            self.caja_mas.width = dp(90)
            self.caja_mas.add_widget(self.b_mas)
        else:
            self.caja_mas.width = 0
        self._valores(data)
        self.caja_dia.clear_widgets()
        es_hoja = data.get("tipo") == "hoja"
        if es_hoja:
            f = rv.pag.modelo[data["key"]]
            self.caja_dia.add_widget(self.e_dia)
            if self.e_dia.text != f["v"]:
                self.e_dia.text = f["v"]
            self.e_dia.disabled = not f["editable"]
            self.e_dia.pintar(f.get("borde", ""))
        else:
            self.caja_dia.add_widget(self.l_dia)
        if con_obs:
            self.caja_obs.clear_widgets()
            if es_hoja:
                f = rv.pag.modelo[data["key"]]
                self.caja_obs.add_widget(self.e_obs)
                if self.e_obs.text != f["obs"]:
                    self.e_obs.text = f["obs"]
                self.e_obs.disabled = not f["editable"]
        self.data = data
        self._key = nueva
        return super().refresh_view_attrs(rv, index, data)


class _RVReg(RecycleView):
    pass


class PaginaRegistro(Pagina):
    clave = "registro"
    titulo = "Registro de avance"
    subtitulo = "Elegí la fecha, ingresá lo ejecutado en cada ubicación y guardá."

    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.fecha = core.hoy_iso()
        cd = self.cab_der
        cd.add_widget(Boton("◀ Partidas", ancho=120, al_tocar=self._alternar_arbol))
        cd.add_widget(Boton("←", ancho=48, al_tocar=lambda: self.mover_fecha(-1), tam=18))
        self.e_fecha = Campo(core.fecha_txt(self.fecha), ancho=150, alinear="center", negrita=True, tam=16,
                             al_enter=self.cambiar_fecha)
        self.e_fecha.bind(focus=lambda w, f: None if f else self.cambiar_fecha())
        cd.add_widget(self.e_fecha)
        cd.add_widget(Boton("→", ancho=48, al_tocar=lambda: self.mover_fecha(1), tam=18))
        cd.add_widget(Boton("Hoy", ancho=70, al_tocar=self.hoy))
        caja = BoxLayout(orientation="horizontal", spacing=dp(16))
        self.arbol = ArbolPartidas(app, self.elegir, "Hoy", size_hint_x=None, width=dp(340))
        caja.add_widget(self.arbol)
        self.panel = BoxLayout(orientation="vertical", spacing=dp(10))
        caja.add_widget(self.panel)
        self.caja = caja
        self.cuerpo.add_widget(caja)
        b = self.barra_inferior()
        izq = BoxLayout(orientation="vertical")
        self.l_estado = Etiqueta("", 14, True)
        self.l_monto = Etiqueta("", 12, color="texto2")
        izq.add_widget(self.l_estado)
        izq.add_widget(self.l_monto)
        b.add_widget(izq)
        self.ver_obs = bool(app.cfg.get("ver_observaciones", True))
        sw = BoxLayout(orientation="horizontal", size_hint_x=None, width=dp(190), spacing=dp(8))
        sw.add_widget(Label(text="Observaciones", font_size=sp(13), color=rgba("texto2"), font_name=ui.FAM))
        anc = AnchorLayout(size_hint_x=None, width=dp(56))
        anc.add_widget(Interruptor(self.ver_obs, al_cambiar=self._toggle_obs))
        sw.add_widget(anc)
        b.add_widget(sw)
        b.add_widget(Boton("Descartar", ancho=120, al_tocar=self.descartar))
        b.add_widget(Boton("Guardar", primario=True, ancho=140, al_tocar=self.guardar))
        self.it = None
        self.modelo = {}
        self.filas_vista = []
        self._abiertos = {}
        self.arbol_visible = True

    # ---------------------------------------------------------------- navegacion
    def _alternar_arbol(self):
        self.arbol_visible = not self.arbol_visible
        if self.arbol_visible:
            self.caja.add_widget(self.arbol, index=len(self.caja.children))
        else:
            self.caja.remove_widget(self.arbol)
        self.cab_der.children[-1].text = "◀ Partidas" if self.arbol_visible else "▶ Partidas"

    def al_cambiar_proyecto(self):
        self.it = None
        self.modelo = {}

    def refrescar(self):
        if not self.p:
            return
        self._marcas_dia()
        self.arbol.cargar()
        if self.it:
            self.arbol.ver(self.it["id"])
        self.mostrar()

    def _marcas_dia(self):
        self.arbol.marcas = {r[0]: "✓" for r in self.p.con.execute(
            "SELECT DISTINCT item FROM avances WHERE fecha=?", (self.fecha,))}

    def cambiar_fecha(self):
        try:
            f = core.txt_a_iso(self.e_fecha.text)
        except core.ErrorCtrlP as e:
            ui.info("Fecha", str(e))
            self.e_fecha.text = core.fecha_txt(self.fecha)
            return
        if f == self.fecha:
            self.e_fecha.text = core.fecha_txt(f)
            return

        def seguir():
            self.fecha = f
            self.e_fecha.text = core.fecha_txt(f)
            self.refrescar()
        self.antes_de_salir(seguir, al_cancelar=lambda: setattr(self.e_fecha, "text", core.fecha_txt(self.fecha)))

    def mover_fecha(self, d):
        nueva = (core.iso_a_fecha(self.fecha) + dt.timedelta(days=d)).isoformat()
        self.e_fecha.text = core.fecha_txt(nueva)
        self.cambiar_fecha()

    def hoy(self):
        self.e_fecha.text = core.fecha_txt(core.hoy_iso())
        self.cambiar_fecha()

    def elegir(self, it):
        if self.it and it["id"] == self.it["id"]:
            return

        def seguir():
            self.it = it
            self.mostrar()
            if self.arbol_visible and self.panel.width < dp(MIN_UBIC) + dp(820):
                self._alternar_arbol()
        self.antes_de_salir(seguir, al_cancelar=lambda: self.arbol.ver(self.it["id"]))

    # ---------------------------------------------------------------- pendientes
    def pendientes(self):
        n = 0
        for f in self.modelo.values():
            v = leer_num(f["v"])
            o = f["obs"].strip()
            if v == "error":
                n += 1
                continue
            orig = f["orig"]
            if orig is None:
                if (v is not None and abs(v) > 1e-9) or o:
                    n += 1
            elif v is None or abs(v - (orig["cantidad"] or 0)) > 1e-9 or o != (orig["obs"] or ""):
                n += 1
        return n

    def antes_de_salir(self, seguir, al_cancelar=None):
        if self.it and self.modelo and self.pendientes():
            def resp(k):
                if k == 2:
                    if self.guardar(preguntar_plano=False):
                        seguir()
                elif k == 1:
                    self.modelo = {}
                    seguir()
                elif al_cancelar:
                    al_cancelar()
            ui.opciones("Avances sin guardar", f"Hay {self.pendientes()} avances sin guardar en esta partida.",
                        ["Cancelar", "Descartar", "Guardar"], resp, primario=2)
            return
        seguir()

    def guardar_pendiente(self):
        if self.it and self.modelo and self.pendientes():
            return self.guardar(preguntar_plano=False)
        return True

    # ---------------------------------------------------------------- armado
    def mostrar(self, conservar=None):
        self.panel.clear_widgets()
        self.modelo = {}
        self.cabeceras = []
        self.filas_vista = []
        if not self.p:
            return
        if not self.p.edificios():
            self.panel.add_widget(Etiqueta("Primero creá las ubicaciones (edificios y áreas) en la sección Ubicaciones.",
                                           15, color="texto2"))
            self.panel.add_widget(Widget())
            self._estado()
            return
        if not self.it:
            self.panel.add_widget(Etiqueta("Elegí una partida en la lista de la izquierda.", 15, color="texto2"))
            self.panel.add_widget(Widget())
            self._estado()
            return
        p = self.p
        it = p.item(self.it["id"])
        self.it = it
        iid = it["id"]
        calc = core.Calculo(p, self.fecha, self.fecha)
        hitos = p.hitos_de(iid)
        con_tramos = bool(p.detalle_de(iid)["tramos"])
        con_equipos = bool(p.detalle_de(iid)["equipos"])
        ant_h = p.ejecutado_hojas(iid, hasta=core.dia_anterior(self.fecha))
        plano_h = p.ejecutado_hojas(iid, desde=self.fecha, hasta=self.fecha, marcas=True)
        cant_tipos = p.cant_tipos_de(iid)
        # cabecera de la partida
        t = Tarjeta(relleno=16, espacio=4)
        f1 = Fila(alto=30)
        f1.add_widget(Etiqueta(it["codigo"], 13, True, color="acento", ancho_fijo=90))
        f1.add_widget(Etiqueta(f"{it['unidad']}  ·  Cantidad {fmt(it['cantidad'])}  ·  P.U. {fmt(it['pu'])}", 12,
                               color="texto2"))
        f1.add_widget(Etiqueta("Avance general", 12, color="texto2", alinear="right", ancho_fijo=120))
        self.l_gen = Etiqueta("", 16, True, alinear="right", ancho_fijo=100)
        f1.add_widget(self.l_gen)
        t.add_widget(f1)
        t.add_widget(Etiqueta(it["descripcion"], 14, True))
        det = []
        if hitos:
            det.append("Pago por hitos: " + "  ·  ".join(
                (f"{tp}: " if tp else "") + ", ".join(f"{h['nombre']} {h['pct']:.2f} %" for h in hs)
                for tp, hs in p.tipos_hito(iid)))
        if con_tramos:
            det.append("Por tramos")
        if det:
            t.add_widget(Etiqueta("  ·  ".join(det), 11, color="texto2"))
        self.panel.add_widget(t)
        # tabla (si no entra a lo ancho, se desliza de lado; la columna Ubicacion nunca queda angosta)
        from kivy.uix.scrollview import ScrollView
        ancho_min = dp(MIN_UBIC) + sum(dp(c[1]) for k, c in enumerate(COLS) if c[1] and (k < 7 or self.ver_obs)) + dp(40)
        lado = ScrollView(do_scroll_y=False, do_scroll_x=True, bar_width=dp(6), scroll_type=["bars", "content"],
                          effect_cls="ScrollEffect")
        tabla = BoxLayout(orientation="vertical", size_hint_x=None)
        lado.bind(width=lambda *_: setattr(tabla, "width", max(lado.width, ancho_min)))
        lado.add_widget(tabla)
        cab = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(38), padding=[dp(6), 0], spacing=dp(4))
        with cab.canvas.before:
            Color(*rgba("subtotal"))
            r = Rectangle()
        cab.bind(pos=lambda *_: setattr(r, "pos", cab.pos), size=lambda *_: setattr(r, "size", cab.size))
        for k, (tt, ancho, alin) in enumerate(COLS):
            if k == 7 and not self.ver_obs:
                break
            lb = Label(text=tt, font_size=sp(12), bold=True, font_name=ui.FAM, halign=alin, valign="middle",
                       color=rgba("acento") if k == 3 else rgba("texto2"))
            if ancho:
                lb.size_hint_x = None
                lb.width = dp(ancho)
            lb.bind(size=lambda w, *_: setattr(w, "text_size", (w.width - dp(6), w.height)))
            cab.add_widget(lb)
        tabla.add_widget(cab)
        self.rv = _RVReg(bar_width=dp(8), scroll_type=["bars", "content"], effect_cls="ScrollEffect")
        self.rv.pag = self
        self.rv.bar_color = rgba("texto2", 0.6)
        lay = RecycleBoxLayout(orientation="vertical", size_hint_y=None, default_size=(None, dp(46)),
                               default_size_hint=(1, None))
        lay.bind(minimum_height=lay.setter("height"))
        self.rv.add_widget(lay)
        self.rv.viewclass = FilaRegistro
        tabla.add_widget(self.rv)
        self.panel.add_widget(lado)
        self.l_nota = Etiqueta("", 12, color="texto2")
        self.panel.add_widget(self.l_nota)
        # filas
        hoy = p.avances_del_dia(iid, self.fecha)
        H = hitos or [None]
        filas = []          # lista de dicts (vista); se filtran por niveles plegados

        def resumen(texto, fondo, indent=0, negrita=True, nv=None, mas=None, plegable=False):
            d = {"tipo": "res", "texto": " " * indent + texto, "fondo": fondo, "negrita": negrita, "vals": {},
                 "nv": nv, "mas": mas, "plegable": plegable, "base_texto": texto}
            filas.append(d)
            return d

        def hoja(texto, key, base, factor, edificio, indent, contractual_txt, bold=False, mas=None):
            nv, eq, tr, hi = key
            orig = hoy.get(key)
            pl = plano_h.get(key, 0.0)
            etq = " " * indent + texto + (f"  (+{fmt(pl)} en plano)" if abs(pl) > 1e-9 else "")
            self.modelo[key] = {"v": "" if orig is None else txt_num(orig["cantidad"]),
                                "obs": "" if orig is None else (orig["obs"] or ""), "orig": orig,
                                "ant": ant_h.get(key, 0.0), "plano": pl, "factor": factor, "base": base, "nivel": nv,
                                "edificio": edificio, "es_hito": bool(hi),
                                "editable": orig is None or p.puede_editar_avance(orig)}
            d = {"tipo": "hoja", "texto": etq, "fondo": "tarjeta", "negrita": bold, "key": key,
                 "vals": {1: contractual_txt, 2: fmt(ant_h.get(key, 0.0))}, "nv": nv, "mas": mas}
            filas.append(d)
            return d

        def bloque(nv, eq, base_grupo, edificio, indent):
            eid = eq["id"] if eq else ""
            tramos = p.tramos_de(iid, nv, eid) if con_tramos else []
            T = ([None] + tramos) if tramos else [None]
            keys = []
            for tr in T:
                tid = tr["id"] if tr else ""
                base = (tr["contractual"] or None) if tr else (base_grupo if len(T) == 1 else None)
                txt_tr = f"Tramo {tr['nombre']}" if tr else ("Sin tramo" if len(T) > 1 else "")
                if len(H) == 1:
                    k = (nv, eid, tid, "")
                    hoja(txt_tr or "Cantidad", k, base, 1.0, edificio, indent, fmt(tr["contractual"]) if tr else "—")
                    keys.append(k)
                else:
                    keys_tr = []
                    if len(T) > 1:
                        labt = resumen(txt_tr, "subtotal", indent, nv=nv)
                    ind_h = indent + 3 if len(T) > 1 else indent
                    for tp, hs in p.tipos_hito(iid):
                        ind_t = ind_h
                        base_t = base
                        if tp:
                            labtp = resumen(tp, "subtotal", ind_h, nv=nv)
                            ind_t = ind_h + 3
                            if not eid and not tid:
                                base_t = cant_tipos.get((nv, tp))
                        keys_tp = []
                        for h in hs:
                            k = (nv, eid, tid, h["id"])
                            hoja(f"{h['nombre']}", k, base_t, h["pct"] / 100.0, edificio, ind_t, f"{h['pct']:.2f} %")
                            keys_tp.append(k)
                        if tp:
                            self.cabeceras.append({"d": labtp, "keys": keys_tp,
                                                   "base": base_t if not eid and not tid else None})
                        keys_tr += keys_tp
                    if len(T) > 1:
                        self.cabeceras.append({"d": labt, "keys": keys_tr, "base": base if tr else None})
                    keys += keys_tr
            return keys

        self.labels_grupo = {}
        niveles_plegables = []
        for g in calc.detalle_ubicaciones(iid):
            for fl in g["filas"]:
                nv = fl["nivel"]
                nombre = g["nombre"] if g["es_area"] else f"{g['nombre']}  {fl['nombre']}"
                c_nv = fl["contractual"]
                tramos_nv = p.tramos_de(iid, nv, "") if con_tramos else []
                if not con_equipos and not tramos_nv and len(H) == 1:
                    hoja(nombre, (nv, "", "", ""), c_nv, 1.0, g["edificio"], 0, fmt(c_nv), bold=g["es_area"],
                         mas="+ tramo" if con_tramos else None)
                    continue
                labn = resumen(nombre, "titulo", nv=nv, mas="+ equipo" if con_equipos else ("+ tramo" if con_tramos else None),
                               plegable=True)
                n0 = len(filas)
                keys_nv = []
                if not con_equipos:
                    keys_nv = bloque(nv, None, c_nv, g["edificio"], 3)
                else:
                    for eq in [None] + p.equipos_de(iid, nv):
                        txt_eq = f"Equipo {eq['nombre']}" if eq else "Sin equipo"
                        base_eq = (eq["contractual"] or None) if eq else None
                        tiene_tr = bool(p.tramos_de(iid, nv, eq["id"] if eq else "")) if con_tramos else False
                        if not tiene_tr and len(H) == 1:
                            k = (nv, eq["id"] if eq else "", "", "")
                            hoja(txt_eq, k, base_eq if eq else None, 1.0, g["edificio"], 3,
                                 fmt(eq["contractual"]) if eq else "—", bold=bool(eq),
                                 mas="+ tramo" if (eq and con_tramos) else None)
                            if eq and con_tramos:
                                filas[-1]["equipo"] = eq["id"]
                            keys_nv.append(k)
                            continue
                        labe = resumen(txt_eq, "subtotal", 3, nv=nv, mas="+ tramo" if (eq and con_tramos) else None)
                        if eq:
                            labe["equipo"] = eq["id"]
                        ks = bloque(nv, eq, base_eq, g["edificio"], 6)
                        self.cabeceras.append({"d": labe, "keys": ks, "base": base_eq})
                        keys_nv += ks
                self.cabeceras.append({"d": labn, "keys": keys_nv, "base": c_nv})
                for d in filas[n0:]:
                    d["dentro_de"] = nv
                niveles_plegables.append((nv, labn, len(filas) - n0, len(keys_nv)))
            if not g["es_area"] and len(g["filas"]) > 1:
                self.labels_grupo[g["edificio"]] = resumen(f"Total {g['nombre']}", "subtotal")
        self.label_general = resumen("General", "titulo0")
        # plegar si hay mucho detalle
        n_det = sum(x[3] for x in niveles_plegables)
        self._plegar = n_det > ALTO_MAX_DETALLE
        abiertos = self._abiertos.setdefault(iid, set())
        abiertos |= {k[0] for k in hoy}
        for nv, labn, _, _ in niveles_plegables:
            labn["plegable"] = self._plegar
        self.todas = filas
        self.recalcular()

    def _vista(self):
        iid = self.it["id"]
        abiertos = self._abiertos.get(iid, set())
        vis = []
        for d in self.todas:
            if self._plegar and d.get("dentro_de") and d["dentro_de"] not in abiertos:
                continue
            if d.get("plegable") and self._plegar:
                d["texto"] = ("▼  " if d["nv"] in abiertos else "▶  ") + d["base_texto"]
            vis.append(d)
        self.filas_vista = vis
        self.rv.data = vis
        self.rv.refresh_from_data()

    def _toque_ubic(self, d):
        if not d or not d.get("plegable") or not self._plegar:
            return
        ab = self._abiertos.setdefault(self.it["id"], set())
        if d["nv"] in ab:
            ab.discard(d["nv"])
        else:
            ab.add(d["nv"])
        self._vista()

    def _boton_mas(self, d):
        if not d:
            return
        if d["mas"] == "+ equipo":
            self.agregar_equipo(d["nv"])
        else:
            self.agregar_tramo(d["nv"], d.get("equipo", ""))

    def _escribio(self, key, campo, texto):
        f = self.modelo.get(key)
        if f is None or f[campo] == texto:
            return
        f[campo] = texto
        Clock.unschedule(self._recalc_ev)
        Clock.schedule_once(self._recalc_ev, 0.25)

    def _recalc_ev(self, *_):
        self.recalcular(solo_valores=True)

    # ---------------------------------------------------------------- calculo (igual que en la computadora)
    def recalcular(self, solo_valores=False):
        if not self.it or not self.modelo:
            self._estado()
            return
        it = self.it
        cant = it["cantidad"] or 0
        vals = {}
        filas_por_key = {d["key"]: d for d in self.todas if d.get("tipo") == "hoja"}
        for key, f in self.modelo.items():
            v = leer_num(f["v"])
            hoy = 0.0 if v in (None, "error") else v
            raw_tot = f["ant"] + f["plano"] + hoy
            vals[key] = (f["ant"], f["plano"] + hoy, raw_tot)
            base = f["base"]
            d = filas_por_key[key]
            d["vals"][4] = fmt(raw_tot)
            d["vals"][5] = fmt_pct(core.pct(raw_tot, base)) if base else "—"
            d["vals"][6] = fmt(base - raw_tot) if base else "—"
            d["saldo_neg"] = bool(base and base - raw_tot < -1e-9)
            f["borde"] = "error" if v == "error" else ("escrito" if hoy else "")

        def eq(keys):
            a = sum(vals[k][0] * self.modelo[k]["factor"] for k in keys)
            dd = sum(vals[k][1] * self.modelo[k]["factor"] for k in keys)
            return a, dd, a + dd

        for c in self.cabeceras:
            a, dd, t_ = eq(c["keys"])
            base = c["base"]
            c["d"]["vals"] = {1: fmt(base), 2: fmt(a), 3: fmt(dd), 4: fmt(t_),
                              5: fmt_pct(core.pct(t_, base)) if base else "—", 6: fmt(base - t_) if base else "—"}
            c["d"]["saldo_neg"] = bool(base and base - t_ < -1e-9)
        por_nv_ant, por_nv_tot = {}, {}
        for key, f in self.modelo.items():
            nv = f["nivel"]
            por_nv_ant[nv] = por_nv_ant.get(nv, 0.0) + vals[key][0] * f["factor"]
            por_nv_tot[nv] = por_nv_tot.get(nv, 0.0) + vals[key][2] * f["factor"]
        cont = self.p.contractual_de(it["id"])
        for ed, d in self.labels_grupo.items():
            nvs = {f["nivel"] for f in self.modelo.values() if f["edificio"] == ed}
            conts = [cont[n] for n in nvs if n in cont]
            sc = sum(conts) if conts else None
            a = sum(por_nv_ant[n] for n in nvs)
            t_ = sum(por_nv_tot[n] for n in nvs)
            d["vals"] = {1: fmt(sc), 2: fmt(a), 3: fmt(t_ - a), 4: fmt(t_), 5: fmt_pct(core.pct(t_, sc)) if sc else "—",
                         6: fmt(sc - t_) if sc is not None else "—"}
            d["saldo_neg"] = bool(sc is not None and sc - t_ < -1e-9)
        a = sum(por_nv_ant.values())
        t_ = sum(por_nv_tot.values())
        g = self.label_general
        g["vals"] = {1: fmt(cant), 2: fmt(a), 3: fmt(t_ - a), 4: fmt(t_), 5: fmt_pct(core.pct(t_, cant)),
                     6: fmt(cant - t_)}
        g["saldo_neg"] = cant - t_ < -1e-9
        self.l_gen.text = fmt_pct(core.pct(t_, cant))
        eqs, trs = self.p.estructura_topes()
        eqs, trs = eqs.get(it["id"], {}), trs.get(it["id"], {})
        dg_ant, dg_tot = {}, {}
        for key, f in self.modelo.items():
            k3 = key[:3]
            dg_ant[k3] = dg_ant.get(k3, 0.0) + vals[key][0] * f["factor"]
            dg_tot[k3] = dg_tot.get(k3, 0.0) + vals[key][2] * f["factor"]
        cob_a, exc_a = core.cobrable_desglose(cant, cont, eqs, trs, dg_ant)
        cob_t, exc_t = core.cobrable_desglose(cant, cont, eqs, trs, dg_tot)
        self.monto_dia = (cob_t - cob_a) * (it["pu"] or 0)
        notas = []
        asign = sum(cont.values())
        if cont and abs(asign - cant) > 0.005:
            notas.append(f"●  Contractual asignado {fmt(asign)} de {fmt(cant)} {it['unidad']}.")
        if any(f["es_hito"] for f in self.modelo.values()):
            notas.append("Con hitos, «Acum.» y «Del día» de las filas de cada ubicación son cantidades equivalentes "
                         "(cantidad × % del hito).")
        if self._plegar:
            notas.append("Tocá el nombre de un nivel para ver u ocultar su detalle.")
        if exc_t - exc_a > 1e-9:
            notas.append(f"Con este registro quedan {fmt(exc_t - exc_a)} {it['unidad']} como excedente no cobrable.")
        self.l_nota.text = "     ".join(notas)
        if solo_valores:
            for w in list(self.rv.layout_manager.children if self.rv.layout_manager else []):
                if isinstance(w, FilaRegistro):
                    w.actualizar_valores()
        else:
            self._vista()
        self._estado()

    def _estado(self):
        n = self.pendientes() if self.modelo else 0
        self.l_estado.text = (f"{n} avances sin guardar · {core.fecha_txt(self.fecha)}" if n
                              else f"Fecha de registro: {core.fecha_txt(self.fecha)}")
        if self.it and self.modelo:
            tp = self.p.total_presupuesto() or 1
            m = getattr(self, "monto_dia", 0)
            self.l_monto.text = (f"Monto cobrable del día en esta partida: {self.p.get_meta('moneda', 'US$')} "
                                 f"{fmt(m)} · {fmt_pct(m / tp, 3)} del presupuesto")
        else:
            self.l_monto.text = ""

    def _toggle_obs(self, si):
        self.ver_obs = si
        self.app.cfg = core.config_poner(ver_observaciones=bool(si))
        if self.it:
            guard = {k: (f["v"], f["obs"]) for k, f in self.modelo.items()}
            self.mostrar()
            for k, (v, o) in guard.items():
                if k in self.modelo:
                    self.modelo[k]["v"], self.modelo[k]["obs"] = v, o
            self.recalcular()

    # ---------------------------------------------------------------- equipos / tramos
    def agregar_equipo(self, nv):
        def crear(r):
            c = leer_num(r["cant"])
            try:
                if c == "error":
                    raise core.ErrorCtrlP("Cantidad no válida.")
                self.p.crear_equipo(self.it["id"], nv, r["nombre"], c)
            except core.ErrorCtrlP as e:
                ui.info("Nuevo equipo", str(e))
                return
            self.app.guardar()
            self.mostrar()

        def form():
            ui.formulario("Nuevo equipo", f"{self.it['codigo']} · {self.p.etiqueta_ubicacion(nv)}",
                          [("nombre", "Nombre del equipo (ej. UMA-01)", False, "", True),
                           ("cant", f"Cantidad asignada en {self.it['unidad']} (opcional, es su tope de cobro)", False, "")],
                          ["Cancelar", "Crear equipo"], crear)
        self._guardar_antes("Nuevo equipo", form)

    def agregar_tramo(self, nv, equipo=""):
        ub = self.p.etiqueta_ubicacion(nv) + (f" · equipo {self.p.nombre_equipo(equipo)}" if equipo else "")

        def crear(r):
            c = leer_num(r["cant"])
            try:
                if c == "error":
                    raise core.ErrorCtrlP("Cantidad no válida.")
                self.p.crear_tramo(self.it["id"], nv, r["nombre"], c, equipo=equipo)
            except core.ErrorCtrlP as e:
                ui.info("Nuevo tramo", str(e))
                return
            self.app.guardar()
            self.mostrar()

        def form():
            ui.formulario("Nuevo tramo", f"{self.it['codigo']} · {ub}",
                          [("nombre", "Nombre del tramo (ej. PV-3 a PV-4)", False, "", True),
                           ("cant", f"Cantidad del tramo en {self.it['unidad']} (opcional, es su tope de cobro)", False, "")],
                          ["Cancelar", "Crear tramo"], crear)
        self._guardar_antes("Nuevo tramo", form)

    def _guardar_antes(self, titulo, seguir):
        if self.pendientes():
            def r(si):
                if si and self.guardar(preguntar_plano=False):
                    seguir()
            ui.preguntar(titulo, "Primero se guardan los avances escritos. ¿Continuar?", r, si="Guardar")
            return
        seguir()

    # ---------------------------------------------------------------- guardar
    def descartar(self):
        self.mostrar()

    def guardar(self, preguntar_plano=True):
        if not self.it:
            return True
        errores = [f["v"] for f in self.modelo.values() if leer_num(f["v"]) == "error"]
        if errores:
            ui.info("Registro de avance", f"Hay cantidades no válidas: {', '.join(errores[:3])}")
            return False
        n = 0
        try:
            for (nv, eq, tr, hi), f in self.modelo.items():
                v = leer_num(f["v"])
                o = f["obs"]
                if f["orig"] is None and (v is None or abs(v) < 1e-12) and not o.strip():
                    continue
                if f["orig"] is not None and not self.p.puede_editar_avance(f["orig"]):
                    continue
                if self.p.guardar_avance(self.it["id"], nv, self.fecha, v, o, hito=hi, tramo=tr, equipo=eq):
                    n += 1
        except core.ErrorCtrlP as e:
            ui.info("Registro de avance", str(e))
            return False
        if n:
            self.app.guardar()
        self._marcas_dia()
        self.arbol.poner_marca(self.it["id"], self.arbol.marcas.get(self.it["id"], ""))
        guardados = list(self.modelo.items())
        self.mostrar()
        self.l_estado.text = ((f"{n} avance guardado" if n == 1 else f"{n} avances guardados")
                              + f" · {core.fecha_txt(self.fecha)}") if n else "Sin cambios para guardar."
        if n:
            ui.aviso(self.l_estado.text)
        if n and preguntar_plano:
            niveles = []
            for (nv, eq, tr, hi), f in guardados:
                v = leer_num(f["v"])
                if isinstance(v, float) and v > 0 and nv not in niveles and self.p.planos(nv):
                    niveles.append(nv)
            if niveles:
                it = self.it

                def r(si):
                    if si:
                        self.app.ir("planos")
                        self.app.paginas["planos"].preparar(it["id"], niveles[0], self.fecha)
                ui.preguntar("¿Marcar en el plano?",
                             f"{it['codigo']} tiene plano en {', '.join(self.p.etiqueta_ubicacion(x) for x in niveles)}."
                             "\n\nPodés marcar ahora por dónde va este avance, o dejarlo pendiente y marcarlo después "
                             "desde Planos.", r, si="Marcar ahora", no="Después")
        return True


def Window_angosta():
    from kivy.core.window import Window
    return Window.width / dp(1) < 1250
