"""
Ctrl-P Android - Planos
=======================
Libreria de planos y registro de avance sobre el plano, igual que en la computadora:
actividades del dia (o por acumulado), hojas por actividad, colores por edificio, marcas (linea, linea libre,
rectangulo, circulo, poligono, area libre con iman, punto), vacios en areas, calibrar, editar/mover/borrar
marcas, deshacer, quitar hoja, eliminar plano, estilos y notas.
"""

import json
import os

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget

import ctrlp_core as core
import planos_base as pb
import ui_k as ui
from paginas import Pagina
from tabla import Tabla
from ui_k import (Boton, Campo, Casilla, Columna, Contador, Desplazable, Espacio, Etiqueta, Fila, Interruptor, Menu,
                  Segmentado, Tarjeta, fmt, leer_num, rgba)
from visor import Visor, elegir_color

GRUPOS_HERR = (("Mover", "Editar"), ("Línea", "Línea libre", "Polígono", "Área libre"), ("Rectángulo", "Círculo", "Punto"),
               ("Calibrar",))
HERR = dict(pb.HERRAMIENTAS)
NOMBRE_HERR = {v: k for k, v in pb.HERRAMIENTAS}


def preguntar_borrado(titulo, que, marcas, al_responder):
    """al_responder(0 cancelar, 1 conservar avances, 2 borrar tambien el avance)."""
    con_av = [m for m in marcas if not m.get("visual")]
    if not con_av:
        msg = f"¿Eliminar {que}?" + (f"\n\nSus {len(marcas)} marcas solo ubican registros manuales: esos registros "
                                     "vuelven a quedar sin marcar." if marcas else "")
        ui.preguntar(titulo, msg, lambda si: al_responder(1 if si else 0), si="Eliminar")
        return
    ui.opciones(titulo, f"¿Eliminar {que}?\n\nTiene {len(marcas)} marcas; {len(con_av)} registraron avance al marcar.\n"
                "«Conservar avances»: se borran los dibujos y las cantidades quedan como registros manuales sin marcar.\n"
                "«Borrar también el avance»: esas cantidades dejan de contar (quedan en el historial).",
                ["Cancelar", "Conservar avances", "Borrar también el avance"], lambda k: al_responder(k or 0), primario=1)


class PaginaPlanos(Pagina):
    clave = "planos"
    titulo = "Planos"
    subtitulo = ("Librería de planos y registro de avance. Cada actividad marca en su propia hoja; los colores son por "
                 "edificio (en Informes se ven por fecha).")

    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.cab_der.add_widget(Boton("◀ Panel", ancho=110, al_tocar=self._alternar_panel))
        self.b_lib = Boton("Librería de planos…", primario=True, ancho=210,
                           al_tocar=lambda: DialogoLibreria(app, self).open())
        self.cab_der.add_widget(self.b_lib)
        caja = BoxLayout(orientation="horizontal", spacing=dp(12))
        # ---- panel izquierdo
        izq = Tarjeta(relleno=12, espacio=6, ajustar_alto=False, size_hint_x=None, width=dp(350))
        f = Fila(alto=44, espacio=6)
        self.l_fecha = Etiqueta("Fecha", 12, color="texto2", ancho_fijo=58)
        f.add_widget(self.l_fecha)
        self.e_fecha = Campo(core.fecha_txt(core.hoy_iso()), ancho=124, alinear="center",
                             al_enter=lambda: self.cargar_actividades())
        self.e_fecha.bind(focus=lambda w, v: None if v else self.cargar_actividades())
        f.add_widget(self.e_fecha)
        f.add_widget(Widget())
        self.sw_acum = Interruptor(False, al_cambiar=lambda _: self._cambiar_acum())
        anc = AnchorLayout(size_hint_x=None, width=dp(56))
        anc.add_widget(self.sw_acum)
        f.add_widget(anc)
        f.add_widget(Etiqueta("Por acumulado", 11, color="texto2", ancho_fijo=70))
        izq.add_widget(f)
        self.l_resumen = Etiqueta("", 11, color="texto2")
        izq.add_widget(self.l_resumen)
        self.t_act = Tabla([("Actividad del día", None, "left"), ("Sin marcar", 84, "right")], al_tocar=self._elegir_act,
                           arbol=True, col_arbol=0, alto_fila=44, min_flexible=180)
        izq.add_widget(self.t_act)
        izq.add_widget(Boton("Otra actividad…", ancho=180, alto=40, al_tocar=self.otra_actividad))
        izq.add_widget(Etiqueta("Hojas de la actividad", 14, True))
        self.t_hojas = Tabla([("Plano · alcance", None, "left"), ("Marcas", 70, "right")], al_tocar=self._elegir_hoja,
                             alto_fila=44, min_flexible=180, size_hint_y=0.6)
        izq.add_widget(self.t_hojas)
        fb = Fila(alto=40, espacio=6)
        self.b_nueva = Boton("Nueva hoja limpia…", alto=40, tam=12, al_tocar=self.nueva_hoja)
        fb.add_widget(self.b_nueva)
        fb.add_widget(Boton("Quitar hoja", ancho=100, alto=40, tam=12, al_tocar=self.quitar_hoja))
        fb.add_widget(Boton("Estilo…", ancho=76, alto=40, tam=12, al_tocar=self.estilo))
        izq.add_widget(fb)
        fn = Fila(alto=44, espacio=6)
        fn.add_widget(Etiqueta("Marcando en", 11, color="texto2", ancho_fijo=80))
        self.m_nivel = Menu([""], "", al_cambiar=lambda _: self._estado_hoja())
        fn.add_widget(self.m_nivel)
        izq.add_widget(fn)
        self.izq = izq
        caja.add_widget(izq)
        # ---- derecha: barra + visor
        der = BoxLayout(orientation="vertical", spacing=dp(8))
        ctl = Tarjeta(relleno=10, espacio=6)
        f1 = Fila(alto=40, espacio=6)
        self.l_titulo = Etiqueta("", 14, True, una_linea=True)
        f1.add_widget(self.l_titulo)
        self.l_escala = Etiqueta("", 11, color="texto2", alinear="right", ancho_fijo=170)
        f1.add_widget(self.l_escala)
        f1.add_widget(Boton("−", ancho=44, alto=40, tam=18, al_tocar=lambda: self.visor.zoom_centro(1 / 1.4)))
        f1.add_widget(Boton("Ajustar", ancho=86, alto=40, al_tocar=lambda: self.visor.ajustar()))
        f1.add_widget(Boton("+", ancho=44, alto=40, tam=18, al_tocar=lambda: self.visor.zoom_centro(1.4)))
        ctl.add_widget(f1)
        self.segs = []
        anchos = {1: 120, 4: 104}
        segs_ws = []
        for g in GRUPOS_HERR:
            s = Segmentado(list(g), "Mover" if "Mover" in g else "__", alto=40,
                           ancho=sum(18 + 9 * len(x) for x in g) + 20, al_cambiar=self._herr)
            self.segs.append(s)
            segs_ws.append(s)
        from pag_informes import FlujoAlto
        self.flujo_herr = FlujoAlto(segs_ws, espacio=8)
        ctl.add_widget(self.flujo_herr)
        f3 = Fila(alto=36, espacio=8)
        self.f_leyenda = BoxLayout(orientation="horizontal", spacing=dp(4))
        f3.add_widget(self.f_leyenda)
        f3.add_widget(Etiqueta("Imán", 11, color="texto2", ancho_fijo=40))
        self.sw_iman = Interruptor(True, al_cambiar=self._iman)
        a1 = AnchorLayout(size_hint_x=None, width=dp(56))
        a1.add_widget(self.sw_iman)
        f3.add_widget(a1)
        f3.add_widget(Etiqueta("Notas", 11, color="texto2", ancho_fijo=44))
        self.sw_notas = Interruptor(True, al_cambiar=self._notas)
        a2 = AnchorLayout(size_hint_x=None, width=dp(56))
        a2.add_widget(self.sw_notas)
        f3.add_widget(a2)
        ctl.add_widget(f3)
        der.add_widget(ctl)
        self.marco = FloatLayout()
        marco_t = Tarjeta(relleno=4, ajustar_alto=False, pos_hint={"x": 0, "y": 0})
        self.visor = Visor(self.al_terminar, self.al_seleccionar, self.al_estado)
        self.visor.al_editar = self.al_mover_marca
        self.visor.al_doble = self.editar
        marco_t.add_widget(self.visor)
        self.marco.add_widget(marco_t)
        self.l_vacio = Etiqueta("", 15, color="texto2", alinear="center", size_hint=(0.8, None),
                                pos_hint={"center_x": 0.5, "center_y": 0.55})
        self.flotante = BoxLayout(orientation="horizontal", size_hint=(None, None), height=dp(52), spacing=dp(8),
                                  padding=dp(4), pos_hint={"center_x": 0.5, "top": 0.98})
        self.flotante.bind(minimum_width=self.flotante.setter("width"))
        der.add_widget(self.marco)
        caja.add_widget(der)
        self.caja = caja
        self.cuerpo.add_widget(caja)
        b = self.barra_inferior()
        self.l_estado = Etiqueta("", 12, color="texto2")
        b.add_widget(self.l_estado)
        self.b_deshacer = Boton("Deshacer", ancho=120, al_tocar=self.deshacer)
        b.add_widget(self.b_deshacer)
        self.b_editar = Boton("Datos de la marca", ancho=170, al_tocar=self.editar)
        b.add_widget(self.b_editar)
        self.b_anular = Boton("Borrar marca", ancho=140, al_tocar=self.anular)
        b.add_widget(self.b_anular)
        self.b_editar.disabled = self.b_anular.disabled = True
        self.pid = self.item = self.act = self.sel = None
        self.marcas_vis = []
        self._img_cache = {}
        self._acts = {}
        self._vista_flotante = None
        Clock.schedule_interval(self._revisar_flotante, 0.25)

    # ---------------------------------------------------------------- panel y herramientas
    def _alternar_panel(self):
        if self.izq.parent:
            self.caja.remove_widget(self.izq)
            self.cab_der.children[-1].text = "▶ Panel"
        else:
            self.caja.add_widget(self.izq, index=len(self.caja.children))
            self.cab_der.children[-1].text = "◀ Panel"
        Clock.schedule_once(lambda *_: self.visor.programar(0.05), 0.1)

    def _herr(self, nombre):
        for s in self.segs:
            s.poner(nombre if nombre in s.botones else "__")
        self.visor.usar(HERR[nombre])

    def _poner_herr(self, nombre):
        for s in self.segs:
            s.poner(nombre if nombre in s.botones else "__")

    def _revisar_flotante(self, *_):
        """Botones flotantes sobre el plano mientras se dibuja (Terminar / Quitar punto / Cancelar) o los vacios."""
        v = self.visor
        if v.vacios:
            modo = "vacios"
        elif v.pts and v.herr in ("linea", "area", "area_libre", "calibrar"):
            modo = "dibujo"
        else:
            modo = None
        if modo == self._vista_flotante:
            return
        self._vista_flotante = modo
        f = self.flotante
        f.clear_widgets()
        if f.parent:
            self.marco.remove_widget(f)
        if not modo:
            return
        if modo == "vacios":
            f.add_widget(Etiqueta("Vacíos del área", 13, True, ancho_fijo=130))
            f.add_widget(Boton("Quitar último", ancho=140, al_tocar=v.deshacer_vacio))
            f.add_widget(Boton("Cancelar", ancho=110, al_tocar=lambda: v.terminar_vacios(False)))
            f.add_widget(Boton("Listo", primario=True, ancho=100, al_tocar=lambda: v.terminar_vacios(True)))
        else:
            if v.herr != "calibrar":
                f.add_widget(Boton("Terminar", primario=True, ancho=120, al_tocar=v.terminar))
            f.add_widget(Boton("Quitar punto", ancho=140, al_tocar=v.deshacer_punto))
            f.add_widget(Boton("Cancelar", ancho=110, al_tocar=v.cancelar))
        self.marco.add_widget(f)

    def _iman(self, si):
        self.visor.iman = si
        self.visor.snap = None
        self.visor._dibujar_temporal()

    def _notas(self, si):
        self.visor.notas = si
        self.visor.redibujar()

    def atras(self):
        """Boton Atras de Android: primero cancela el dibujo en curso."""
        if self.visor.vacios or self.visor.pts:
            self.visor.cancelar()
            return True
        return False

    # ---------------------------------------------------------------- estado general
    def al_cambiar_proyecto(self):
        self.pid = self.item = self.act = self.sel = None
        self._img_cache = {}
        self.visor.limpiar()

    def _fecha(self):
        try:
            f = core.txt_a_iso(self.e_fecha.text)
        except core.ErrorCtrlP as e:
            ui.info("Fecha", str(e))
            return None
        self.e_fecha.text = core.fecha_txt(f)
        return f

    @property
    def nivel(self):
        if not self.pid:
            return None
        nvs = self.p.plano_niveles(self.pid)
        if len(nvs) == 1:
            return nvs[0]
        for nv in nvs:
            if self.p.etiqueta_ubicacion(nv) == self.m_nivel.valor:
                return nv
        return None

    def refrescar(self):
        if not self.p:
            return
        self.b_lib.disabled = False
        self.cargar_actividades()
        self._hojas()
        if not self.p.planos():
            self._vacio("La librería está vacía.\n\nAbrí «Librería de planos…» y cargá los planos (PDF o imagen), "
                        "vinculados por nivel, por edificio o generales.\nEs opcional: solo si querés llevar ese control.")
        elif not self.pid:
            self._vacio("Elegí una actividad a la izquierda y abrí una de sus hojas,\no empezá una «Nueva hoja limpia…» "
                        "con un plano de la librería.")
        else:
            if self.l_vacio.parent:
                self.marco.remove_widget(self.l_vacio)
            self.cargar_marcas()

    def _vacio(self, txt):
        self.visor.limpiar()
        self.l_titulo.text = ""
        self.l_escala.text = ""
        self.l_vacio.text = txt
        if not self.l_vacio.parent:
            self.marco.add_widget(self.l_vacio)
        self.f_leyenda.clear_widgets()

    # ---------------------------------------------------------------- actividades
    def cargar_actividades(self):
        self._acts = {}
        if not self.p:
            self.t_act.cargar([])
            return
        f = self._fecha()
        if not f:
            return
        if self.sw_acum.activo:
            return self._cargar_acumulado(f)
        p = self.p
        items = {i["id"]: i for i in p.items()}
        niveles_con_plano = {r[0] for r in p.con.execute("SELECT DISTINCT nivel FROM plano_ubic")}
        cortes = p.cortes_acumulado()
        pend = [dict(r) for r in p.con.execute(
            "SELECT * FROM avances WHERE marca='' AND cantidad>0 AND fecha=? ORDER BY item", (f,))]
        orden = []
        for x in pend:
            ub = p.con.execute("SELECT COALESCE(SUM(cantidad),0) FROM marcas WHERE ref=? AND anulada=0 AND visual=1",
                               (x["id"],)).fetchone()[0]
            x["pendiente"] = max(x["cantidad"] - ub, 0.0)
            c = cortes.get((x["item"], x["nivel"], x["equipo"] or "", x["tramo"] or "", x["hito"] or ""))
            x["en_acum"] = bool(c and c >= x["fecha"])
            if x["en_acum"]:
                x["pendiente"] = 0.0
            if x["item"] not in orden:
                orden.append(x["item"])
        if self.item and self.item not in orden and self.item in items:
            orden.append(self.item)
        orden.sort(key=lambda i: items[i]["orden"] if i in items else 0)
        n_pend = 0
        filas = []
        for iid in orden:
            it = items.get(iid)
            if not it:
                continue
            falta = sum(x["pendiente"] for x in pend if x["item"] == iid and x["nivel"] in niveles_con_plano)
            n_pend += 1 if falta > 1e-9 else 0
            hijos = [x for x in pend if x["item"] == iid]
            filas.append({"id": f"i:{iid}", "nivel": 0, "abierto": True if hijos else None, "estilo": "titulo",
                          "vals": [f"{it['codigo']} {it['descripcion'][:40]}",
                                   f"{fmt(falta)} {it['unidad']}" if falta else "✓"]})
            self._acts[f"i:{iid}"] = {"item": iid, "ref": "", "fecha": f}
            for x in hijos:
                partes = [p.etiqueta_ubicacion(x["nivel"])]
                if x["equipo"]:
                    partes.append(p.nombre_equipo(x["equipo"]))
                if x["tramo"]:
                    partes.append("T " + p.nombre_tramo(x["tramo"]))
                if x["hito"]:
                    partes.append(p.nombre_hito(x["hito"]))
                partes.append(f"{fmt(x['cantidad'])} {it['unidad']}")
                sin_plano = x["nivel"] not in niveles_con_plano
                k = f"r:{x['id']}"
                filas.append({"id": k, "nivel": 1, "padre": f"i:{iid}", "abierto": None,
                              "estilo": "fuera" if (sin_plano or x["pendiente"] <= 1e-9) else "",
                              "vals": [" · ".join(partes), "sin plano" if sin_plano else (
                                  "en acum." if x["en_acum"] else (fmt(x["pendiente"]) if x["pendiente"] > 1e-9 else "✓"))]})
                self._acts[k] = {"item": iid, "nivel": x["nivel"], "equipo": x["equipo"], "tramo": x["tramo"],
                                 "hito": x["hito"], "ref": x["id"], "pendiente": x["pendiente"],
                                 "cantidad_reg": x["cantidad"], "fecha": x["fecha"]}
        self.l_resumen.text = (f"{core.fecha_txt(f)} · {len(orden)} actividades" +
                               (f", {n_pend} con avance sin marcar" if n_pend else ""))
        if not orden:
            filas.append({"id": None, "nivel": 0, "abierto": None, "estilo": "fuera", "vals": ["Sin avance este día.", ""]})
        self.t_act.cargar(filas, False)
        self._resaltar_act()

    def _resaltar_act(self):
        k = (self.act or {}).get("clave") or (f"r:{self.act['ref']}" if (self.act or {}).get("ref") and
                                              self.act["ref"] != core.ACUM else None)
        if k and k in self._acts:
            self.t_act.seleccionar(k, ver=False)
        elif self.item and f"i:{self.item}" in self._acts:
            self.t_act.seleccionar(f"i:{self.item}", ver=False)

    def _cambiar_acum(self):
        on = self.sw_acum.activo
        self.l_fecha.text = "Corte al" if on else "Fecha"
        self.act = None
        self.cargar_actividades()
        if on:
            self.l_estado.text = ("Marcar por acumulado: elegí la actividad y ubicación y dibujá todo lo ejecutado hasta "
                                  "la fecha de corte. No crea avance nuevo: ubica en el plano lo que ya está registrado.")

    def _cargar_acumulado(self, f):
        p = self.p
        items = {i["id"]: i for i in p.items()}
        niveles_con_plano = {r[0] for r in p.con.execute("SELECT DISTINCT nivel FROM plano_ubic")}
        datos = p.acumulado_plano(f)
        orden = sorted({x["item"] for x in datos} | ({self.item} if self.item in items else set()),
                       key=lambda i: items[i]["orden"] if i in items else 0)
        n_pend = 0
        filas = []
        for iid in orden:
            it = items.get(iid)
            if not it:
                continue
            mias = [x for x in datos if x["item"] == iid]
            falta = sum(x["pendiente"] for x in mias if x["nivel"] in niveles_con_plano)
            n_pend += 1 if falta > 1e-9 else 0
            filas.append({"id": f"i:{iid}", "nivel": 0, "abierto": True if mias else None, "estilo": "titulo",
                          "vals": [f"{it['codigo']} {it['descripcion'][:40]}",
                                   f"{fmt(falta)} {it['unidad']}" if falta else "✓"]})
            self._acts[f"i:{iid}"] = {"item": iid, "ref": "", "fecha": f}
            for x in sorted(mias, key=lambda x: p.etiqueta_ubicacion(x["nivel"])):
                partes = [p.etiqueta_ubicacion(x["nivel"])]
                if x["equipo"]:
                    partes.append(p.nombre_equipo(x["equipo"]))
                if x["tramo"]:
                    partes.append("T " + p.nombre_tramo(x["tramo"]))
                if x["hito"]:
                    partes.append(p.nombre_hito(x["hito"]))
                partes.append(f"acum. {fmt(x['acumulado'])} {it['unidad']}")
                sin_plano = x["nivel"] not in niveles_con_plano
                k = "a:" + "|".join((iid, x["nivel"], x["equipo"], x["tramo"], x["hito"]))
                filas.append({"id": k, "nivel": 1, "padre": f"i:{iid}", "abierto": None,
                              "estilo": "fuera" if (sin_plano or x["pendiente"] <= 1e-9) else "",
                              "vals": [" · ".join(partes), "sin plano" if sin_plano else (
                                  fmt(x["pendiente"]) if x["pendiente"] > 1e-9 else "✓")]})
                self._acts[k] = {"item": iid, "nivel": x["nivel"], "equipo": x["equipo"], "tramo": x["tramo"],
                                 "hito": x["hito"], "ref": core.ACUM, "pendiente": x["pendiente"],
                                 "cantidad_reg": x["acumulado"], "fecha": f, "clave": k}
        self.l_resumen.text = (f"Acumulado al {core.fecha_txt(f)} · {len(orden)} actividades" +
                               (f", {n_pend} con avance sin marcar" if n_pend else ""))
        if not orden:
            filas.append({"id": None, "nivel": 0, "abierto": None, "estilo": "fuera",
                          "vals": ["Sin avance a esa fecha.", ""]})
        self.t_act.cargar(filas, False)
        self._resaltar_act()

    def _elegir_act(self, fila):
        k = fila.get("id")
        if k not in self._acts:
            return
        act = dict(self._acts[k])
        cambio = act["item"] != self.item
        self.act = act
        self.item = act["item"]
        self.visor.estilo_temp = self.p.estilo_de(self.item)
        if cambio:
            self.pid = None
            self._hojas(auto=True)
        elif act.get("ref") and self.pid and act["nivel"] not in self.p.plano_niveles(self.pid):
            self._hojas(auto=True)
        else:
            self._estado_hoja()
        it = self.p.item(self.item)
        if act.get("ref") == core.ACUM:
            self.l_estado.text = (f"Por acumulado: {it['codigo']} en {self.p.etiqueta_ubicacion(act['nivel'])}, acumulado "
                                  f"{fmt(act['cantidad_reg'])} {it['unidad']} al {core.fecha_txt(act['fecha'])}; falta "
                                  f"marcar {fmt(act['pendiente'])}. Dibujá todo lo ejecutado hasta esa fecha.")
        elif act.get("ref"):
            self.l_estado.text = (f"Marcando {it['codigo']} en {self.p.etiqueta_ubicacion(act['nivel'])}: falta ubicar "
                                  f"{fmt(act['pendiente'])} {it['unidad']}. Elegí una herramienta y dibujá.")

    def otra_actividad(self):
        def elegida(iid):
            f = self._fecha() or core.hoy_iso()
            self.item = iid
            self.act = {"item": iid, "ref": "", "fecha": f}
            self.pid = None
            self.cargar_actividades()
            self._hojas(auto=True)
        DialogoPartida(self.app, elegida).open()

    # ---------------------------------------------------------------- hojas
    def _hojas(self, auto=False):
        if not self.p or not self.item:
            self.t_hojas.cargar([])
            self.b_nueva.disabled = True
            return
        self.b_nueva.disabled = False
        hojas = self.p.hojas_de(self.item)
        filas = []
        for h in hojas:
            x = self.p.plano(h["plano"])
            filas.append({"id": h["plano"], "vals": [f"{x['nombre']} · {self.p.etiqueta_plano_ubic(h['plano'])}",
                                                     f"{h['n_marcas']}"]})
        if not hojas:
            filas.append({"id": None, "estilo": "fuera", "vals": ["Sin hojas: «Nueva hoja limpia…»", ""]})
        self.t_hojas.cargar(filas, False)
        if auto:
            nv = (self.act or {}).get("nivel")
            cand = [h["plano"] for h in hojas if not nv or nv in self.p.plano_niveles(h["plano"])]
            if self.pid and self.pid in [h["plano"] for h in hojas]:
                cand = [self.pid]
            if cand:
                self.abrir_hoja(cand[0])
            else:
                self.pid = None
                self.refrescar_vista_vacia()
        elif self.pid:
            self.t_hojas.seleccionar(self.pid, ver=False)

    def refrescar_vista_vacia(self):
        it = self.p.item(self.item)
        nv = (self.act or {}).get("nivel")
        libres = self.p.planos(nv) if nv else self.p.planos()
        if libres:
            self._vacio(f"{it['codigo']} todavía no tiene hoja" + (f" en {self.p.etiqueta_ubicacion(nv)}" if nv else "") +
                        ".\n\nUsá «Nueva hoja limpia…» y elegí un plano de la librería.")
        else:
            self._vacio("No hay planos en la librería" + (f" para {self.p.etiqueta_ubicacion(nv)}" if nv else "") +
                        ".\n\nCargalos desde «Librería de planos…».")

    def _elegir_hoja(self, fila):
        pid = fila.get("id")
        if pid and pid != self.pid and self.p.plano(pid):
            self.abrir_hoja(pid)

    def quitar_hoja(self):
        pid = self.t_hojas.sel_id if (self.t_hojas.sel_id and self.p.plano(self.t_hojas.sel_id)) else self.pid
        if not self.item or not pid:
            ui.info("Quitar hoja", "Elegí la hoja en la lista «Hojas de la actividad».")
            return
        h = self.p.hoja(pid, self.item)
        if not h:
            return
        if self.p.solo_agregar:
            ui.info("Quitar hoja", "En un archivo de «Solo agregar avance» no se pueden quitar hojas.")
            return
        it = self.p.item(self.item)

        def r(k):
            if not k:
                return
            ficha = self.app.punto_deshacer("Quitar hoja")
            try:
                self.p.eliminar_hoja(h["id"], conservar=(k == 1))
            except core.ErrorCtrlP as e:
                ui.info("Hoja", str(e))
                return
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            if self.pid == pid:
                self.pid = None
                self.visor.limpiar()
            self.visor.sel = None
            self.al_seleccionar(None)
            self.refrescar()
            self.l_estado.text = f"Se quitó la hoja de {it['codigo']}. «Deshacer» para volver atrás."
        preguntar_borrado("Quitar hoja", f"la hoja de {it['codigo']} en «{self.p.plano(pid)['nombre']}» (el plano queda "
                          "limpio en la librería)", self.p.marcas(pid, item=self.item), r)

    def nueva_hoja(self):
        if not self.item:
            ui.info("Hoja", "Elegí primero la actividad.")
            return
        DialogoLibreria(self.app, self, elegir=True).open()

    def usar_plano(self, pid):
        if self.p.hoja(pid, self.item):
            ui.info("Hoja existente", "Esta actividad ya tiene hoja en ese plano: se continúa con su historial.")
        else:
            self.p.crear_hoja(pid, self.item)
            self.app.guardar()
        self._hojas()
        self.abrir_hoja(pid)

    def abrir_hoja(self, pid):
        x = self.p.plano(pid)
        if not x:
            return
        self.pid = pid
        self.t_hojas.seleccionar(pid, ver=False)
        self.l_estado.text = "Abriendo plano…"

        def abrir(*_):
            try:
                if pid not in self._img_cache:
                    lado = pb.LADO_VISTA if ui.ANDROID else None
                    self._img_cache = {pid: pb.imagen_de(self.p, pid, lado)}
                img = self._img_cache[pid]
            except Exception as e:
                ui.info("Plano", f"No se pudo abrir el plano:\n{e}")
                return
            if self.l_vacio.parent:
                self.marco.remove_widget(self.l_vacio)
            self.visor.cargar(img, x["escala"], x["unidad"], tam_original=(x["ancho"], x["alto"]))
            self.sel = None
            self._estado_hoja()
            self.al_seleccionar(None)
        Clock.schedule_once(abrir, 0.05)

    def _estado_hoja(self):
        if not self.pid:
            return
        x = self.p.plano(self.pid)
        it = self.p.item(self.item)
        self.l_titulo.text = f"{it['codigo']} · {x['nombre']} · {self.p.etiqueta_plano_ubic(self.pid)}"
        self.l_escala.text = f"100 px = {x['escala'] * 100:,.4g} {x['unidad']}" if x["escala"] else "Sin calibrar"
        nvs = self.p.plano_niveles(self.pid)
        ops = [self.p.etiqueta_ubicacion(n) for n in nvs]
        self.m_nivel.opciones = ops or [""]
        nv_act = (self.act or {}).get("nivel")
        if nv_act in nvs:
            self.m_nivel.poner(self.p.etiqueta_ubicacion(nv_act))
        elif self.m_nivel.valor not in ops:
            self.m_nivel.poner(ops[0] if ops else "")
        self.m_nivel.disabled = len(ops) <= 1
        self.cargar_marcas()

    def estilo(self):
        if not self.item:
            ui.info("Estilo", "Elegí primero una actividad.")
            return

        def ok(e):
            self.app.guardar()
            self.visor.estilo_temp = e
            self.cargar_marcas()
        DialogoEstilo(self.p, self.item, ok).open()

    # ---------------------------------------------------------------- marcas (color por edificio)
    def cargar_marcas(self):
        self.f_leyenda.clear_widgets()
        if not self.p or not self.pid or not self.item:
            return
        p = self.p
        colores = p.colores_edificios()
        marcas = p.marcas(self.pid, item=self.item)
        items = {i["id"]: i for i in p.items()}
        hitos = {x["id"]: p.etiqueta_hito(dict(x), False) for x in p.con.execute("SELECT id, nombre, tipo FROM hitos")}
        varias = len(p.plano_niveles(self.pid)) > 1
        eds = []
        for m in marcas:
            ed = p.edificio_de_nivel(m["nivel"])
            m["color"] = colores.get(ed, "#2563EB")
            m["nota_txt"] = pb.texto_nota(p, m, items, hitos, p.etiqueta_ubicacion(m["nivel"]) if varias else None)
            if ed not in eds:
                eds.append(ed)
        for nv in p.plano_niveles(self.pid):
            ed = p.edificio_de_nivel(nv)
            if ed not in eds:
                eds.append(ed)
        nombres = {e["id"]: e["nombre"] for e in p.edificios()}
        if varias or len(eds) > 1:
            self.f_leyenda.add_widget(Etiqueta("Colores por edificio:", 11, color="texto2", ancho_fijo=130))
            for ed in eds:
                if ed not in nombres:
                    continue
                b = Boton(nombres[ed], ancho=max(56, 14 + 8 * len(nombres[ed])), alto=30, tam=11,
                          al_tocar=lambda e=ed: self._color_edificio(e))
                b._c_normal = rgba(colores.get(ed, "#2563EB"))
                b.color = [1, 1, 1, 1]
                b._estado()
                self.f_leyenda.add_widget(b)
        self.f_leyenda.add_widget(Widget())
        tramos = []
        for t in p.con.execute("SELECT * FROM tramos WHERE plano=? AND item=? AND geom IS NOT NULL", (self.pid, self.item)):
            t = dict(t)
            try:
                t["geom_pts"] = json.loads(t["geom"])
            except Exception:
                t["geom_pts"] = []
            tramos.append(t)
        self.marcas_vis = marcas
        self.visor.poner_marcas(marcas, {self.item: p.estilo_de(self.item)}, tramos)
        if not self.sel and not (self.act or {}).get("ref"):
            self.l_estado.text = f"{len(marcas)} marcas en esta hoja. Elegí una herramienta para marcar."

    def _color_edificio(self, ed):
        def ok(c):
            self.p.poner_color_edificio(ed, c)
            self.app.guardar()
            self.cargar_marcas()
        elegir_color(self.p.colores_edificios().get(ed), "Color del edificio", ok)

    def al_estado(self, txt):
        if not self.sel:
            self.l_estado.text = txt

    def al_seleccionar(self, mid):
        self.sel = mid
        self.b_editar.disabled = self.b_anular.disabled = not mid
        if not mid:
            return
        m = self.p.marca(mid)
        if not m:
            return
        it = self.p.item(m["item"])
        partes = [self.p.etiqueta_ubicacion(m["nivel"]), f"{fmt(m['cantidad'])} {it['unidad']}", core.fecha_txt(m["fecha"])]
        if m.get("visual"):
            partes.append("ubica un registro manual")
        if m.get("equipo"):
            partes.append("equipo " + self.p.nombre_equipo(m["equipo"]))
        if m["tramo"]:
            partes.append("tramo " + self.p.nombre_tramo(m["tramo"]))
        if m["hito"]:
            partes.append(self.p.nombre_hito(m["hito"]))
        if m["altura"]:
            partes.append(m["altura"])
        if m["nota"]:
            partes.append(f"«{m['nota']}»")
        partes.append(f"por {m['usuario']}")
        self.l_estado.text = "  ·  ".join(partes)

    def _coincidentes(self, tipo, pts):
        nueva = {"tipo": tipo, "geom": pts}
        tol = max(self.visor.tam) / 300
        return [m["nota_txt"] for m in self.marcas_vis if pb.coinciden(nueva, m, tol) or pb.coinciden(m, nueva, tol)]

    def _empezar_vacios(self, ext, huecos, fin):
        def al_fin(h):
            self._poner_herr(NOMBRE_HERR.get(self.visor.herr, "Mover"))
            fin(h)
        self.visor.iniciar_vacios(ext, huecos, al_fin)

    # ---------------------------------------------------------------- terminar un trazo
    def al_terminar(self, tipo, pts, huecos=None, previo=None):
        if not self.p or not self.pid:
            return
        plano = self.p.plano(self.pid)
        if tipo == "calibrar":
            if self.p.solo_agregar:
                ui.info("Calibrar", "En un archivo de «Solo agregar avance» no se puede calibrar.")
                return
            px = pb.largo_px(pts)
            if px < 5:
                return

            def validar(v):
                n = leer_num(v["d"])
                return "" if isinstance(n, float) and n > 0 else "Escribí la distancia real (mayor que cero)."

            def ok(r):
                esc = leer_num(r["d"]) / px
                ficha = self.app.punto_deshacer("Calibrar plano")
                self.p.calibrar_plano(self.pid, esc, (r["u"] or "m").strip())
                self.app.confirmar_deshacer(ficha)
                self.app.guardar()
                self.visor.escala, self.visor.unidad = esc, (r["u"] or "m").strip()
                self._estado_hoja()
                self._herr("Mover")
            ui.formulario("Calibrar plano", f"Marcaste {px:,.1f} px en el plano. ¿Cuánto mide en la realidad? (acepta "
                          "decimales)", [("d", "Distancia real", False, ""), ("u", "Unidad", False, plano["unidad"] or "m")],
                          ["Cancelar", "Calibrar"], ok, validar=validar)
            return
        if not self.item:
            ui.info("Marcar", "Elegí primero la actividad.")
            return
        act = dict(self.act or {"item": self.item, "ref": "", "fecha": self._fecha() or core.hoy_iso()})
        if act.get("ref") == core.ACUM and act.get("pendiente", 0) <= 1e-9:
            ui.info("Por acumulado", "Lo acumulado de esa actividad y ubicación ya está todo marcado al corte. Para "
                    "marcar más, cambiá la fecha de corte o registrá el avance.")
            return
        if self.sw_acum.activo and not act.get("ref"):
            ui.info("Por acumulado", "Con «Por acumulado» elegí en la lista la ubicación (fila de abajo de la actividad) "
                    "que vas a marcar.")
            return
        if act.get("ref") and act.get("pendiente", 0) <= 1e-9:
            act = {"item": act["item"], "ref": "", "fecha": act["fecha"], "equipo": act.get("equipo"),
                   "tramo": act.get("tramo"), "hito": act.get("hito"), "nivel": act.get("nivel")}
        if act.get("ref"):
            if act["nivel"] not in self.p.plano_niveles(self.pid):
                ui.info("Ubicación", f"Este registro es de {self.p.etiqueta_ubicacion(act['nivel'])}, que no está en el "
                        f"alcance de este plano ({self.p.etiqueta_plano_ubic(self.pid)}).")
                return
        else:
            act["nivel"] = self.nivel
            act["fecha"] = self._fecha() or act.get("fecha")
            if not act["nivel"]:
                ui.info("Ubicación", "Elegí en «Marcando en» qué edificio-nivel estás marcando.")
                return

        def resultado(r):
            if not r:
                return
            if r.get("accion") == "vacios":
                self._empezar_vacios(pts, huecos, lambda h: self.al_terminar(tipo, pts, huecos if h is None else h,
                                                                             r["previo"]))
                return
            ficha = self.app.punto_deshacer("Nueva marca")
            try:
                tramo = r["tramo"]
                if r.get("tramo_nuevo"):
                    tramo = self.p.crear_tramo(act["item"], act["nivel"], r["tramo_nuevo"], None, plano=self.pid,
                                               geom=pts if tipo == "linea" else None, equipo=r.get("equipo", ""))
                self.p.agregar_marca(self.pid, act["item"], tipo, pts, r["medida"], r["factor"], r["cantidad"], r["fecha"],
                                     r["hito"], tramo, r["altura"], r["nota"], equipo=r.get("equipo", ""),
                                     nivel=act["nivel"], ref=act.get("ref", ""), modo=r["modo"], huecos=huecos)
            except core.ErrorCtrlP as e:
                ui.info("Marca", str(e))
                return
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            it = self.p.item(act["item"])
            ref = act.get("ref")
            self.cargar_actividades()
            k = act.get("clave") or f"r:{ref}"
            if ref and k in self._acts:
                self.act = dict(self._acts[k])
                self.t_act.seleccionar(k, ver=False)
            self._hojas()
            self.cargar_marcas()
            accion = {"ubicar": "Se ubicó", "reemplazar": "Se reemplazó por la medida del plano:", "avance": "Se registró",
                      "acumulado": "Se marcó del acumulado"}[r["modo"]]
            self.l_estado.text = (f"{accion} {fmt(r['cantidad'])} {it['unidad']} de {it['codigo']} en "
                                  f"{self.p.etiqueta_ubicacion(act['nivel'])} ({core.fecha_txt(r['fecha'])}).")
            ui.aviso(self.l_estado.text)
        DialogoMarca(self.p, plano, tipo, pts, act, resultado, coincidentes=self._coincidentes(tipo, pts),
                     huecos=huecos, previo=previo).open()

    def preparar(self, iid, nivel, fecha):
        """Viene del Registro de avance: elige la actividad y abre su hoja para esa ubicacion."""
        self.e_fecha.text = core.fecha_txt(fecha)
        self.item = None
        self.cargar_actividades()
        hijos = [k for k, a in self._acts.items() if a.get("item") == iid and a.get("nivel") == nivel
                 and a.get("pendiente", 0) > 1e-9]
        objetivo = hijos[0] if hijos else (f"i:{iid}" if f"i:{iid}" in self._acts else None)
        if objetivo:
            self.t_act.seleccionar(objetivo)
            self._elegir_act({"id": objetivo})
        if not self.pid:
            libres = self.p.planos(nivel)
            if len(libres) == 1:
                def r(si):
                    if si:
                        self.usar_plano(libres[0]["id"])
                ui.preguntar("Nueva hoja", f"{self.p.item(iid)['codigo']} todavía no tiene hoja para "
                             f"{self.p.etiqueta_ubicacion(nivel)}.\n\n¿Empezar una hoja limpia con el plano "
                             f"«{libres[0]['nombre']}» ({self.p.etiqueta_plano_ubic(libres[0]['id'])})?", r, si="Empezar")
            elif libres:
                DialogoLibreria(self.app, self, elegir=True, nivel=nivel).open()
        unidad = self.p.item(iid)["unidad"]
        self._herr("Línea" if unidad in ("ML", "M") else ("Polígono" if unidad == "M2" else "Punto"))

    def editar(self):
        if not self.sel:
            return
        m = self.p.marca(self.sel)
        plano = self.p.plano(self.pid)
        act = {"item": m["item"], "nivel": m["nivel"], "ref": "", "fecha": m["fecha"]}
        mid = m["id"]

        def resultado(r):
            if not r:
                return
            if r.get("accion") == "vacios":
                self._empezar_vacios(m["geom"], m.get("huecos") or [],
                                     lambda h: None if h is None else self.al_mover_marca(mid, m["geom"], h))
                return
            ficha = self.app.punto_deshacer("Editar datos de la marca")
            try:
                tramo = r["tramo"]
                if r.get("tramo_nuevo"):
                    tramo = self.p.crear_tramo(m["item"], m["nivel"], r["tramo_nuevo"], None, plano=self.pid,
                                               geom=m["geom"] if m["tipo"] == "linea" else None, equipo=r.get("equipo", ""))
                self.p.editar_marca(mid, cantidad=r["cantidad"], fecha=r["fecha"], nota=r["nota"], altura=r["altura"],
                                    hito=r["hito"], tramo=tramo, equipo=r.get("equipo", ""))
            except core.ErrorCtrlP as e:
                ui.info("Marca", str(e))
                return
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            self.cargar_actividades()
            self.cargar_marcas()
            self.al_seleccionar(mid)
        DialogoMarca(self.p, plano, m["tipo"], m["geom"], act, resultado, marca=m).open()

    def al_mover_marca(self, mid, geom, huecos=None, deshacer=None):
        """Editar movio la marca o cambio su forma (o se cambiaron sus vacios)."""
        m = self.p.marca(mid)
        plano = self.p.plano(self.pid)
        nueva = pb.medida(m["tipo"], geom, plano["escala"], m.get("huecos") if huecos is None else huecos)
        cambios = {"geom": geom}
        if huecos is not None:
            cambios["huecos"] = huecos

        def aplicar():
            ficha = self.app.punto_deshacer("Vacíos del área" if huecos is not None and geom == m["geom"]
                                            else "Mover o cambiar forma de la marca")
            try:
                self.p.editar_marca(mid, **cambios)
            except core.ErrorCtrlP as e:
                ui.info("Marca", str(e))
                self.cargar_marcas()
                return
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            if "cantidad" in cambios:
                self.cargar_actividades()
            self.cargar_marcas()
            self.visor.sel = mid
            self.visor.redibujar()
            self.al_seleccionar(mid)
        tol = max(0.005, abs(m["medida"] or 0) * 1e-4)
        if nueva is not None and m["tipo"] != "punto" and abs(nueva - (m["medida"] or 0)) > tol:
            cambios["medida"] = nueva
            f = m["factor"] or 1
            del_plano = m["medida"] is not None and abs((m["medida"] or 0) * f - (m["cantidad"] or 0)) < 0.005
            if not m.get("visual") and del_plano and abs(nueva * f - m["cantidad"]) > 0.005:
                it = self.p.item(m["item"])

                def r(k):
                    if k is None or k == 0:
                        self.cargar_marcas()
                        return
                    if k == 2:
                        cambios["cantidad"] = round(nueva * f, 4)
                    else:
                        cambios.pop("medida")
                    aplicar()
                ui.opciones("Cambió la medida", f"La marca medía {fmt(m['cantidad'])} {it['unidad']} y ahora mide "
                            f"{fmt(nueva * f)} {it['unidad']}.\n\n¿Actualizar la cantidad del avance con la nueva medida?",
                            ["Deshacer", "Solo mover", "Actualizar cantidad"], r, primario=2)
                return
        aplicar()

    def anular(self):
        if not self.sel:
            return
        m = self.p.marca(self.sel)
        it = self.p.item(m["item"])
        sel = self.sel

        def hacer(k):
            if not k:
                return
            ficha = self.app.punto_deshacer("Borrar marca")
            try:
                if k == 1 and not m.get("visual"):
                    self.p.quitar_del_plano(sel)
                else:
                    self.p.anular_marca(sel)
            except core.ErrorCtrlP as e:
                ui.info("Marca", str(e))
                return
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            self.visor.sel = None
            self.al_seleccionar(None)
            self.cargar_actividades()
            self._hojas()
            self.cargar_marcas()
        if m.get("visual"):
            ui.preguntar("Borrar marca", "Esta marca solo ubica un registro manual. Al borrarla, ese registro vuelve a "
                         "quedar sin marcar (la cantidad no cambia).", lambda si: hacer(1 if si else 0), si="Borrar")
        else:
            ui.opciones("Borrar marca", f"{fmt(m['cantidad'])} {it['unidad']} del {core.fecha_txt(m['fecha'])} en "
                        f"{self.p.etiqueta_ubicacion(m['nivel'])}.\n\n«Quitar del plano»: se borra el dibujo y la cantidad "
                        "queda como registro manual sin marcar.\n«Borrar también el avance»: la cantidad deja de contar "
                        "(queda en el historial).", ["Cancelar", "Quitar del plano", "Borrar también el avance"], hacer,
                        primario=1)

    def deshacer(self):
        if self.visor.pts:
            self.visor.deshacer_punto()
            return
        desc, err = self.app.deshacer()
        if err:
            self.l_estado.text = err
            return
        if self.pid and not self.p.plano(self.pid):
            self.pid = None
            self.visor.limpiar()
        self.visor.sel = None
        self.al_seleccionar(None)
        self.refrescar()
        self.l_estado.text = f"Se deshizo: {desc}."


# =========================================================================
#  Dialogo de marca
# =========================================================================
class DialogoMarca(ui.Dialogo):
    """Datos de una marca. al_resultado(dict) o al_resultado(None) si cancela."""

    def __init__(self, p, plano, tipo, pts, act, al_resultado, marca=None, coincidentes=(), huecos=None, previo=None):
        super().__init__("Editar marca" if marca else "Marcar en el plano", ancho=640)
        self.p, self.plano, self.tipo, self.pts = p, plano, tipo, pts
        self.huecos = huecos or []
        self.act, self.marca, self.cb = act, marca, al_resultado
        self.item = p.item(act["item"])
        self.med = pb.medida(tipo, pts, plano["escala"], self.huecos) if not marca else marca["medida"]
        it = self.item
        u = it["unidad"]
        self.ref = act.get("ref") or ""
        c = self.cuerpo
        c.add_widget(Etiqueta(f"{it['codigo']} {it['descripcion'][:90]}", 13, True, color="acento"))
        c.add_widget(Etiqueta(p.etiqueta_ubicacion(act["nivel"]) + "  ·  " + plano["nombre"], 12, color="texto2"))
        if coincidentes:
            c.add_widget(Etiqueta("Coincide con marcas anteriores en el mismo lugar:\n" +
                                  "\n".join(f"• {x}" for x in coincidentes[:5]) +
                                  "\nLa nota se suma a las anteriores (mismo color en el plano).", 12, color="acento"))
        self.cajas = Columna(espacio=6)
        c.add_widget(self.cajas)
        self._cajas()
        self.modo = None
        self.e_factor = Campo(f"{(marca['factor'] if marca else 1) or 1:g}", ancho=90, alinear="right", numerico=True,
                              al_cambiar=lambda *_: self._calc())
        self.e_cant = Campo("", ancho=140, alinear="right", numerico=True)
        self.e_fecha = Campo(core.fecha_txt(marca["fecha"] if marca else act.get("fecha") or core.hoy_iso()), ancho=150,
                             alinear="center")
        self.l_med = Etiqueta("", 13)
        self.opc = {}

        def opcion(clave, texto):
            cb = Casilla(texto, False, al_cambiar=lambda _, k=clave: self._elegir_modo(k), tam=13)
            self.opc[clave] = cb
            return cb
        if self.ref == core.ACUM and not marca:
            c.add_widget(Etiqueta(f"Acumulado al {core.fecha_txt(act['fecha'])}: {fmt(act['cantidad_reg'])} {u}  ·  falta "
                                  f"marcar {fmt(act['pendiente'])} {u}", 13, True))
            c.add_widget(opcion("medida", "Usar la medida del plano"))
            c.add_widget(self._fila_medida())
            f = Fila(alto=46)
            f.add_widget(opcion("manual", "Ingresar la cantidad que representa"))
            f.add_widget(self.e_cant)
            c.add_widget(f)
            self.e_cant.text = f"{act['pendiente']:.2f}"
            self._elegir_modo("medida" if self.med is not None else "manual")
        elif self.ref and not marca:
            c.add_widget(Etiqueta(f"Registro del {core.fecha_txt(act['fecha'])}: {fmt(act['cantidad_reg'])} {u}  ·  falta "
                                  f"ubicar {fmt(act['pendiente'])} {u}", 13, True))
            c.add_widget(opcion("ubicar", "Solo marcar (ubica la cantidad ya registrada)"))
            f = Fila(alto=46)
            f.add_widget(Espacio(1, ancho=34))
            f.add_widget(Etiqueta("Cantidad que representa esta marca", 12, color="texto2"))
            f.add_widget(self.e_cant)
            c.add_widget(f)
            self.e_cant.text = f"{act['pendiente']:.2f}"
            c.add_widget(opcion("medida", "Usar la medida del plano"))
            c.add_widget(self._fila_medida())
            self._elegir_modo("ubicar")
        else:
            f = Fila(alto=46)
            f.add_widget(Etiqueta("Fecha", 13, True, ancho_fijo=60))
            f.add_widget(self.e_fecha)
            f.add_widget(Widget())
            c.add_widget(f)
            if marca and marca.get("visual"):
                self.e_fecha.disabled = True
            c.add_widget(opcion("medida", "Usar la medida del plano"))
            c.add_widget(self._fila_medida())
            f = Fila(alto=46)
            f.add_widget(opcion("manual", "Ingresar la cantidad"))
            f.add_widget(self.e_cant)
            c.add_widget(f)
            modo = "medida" if self.med is not None else "manual"
            if marca:
                self.e_cant.text = f"{marca['cantidad']:.2f}"
                modo = "medida" if (marca["medida"] is not None and abs(
                    (marca["medida"] or 0) * (marca["factor"] or 1) - marca["cantidad"]) < 1e-6) else "manual"
            self._elegir_modo(modo)
        if self.med is None and "medida" in self.opc:
            self.opc["medida"].disabled = True
        c.add_widget(Etiqueta("Factor: multiplica la medida (ej. altura del muro para pasar de m a m², sección para m³).",
                              11, color="texto2"))
        f2 = Fila(alto=70, espacio=12)
        c1 = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(220), spacing=dp(4))
        c1.add_widget(Etiqueta("Franja / altura (opcional)", 12, True))
        self.e_altura = Campo(marca["altura"] if marca else "", pista="ej. 0.00 a 1.20 m")
        c1.add_widget(self.e_altura)
        c2 = BoxLayout(orientation="vertical", spacing=dp(4))
        c2.add_widget(Etiqueta("Nota (opcional)", 12, True))
        self.e_nota = Campo(marca["nota"] if marca else "")
        c2.add_widget(self.e_nota)
        f2.add_widget(c1)
        f2.add_widget(c2)
        c.add_widget(f2)
        self.l_err = Etiqueta("", 13, color="rojo")
        c.add_widget(self.l_err)
        if previo:
            for k, e in (("factor", self.e_factor), ("altura", self.e_altura), ("nota", self.e_nota)):
                if previo.get(k) not in (None, ""):
                    e.text = str(previo[k])
        textos = ["Cancelar", "Guardar"]
        if tipo == "area":
            n = len(self.huecos if not marca else (marca.get("huecos") or []))
            textos = [f"Vacíos ({n})…" if n else "Agregar vacíos…"] + textos
        self.botones(textos, len(textos) - 1, self._boton)
        self._calc()

    def _boton(self, k):
        n = len(self.pie.children) - 1
        textos = [w.text for w in reversed(self.pie.children) if isinstance(w, Boton)]
        t = textos[k]
        if t == "Cancelar":
            self.dismiss()
            self.cb(None)
        elif t == "Guardar":
            self.ok()
        else:
            self.dismiss()
            self.cb({"accion": "vacios", "previo": {"factor": self.e_factor.text, "altura": self.e_altura.text,
                                                    "nota": self.e_nota.text}})

    def _fila_medida(self):
        f = Fila(alto=46, espacio=6)
        f.add_widget(Espacio(1, ancho=34))
        f.add_widget(self.l_med)
        f.add_widget(self.e_factor)
        f.add_widget(Etiqueta("factor", 11, color="texto2", ancho_fijo=50))
        return f

    def _elegir_modo(self, k):
        self.modo = k
        for kk, cb in self.opc.items():
            cb.activo = kk == k

    def _cajas(self):
        p, it, act, m = self.p, self.item, self.act, self.marca
        nv = act["nivel"]
        self.hitos = p.hitos_de(it["id"])
        self.equipos = p.equipos_de(it["id"], nv)
        fijo = bool(self.ref) or bool(m and m.get("visual"))
        ini_h = (m or {}).get("hito") or act.get("hito") or ""
        ini_e = (m or {}).get("equipo") or act.get("equipo") or ""
        ini_t = (m or {}).get("tramo") or act.get("tramo") or ""
        self._ini = (ini_h, ini_e, ini_t)
        self.tramos = []
        self.m_hito = self.m_equipo = self.m_tramo = None
        self.e_tramo = None
        if fijo:
            partes = [x for x in (("Equipo " + p.nombre_equipo(ini_e)) if ini_e else "",
                                  ("Tramo " + p.nombre_tramo(ini_t)) if ini_t else "",
                                  p.nombre_hito(ini_h) if ini_h else "") if x]
            if partes:
                self.cajas.add_widget(Etiqueta(" · ".join(partes), 13, True))
            return
        if self.hitos:
            self.cajas.add_widget(Etiqueta("Hito", 12, True))
            ops = [p.etiqueta_hito(h) for h in self.hitos]
            self.m_hito = Menu(ops, next((ops[k] for k, h in enumerate(self.hitos) if h["id"] == ini_h), ops[0]))
            self.cajas.add_widget(self.m_hito)
        if p.detalle_de(it["id"])["equipos"]:
            self.cajas.add_widget(Etiqueta("Equipo", 12, True))
            self.m_equipo = Menu(["(sin equipo)"] + [e["nombre"] for e in self.equipos],
                                 next((e["nombre"] for e in self.equipos if e["id"] == ini_e), "(sin equipo)"),
                                 al_cambiar=lambda _: self._menu_tramos())
            self.cajas.add_widget(self.m_equipo)
        self.caja_tramo = Columna(espacio=4)
        self.cajas.add_widget(self.caja_tramo)
        self._menu_tramos(ini_t)

    def _equipo_sel(self):
        return next((e["id"] for e in self.equipos if self.m_equipo and e["nombre"] == self.m_equipo.valor), "")

    def _menu_tramos(self, inicial=""):
        self.caja_tramo.clear_widgets()
        p, it = self.p, self.item
        self.tramos = p.tramos_de(it["id"], self.act["nivel"], self._equipo_sel()) if p.detalle_de(it["id"])["tramos"] else []
        self.m_tramo = None
        if self.tipo == "punto" and not self.tramos:
            return
        if not p.detalle_de(it["id"])["tramos"]:
            return
        ops = ["(sin tramo)"] + [t["nombre"] for t in self.tramos] + ["+ Nuevo tramo…"]
        self.caja_tramo.add_widget(Etiqueta("Tramo", 12, True))
        self.m_tramo = Menu(ops, next((t["nombre"] for t in self.tramos if t["id"] == inicial), "(sin tramo)"),
                            al_cambiar=lambda v: self._tramo_nuevo(v))
        self.caja_tramo.add_widget(self.m_tramo)
        self.e_tramo = Campo("", pista="Nombre del tramo nuevo", mayus=True)

    def _tramo_nuevo(self, v):
        if v.startswith("+"):
            if not self.e_tramo.parent:
                self.caja_tramo.add_widget(self.e_tramo)
        elif self.e_tramo.parent:
            self.caja_tramo.remove_widget(self.e_tramo)

    def _calc(self):
        u = self.item["unidad"]
        f = leer_num(self.e_factor.text)
        f = f if isinstance(f, float) else 1.0
        if self.med is None:
            self.l_med.text = "Calibrá el plano para medir   ×"
        elif self.tipo == "punto":
            self.l_med.text = f"1 pieza  →  {fmt(f)} {u}   ×"
        else:
            un = (self.plano.get("unidad") or "m") + ("²" if self.tipo == "area" else "")
            vac = len(self.huecos) if not self.marca else len(self.marca.get("huecos") or [])
            self.l_med.text = (f"Medida {fmt(self.med)} {un}" + (f" (menos {vac} vacío{'s' if vac > 1 else ''})" if vac
                                                                   else "") + f"  →  {fmt(self.med * f)} {u}   ×")

    def ok(self):
        f = leer_num(self.e_factor.text)
        if f in ("error",) or f is None or f <= 0:
            self.l_err.text = "El factor debe ser un número mayor que cero."
            return
        modo = self.modo
        if modo == "medida" and self.med is None:
            self.l_err.text = "El plano no está calibrado: calibralo o ingresá la cantidad."
            return
        cant = self.med * f if modo == "medida" else leer_num(self.e_cant.text)
        if cant in ("error", None) or cant <= 0:
            self.l_err.text = "Escribí una cantidad mayor que cero."
            return
        base = {"factor": f, "medida": self.med, "altura": self.e_altura.text.strip(), "nota": self.e_nota.text.strip()}
        u = self.item["unidad"]
        if self.ref == core.ACUM and not self.marca:
            pend = self.act["pendiente"]
            h, e, t = self._ini

            def fin(c):
                self.dismiss()
                self.cb(dict(base, modo="acumulado", cantidad=c, fecha=self.act["fecha"], hito=h, equipo=e, tramo=t,
                             tramo_nuevo=None))
            if cant > pend + 0.005:
                ui.preguntar("Más que lo acumulado", f"Esta marca da {fmt(cant)} {u} y del acumulado al "
                             f"{core.fecha_txt(self.act['fecha'])} faltan marcar {fmt(pend)}.\n\nLa marca no crea avance: "
                             "si se ejecutó más, registralo en Registro de avance.",
                             lambda si: si and fin(pend), si=f"Marcar {fmt(pend)}")
                return
            fin(cant)
            return
        if self.ref and not self.marca:
            fecha = self.act["fecha"]
            h, e, t = self._ini
            pend = self.act["pendiente"]

            def fin(c, res_modo="ubicar"):
                self.dismiss()
                self.cb(dict(base, modo=res_modo, cantidad=c, fecha=fecha, hito=h, equipo=e, tramo=t, tramo_nuevo=None))
            if modo == "medida":
                if abs(cant - pend) > 0.005:
                    def r(k):
                        if k == 2:
                            fin(cant, "reemplazar")
                        elif k == 1:
                            fin(pend)
                    ui.opciones("La medida no coincide", f"La medida del plano da {fmt(cant)} {u} y en el registro "
                                f"faltaban ubicar {fmt(pend)}.\n\n¿Reemplazar la cantidad manual por la medida del plano, "
                                "o conservar la manual?", ["Cancelar", "Conservar la manual", "Reemplazar"], r, primario=2)
                    return
                fin(pend)
                return
            if cant > pend + 0.005:
                self.l_err.text = f"Esta marca no puede representar más de lo que falta ubicar ({fmt(pend)})."
                return
            fin(cant)
            return
        if self.marca and self.marca.get("visual"):
            h, e, t = self._ini
            self.dismiss()
            self.cb(dict(base, modo="ubicar", cantidad=cant, fecha=self.marca["fecha"], hito=h, equipo=e, tramo=t,
                         tramo_nuevo=None))
            return
        try:
            fecha = core.txt_a_iso(self.e_fecha.text)
        except core.ErrorCtrlP as ex:
            self.l_err.text = str(ex)
            return
        hito = ""
        if self.hitos and self.m_hito:
            k = [self.p.etiqueta_hito(x) for x in self.hitos].index(self.m_hito.valor)
            hito = self.hitos[k]["id"]
        tramo, nuevo = "", None
        if self.m_tramo:
            tn = self.m_tramo.valor
            if tn.startswith("+"):
                nuevo = core.mayus(self.e_tramo.text)
                if not nuevo:
                    self.l_err.text = "Escribí el nombre del tramo nuevo."
                    return
            elif tn != "(sin tramo)":
                tramo = next(t["id"] for t in self.tramos if t["nombre"] == tn)
        self.dismiss()
        self.cb(dict(base, modo="avance", cantidad=cant, fecha=fecha, hito=hito, equipo=self._equipo_sel(), tramo=tramo,
                     tramo_nuevo=nuevo))


# =========================================================================
#  Estilo por actividad
# =========================================================================
class DialogoEstilo(ui.Dialogo):
    def __init__(self, p, iid, al_ok):
        super().__init__("Estilo de marcado", ancho=640)
        self.p, self.iid, self.cb = p, iid, al_ok
        self.e = p.estilo_de(iid)
        it = p.item(iid)
        self.cuerpo.add_widget(Etiqueta(f"{it['codigo']} {it['descripcion'][:70]}", 12, color="texto2"))
        self.v = {}

        def seccion(t):
            tt = Tarjeta(relleno=12, espacio=6)
            tt.add_widget(Etiqueta(t, 14, True))
            self.cuerpo.add_widget(tt)
            return tt

        def num(t, clave, sub, texto, ayuda=""):
            e = Campo(f"{self.e[sub][clave]:g}", ancho=100, alinear="right", numerico=True)
            self.v[(sub, clave)] = e
            t.fila(texto, e, ayuda)

        def alpha(t, clave, sub, texto):
            from kivy.uix.slider import Slider
            f = BoxLayout(orientation="horizontal", size_hint=(None, None), size=(dp(260), dp(44)), spacing=dp(8))
            s = Slider(min=5, max=100, value=float(self.e[sub][clave]), step=1)
            l = Etiqueta(f"{float(self.e[sub][clave]):.0f} %", 13, ancho_fijo=56)
            s.bind(value=lambda w, v, l=l: setattr(l, "text", f"{v:.0f} %"))
            f.add_widget(s)
            f.add_widget(l)
            self.v[(sub, clave)] = s
            t.fila(texto, f)
        t = seccion("Líneas")
        num(t, "grosor", "linea", "Grosor (px del plano)",
            "Sin límite práctico: para ductos anchos en isométricos usá valores grandes (ej. 80).")
        alpha(t, "alpha", "linea", "Opacidad")
        t = seccion("Áreas")
        alpha(t, "alpha", "area", "Opacidad del relleno")
        num(t, "borde", "area", "Grosor del borde (px)")
        alpha(t, "alpha_borde", "area", "Opacidad del borde")
        t = seccion("Puntos")
        self.m_forma = Menu(pb.FORMAS_PUNTO, self.e["punto"].get("forma", "Círculo"), ancho=180)
        t.fila("Forma", self.m_forma)
        num(t, "tamano", "punto", "Tamaño (px en pantalla)")
        alpha(t, "alpha", "punto", "Opacidad")
        num(t, "borde", "punto", "Grosor del borde (px)")
        self.l_err = Etiqueta("", 13, color="rojo")
        self.cuerpo.add_widget(self.l_err)
        self.botones(["Cancelar", "Guardar"], 1, self._fin)

    def _fin(self, k):
        if k == 0:
            self.dismiss()
            return
        e = self.e
        from kivy.uix.slider import Slider
        for (sub, clave), w in self.v.items():
            if isinstance(w, Slider):
                e[sub][clave] = round(float(w.value), 0)
                continue
            n = leer_num(w.text)
            if not isinstance(n, float) or n < 0:
                self.l_err.text = "Revisá los números: deben ser mayores o iguales a cero."
                return
            e[sub][clave] = n
        e["punto"]["forma"] = self.m_forma.valor
        self.p.guardar_estilo(self.iid, e)
        self.dismiss()
        self.cb(e)


# =========================================================================
#  Libreria, alcance y partida
# =========================================================================
class DialogoAlcance(ui.Dialogo):
    ALCANCES = ["Por nivel", "Por edificio", "General"]

    def __init__(self, app, ruta=None, pid=None, al_terminar=None):
        super().__init__("Cargar plano a la librería" if ruta else "Alcance del plano", ancho=760)
        self.app, self.ruta, self.pid, self.al_terminar = app, ruta, pid, al_terminar
        p = app.p
        x = p.plano(pid) if pid else None
        c = self.cuerpo
        if ruta:
            c.add_widget(Etiqueta(os.path.basename(ruta), 12, color="texto2"))
        c.add_widget(Etiqueta("Nombre del plano", 13, True))
        self.e_nom = Campo(x["nombre"] if x else os.path.splitext(os.path.basename(ruta))[0][:60])
        c.add_widget(self.e_nom)
        c.add_widget(Etiqueta("¿A qué se vincula?", 13, True))
        ini = {"nivel": "Por nivel", "edificio": "Por edificio", "general": "General"}.get((x or {}).get("alcance") or "nivel")
        self.seg = Segmentado(self.ALCANCES, ini, ancho=420, al_cambiar=lambda _: self._opciones())
        c.add_widget(self.seg)
        self.ayuda = Etiqueta("", 12, color="texto2")
        c.add_widget(self.ayuda)
        self.caja = Columna(espacio=6)
        c.add_widget(self.caja)
        self.ubs = p.ubicaciones()
        self.eds = [e for e in p.edificios() if not e["es_area"]]
        actuales = p.plano_niveles(pid) if pid else []
        self.nivel_sel = p.etiqueta_ubicacion(actuales[0]) if actuales else (self.ubs[0]["etiqueta"] if self.ubs else "")
        ed_ini = p.edificio_de_nivel(actuales[0]) if actuales else (self.eds[0]["id"] if self.eds else None)
        self.ed_sel = next((e["nombre"] for e in self.eds if e["id"] == ed_ini), self.eds[0]["nombre"] if self.eds else "")
        self.nom_alc = (x or {}).get("nombre_alcance") if (x or {}).get("alcance") == "general" else "GENERAL"
        self.marcados = {u["nivel"]: u["nivel"] in actuales for u in self.ubs}
        self.cont_pag = None
        self.sw_aplanar = None
        self.seg_dpi = None
        if ruta:
            if ruta.lower().endswith(".pdf"):
                try:
                    n = pb.paginas_pdf(ruta)
                except Exception:
                    n = 1
                if n > 1:
                    c.add_widget(Etiqueta(f"Página (el PDF tiene {n})", 13, True))
                    self.cont_pag = Contador(1, 1, n)
                    c.add_widget(self.cont_pag)
            t = Tarjeta(relleno=12)
            self.seg_dpi = Segmentado(["150 dpi", "200 dpi", "300 dpi"], "200 dpi", ancho=300)
            t.fila("Resolución", self.seg_dpi, "Más resolución = más detalle al acercar, archivo más pesado. El plano "
                   "queda aplanado y comprimido (liviano y rápido de mover).")
            c.add_widget(t)
        self.l_msg = Etiqueta("", 13, color="texto2")
        c.add_widget(self.l_msg)
        self.botones(["Cancelar", "Cargar" if ruta else "Guardar"], 1, self._fin)
        self._opciones()

    def _opciones(self):
        self.caja.clear_widgets()
        a = self.seg.valor
        if a == "Por nivel":
            self.ayuda.text = "El plano es de un solo edificio-nivel (ej. B1 NIVEL 1). Todas sus marcas son de esa ubicación."
            m = Menu([u["etiqueta"] for u in self.ubs] or [""], self.nivel_sel, ancho=320,
                     al_cambiar=lambda v: setattr(self, "nivel_sel", v))
            self.caja.add_widget(m)
        elif a == "Por edificio":
            self.ayuda.text = ("El plano es de un edificio completo (ej. un isométrico o una fachada de B1). Al marcar "
                               "elegís el nivel del edificio.")
            m = Menu([e["nombre"] for e in self.eds] or [""], self.ed_sel, ancho=240,
                     al_cambiar=lambda v: setattr(self, "ed_sel", v))
            self.caja.add_widget(m)
        else:
            self.ayuda.text = ("El plano muestra varios edificios (ej. GENERAL NIVEL 1). El programa no sabe dónde queda "
                               "cada edificio: al marcar elegís a qué ubicación corresponde.")
            f = Fila(alto=46)
            f.add_widget(Etiqueta("Nombre del alcance", 12, color="texto2", ancho_fijo=150))
            self.e_alc = Campo(self.nom_alc, mayus=True, ancho=280,
                               al_cambiar=lambda t: setattr(self, "nom_alc", t))
            f.add_widget(self.e_alc)
            f.add_widget(Widget())
            self.caja.add_widget(f)
            nombres_nv = []
            for u in self.ubs:
                if u["nv_nombre"] and u["nv_nombre"] not in nombres_nv:
                    nombres_nv.append(u["nv_nombre"])
            if nombres_nv:
                f2 = Fila(alto=46)
                f2.add_widget(Etiqueta("Marcar todos los", 12, color="texto2", ancho_fijo=130))
                self.m_rapido = Menu(nombres_nv, nombres_nv[0], ancho=180)
                f2.add_widget(self.m_rapido)
                f2.add_widget(Boton("Marcar", ancho=100, al_tocar=self._rapido))
                f2.add_widget(Widget())
                self.caja.add_widget(f2)
            g = GridLayout(cols=3, spacing=dp(6), size_hint_y=None)
            g.bind(minimum_height=g.setter("height"))
            self.casillas = {}
            for u in self.ubs:
                cb = Casilla(u["etiqueta"], self.marcados[u["nivel"]], tam=12, negrita=False,
                             al_cambiar=lambda v, nv=u["nivel"]: self.marcados.__setitem__(nv, v))
                self.casillas[u["nivel"]] = cb
                g.add_widget(cb)
            self.caja.add_widget(g)

    def _rapido(self):
        n = self.m_rapido.valor
        for u in self.ubs:
            if u["nv_nombre"] == n:
                self.marcados[u["nivel"]] = True
                self.casillas[u["nivel"]].activo = True
        if self.e_alc.text in ("", "GENERAL"):
            self.e_alc.text = f"GENERAL {n}"

    def _seleccion(self):
        a = self.seg.valor
        p = self.app.p
        if a == "Por nivel":
            nv = next((u["nivel"] for u in self.ubs if u["etiqueta"] == self.nivel_sel), None)
            return "nivel", [nv] if nv else [], ""
        if a == "Por edificio":
            e = next((x for x in self.eds if x["nombre"] == self.ed_sel), None)
            return "edificio", [n["id"] for n in p.niveles_de(e["id"])] if e else [], e["nombre"] if e else ""
        return "general", [u["nivel"] for u in self.ubs if self.marcados[u["nivel"]]], self.nom_alc

    def _fin(self, k):
        if k == 0:
            self.dismiss()
            return
        p = self.app.p
        alc, niveles, nom = self._seleccion()
        if not niveles:
            ui.info("Plano", "Elegí la ubicación (o las ubicaciones) del plano.")
            return
        if self.ruta:
            self.l_msg.text = "Procesando el plano… (los planos grandes pueden tardar unos segundos)"
            Clock.schedule_once(lambda *_: self._cargar(alc, niveles, nom), 0.1)
            return
        ficha = self.app.punto_deshacer("Cambiar alcance del plano")
        try:
            p.renombrar_plano(self.pid, self.e_nom.text)
            p.vincular_plano(self.pid, niveles, alc, nom)
        except core.ErrorCtrlP as e:
            ui.info("Alcance", str(e))
            return
        self.app.confirmar_deshacer(ficha)
        self.app.guardar()
        self.dismiss()
        if self.al_terminar:
            self.al_terminar()

    def _cargar(self, alc, niveles, nom):
        p = self.app.p
        try:
            dpi = int(self.seg_dpi.valor.split()[0]) if self.seg_dpi else 200
            pag = (self.cont_pag.v if self.cont_pag else 1) - 1
            tipo, datos, w, h = pb.importar_archivo(self.ruta, True, dpi, pag)
            ficha = self.app.punto_deshacer("Cargar plano")
            pid = p.agregar_plano(niveles[0], self.e_nom.text, tipo, datos, w, h, alcance=alc, nombre_alcance=nom)
            p.vincular_plano(pid, niveles, alc, nom)
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
        except Exception as e:
            self.l_msg.text = ""
            ui.info("No se pudo cargar el plano", str(e))
            return
        self.dismiss()
        ui.info("Plano cargado", f"{self.e_nom.text} · {p.etiqueta_plano_ubic(pid)} · {len(datos) / 1048576:,.1f} MB.\n\n"
                "Al abrirlo por primera vez, usá «Calibrar» (dos puntos de una cota conocida) para poder medir.")
        if self.al_terminar:
            self.al_terminar()


class DialogoLibreria(ui.ModalView):
    def __init__(self, app, pagina, elegir=False, nivel=None):
        from dialogos import VentanaGrande
        super().__init__(size_hint=(0, 0), auto_dismiss=False)
        self.app, self.pagina, self.elegir, self.nivel = app, pagina, elegir, nivel
        p = app.p
        it = p.item(pagina.item) if (elegir and pagina.item) else None
        self.v = VentanaGrande("Elegí el plano para la hoja de " + it["codigo"] if it else "Librería de planos",
                               "Cada actividad tiene su hoja en cada plano: si el plano ya tiene marcas de otras "
                               "actividades, para esta se abre limpio." if it else
                               "Los planos de la librería siempre quedan limpios; las marcas van en las hojas de cada "
                               "actividad.")
        self.t = Tabla([("Plano", 260, "left"), ("Alcance", 240, "left"), ("Calibrado", 96, "center"),
                        ("Hojas (actividades marcadas)", None, "left")], al_tocar=self._tocar_plano)
        self.v.cuerpo.add_widget(self.t)
        self.v.cuerpo.add_widget(Etiqueta("Todas las hojas de marcado", 14, True))
        self.th = Tabla([("Actividad", None, "left"), ("Plano · alcance", 330, "left"), ("Marcas", 80, "right"),
                         ("Última", 100, "center")], al_tocar=self._tocar_hoja, size_hint_y=0.7)
        self.v.cuerpo.add_widget(self.th)
        bloq = p.solo_agregar
        bot = []
        for txt, cmd in (("Cargar plano…", self.cargar), ("Alcance…", self.alcance), ("Eliminar plano", self.eliminar),
                         ("Eliminar hoja", self.eliminar_hoja)):
            bot.append((txt, cmd, False))
        bot.append(("Cerrar", self.dismiss, not elegir))
        if elegir:
            bot.append(("Usar para " + (it["codigo"] if it else "la actividad"), self.usar, True))
        self.v.botones(bot)
        if bloq:
            for w in self.v.pie_botones.children:
                if w.text in ("Cargar plano…", "Alcance…", "Eliminar plano", "Eliminar hoja"):
                    w.disabled = True
        self.l_ayuda = self.v.l_pie
        self.l_ayuda.text = "Tocá un plano o una hoja para elegirlo; tocá de nuevo para abrirlo."
        self.cargar_listas()

    def open(self, *a, **kw):
        self.v.open()

    def dismiss(self, *a, **kw):
        self.v.dismiss()

    def cargar_listas(self):
        p = self.app.p
        items = {i["id"]: i for i in p.items()}
        filas = []
        for x in p.planos():
            if self.nivel and self.nivel not in x["niveles"]:
                continue
            hojas = p.hojas_de(pid=x["id"])
            txt = ", ".join(f"{items[h['item']]['codigo']} ({h['n_marcas']})" for h in hojas if h["item"] in items) or "—"
            filas.append({"id": x["id"], "vals": [x["nombre"], p.etiqueta_plano_ubic(x["id"]), "✓" if x["escala"] else "—",
                                                  txt]})
        if not filas:
            filas.append({"id": None, "vals": ["La librería está vacía: «Cargar plano…».", "", "", ""]})
        self.t.cargar(filas, False)
        fh = []
        for h in p.hojas_de():
            it = items.get(h["item"])
            x = p.plano(h["plano"])
            if not it or not x:
                continue
            fh.append({"id": h["id"], "vals": [f"{it['codigo']} {it['descripcion'][:50]}",
                                               f"{x['nombre']} · {p.etiqueta_plano_ubic(h['plano'])}", h["n_marcas"],
                                               core.fecha_txt(h["ultima"]) if h["ultima"] else ""]})
        self.th.cargar(fh, False)

    def _tocar_plano(self, f):
        if f.get("id") and getattr(self, "_ultimo", None) == ("p", f["id"]):
            (self.usar if self.elegir else self.alcance)()
        self._ultimo = ("p", f.get("id"))

    def _tocar_hoja(self, f):
        if f.get("id") and getattr(self, "_ultimo", None) == ("h", f["id"]):
            self.usar_hoja()
        self._ultimo = ("h", f.get("id"))

    def _sel(self):
        s = self.t.sel_id
        return s if s and self.app.p.plano(s) else None

    def cargar(self):
        ui.elegir_archivo("Cargar plano (PDF o imagen)", ui.carpeta_docs(self.app.cfg),
                          (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"),
                          lambda r: DialogoAlcance(self.app, ruta=r, al_terminar=self._actualizado).open())

    def _actualizado(self):
        self.cargar_listas()
        self.pagina.refrescar()

    def alcance(self):
        pid = self._sel()
        if pid:
            DialogoAlcance(self.app, pid=pid, al_terminar=self._actualizado).open()
        else:
            ui.info("Alcance", "Tocá un plano de la librería (lista de arriba).")

    def eliminar(self):
        pid = self._sel()
        if not pid:
            ui.info("Eliminar plano", "Tocá un plano de la librería (lista de arriba).")
            return
        x = self.app.p.plano(pid)

        def r(k):
            if not k:
                return
            ficha = self.app.punto_deshacer("Eliminar plano", datos_de=[pid])
            try:
                self.app.p.eliminar_plano(pid, conservar=(k == 1))
            except core.ErrorCtrlP as e:
                ui.info("Plano", str(e))
                return
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            if self.pagina.pid == pid:
                self.pagina.pid = None
                self.pagina.visor.limpiar()
            self._actualizado()
        preguntar_borrado("Eliminar plano", f"«{x['nombre']}» de la librería, con todas sus hojas",
                          self.app.p.marcas(pid), r)

    def eliminar_hoja(self):
        p = self.app.p
        s = self.th.sel_id
        h = next((x for x in p.hojas_de() if x["id"] == s), None) if s else None
        if not h:
            ui.info("Eliminar hoja", "Tocá una hoja en la lista «Todas las hojas de marcado».")
            return
        it = p.item(h["item"])

        def r(k):
            if not k:
                return
            ficha = self.app.punto_deshacer("Eliminar hoja")
            try:
                p.eliminar_hoja(h["id"], conservar=(k == 1))
            except core.ErrorCtrlP as e:
                ui.info("Hoja", str(e))
                return
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            if self.pagina.pid == h["plano"] and self.pagina.item == h["item"]:
                self.pagina.pid = None
                self.pagina.visor.limpiar()
            self._actualizado()
        preguntar_borrado("Eliminar hoja", f"la hoja de {it['codigo']} en «{p.plano(h['plano'])['nombre']}» (el plano "
                          "queda limpio en la librería)", p.marcas(h["plano"], item=h["item"]), r)

    def usar(self):
        pid = self._sel()
        if not pid or not self.elegir:
            if self.elegir:
                ui.info("Plano", "Tocá un plano de la librería.")
            return
        self.dismiss()
        self.pagina.usar_plano(pid)

    def usar_hoja(self):
        p = self.app.p
        s = self.th.sel_id
        h = next((x for x in p.hojas_de() if x["id"] == s), None) if s else None
        if not h:
            return
        pg = self.pagina
        if pg.item and h["item"] != pg.item:
            otra = p.item(h["item"])
            act = p.item(pg.item)

            def r(k):
                if k == 2:
                    self.dismiss()
                    pg.usar_plano(h["plano"])
                elif k == 1:
                    self.dismiss()
                    pg.item = h["item"]
                    pg.act = {"item": h["item"], "ref": "", "fecha": pg._fecha() or core.hoy_iso()}
                    pg.cargar_actividades()
                    pg._hojas()
                    pg.abrir_hoja(h["plano"])
            ui.opciones("Esta hoja es de otra actividad",
                        f"La hoja de «{p.plano(h['plano'])['nombre']}» ya está marcada con {otra['codigo']} "
                        f"{otra['descripcion'][:50]}: no pertenece a {act['codigo']}.\n\n¿Abrir ese mismo plano limpio "
                        f"para {act['codigo']}, o pasar a trabajar en {otra['codigo']}?",
                        ["Cancelar", f"Ir a {otra['codigo']}", f"Limpio para {act['codigo']}"], r, primario=2)
            return
        self.dismiss()
        if not pg.item:
            pg.item = h["item"]
            pg.act = {"item": h["item"], "ref": "", "fecha": pg._fecha() or core.hoy_iso()}
            pg.cargar_actividades()
        pg._hojas()
        pg.abrir_hoja(h["plano"])


class DialogoPartida(ui.Dialogo):
    """Elegir cualquier partida del presupuesto."""

    def __init__(self, app, al_elegir):
        super().__init__("Elegí la actividad a marcar", ancho=760)
        self.cb = al_elegir
        self.partidas = [i for i in app.p.partidas() if i["vigente"]]
        self.e = Campo("", pista="Buscar por código o descripción", al_cambiar=lambda *_: self._filtrar())
        self.cuerpo.add_widget(self.e)
        self.t = Tabla([("Código", 110, "left"), ("Descripción", None, "left"), ("Unid.", 70, "center")],
                       al_tocar=self._tocar, size_hint_y=None, height=dp(420))
        self.cuerpo.add_widget(self.t)
        self.botones(["Cancelar", "Elegir"], 1, self._fin)
        self._filtrar()

    def _filtrar(self):
        q = core.clave_texto(self.e.text)
        vis = [i for i in self.partidas if not q or q in core.clave_texto(i["codigo"] + " " + i["descripcion"])][:400]
        self.t.cargar([{"id": i["id"], "vals": [i["codigo"], i["descripcion"], i["unidad"]]} for i in vis], False)

    def _tocar(self, f):
        if getattr(self, "_ultimo", None) == f.get("id"):
            self._fin(1)
        self._ultimo = f.get("id")

    def _fin(self, k):
        if k == 0:
            self.dismiss()
            return
        if not self.t.sel_id:
            ui.aviso("Tocá una actividad de la lista.")
            return
        self.dismiss()
        self.cb(self.t.sel_id)
