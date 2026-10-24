"""
Ctrl-P Android - Informes de avance
===================================
Estado al (un dia) o periodo, detalle por dia o semana, vista por partida, detallada por ubicacion o
planos marcados; grafica (5 tipos, solo porcentajes) arriba de los indicadores. En la tablet no se exporta
(el Excel y el corte de estimacion se sacan en la computadora). Los calculos son los de ctrlp_core.
"""

import datetime as dt
import math
import os

from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KImage
from kivy.uix.widget import Widget
from PIL import Image, ImageDraw, ImageFont

import ctrlp_core as core
import ui_k as ui
from paginas import Pagina
from tabla import Tabla
from ui_k import (Boton, Campo, Etiqueta, Fila, Flujo, Interruptor, Menu, Segmentado, Tarjeta, fmt, fmt_pct, rgba)

COLORES = ("#4E79A7", "#16A34A", "#CBD5E1")
TIPOS_GRAFICA = ("Dona", "Pastel", "Barra 100 %", "Columnas", "Medidor")


def _fuente(tam, negrita=False):
    try:
        return ImageFont.truetype(os.path.join(ui.recursos(), "fuentes", "Inter-Bold.ttf" if negrita
                                               else "Inter-Regular.ttf"), tam)
    except Exception:
        return ImageFont.load_default()


def dibujar_grafica(tipo, fr, avance, escala=3):
    """Grafica de porcentajes con PIL (nitida en tablet). Devuelve una imagen RGBA."""
    s = escala
    fondo = (0, 0, 0, 0)
    txt = ui.rgba("texto")
    txt = tuple(int(c * 255) for c in txt[:3]) + (255,)
    txt2 = tuple(int(c * 255) for c in ui.rgba("texto2")[:3]) + (255,)
    borde = tuple(int(c * 255) for c in ui.rgba("borde")[:3]) + (255,)
    tarjeta = tuple(int(c * 255) for c in ui.rgba("tarjeta")[:3]) + (255,)
    if tipo in ("Dona", "Pastel"):
        W, H = 118 * s, 118 * s
        img = Image.new("RGBA", (W, H), fondo)
        d = ImageDraw.Draw(img)
        ini = -90.0
        for f, c in zip(fr, COLORES):
            ext = 360.0 * f
            if ext >= 359.99:
                d.ellipse([6 * s, 6 * s, 112 * s, 112 * s], fill=c)
            elif ext > 0.05:
                d.pieslice([6 * s, 6 * s, 112 * s, 112 * s], ini, ini + ext, fill=c)
            ini += ext
        if tipo == "Dona":
            d.ellipse([27 * s, 27 * s, 91 * s, 91 * s], fill=tarjeta)
            t = f"{avance * 100:,.2f} %"
            d.text((59 * s, 54 * s), t, fill=txt, font=_fuente(10 * s, True), anchor="mm")
            d.text((59 * s, 70 * s), "avance", fill=txt2, font=_fuente(8 * s), anchor="mm")
        return img
    if tipo == "Barra 100 %":
        W, H = 360 * s, 118 * s
        img = Image.new("RGBA", (W, H), fondo)
        d = ImageDraw.Draw(img)
        x, y0, y1 = 4 * s, 40 * s, 74 * s
        for f, c in zip(fr, COLORES):
            w = (W - 8 * s) * f
            if w > 0.5:
                d.rectangle([x, y0, x + w, y1], fill=c)
            x += w
        d.rectangle([4 * s, y0, W - 4 * s, y1], outline=borde, width=s)
        d.text((4 * s, 22 * s), f"Avance {avance * 100:,.2f} %", fill=txt, font=_fuente(12 * s, True), anchor="lm")
        for k in range(0, 101, 25):
            xx = 4 * s + (W - 8 * s) * k / 100
            d.line([xx, y1 + 2 * s, xx, y1 + 7 * s], fill=txt2, width=s)
            d.text((xx, y1 + 16 * s), f"{k} %", fill=txt2, font=_fuente(8 * s),
                   anchor="lm" if k == 0 else ("rm" if k == 100 else "mm"))
        return img
    if tipo == "Columnas":
        W, H = 230 * s, 118 * s
        img = Image.new("RGBA", (W, H), fondo)
        d = ImageDraw.Draw(img)
        base, alto = H - 18 * s, H - 34 * s
        d.line([6 * s, base, W - 6 * s, base], fill=borde, width=s)
        for k, (f, c) in enumerate(zip(fr, COLORES)):
            x0 = (18 + k * 72) * s
            h = max(2 * s, alto * f) if f > 0 else 0
            if h:
                d.rectangle([x0, base - h, x0 + 44 * s, base], fill=c)
            d.text((x0 + 22 * s, base - h - 8 * s), f"{f * 100:,.2f} %", fill=txt, font=_fuente(9 * s, True), anchor="mm")
        return img
    # Medidor
    W, H = 180 * s, 118 * s
    img = Image.new("RGBA", (W, H), fondo)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 10 * s, 14 * s, 170 * s, 174 * s
    ini = 180.0
    for f, c in zip(fr, COLORES):
        ext = 180.0 * f
        if ext > 0.05:
            d.pieslice([x0, y0, x1, y1], ini, ini + ext, fill=c)
        ini += ext
    d.pieslice([x0 + 34 * s, y0 + 34 * s, x1 - 34 * s, y1 - 34 * s], 180, 360, fill=tarjeta)
    d.text((90 * s, 78 * s), f"{avance * 100:,.2f} %", fill=txt, font=_fuente(13 * s, True), anchor="mm")
    d.text((90 * s, 98 * s), "avance", fill=txt2, font=_fuente(9 * s), anchor="mm")
    return img


# columnas que se pueden ocultar en Informes (en la tablet no se exporta: el Excel se saca en la computadora)
COLUMNAS_OPCIONALES = [
    ("unidad", "Unidad"), ("cantidad", "Cantidad / contractual"), ("ant", "Acumulado anterior"),
    ("p_ant", "% anterior"), ("per", "Este período / del día"), ("p_per", "% del período"),
    ("tot", "Acumulado total"), ("p_tot", "% acumulado"), ("saldo", "Saldo"), ("obs", "Observaciones"),
]


class PaginaInformes(Pagina):
    clave = "informes"
    titulo = "Informes de avance"

    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        hoy = core.hoy_iso()
        dh = core.iso_a_fecha(hoy)
        lunes = (dh - dt.timedelta(days=(dh.weekday() - core.INICIO_SEMANA) % 7)).isoformat()   # inicio de semana
        # controles
        ctl = Tarjeta(relleno=12, espacio=8)
        ws = []
        self.s_modo = Segmentado(["Estado al", "Período"], "Período", ancho=220, al_cambiar=lambda _: self._modo())
        ws.append(self.s_modo)
        self.g_fechas = Fila(alto=40, espacio=6)
        self.g_fechas.size_hint_x = None
        self.l_desde = Etiqueta("Desde", 13, color="texto2", ancho_fijo=52)
        self.e_desde = Campo(core.fecha_txt(lunes), ancho=130, alto=40, alinear="center", al_enter=self.generar)
        self.l_hasta = Etiqueta("Hasta", 13, color="texto2", ancho_fijo=52)
        self.e_hasta = Campo(core.fecha_txt(hoy), ancho=130, alto=40, alinear="center", al_enter=self.generar)
        self._armar_fechas()
        ws.append(self.g_fechas)
        g = Fila(alto=40, espacio=6)
        g.size_hint_x = None
        g.width = dp(64 + 330)
        g.add_widget(Etiqueta("Detalle", 13, color="texto2", ancho_fijo=58))
        self.s_det = Segmentado(["Sumatoria", "+ Por día", "+ Por semana"], "Sumatoria", ancho=330,
                                al_cambiar=lambda _: self.generar())
        g.add_widget(self.s_det)
        ws.append(g)
        # de que dia a que dia van las semanas (se elige en la computadora y viaja en el proyecto)
        g = Fila(alto=40, espacio=6)
        g.size_hint_x = None
        g.width = dp(230)
        self.l_sem = Etiqueta("", 12, color="texto2")
        g.add_widget(self.l_sem)
        ws.append(g)
        g = Fila(alto=40, espacio=6)
        g.size_hint_x = None
        g.width = dp(50 + 480)
        g.add_widget(Etiqueta("Vista", 13, color="texto2", ancho_fijo=44))
        self.s_vista = Segmentado(["Por partida", "Detallado por ubicación", "Planos marcados"], "Por partida", ancho=480,
                                  al_cambiar=lambda _: self.generar())
        g.add_widget(self.s_vista)
        ws.append(g)
        g = Fila(alto=40, espacio=6)
        g.size_hint_x = None
        g.width = dp(70 + 560)
        g.add_widget(Etiqueta("Mostrar", 13, color="texto2", ancho_fijo=64))
        self.s_filtro = Segmentado([t for _, t in core.FILTROS], "Presupuesto completo", ancho=560,
                                   al_cambiar=lambda _: self.generar())
        g.add_widget(self.s_filtro)
        ws.append(g)
        g = Fila(alto=40, espacio=8)
        g.size_hint_x = None
        g.width = dp(250)
        g.add_widget(Etiqueta("Ver solo lo contractual", 13, color="texto2"))
        self.sw_contr = Interruptor(False, al_cambiar=lambda _: self.generar())
        anc = AnchorLayout(size_hint_x=None, width=dp(56))
        anc.add_widget(self.sw_contr)
        g.add_widget(anc)
        ws.append(g)
        g = Fila(alto=40, espacio=6)
        g.size_hint_x = None
        g.width = dp(100 + 96 + 170 + 130 + 18)
        g.add_widget(Boton("Desplegar", ancho=100, alto=40, al_tocar=lambda: self.tabla and self.tabla.desplegar(True)))
        g.add_widget(Boton("Agrupar", ancho=96, alto=40, al_tocar=lambda: self.tabla and self.tabla.desplegar(False)))
        self.b_cols = Boton("Columnas", ancho=170, alto=40, al_tocar=self.columnas)
        g.add_widget(self.b_cols)
        g.add_widget(Boton("Actualizar", primario=True, ancho=130, alto=40, al_tocar=self.generar))
        ws.append(g)
        for w in ws:
            if w.size_hint_x is not None:
                w.size_hint_x = None
        self.flujo_ctl = FlujoAlto(ws)
        ctl.add_widget(self.flujo_ctl)
        self.cuerpo.add_widget(ctl)
        # grafica (arriba) e indicadores
        self.resumen = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(260), spacing=dp(10))
        tg = Tarjeta(relleno=10, espacio=4, ajustar_alto=False, size_hint_y=None, height=dp(150))
        fila_g = BoxLayout(orientation="horizontal", spacing=dp(16))
        self.img_graf = KImage(size_hint=(None, 1), width=dp(130), fit_mode="contain")
        fila_g.add_widget(self.img_graf)
        centro = BoxLayout(orientation="vertical", spacing=dp(4))
        self.ley = BoxLayout(orientation="horizontal", spacing=dp(24))
        centro.add_widget(self.ley)
        self.l_graf = Etiqueta("", 11, color="texto2")
        centro.add_widget(self.l_graf)
        fila_g.add_widget(centro)
        der = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(170), spacing=dp(4))
        der.add_widget(Etiqueta("Gráfica", 11, color="texto2", alinear="right"))
        self.m_graf = Menu(list(TIPOS_GRAFICA), app.cfg.get("tipo_grafica", "Dona"), ancho=170, al_cambiar=self._tipo_graf)
        der.add_widget(self.m_graf)
        der.add_widget(Widget())
        fila_g.add_widget(der)
        tg.add_widget(fila_g)
        self.resumen.add_widget(tg)
        kp = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(100), spacing=dp(10))
        self.kpis = []
        for k in range(5):
            t = Tarjeta(relleno=10, espacio=0, ajustar_alto=False)
            a = Etiqueta("", 11, color="texto2", una_linea=True)
            b = Etiqueta("", 20, True, una_linea=True)
            c = Etiqueta("", 11, color="texto2")
            t.add_widget(a)
            t.add_widget(b)
            t.add_widget(c)
            t.add_widget(Widget())
            kp.add_widget(t)
            self.kpis.append((a, b, c))
        self.resumen.add_widget(kp)
        fila_res = Fila(alto=30)
        fila_res.add_widget(Widget())
        self.b_res = Boton("▲ Ocultar resumen", plano=True, ancho=200, alto=30, tam=12, al_tocar=self._alternar_resumen)
        fila_res.add_widget(self.b_res)
        self.cuerpo.add_widget(fila_res)
        self.cuerpo.add_widget(self.resumen)
        self.contenedor = BoxLayout(orientation="vertical")
        self.cuerpo.add_widget(self.contenedor)
        self.tabla = None
        self.visibles = set(k for k, _ in COLUMNAS_OPCIONALES)
        self._graf_datos = None
        self.visor_pl = None

    def _armar_fechas(self):
        g = self.g_fechas
        g.clear_widgets()
        estado = self.s_modo.valor == "Estado al"
        if not estado:
            g.add_widget(self.l_desde)
            g.add_widget(self.e_desde)
        self.l_hasta.text = "Fecha" if estado else "Hasta"
        g.add_widget(self.l_hasta)
        g.add_widget(self.e_hasta)
        g.width = dp(52 + 130 + 12) * (1 if estado else 2)

    def _alternar_resumen(self):
        vis = self.resumen.parent is not None
        if vis:
            self.cuerpo.remove_widget(self.resumen)
            self.b_res.text = "▼ Mostrar resumen"
        else:
            self.cuerpo.add_widget(self.resumen, index=1)
            self.b_res.text = "▲ Ocultar resumen"

    def _tipo_graf(self, v):
        self.app.cfg = core.config_poner(tipo_grafica=v)
        if self._graf_datos:
            self._grafica(*self._graf_datos)

    def _grafica(self, partes, titulo):
        self._graf_datos = (partes, titulo)
        total = sum(max(v, 0.0) for _, v in partes) or 1.0
        fr = [max(v, 0.0) / total for _, v in partes]
        avance = fr[0] + fr[1]
        tipo = self.m_graf.valor
        img = dibujar_grafica(tipo, fr, avance)
        self.img_graf.texture = ui.textura(img)
        self.img_graf.width = dp(130) * img.width / img.height
        self.ley.clear_widgets()
        for (nombre, v), f, c in zip(partes, fr, COLORES):
            g = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(210))
            fila = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(20), spacing=dp(6))
            cuad = Widget(size_hint=(None, None), size=(dp(12), dp(12)))
            from kivy.graphics import Color, RoundedRectangle
            with cuad.canvas:
                Color(*ui.rgba(c))
                rr = RoundedRectangle(radius=[dp(3)], pos=cuad.pos, size=cuad.size)
            cuad.bind(pos=lambda w, *_ , rr=rr: setattr(rr, "pos", w.pos))
            anc = AnchorLayout(size_hint_x=None, width=dp(14))
            anc.add_widget(cuad)
            fila.add_widget(anc)
            fila.add_widget(Etiqueta(nombre, 12, color="texto2", una_linea=True))
            g.add_widget(fila)
            g.add_widget(Etiqueta(f"{f * 100:,.2f} %", 20, True))
            g.add_widget(Widget())
            self.ley.add_widget(g)
        self.ley.add_widget(Widget())
        self.l_graf.text = titulo

    def _modo(self):
        self._armar_fechas()
        self.s_det.disabled = self.s_modo.valor == "Estado al"
        self.flujo_ctl.rearmar()
        self.generar()

    def _rango(self):
        hasta = core.txt_a_iso(self.e_hasta.text)
        if self.s_modo.valor == "Estado al":
            return "estado", hasta, hasta
        desde = core.txt_a_iso(self.e_desde.text)
        if desde > hasta:
            raise core.ErrorCtrlP("La fecha «Desde» es posterior a «Hasta».")
        return "periodo", desde, hasta

    def refrescar(self):
        if self.p:
            self.generar()

    def columnas(self):
        import dialogos

        def ok(vis):
            self.visibles = vis
            self.b_cols.text = f"Columnas · {len(vis)} de {len(COLUMNAS_OPCIONALES)}"
            self.generar()
        dialogos.dialogo_columnas(self.visibles, ok)

    # ---------------------------------------------------------------- generar
    def generar(self):
        if not self.p:
            return
        try:
            modo, desde, hasta = self._rango()
        except core.ErrorCtrlP as e:
            ui.info("Informes", str(e))
            return
        self._proy_cargado = self.p
        self._rev_cargada = self.p.rev
        if modo != "estado":
            self.e_desde.text = core.fecha_txt(desde)
        self.e_hasta.text = core.fecha_txt(hasta)
        contr = self.sw_contr.activo
        calc = core.Calculo(self.p, desde, hasta, contr)
        t = calc.totales()
        mon = self.p.get_meta("moneda", "US$")
        estado = modo == "estado"
        self.poner_sub((f"Estado al {core.fecha_txt(hasta)}" if estado else
                        f"Período del {core.fecha_txt(desde)} al {core.fecha_txt(hasta)}") +
                       f" · presupuesto V{self.p.version_presupuesto}" + (" · solo lo contractual" if contr else ""))
        datos = [("Acumulado anterior", fmt_pct(t["p_ant"], 2), f"{mon} {fmt(t['m_ant'])}"),
                 ("Avance financiero del día" if estado else "Avance financiero del período", fmt_pct(t["p_per"], 2),
                  f"{mon} {fmt(t['m_per'])}"),
                 ("Acumulado total", fmt_pct(t["p_tot"], 2), f"{mon} {fmt(t['m_tot'])}"),
                 ("Saldo por ejecutar", fmt_pct(t["p_saldo"], 2), f"{mon} {fmt(t['total'] - t['m_tot'])}"),
                 ("Fuera de lo contractual" if contr else "Excedente no cobrable", f"{mon} {fmt(t['m_exc'])}",
                  f"{sum(1 for i in calc.items if i['tipo'] == 'P' and calc.res[i['id']]['exc_tot'] > 1e-9)} partidas "
                  + ("con avance que no cuenta" if contr else "sobre su contractual"))]
        for (a, b, c), (x, y, z) in zip(self.kpis, datos):
            a.text, b.text, c.text = x, y, z
        falta = max(t["total"] - t["m_tot"], 0.0)
        self._grafica([("Ejecutado antes" if not estado else "Ejecutado antes del día", t["m_ant"]),
                       ("Cobrado en el período" if not estado else "Cobrado en el día", t["m_per"]),
                       ("Falta por ejecutar", falta)],
                      "Porcentaje del presupuesto total · montos cobrables (con tope contractual)")
        det = {"+ Por día": "dia", "+ Por semana": "semana"}.get(self.s_det.valor, "")
        self.l_sem.text = f"Semanas: {core.texto_semana(self.p.inicio_semana)}"
        cortes = core.buckets(desde, hasta, det, self.p.inicio_semana) if (det and not estado) else []
        if len(cortes) > 62:
            cortes = []
            self.s_det.poner("Sumatoria")
            ui.info("Detalle", "El período es muy largo para el detalle por día; elegí por semana.")
        if self.s_vista.valor == "Planos marcados":
            self._planos(estado, desde, hasta)
            return
        if self.s_vista.valor == "Por partida":
            self._por_partida(calc, estado, cortes)
        else:
            self._detallado(calc, estado)

    def _filtro(self):
        return {t: k for k, t in core.FILTROS}.get(self.s_filtro.valor, "completo")

    def _nueva_tabla(self, cols):
        self.contenedor.clear_widgets()
        self.tabla = Tabla([(t, w, a) for _, t, w, a in cols], arbol=True, col_arbol=1, alto_fila=42, min_flexible=260)
        self.contenedor.add_widget(self.tabla)
        return [c[0] for c in cols]

    def _por_partida(self, calc, estado, cortes):
        vis = self.visibles
        cols = [("codigo", "Código", 100, "left"), ("descripcion", "Descripción", None, "left")]
        if "unidad" in vis:
            cols.append(("unidad", "Unid.", 60, "center"))
        if "cantidad" in vis:
            cols.append(("cantidad", "Cantidad", 104, "right"))
        if not estado and "ant" in vis:
            cols.append(("ant", "Acum. anterior", 112, "right"))
        if not estado and "p_ant" in vis:
            cols.append(("p_ant", "% ant.", 78, "right"))
        ex_b = []
        for k, (et, b0, b1) in enumerate(cortes):
            cols.append((f"b{k}", et, 96, "right"))
            ex_b.append(self.p.ejecutado_periodo(b0, b1, self.sw_contr.activo))
        cols.append(("per", "Ejecutado del día" if estado else "Período", 112, "right"))
        if not estado and "p_per" in vis:
            cols.append(("p_per", "% período", 86, "right"))
        if "tot" in vis:
            cols.append(("tot", "Acum. a la fecha" if estado else "Acum. total", 118, "right"))
        if "p_tot" in vis:
            cols.append(("p_tot", "%", 78, "right"))
        if "saldo" in vis:
            cols.append(("saldo", "Saldo", 104, "right"))
        cols += [("m_per", "Monto del día" if estado else "Monto período", 124, "right"),
                 ("aporte", "% aporte", 84, "right")]
        keys = self._nueva_tabla(cols)
        tp = calc.total_presu or 1
        filtro = self._filtro()
        vis_ids = calc.visibles(filtro)            # siempre con su partida principal y subpartidas
        solo = filtro != "completo"
        filas = []
        nivel = {}
        hay_hijos = {}
        for it in calc.items:
            r = calc.res[it["id"]]
            n = (nivel.get(it["padre"], -1) + 1) if it["padre"] else 0
            if it["id"] not in vis_ids:
                continue
            if it["tipo"] == "T":
                nivel[it["id"]] = n
                vals = {k: "" for k in keys}
                vals.update(codigo=it["codigo"], descripcion=it["descripcion"], m_per=fmt(r["m_per"]),
                            aporte=fmt_pct(r["m_per"] / tp, 3))
                filas.append({"id": it["id"], "padre": it["padre"] or "", "nivel": n, "vals": [vals[k] for k in keys],
                              "estilo": "titulo0" if not it["padre"] else "titulo",
                              "abierto": True if (solo or not it["padre"]) else False})
                continue
            if not it["vigente"] and abs(r["tot"]) < 1e-9:
                continue
            vals = {"codigo": it["codigo"], "descripcion": it["descripcion"] + ("" if it["vigente"] else
                                                                               "  [fuera del presupuesto]"),
                    "unidad": it["unidad"], "cantidad": fmt(r["cantidad"]), "ant": fmt(r["ant"]),
                    "p_ant": fmt_pct(r["p_ant"]), "per": fmt(r["per"]), "p_per": fmt_pct(r["p_per"]),
                    "tot": fmt(r["tot"]), "p_tot": fmt_pct(r["p_tot"]), "saldo": fmt(r["saldo"]),
                    "m_per": fmt(r["m_per"]), "aporte": fmt_pct(r["m_per"] / tp, 3)}
            for k in range(len(cortes)):
                vals[f"b{k}"] = fmt(sum(ex_b[k].get(it["id"], {}).values()))
            hay_hijos[it["padre"]] = True
            filas.append({"id": it["id"], "padre": it["padre"] or "", "nivel": nivel.get(it["padre"], -1) + 1,
                          "vals": [vals.get(k, "") for k in keys], "abierto": None,
                          "estilo": "verde" if core.completa(r) else ("rojo" if r["saldo"] < -1e-9 else
                                                                      ("fuera" if not it["vigente"] else ""))})
        tit_con_hijos = set()
        for f in filas:
            if f.get("padre"):
                tit_con_hijos.add(f["padre"])
        for f in filas:
            if f.get("abierto") is not None and f["id"] not in tit_con_hijos:
                f["abierto"] = None
        t = calc.totales()
        vals = {k: "" for k in keys}
        vals.update(descripcion="TOTAL DEL PROYECTO", m_per=fmt(t["m_per"]), aporte=fmt_pct(t["p_per"], 3))
        filas.append({"id": "__total", "nivel": 0, "vals": [vals[k] for k in keys], "estilo": "total", "abierto": None})
        self.tabla.cargar(filas, False)

    def _detallado(self, calc, estado):
        vis = self.visibles
        cols = [("codigo", "Código", 110, "left"), ("descripcion", "Actividad / ubicación", None, "left")]
        if "unidad" in vis:
            cols.append(("unidad", "Unid.", 60, "center"))
        if "cantidad" in vis:
            cols.append(("cont", "Contractual", 104, "right"))
        if not estado and "ant" in vis:
            cols.append(("ant", "Acum. anterior", 112, "right"))
        cols.append(("per", "Ejecutado del día" if estado else "Período", 112, "right"))
        if "tot" in vis:
            cols.append(("tot", "Acum. a la fecha" if estado else "Acum. total", 118, "right"))
        if "p_tot" in vis:
            cols += [("p_nivel", "% nivel", 80, "right"), ("p_ed", "% edificio", 86, "right"),
                     ("p_gen", "% general", 86, "right")]
        if "saldo" in vis:
            cols.append(("saldo", "Saldo", 104, "right"))
        if "obs" in vis:
            cols.append(("obs", "Observaciones", 260, "left"))
        keys = self._nueva_tabla(cols)
        obs = self.p.observaciones(calc.desde, calc.hasta) if "obs" in vis else {}
        vis_ids = calc.visibles(self._filtro())
        filas = []
        n = 0
        for it in calc.items:
            if it["tipo"] != "P":
                continue
            r = calc.res[it["id"]]
            if it["id"] not in vis_ids:
                continue
            if not r["cont"] and abs(r["tot"]) < 1e-9:
                continue
            n += 1
            vals = {"codigo": it["codigo"], "descripcion": it["descripcion"], "unidad": it["unidad"],
                    "cont": fmt(r["cantidad"]), "ant": fmt(r["ant"]), "per": fmt(r["per"]), "tot": fmt(r["tot"]),
                    "p_gen": fmt_pct(r["p_tot"]), "saldo": fmt(r["saldo"])}
            pid = it["id"]
            hijos = []
            for g in calc.detalle_ubicaciones(it["id"]):
                for fl in g["filas"]:
                    if abs(fl["tot"]) < 1e-9 and fl["contractual"] is None:
                        continue
                    nombre = g["nombre"] if g["es_area"] else f"{g['nombre']} {fl['nombre']}"
                    o = " | ".join(obs.get((it["id"], fl["nivel"]), []))
                    v2 = {"descripcion": nombre, "unidad": it["unidad"], "cont": fmt(fl["contractual"]),
                          "ant": fmt(fl["ant"]), "per": fmt(fl["per"]), "tot": fmt(fl["tot"]),
                          "p_nivel": fmt_pct(fl["p_nivel"]), "saldo": fmt(fl["saldo"]), "obs": o}
                    nid = f"{pid}|{fl['nivel']}"
                    hs = fl.get("hojas", [])
                    hijos.append({"id": nid, "padre": pid, "nivel": 1, "vals": [v2.get(k, "") for k in keys],
                                  "abierto": True if hs else None,
                                  "estilo": "rojo" if fl["saldo"] is not None and fl["saldo"] < -1e-9 else ""})
                    for j, h in enumerate(hs):
                        base = h["contractual"] if h["contractual"] else (fl["contractual"] if not h["tramo"] else None)
                        sal = (base - h["tot"]) if base else None
                        v3 = {"descripcion": h["nombre"], "unidad": it["unidad"],
                              "cont": f"{h['factor'] * 100:.2f} %" if h["hito"] else fmt(h["contractual"]),
                              "ant": fmt(h["ant"]), "per": fmt(h["per"]), "tot": fmt(h["tot"]),
                              "p_nivel": fmt_pct(core.pct(h["tot"], base)) if base else "",
                              "saldo": fmt(sal) if base else ""}
                        hijos.append({"id": f"{nid}|{j}", "padre": nid, "nivel": 2, "vals": [v3.get(k, "") for k in keys],
                                      "abierto": None,
                                      "estilo": "rojo" if sal is not None and sal < -1e-9 else "fuera"})
                if not g["es_area"] and (abs(g["tot"]) > 1e-9 or g["contractual"]):
                    v4 = {"descripcion": f"Total {g['nombre']}", "unidad": it["unidad"], "cont": fmt(g["contractual"]),
                          "ant": fmt(g["ant"]), "per": fmt(g["per"]), "tot": fmt(g["tot"]),
                          "p_ed": fmt_pct(g["p_edificio"]), "p_gen": fmt_pct(g["p_general"]), "saldo": fmt(g["saldo"])}
                    hijos.append({"id": f"{pid}|T{g['edificio']}", "padre": pid, "nivel": 1,
                                  "vals": [v4.get(k, "") for k in keys], "abierto": None,
                                  "estilo": "rojo" if g["saldo"] is not None and g["saldo"] < -1e-9 else "subtotal"})
            filas.append({"id": pid, "padre": "", "nivel": 0, "vals": [vals.get(k, "") for k in keys],
                          "estilo": "titulo_verde" if core.completa(r) else "titulo", "abierto": True if hijos else None})
            filas += hijos
        if not n:
            filas.append({"id": None, "nivel": 0, "abierto": None,
                          "vals": ["", "No hay partidas con avance o cantidades contractuales en este corte."]})
        self.tabla.cargar(filas, False)

    # ---------------------------------------------------------------- planos marcados
    def _colores_pl(self):
        import planos_base as pb
        cfg = core.leer_config()
        return cfg.get("color_periodo", pb.COLOR_PERIODO), cfg.get("color_anterior", pb.COLOR_ANTERIOR)

    def _planos(self, estado, desde, hasta):
        import planos_base as pb
        from visor import Visor
        p = self.p
        self.contenedor.clear_widgets()
        self.tabla = None
        marco = Tarjeta(relleno=8, espacio=6, ajustar_alto=False)
        items = {i["id"]: i for i in p.items()}
        hojas = [h for h in p.hojas_de() if h["item"] in items and p.plano(h["plano"])]
        etqs = {f"{items[h['item']]['codigo']} {items[h['item']]['descripcion'][:34]} · {p.plano(h['plano'])['nombre']}": h
                for h in hojas}
        ops = list(etqs) or ["(no hay hojas marcadas)"]
        sel = getattr(self, "_hoja_sel", None)
        if sel not in etqs:
            sel = ops[0]
        f = Fila(alto=44, espacio=8)
        self.m_hoja = Menu(ops, sel, al_cambiar=lambda v: (setattr(self, "_hoja_sel", v), self.generar()))
        f.add_widget(self.m_hoja)
        h = etqs.get(sel)
        self.hoja_pl = h
        cp, ca = self._colores_pl()
        if h:
            nvs = p.plano_niveles(h["plano"])
            ops_u = ["Todas las ubicaciones"] + [p.etiqueta_ubicacion(n) for n in nvs]
            ub = getattr(self, "_ub_sel", ops_u[0])
            if ub not in ops_u:
                ub = ops_u[0]
            self.m_ub = Menu(ops_u, ub, ancho=220, al_cambiar=lambda v: (setattr(self, "_ub_sel", v), self.generar()))
            f.add_widget(self.m_ub)
        bper = Boton("Período", ancho=100, al_tocar=lambda: self._color_pl("periodo"))
        bper._c_normal = ui.rgba(cp)
        bper.color = [1, 1, 1, 1]
        bper._estado()
        bant = Boton("Anterior", ancho=100, al_tocar=lambda: self._color_pl("anterior"))
        bant._c_normal = ui.rgba(ca)
        bant.color = [1, 1, 1, 1]
        bant._estado()
        f.add_widget(bper)
        f.add_widget(bant)
        f.add_widget(Etiqueta("Notas", 12, color="texto2", ancho_fijo=48))
        self.notas_pl = getattr(self, "notas_pl", True)
        sw = Interruptor(self.notas_pl, al_cambiar=self._notas)
        anc = AnchorLayout(size_hint_x=None, width=dp(56))
        anc.add_widget(sw)
        f.add_widget(anc)
        marco.add_widget(f)
        self.visor_pl = Visor(solo_ver=True)
        self.visor_pl.notas = self.notas_pl
        marco.add_widget(self.visor_pl)
        self.l_pl = Etiqueta("", 12, color="texto2")
        marco.add_widget(self.l_pl)
        self.contenedor.add_widget(marco)
        if not h:
            self.l_pl.text = "Todavía no hay hojas de marcado. Se marcan en la pestaña Planos."
            return
        filtro = next((n for n in nvs if p.etiqueta_ubicacion(n) == ub), None)
        img = pb.imagen_de(p, h["plano"])
        x = p.plano(h["plano"])
        self.visor_pl.cargar(img, x["escala"], x["unidad"])
        hitos = {r["id"]: p.etiqueta_hito(dict(r), False) for r in p.con.execute("SELECT id, nombre, tipo FROM hitos")}
        varias = len(nvs) > 1
        vis = []
        n_per = 0
        for m in p.marcas(h["plano"], item=h["item"]):
            if m["fecha"] > hasta or (filtro and m["nivel"] != filtro):
                continue
            m["color"] = cp if m["fecha"] >= desde else ca
            n_per += m["fecha"] >= desde
            m["nota_txt"] = pb.texto_nota(p, m, items, hitos, p.etiqueta_ubicacion(m["nivel"]) if varias else None)
            vis.append(m)
        tol = max(img.size) / 300
        for k, a in enumerate(vis):
            for b in vis[k + 1:]:
                if pb.coinciden(a, b, tol):
                    a["color"] = b["color"]
        self.marcas_pl = vis
        self.estilos_pl = {h["item"]: p.estilo_de(h["item"])}
        self.visor_pl.poner_marcas(vis, self.estilos_pl)
        per = core.fecha_txt(hasta) if estado else f"del {core.fecha_txt(desde)} al {core.fecha_txt(hasta)}"
        self.l_pl.text = (f"{len(vis)} marcas · {n_per} {'de ese día' if estado else 'del período'} ({per}) en el color "
                          "de fecha/período, el resto anterior. Las posteriores no se muestran.")

    def _notas(self, si):
        self.notas_pl = si
        if self.visor_pl:
            self.visor_pl.notas = si
            self.visor_pl.redibujar()

    def _color_pl(self, cual):
        import visor
        cp, ca = self._colores_pl()

        def ok(c):
            self.app.cfg = core.config_poner(**({"color_periodo": c} if cual == "periodo" else {"color_anterior": c}))
            self.generar()
        visor.elegir_color(cp if cual == "periodo" else ca,
                           "Color de lo " + ("de la fecha o período" if cual == "periodo" else "anterior"), ok)


class FlujoAlto(BoxLayout):
    """Controles en renglones segun el ancho (cada control de ancho fijo y alto 40)."""

    def __init__(self, widgets, espacio=12, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(8), **kw)
        self._ws = widgets
        self._esp = espacio
        self.bind(width=lambda *_: self.rearmar())

    def rearmar(self):
        for w in self._ws:
            if w.parent:
                w.parent.remove_widget(w)
        self.clear_widgets()
        fila, ancho = None, 0
        for w in self._ws:
            if fila is None or ancho + w.width > self.width:
                fila = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(self._esp))
                self.add_widget(fila)
                ancho = 0
            fila.add_widget(w)
            ancho += w.width + dp(self._esp)
        for f in self.children:
            f.add_widget(Widget())
        n = len(self.children)
        self.height = n * dp(40) + max(0, n - 1) * dp(8)
