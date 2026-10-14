"""
Ctrl-P Android - ventanas grandes: importar presupuesto (nuevo / actualizar), importar archivo recibido,
sugerir ubicaciones, usuarios y columnas de informes. Misma logica que en la computadora.
(En la tablet, lo que alla es doble clic aca es un toque.)
"""

import os
import shutil

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget

import ctrlp_core as core
import ui_k as ui
from tabla import Tabla
from ui_k import (Boton, Campo, Columna, Contador, Desplazable, Etiqueta, Fila, Interruptor, Menu, Tarjeta, fmt,
                  leer_num, rgba)


class VentanaGrande(ModalView):
    """Ventana casi a pantalla completa con titulo, cuerpo y pie con botones."""

    def __init__(self, titulo, subtitulo="", **kw):
        super().__init__(size_hint=(0.96, 0.94), auto_dismiss=False, background="",
                         background_color=[0, 0, 0, 0.45], **kw)
        caja = Tarjeta(relleno=0, espacio=0, ajustar_alto=False, fondo="fondo")
        cab = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(78), padding=[dp(24), dp(10)])
        izq = BoxLayout(orientation="vertical")
        izq.add_widget(Etiqueta(titulo, 22, True))
        self.l_sub = Etiqueta(subtitulo, 12, color="texto2", una_linea=True)
        izq.add_widget(self.l_sub)
        cab.add_widget(izq)
        self.l_paso = Etiqueta("", 14, True, color="acento", alinear="right", ancho_fijo=260)
        cab.add_widget(self.l_paso)
        caja.add_widget(cab)
        self.cuerpo = BoxLayout(orientation="vertical", padding=[dp(24), 0, dp(24), dp(8)], spacing=dp(10))
        caja.add_widget(self.cuerpo)
        pie = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(74), padding=[dp(24), dp(14)],
                        spacing=dp(10))
        from kivy.graphics import Color, Rectangle
        with pie.canvas.before:
            Color(*rgba("tarjeta"))
            r = Rectangle()
        pie.bind(pos=lambda *_: setattr(r, "pos", pie.pos), size=lambda *_: setattr(r, "size", pie.size))
        self.l_pie = Etiqueta("", 12, color="texto2")
        pie.add_widget(self.l_pie)
        self.pie_botones = BoxLayout(orientation="horizontal", size_hint_x=None, spacing=dp(10))
        self.pie_botones.bind(minimum_width=self.pie_botones.setter("width"))
        pie.add_widget(self.pie_botones)
        caja.add_widget(pie)
        self.add_widget(caja)

    def botones(self, lista):
        """lista: [(texto, funcion, primario)]"""
        self.pie_botones.clear_widgets()
        for t, fn, prim in lista:
            self.pie_botones.add_widget(Boton(t, primario=prim, ancho=max(120, 16 + 9 * len(t)), al_tocar=fn))

    def kpis(self, datos):
        f = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(96), spacing=dp(12))
        for a, b, c, ok in datos:
            t = Tarjeta(relleno=12, espacio=2, ajustar_alto=False)
            t.add_widget(Etiqueta(a, 12, color="texto2"))
            t.add_widget(Etiqueta(b, 20, True))
            t.add_widget(Etiqueta(c, 11, ok, color="acento" if ok else "texto2"))
            f.add_widget(t)
        self.cuerpo.add_widget(f)


# =========================================================================
#  Importar presupuesto
# =========================================================================
class AsistenteImportacion(VentanaGrande):
    def __init__(self, app, ruta, modo="nuevo"):
        super().__init__("Revisión de importación" if modo == "nuevo" else "Actualización de presupuesto",
                         os.path.basename(ruta))
        self.app, self.ruta, self.modo = app, ruta, modo
        try:
            self.hoja, self.filas = core.leer_excel(ruta)
        except core.ErrorCtrlP as e:
            ui.info("No se puede importar", str(e))
            self._error = True
            return
        self._error = False
        self.filas = [list(r) for r in self.filas]
        self.mapa, self.inicio = core.detectar_columnas(self.filas)
        self.correcciones = {}
        self.obs_sel = 0
        self.paso_columnas()

    def open(self, *a, **kw):
        if getattr(self, "_error", False):
            return
        return super().open(*a, **kw)

    # ---- paso 2: columnas
    def paso_columnas(self):
        self.cuerpo.clear_widgets()
        self.l_paso.text = "Paso 2 de 3 · Columnas"
        n_cols = min(26, max([len(r) for r in self.filas[:200] if r] or [6]))
        letras = [chr(65 + k) for k in range(n_cols)]
        enc = {}
        for r in self.filas[max(0, self.inicio - 3):self.inicio]:
            for k, v in enumerate(r or []):
                if v not in (None, "") and k < len(letras):
                    enc[k] = f"{letras[k]} · {str(v)[:18]}"
        self.opciones = ["(ninguna)"] + [enc.get(k, letras[k]) for k in range(len(letras))]
        t = Tarjeta(relleno=14)
        g = GridLayout(cols=3, spacing=dp(12), size_hint_y=None)
        g.bind(minimum_height=g.setter("height"))
        self.menus = {}
        for campo, nombre in core.CAMPOS:
            c = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(72), spacing=dp(4))
            c.add_widget(Etiqueta(nombre, 13, True))
            col_ = self.mapa.get(campo)
            v = self.opciones[col_ + 1] if col_ is not None and col_ + 1 < len(self.opciones) else "(ninguna)"
            m = Menu(self.opciones, v, al_cambiar=lambda _: self._preview())
            self.menus[campo] = m
            c.add_widget(m)
            g.add_widget(c)
        c = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(72), spacing=dp(4))
        c.add_widget(Etiqueta("Fila donde empiezan los datos", 13, True))
        self.cont_ini = Contador(self.inicio + 1, 1, max(1, len(self.filas)), al_cambiar=lambda _: self._preview())
        c.add_widget(self.cont_ini)
        g.add_widget(c)
        t.add_widget(g)
        self.cuerpo.add_widget(t)
        cols = [("Fila", 60, "right")] + [(n, None if c == "descripcion" else 120,
                                           "left" if c in ("codigo", "descripcion") else "right") for c, n in core.CAMPOS]
        self.t_prev = Tabla(cols)
        self.cuerpo.add_widget(self.t_prev)
        self._preview()
        self.l_pie.text = ("Revisá que cada columna esté bien identificada. El programa ya propuso las que encontró en el "
                           "encabezado.")
        self.botones([("Cancelar", self.dismiss, False), ("Siguiente", self.paso_revision, True)])

    def _mapa_actual(self):
        m = {}
        for campo, menu in self.menus.items():
            i = self.opciones.index(menu.valor) if menu.valor in self.opciones else 0
            if i > 0:
                m[campo] = i - 1
        return m, max(0, self.cont_ini.v - 1)

    def _preview(self):
        m, ini = self._mapa_actual()
        filas = []
        for k in range(ini, min(ini + 60, len(self.filas))):
            r = self.filas[k]
            vals = [k + 1]
            for campo, _ in core.CAMPOS:
                c = m.get(campo)
                v = r[c] if c is not None and c < len(r) else ""
                vals.append(fmt(v) if isinstance(v, float) else ("" if v is None else str(v)[:80]))
            filas.append({"id": k, "vals": vals})
        self.t_prev.cargar(filas, False)

    # ---- paso 3: revision
    def paso_revision(self):
        m, ini = self._mapa_actual()
        faltan = [n for c, n in core.CAMPOS if c not in m and c != "total"]
        if faltan:
            ui.info("Columnas", "Falta indicar: " + ", ".join(faltan))
            return
        self.m_rev, self.ini_rev = m, ini
        self.an = core.analizar_presupuesto(self.filas, m, ini, self.ruta)
        if self.an["partidas"] == 0:
            ui.info("Revisión", "No se encontraron partidas con esas columnas.")
            return
        self._revision()

    def _revision(self):
        self.cuerpo.clear_widgets()
        self.l_paso.text = "Paso 3 de 3 · Revisión"
        if self.modo == "nuevo":
            self._revision_nuevo(self.ini_rev)
            fin = ("Crear proyecto", self.crear, True)
        else:
            fin = self._revision_actualizacion()
        bot = [("Atrás", self.paso_columnas, False), ("Cargar Excel corregido…", self.recargar, False)]
        if fin:
            bot.append(fin)
        self.botones(bot)

    def recargar(self):
        def elegido(ruta):
            try:
                hoja, filas = core.leer_excel(ruta)
            except core.ErrorCtrlP as e:
                ui.info("No se puede cargar", str(e))
                return
            quedan, ya, perdidas = {}, 0, 0
            for (fila, campo), (orig, nuevo) in self.correcciones.items():
                c = self.m_rev.get(campo)
                v = filas[fila - 1][c] if fila - 1 < len(filas) and c is not None and c < len(filas[fila - 1]) else None
                if str(v) == str(orig):
                    quedan[(fila, campo)] = (orig, nuevo)
                elif str(v) == str(nuevo):
                    ya += 1
                else:
                    perdidas += 1
            self.ruta, self.filas, self.correcciones = ruta, [list(r) for r in filas], {}
            for (fila, campo), (orig, nuevo) in quedan.items():
                self._aplicar_correccion(fila, campo, nuevo, orig)
            self.an = core.analizar_presupuesto(self.filas, self.m_rev, self.ini_rev, self.ruta)
            self._revision()
            msg = f"Se cargó {os.path.basename(ruta)}."
            if quedan:
                msg += f"\n{len(quedan)} correcciones hechas aquí se mantienen."
            if ya:
                msg += f"\n{ya} correcciones ya vienen en el Excel."
            if perdidas:
                msg += f"\n{perdidas} correcciones ya no aplican porque esas celdas cambiaron en el Excel."
            ui.info("Excel corregido", msg)
        ui.elegir_archivo("Excel corregido", os.path.dirname(self.ruta), (".xlsx", ".xlsm"), elegido)

    def _aplicar_correccion(self, fila, campo, nuevo, orig=None):
        c = self.m_rev[campo]
        r = self.filas[fila - 1]
        while len(r) <= c:
            r.append(None)
        if orig is None:
            orig = r[c]
        r[c] = nuevo
        prev = self.correcciones.get((fila, campo))
        o = prev[0] if prev else orig
        if str(o) == str(nuevo):
            self.correcciones.pop((fila, campo), None)
        else:
            self.correcciones[(fila, campo)] = (o, nuevo)

    def _editar_obs(self, f):
        fila = f["vals"][0]
        campos = [(c, n) for c, n in core.CAMPOS if c != "total" and c in self.m_rev]
        d = ui.Dialogo("Corregir celda")
        d.cuerpo.add_widget(Etiqueta(f"Fila {fila} del Excel. La corrección queda anotada en el historial del proyecto.",
                                     13, color="texto2"))
        d.cuerpo.add_widget(Etiqueta("Columna", 13, True))
        nombres = [n for _, n in campos]
        m = Menu(nombres, nombres[0])
        d.cuerpo.add_widget(m)
        d.cuerpo.add_widget(Etiqueta("Valor", 13, True))

        def actual(nombre):
            campo = dict((n, c) for c, n in campos)[nombre]
            r = self.filas[fila - 1]
            v = r[self.m_rev[campo]] if self.m_rev[campo] < len(r) else None
            return "" if v is None else (fmt(v) if isinstance(v, float) else str(v))
        e = Campo(actual(nombres[0]))
        m._cb = lambda v: setattr(e, "text", actual(v))
        d.cuerpo.add_widget(e)

        def fin(k):
            if k == 0:
                d.dismiss()
                return
            campo = dict((n, c) for c, n in campos)[m.valor]
            v = e.text.strip()
            if campo in ("cantidad", "pu"):
                n = leer_num(v)
                if n == "error" or n is None:
                    ui.aviso("Escribí un número válido.")
                    return
                v = n
            elif campo == "unidad":
                v = v.upper()
            d.dismiss()
            self._aplicar_correccion(fila, campo, v)
            self.an = core.analizar_presupuesto(self.filas, self.m_rev, self.ini_rev, self.ruta)
            sel = self.obs_sel
            self._revision()
            if self.an["observaciones"]:
                self._ver_obs(min(sel, len(self.an["observaciones"])))
        d.botones(["Cancelar", "Corregir"], 1, fin)
        d.open()

    def _revision_nuevo(self, ini):
        an = self.an
        enc = core.datos_encabezado(self.filas, ini)
        self.kpis([("Partidas", f"{an['partidas']:,}", "Cantidad × precio revisado", False),
                   ("Títulos", f"{an['titulos']:,}", f"{an['capitulos']} capítulos, hasta {an['profundidad']} niveles", False),
                   ("Total importado", fmt(an["total_importado"]),
                    "Cuadra con el total de la hoja" if an["total_hoja"] is not None and an["cuadra"] else
                    ("No hay fila TOTAL para comparar" if an["total_hoja"] is None else f"La hoja dice {fmt(an['total_hoja'])}"),
                    an["cuadra"] and an["total_hoja"] is not None),
                   ("Observaciones", f"{len(an['observaciones'])} tipos", "No impiden crear el proyecto", False)])
        medio = BoxLayout(orientation="horizontal", spacing=dp(12))
        self._observaciones(medio)
        self.cuerpo.add_widget(medio)
        t = Tarjeta(relleno=12)
        g = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(70), spacing=dp(12))
        self.campos_datos = {}
        for cl, n, w in (("nombre", "Nombre del proyecto (editable)", None), ("contratista", "Contratista", 230),
                         ("propietario", "Propietario", 230), ("moneda", "Moneda", 90)):
            c = BoxLayout(orientation="vertical", spacing=dp(4))
            if w:
                c.size_hint_x = None
                c.width = dp(w)
            c.add_widget(Etiqueta(n, 11, color="texto2"))
            ini_v = (enc.get("nombre_corto") or enc["nombre"]) if cl == "nombre" else enc[cl]
            e = Campo(ini_v, mayus=(cl == "nombre"))
            self.campos_datos[cl] = e
            c.add_widget(e)
            g.add_widget(c)
        t.add_widget(g)
        self.cuerpo.add_widget(t)
        self.l_pie.text = "El presupuesto quedará de solo lectura. Nada se crea hasta tocar «Crear proyecto»."

    def _observaciones(self, medio):
        an = self.an
        izq = Columna(espacio=4, relleno=12)
        marco = Tarjeta(relleno=0, ajustar_alto=False, size_hint_x=None, width=dp(360))
        marco.add_widget(Desplazable(izq))
        izq.add_widget(Etiqueta("Observaciones", 15, True))
        self.obs_botones = []
        if not an["observaciones"]:
            izq.add_widget(Etiqueta("Sin observaciones.", 13, color="texto2"))
        for k, o in enumerate(an["observaciones"]):
            b = Boton(f"{o['tipo']}  ·  {o['cantidad']}", plano=True, alto=40, tam=13, al_tocar=lambda k=k: self._ver_obs(k))
            b.halign = "left"
            b.color = rgba("texto")
            izq.add_widget(b)
            izq.add_widget(Etiqueta(o["detalle"], 11, color="texto2"))
            self.obs_botones.append(b)
        b = Boton("Todas las partidas", plano=True, alto=40, tam=13,
                  al_tocar=lambda: self._ver_obs(len(self.an["observaciones"])))
        b.halign = "left"
        b.color = rgba("texto")
        izq.add_widget(b)
        self.obs_botones.append(b)
        izq.add_widget(Etiqueta("Tocá una fila de la tabla para corregir una celda.", 11, color="texto2"))
        if self.correcciones:
            izq.add_widget(Etiqueta(f"{len(self.correcciones)} correcciones hechas aquí", 12, True, color="acento"))
        medio.add_widget(marco)
        cols = [("Fila", 56, "right"), ("Código", 110, "left"), ("Descripción", None, "left"), ("Unid.", 56, "center"),
                ("Cantidad", 96, "right"), ("P. unitario", 96, "right"), ("Total", 116, "right")]
        self.t_obs = Tabla(cols, al_tocar=self._editar_obs)
        medio.add_widget(self.t_obs)
        self._ver_obs(0 if an["observaciones"] else len(an["observaciones"]))

    def _ver_obs(self, k):
        self.obs_sel = k
        for j, b in enumerate(self.obs_botones):
            b._c_normal = rgba("suave") if j == k else [0, 0, 0, 0]
            b._estado()
        if k < len(self.an["observaciones"]):
            filas = self.an["observaciones"][k]["filas"][:800]
        else:
            filas = [(i["fila"], i["codigo"], i["descripcion"], i["unidad"], i["cantidad"], i["pu"], i["total"])
                     for i in self.an["items"] if i["tipo"] == "P"]
        corr = {f for f, _ in self.correcciones}
        self.t_obs.cargar([{"id": n, "vals": [f[0], f[1], f[2], f[3]] + [fmt(x) if isinstance(x, float) else "" for x in f[4:]],
                            "estilo": "subtotal" if f[0] in corr else ""} for n, f in enumerate(filas)], False)

    def crear(self):
        nombre = core.mayus(self.campos_datos["nombre"].text) or "PROYECTO"
        datos = {k: e.text for k, e in self.campos_datos.items()}
        datos["nombre"] = nombre

        def elegido(ruta):
            def seguir():
                app = self.app
                try:
                    p = core.Proyecto.crear(ruta, app.usuario, self.an, datos)
                    p.sincronizar_usuarios()
                    if self.correcciones:
                        por_fila = {i["fila"]: i for i in self.an["items"]}
                        for (fila, campo), (orig, nuevo) in sorted(self.correcciones.items()):
                            it = por_fila.get(fila)
                            p.registrar(f"Corrección al importar (fila {fila}): {dict(core.CAMPOS)[campo]}",
                                        p.etiqueta_item(it) if it else "", "", orig, nuevo)
                        p.guardar()
                except Exception as e:
                    ui.info("No se pudo crear", str(e))
                    return
                self.dismiss()
                app._proyecto_listo(p)
                ui.info("Proyecto creado", f"Se creó «{nombre}».\n\nSiguiente paso: creá las ubicaciones (edificios, "
                        "niveles y áreas).")
            self.app.cerrar_proyecto(seguir)
        ui.guardar_archivo("Guardar proyecto", ui.carpeta_docs(self.app.cfg), f"{nombre[:50]}{core.EXT}", (core.EXT,),
                           elegido)

    # ---- actualizacion
    def _revision_actualizacion(self):
        p = self.app.p
        self.comp = core.comparar_presupuestos(p, self.an)
        c = self.comp
        if not c["mismo"]:
            self.kpis([("Coincidencia de partidas", f"{c['coincidencia'] * 100:.2f} %", "Con el presupuesto actual", False),
                       ("Coincidencia de capítulos", f"{c['coincidencia_capitulos'] * 100:.2f} %", "Títulos principales",
                        False)])
            t = Tarjeta()
            t.add_widget(Etiqueta("Este Excel no es el mismo presupuesto del proyecto.", 17, True, color="rojo"))
            t.add_widget(Etiqueta("La mayoría de sus partidas y capítulos no coinciden con las del proyecto. Cargarlo "
                                  "provocaría errores (avances y cantidades contractuales quedarían sin su partida), por "
                                  "eso no se puede aplicar.\n\nRevisá que sea el archivo correcto, o creá un proyecto nuevo "
                                  "con este presupuesto.", 14))
            self.cuerpo.add_widget(t)
            self.cuerpo.add_widget(Widget())
            self.l_pie.text = "No se aplicó ningún cambio."
            return ("Cerrar", self.dismiss, True)
        con_av = sum(1 for _, av in c["eliminadas"] if av)
        self.kpis([("Sin cambios", f"{len(c['sin_cambios']):,}", "Se mantienen igual", False),
                   ("Modificadas", f"{len(c['modificadas'])}", "Conservan avance y contractual", False),
                   ("Por confirmar", f"{len(c['probables'])}", "Tocá para aceptar o rechazar", bool(c["probables"])),
                   ("Nuevas / eliminadas", f"{len(c['nuevas'])} / {len(c['eliminadas'])}",
                    f"{con_av} con avance quedan como «fuera»", False)])
        cols = [("Resultado", 190, "left"), ("Código", 170, "left"), ("Descripción", None, "left"), ("Antes", 190, "left"),
                ("Después", 190, "left")]
        self.t_comp = Tabla(cols, al_tocar=self._toggle)
        self.aceptar = {}
        filas = []
        for a, n, s in c["probables"]:
            self.aceptar[n["id"]] = True
            filas.append({"id": "P" + n["id"], "vals": ["✓ Vincular (probable)", f"{a['codigo']} → {n['codigo']}",
                                                       n["descripcion"], f"{fmt(a['cantidad'])} × {fmt(a['pu'])}",
                                                       f"{fmt(n['cantidad'])} × {fmt(n['pu'])}"]})
        for a, n in c["modificadas"]:
            filas.append({"id": None, "vals": ["Modificada", n["codigo"], n["descripcion"],
                                               f"{fmt(a['cantidad'])} {a['unidad']} × {fmt(a['pu'])}",
                                               f"{fmt(n['cantidad'])} {n['unidad']} × {fmt(n['pu'])}"]})
        for n in c["nuevas"]:
            filas.append({"id": None, "vals": ["Nueva", n["codigo"], n["descripcion"], "",
                                               f"{fmt(n['cantidad'])} {n['unidad']} × {fmt(n['pu'])}"]})
        for a, av in c["eliminadas"]:
            filas.append({"id": None, "estilo": "rojo" if av else "",
                          "vals": ["Eliminada" + (" (con avance)" if av else ""), a["codigo"], a["descripcion"],
                                   f"{fmt(a['cantidad'])} {a['unidad']} × {fmt(a['pu'])}",
                                   "Fuera del presupuesto vigente" if av else "Se retira"]})
        self.t_comp.cargar(filas, False)
        self.cuerpo.add_widget(self.t_comp)
        self.l_pie.text = ((f"Solo coincide el {c['coincidencia'] * 100:.2f} % de las partidas: revisá bien antes de "
                            "aplicar. " if c["dudoso"] else "") +
                           f"Total actual {fmt(p.total_presupuesto())} → nuevo {fmt(self.an['total_importado'])}. "
                           "Se hará una copia de seguridad antes de aplicar.")
        return ("Aplicar actualización", self.aplicar, True)

    def _toggle(self, f):
        iid = f.get("id")
        if iid and str(iid).startswith("P"):
            k = iid[1:]
            self.aceptar[k] = not self.aceptar[k]
            self.t_comp.poner_valor(iid, 0, "✓ Vincular (probable)" if self.aceptar[k] else "× Tratar como nueva")

    def aplicar(self):
        p = self.app.p
        try:
            carpeta = core.Proyecto.carpeta_respaldos(p.ruta)
            os.makedirs(carpeta, exist_ok=True)
            p.guardar()
            stem = os.path.splitext(os.path.basename(p.ruta))[0]
            shutil.copy2(p.ruta, os.path.join(carpeta, f"{stem}_antes de presupuesto V{p.version_presupuesto + 1}{core.EXT}"))
            v = core.aplicar_actualizacion(p, self.an, self.comp, self.aceptar, self.ruta)
            self.app.guardar()
        except Exception as e:
            ui.info("No se pudo actualizar", str(e))
            return
        self.dismiss()
        self.app._proyecto_listo(p)
        ui.info("Presupuesto actualizado", f"El proyecto ahora usa el presupuesto V{v}.")


# =========================================================================
#  Importar archivo recibido
# =========================================================================
class DialogoImportacion(VentanaGrande):
    def __init__(self, app, imp):
        super().__init__("Resumen de cambios", imp["archivo"] + (f"  ·  {imp['aviso']}" if imp["aviso"] else ""))
        self.app, self.imp = app, imp
        p = app.p
        cols = [("Cambio", 170, "left"), ("Fecha", 100, "center"), ("Actividad", None, "left"), ("Ubicación", 170, "left"),
                ("Valor", 200, "left"), ("Usuario", 180, "left")]
        self.t = Tabla(cols, al_tocar=self._toggle)
        self.usar = {}
        filas = []
        for l, r in imp["modificados"]:
            self.usar[l["id"]] = True
            it = p.item(r["item"])
            filas.append({"id": "M" + l["id"], "estilo": "rojo", "vals": [
                "✓ Usar el recibido", core.fecha_txt(r["fecha"]), p.etiqueta_item(it) if it else "", r["ubicacion"],
                f"{fmt(l['cantidad'])} → {fmt(r['cantidad'])}", r["mod_usuario"]]})
        for r in imp["nuevos"]:
            it = p.item(r["item"])
            filas.append({"id": None, "vals": ["Avance nuevo", core.fecha_txt(r["fecha"]), p.etiqueta_item(it) if it else "",
                                               r["ubicacion"], f"{fmt(r['cantidad'])} {it['unidad'] if it else ''}" +
                                               (f" · {r['obs']}" if r["obs"] else ""), r["usuario"]]})
        for r, l, n in imp["contractual"]:
            it = p.item(r["item"])
            filas.append({"id": None, "vals": ["Contractual", "", p.etiqueta_item(it) if it else "", n,
                                               f"{fmt(l)} → {fmt(r['cantidad'])}", ""]})
        for tipo, d in imp["ubicaciones"]:
            filas.append({"id": None, "vals": ["Ubicación nueva", "", "", d["nombre"], tipo, ""]})
        self.t.cargar(filas, False)
        self.cuerpo.add_widget(self.t)
        self.l_pie.text = (f"{len(imp['nuevos'])} avances nuevos · {len(imp['modificados'])} registros modificados (tocá "
                           f"para elegir) · {len(imp['contractual'])} contractuales · {len(imp['historial'])} filas de "
                           "historial")
        self.botones([("Cancelar", self.dismiss, False), ("Aplicar cambios", self.aplicar, True)])

    def _toggle(self, f):
        iid = f.get("id")
        if iid and str(iid).startswith("M"):
            k = iid[1:]
            self.usar[k] = not self.usar[k]
            self.t.poner_valor(iid, 0, "✓ Usar el recibido" if self.usar[k] else "× Mantener el mío")

    def aplicar(self):
        p = self.app.p
        try:
            p.guardar()
            carpeta = core.Proyecto.carpeta_respaldos(p.ruta)
            os.makedirs(carpeta, exist_ok=True)
            stem = os.path.splitext(os.path.basename(p.ruta))[0]
            shutil.copy2(p.ruta, os.path.join(carpeta, f"{stem}_antes de importar "
                                                       f"{os.path.splitext(self.imp['archivo'])[0]}{core.EXT}"))
            core.aplicar_importacion(p, self.imp, self.usar)
            self.app.guardar()
        except Exception as e:
            ui.info("No se pudo importar", str(e))
            return
        self.dismiss()
        self.app._proyecto_listo(p)
        ui.info("Importación aplicada", "Los cambios recibidos se incorporaron al proyecto.")


# =========================================================================
#  Sugerir ubicaciones
# =========================================================================
class DialogoSugerencias(VentanaGrande):
    def __init__(self, app, sug, al_terminar):
        super().__init__("Partidas que mencionan una ubicación")
        self.app, self.sug, self.al_terminar = app, sug, al_terminar
        self.t = Tabla([("Asignar", 90, "center"), ("Código", 120, "left"), ("Descripción", None, "left"),
                        ("Ubicación propuesta", 220, "left")], al_tocar=self._toggle)
        self.ok = {}
        filas = []
        for k, (it, nv, et) in enumerate(sug):
            self.ok[k] = True
            filas.append({"id": k, "vals": ["✓", it["codigo"], it["descripcion"], et]})
        self.t.cargar(filas, False)
        self.cuerpo.add_widget(self.t)
        self.l_pie.text = "Tocá para quitar una sugerencia. Revisá: textos como «B1» pueden ser nombres de equipos."
        self.botones([("Cancelar", self.dismiss, False), ("Asignar", self.aplicar, True)])

    def _toggle(self, f):
        k = f["id"]
        self.ok[k] = not self.ok[k]
        self.t.poner_valor(k, 0, "✓" if self.ok[k] else "×")

    def aplicar(self):
        p = self.app.p
        n = 0
        for k, (it, nv, _) in enumerate(self.sug):
            if self.ok[k]:
                try:
                    p.set_ubic_fija(it["id"], nv)
                    n += 1
                except core.ErrorCtrlP:
                    pass
        if n:
            self.app.guardar()
        self.dismiss()
        self.al_terminar()
        ui.info("Ubicaciones asignadas", f"{n} partidas quedaron con ubicación fija.")


# =========================================================================
#  Usuarios
# =========================================================================
class DialogoUsuarios(VentanaGrande):
    def __init__(self, app):
        admin = core.es_admin(app.usuario)
        super().__init__("Usuarios", app.usuario + ("  ·  Administrador · puede ver y cambiar todas las contraseñas"
                                                    if admin else ("  ·  Usuario con contraseña" if app.con_clave
                                                                   else "  ·  Usuario sin contraseña")))
        self.app = app
        self.ver = False
        self.sel = None
        self.armar()

    def _extra(self):
        return self.app.p.usuarios_proyecto() if self.app.p else None

    def armar(self):
        self.cuerpo.clear_widgets()
        app = self.app
        if core.es_admin(app.usuario):
            f = Fila(alto=46)
            f.add_widget(Etiqueta("Usuarios con contraseña", 15, True))
            f.add_widget(Boton("Cambiar contraseña", ancho=190, al_tocar=self.cambiar_otro))
            f.add_widget(Boton("Quitar contraseña", ancho=180, al_tocar=self.quitar))
            f.add_widget(Boton("Ocultar contraseñas" if self.ver else "Mostrar contraseñas", ancho=200,
                               al_tocar=self._alternar))
            self.cuerpo.add_widget(f)
            self.t = Tabla([("Usuario", None, "left"), ("Contraseña", 220, "left"), ("Creado", 200, "left")],
                           al_tocar=lambda fl: setattr(self, "sel", fl.get("id")))
            regs = core.usuarios_registrados(self._extra())
            filas = []
            for u in sorted(regs):
                r = regs[u]
                c = core.ver_clave(app.llave, r.get("cifrada")) if self.ver else "••••••"
                if self.ver and not c:
                    c = "(se ve en la computadora)" if app.llave is None else "(no disponible)"
                filas.append({"id": u, "vals": [u, c, r.get("creado", "")]})
            if not regs:
                filas.append({"id": None, "vals": ["Todavía no hay otros usuarios con contraseña.", "", ""]})
            self.t.cargar(filas, False)
            self.cuerpo.add_widget(self.t)
        else:
            t = Tarjeta()
            if app.con_clave:
                t.fila("Mi contraseña", Boton("Cambiar…", ancho=140, al_tocar=self.cambiar_mia),
                       "Necesitás tu contraseña actual.")
            else:
                t.fila("Proteger mi usuario", Boton("Crear contraseña…", ancho=190, al_tocar=self.crear_mia),
                       "Así nadie más puede entrar con tu nombre.")
            self.cuerpo.add_widget(t)
            self.cuerpo.add_widget(Widget())
        self.botones([("Cambiar de usuario", self.cambiar_usuario, False), ("Cerrar", self.dismiss, True)])

    def _alternar(self):
        self.ver = not self.ver
        self.armar()

    def _sinc(self):
        if self.app.p:
            self.app.p.sincronizar_usuarios()
            self.app.guardar()

    def _sel(self):
        if not self.sel or self.sel not in core.usuarios_registrados(self._extra()):
            ui.info("Usuarios", "Tocá un usuario de la lista.")
            return None
        return self.sel

    def cambiar_otro(self):
        u = self._sel()
        if not u:
            return

        def ok(r):
            core.cambiar_clave(u, r["clave"], self._extra())
            self._sinc()
            self.armar()
        ui.formulario("Cambiar contraseña", u, [("clave", "Nueva contraseña", True, "")], ["Cancelar", "Guardar"], ok,
                      validar=lambda v: "" if len(v["clave"]) >= 4 else "Mínimo 4 caracteres.")

    def quitar(self):
        u = self._sel()
        if not u:
            return

        def r(si):
            if si:
                core.quitar_clave(u)
                self._sinc()
                self.armar()
        ui.preguntar("Quitar contraseña", f"{u} volverá a entrar solo con su nombre.", r, si="Quitar")

    def cambiar_mia(self):
        u = self.app.usuario
        n, e = u.split(" - ", 1)

        def validar(v):
            try:
                core.verificar_usuario(n, e, v["actual"], self._extra())
            except core.ErrorCtrlP:
                return "La contraseña actual no es correcta."
            if v["nueva"] != v["nueva2"]:
                return "Las contraseñas nuevas no coinciden."
            return "" if len(v["nueva"]) >= 4 else "Mínimo 4 caracteres."

        def ok(r):
            core.cambiar_clave(u, r["nueva"], self._extra())
            self._sinc()
            ui.info("Contraseña", "Tu contraseña se cambió.")
        ui.formulario("Cambiar mi contraseña", u, [("actual", "Contraseña actual", True, ""),
                                                   ("nueva", "Nueva contraseña", True, ""),
                                                   ("nueva2", "Repetir nueva contraseña", True, "")],
                      ["Cancelar", "Guardar"], ok, validar=validar)

    def crear_mia(self):
        u = self.app.usuario
        n, e = u.split(" - ", 1)

        def validar(v):
            if v["clave"] != v["clave2"]:
                return "Las contraseñas no coinciden."
            try:
                core.registrar_usuario(n, e, v["clave"], self._extra())
            except core.ErrorCtrlP as ex:
                return str(ex)
            return ""

        def ok(_):
            self.app.con_clave = True
            self._sinc()
            self.armar()
        ui.formulario("Crear contraseña", u, [("clave", "Contraseña", True, ""), ("clave2", "Repetir contraseña", True, "")],
                      ["Cancelar", "Guardar"], ok, validar=validar)

    def cambiar_usuario(self):
        def seguir():
            self.dismiss()
            app = self.app
            app.usuario = None
            app.llave = None
            app.con_clave = False
            app.paginas = {}
            app.pagina = None
            app.mostrar_login()
        self.app.cerrar_proyecto(seguir)


# =========================================================================
#  Columnas de informes
# =========================================================================
def dialogo_columnas(visibles, al_aceptar):
    import ctrlp_excel as xl
    d = ui.Dialogo("Columnas visibles", ancho=480)
    d.cuerpo.add_widget(Etiqueta("Las que ocultes tampoco se exportan al Excel.", 13, color="texto2"))
    sw = {}
    for k, n in xl.COLUMNAS_OPCIONALES:
        f = Fila(alto=44)
        f.add_widget(Etiqueta(n, 14))
        s = Interruptor(k in visibles)
        sw[k] = s
        f.add_widget(s)
        d.cuerpo.add_widget(f)

    def fin(i):
        d.dismiss()
        if i == 1:
            al_aceptar({k for k, s in sw.items() if s.activo})
    d.botones(["Cancelar", "Aceptar"], 1, fin)
    d.open()
