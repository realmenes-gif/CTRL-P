"""
Ctrl-P Android - paginas: base, Proyecto, Presupuesto, Ubicaciones y Apariencia.
(Datos fijos, Registro, Informes y Planos estan en sus propios modulos.)
"""

import os

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

import ctrlp_core as core
import dibujos
import ui_k as ui
from tabla import Tabla, filas_presupuesto
from ui_k import (Boton, Campo, Chip, Columna, Contador, Desplazable, Espacio, Etiqueta, Fila, Flujo, Interruptor,
                  Segmentado, Tarjeta, fmt, rgba)


class Pagina(BoxLayout):
    clave = ""
    titulo = ""
    subtitulo = ""

    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", **kw)
        self.app = app
        self.cab = BoxLayout(orientation="horizontal", size_hint_y=None, padding=[dp(28), dp(18), dp(28), dp(10)],
                             spacing=dp(16))
        izq = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        izq.add_widget(Etiqueta(self.titulo, 26, True))
        self.l_sub = Etiqueta(self.subtitulo, 13, color="texto2")
        izq.add_widget(self.l_sub)
        izq.bind(minimum_height=izq.setter("height"))
        self.cab.add_widget(izq)
        self.cab_der = BoxLayout(orientation="horizontal", size_hint=(None, None), spacing=dp(8), height=dp(48))
        self.cab_der.bind(minimum_width=self.cab_der.setter("width"))
        self.cab.add_widget(self.cab_der)
        izq.bind(height=lambda *_: setattr(self.cab, "height", max(izq.height, self.cab_der.height) + dp(28)))
        self.add_widget(self.cab)
        self.cuerpo = BoxLayout(orientation="vertical", padding=[dp(28), 0, dp(28), dp(10)], spacing=dp(10))
        self.add_widget(self.cuerpo)

    @property
    def p(self):
        return self.app.p

    def poner_sub(self, t):
        self.l_sub.text = t

    def refrescar(self):
        pass

    def barra_inferior(self):
        b = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(72), padding=[dp(28), dp(12)],
                      spacing=dp(10))
        from kivy.graphics import Color, Line, Rectangle
        with b.canvas.before:
            Color(*rgba("tarjeta"))
            r = Rectangle()
            Color(*rgba("borde"))
            ln = Line(width=1)
        b.bind(pos=lambda *_: (setattr(r, "pos", b.pos), setattr(ln, "points", [b.x, b.top, b.right, b.top])),
               size=lambda *_: (setattr(r, "size", b.size), setattr(ln, "points", [b.x, b.top, b.right, b.top])))
        self.add_widget(b)
        return b


# =========================================================================
#  Proyecto
# =========================================================================
class PaginaProyecto(Pagina):
    clave = "proyecto"
    titulo = "Proyecto"

    def refrescar(self):
        self.cuerpo.clear_widgets()
        self.col = Columna(espacio=14)
        self.cuerpo.add_widget(Desplazable(self.col))
        if not self.p:
            self.poner_sub("Creá un proyecto nuevo importando el presupuesto, o abrí uno existente.")
            self._sin_proyecto()
        else:
            self.poner_sub(f"Se guarda en: {self.p.ruta}")
            self._con_proyecto()
            self._proy_cargado = self.p
            self._rev_cargada = self.p.rev

    def _sin_proyecto(self):
        t1 = Tarjeta()
        t1.add_widget(Etiqueta("Nuevo proyecto", 18, True))
        t1.add_widget(Etiqueta("Importá el presupuesto desde un Excel de una sola hoja. El presupuesto queda de solo "
                               "lectura y es la base del proyecto.", 13, color="texto2"))
        t1.add_widget(Boton("Importar presupuesto…", primario=True, ancho=230, al_tocar=self.app.nuevo_proyecto))
        t2 = Tarjeta()
        t2.add_widget(Etiqueta("Abrir proyecto", 18, True))
        t2.add_widget(Etiqueta("Abrí un archivo .ctrlp. Al abrirlo se guarda una copia de seguridad del día.", 13,
                               color="texto2"))
        t2.add_widget(Boton("Abrir .ctrlp…", ancho=180, al_tocar=lambda: self.app.abrir_proyecto()))
        self.col.add_widget(ui.par(t1, t2))
        rec = [r for r in core.leer_config().get("recientes", []) if os.path.isfile(r.get("ruta", ""))]
        if rec:
            self.col.add_widget(Etiqueta("Recientes", 16, True))
            t = Tarjeta()
            for r in rec:
                t.fila(r.get("nombre", ""), Boton("Abrir", ancho=100, al_tocar=lambda r=r: self.app.abrir_proyecto(r["ruta"])),
                       f"{r['ruta']}  ·  abierto {r.get('abierto', '')}")
            self.col.add_widget(t)

    def _con_proyecto(self):
        p = self.p
        self.col.add_widget(Etiqueta("Datos del proyecto", 16, True))
        t = Tarjeta()
        self.campos = {}
        for k, txt in (("nombre", "Nombre del proyecto"), ("propietario", "Propietario"),
                       ("contratista", "Contratista"), ("moneda", "Moneda")):
            e = Campo(p.get_meta(k), mayus=(k == "nombre"), ancho=560 if k != "moneda" else 140)
            e.disabled = p.solo_agregar
            self.campos[k] = e
            t.fila(txt, e)
        f = Fila()
        f.add_widget(Widget())
        b = Boton("Guardar cambios", primario=True, ancho=180, al_tocar=self.guardar_datos)
        b.disabled = p.solo_agregar
        f.add_widget(b)
        t.add_widget(f)
        self.col.add_widget(t)
        self.col.add_widget(Etiqueta("Presupuesto", 16, True))
        t1 = Tarjeta()
        partidas = [i for i in p.partidas() if i["vigente"]]
        t1.fila(f"Versión V{p.version_presupuesto}", Etiqueta(f"{p.get_meta('moneda', 'US$')} {fmt(p.total_presupuesto())}",
                                                             15, True, ancho_fijo=200, alinear="right"),
                f"{len(partidas)} partidas vigentes")
        b = Boton("Actualizar…", ancho=140, al_tocar=self.actualizar_presupuesto)
        b.disabled = p.solo_agregar
        t1.fila("Presupuesto nuevo", b, "Se vinculan las partidas para no perder avances ni contractuales.")
        t2 = Tarjeta()
        self.sw_solo = Interruptor(True)
        t2.fila("Solo agregar avance", self.sw_solo,
                "Quien reciba la copia podrá registrar avances nuevos, pero no modificar lo anterior.")
        t2.fila("Exportar copia", Boton("Exportar…", ancho=140, al_tocar=self.exportar),
                "Un archivo .ctrlp para otro equipo. Tu archivo sigue siendo editable.")
        b = Boton("Importar…", ancho=140, al_tocar=self.importar)
        b.disabled = p.solo_agregar
        t2.fila("Importar archivo recibido", b,
                "Por ejemplo la actualizacion_semanal que te devolvieron. Antes de aplicar se muestra el resumen.")
        self.col.add_widget(ui.par(t1, t2))
        self.col.add_widget(Etiqueta("Respaldos e historial", 16, True))
        t = Tarjeta()
        t.fila("Archivo del proyecto (aquí se guarda tu avance)", None, p.ruta)
        t.fila("Copias de seguridad", None,
               f"{core.Proyecto.carpeta_respaldos(p.ruta)}\nUna foto del proyecto tal como estaba al abrirlo cada día. "
               "Ahí NO se guarda lo que registrás después: tu trabajo va al archivo del proyecto.")
        b = Boton("Abrir historial", ancho=160, al_tocar=self.abrir_historial)
        t.fila("Historial de cambios (Excel)", b, "Fecha, usuario, versión, qué se modificó, valor anterior y nuevo.")
        f = Fila(alto=44)
        f.add_widget(Boton("Abrir otro proyecto…", ancho=210, al_tocar=lambda: self.app.abrir_proyecto()))
        f.add_widget(Boton("Nuevo proyecto…", ancho=180, al_tocar=self.nuevo))
        t.fila("Otros proyectos", f, ancho_control=400)
        f.size_hint_x = None
        f.width = dp(400)
        self.col.add_widget(t)
        self.col.add_widget(Espacio(20))

    def abrir_historial(self):
        r = self.p.ruta_historial()
        if not os.path.isfile(r):
            ui.info("Historial", "Todavía no hay historial en Excel (se crea al guardar).")
            return
        if not ui.compartir_archivo(r, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
            ui.info("Historial", f"El historial está en:\n{r}")

    def nuevo(self):
        def seguir():
            self.refrescar()
            self.app.nuevo_proyecto()
        self.app.cerrar_proyecto(seguir)

    def guardar_datos(self):
        self.p.cambiar_datos({k: e.text for k, e in self.campos.items()})
        self.app.guardar()
        ui.info("Datos guardados", "Los datos del proyecto se actualizaron.")

    def actualizar_presupuesto(self):
        def elegido(ruta):
            import dialogos
            dialogos.AsistenteImportacion(self.app, ruta, modo="actualizar").open()
        ui.elegir_archivo("Elegí el Excel del presupuesto actualizado", ui.carpeta_docs(self.app.cfg),
                          (".xlsx", ".xlsm"), elegido)

    def exportar(self):
        base = os.path.splitext(os.path.basename(self.p.ruta))[0]
        solo = self.sw_solo.activo
        nombre = f"{'actualizacion_semanal' if solo else base + ' copia'}{core.EXT}"

        def elegido(destino):
            if os.path.abspath(destino) == os.path.abspath(self.p.ruta):
                ui.info("Exportar", "Elegí un nombre distinto al del proyecto abierto.")
                return
            try:
                core.exportar_copia(self.p, destino, solo)
                self.app.guardar()
            except Exception as e:
                ui.info("No se pudo exportar", str(e))
                return
            ui.info("Copia exportada", f"Se creó:\n{destino}\n\nPodés seguir trabajando normalmente en tu archivo.")
        ui.guardar_archivo("Exportar copia", ui.carpeta_docs(self.app.cfg), nombre, (core.EXT,), elegido)

    def importar(self):
        def elegido(ruta):
            if os.path.abspath(ruta) == os.path.abspath(self.p.ruta):
                ui.info("Importar", "Ese es el archivo que tenés abierto.")
                return
            try:
                imp = core.analizar_importacion(self.p, ruta)
            except core.ErrorCtrlP as e:
                ui.info("No se pudo importar", str(e))
                return
            import dialogos
            dialogos.DialogoImportacion(self.app, imp).open()
        ui.elegir_archivo("Importar archivo recibido", ui.carpeta_docs(self.app.cfg), (core.EXT,), elegido)


# =========================================================================
#  Presupuesto
# =========================================================================
class PaginaPresupuesto(Pagina):
    clave = "presupuesto"
    titulo = "Presupuesto"

    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        f = Fila(alto=46, espacio=10)
        self.e_q = Campo("", pista="Buscar por código o descripción", ancho=360, al_cambiar=lambda *_: self._programar())
        f.add_widget(self.e_q)
        self.l_info = Etiqueta("", 13, color="texto2")
        f.add_widget(self.l_info)
        f.add_widget(Boton("Desplegar todo", ancho=150, al_tocar=lambda: self.tabla.desplegar(True)))
        f.add_widget(Boton("Agrupar todo", ancho=140, al_tocar=lambda: self.tabla.desplegar(False)))
        self.cuerpo.add_widget(f)
        self.tabla = Tabla([("Código", 110, "left"), ("Descripción", None, "left"), ("Unid.", 64, "center"),
                            ("Cantidad", 120, "right"), ("Precio unitario", 130, "right"), ("Total", 150, "right")],
                           arbol=True, col_arbol=1)
        self.cuerpo.add_widget(self.tabla)

    def _programar(self):
        Clock.unschedule(self.cargar)
        Clock.schedule_once(self.cargar, 0.35)

    def refrescar(self):
        if self.p:
            self.poner_sub(f"Versión V{self.p.version_presupuesto} · solo lectura · respeta el orden del Excel")
            self._proy_cargado = self.p
            self._rev_cargada = self.p.rev
        self.cargar()

    def cargar(self, *_):
        if not self.p:
            self.tabla.cargar([])
            return
        tot = self._totales()

        def cols(it):
            if it["tipo"] == "T":
                return [it["codigo"], it["descripcion"], "", "", "", fmt(tot.get(it["id"], 0.0))]
            return [it["codigo"], it["descripcion"], it["unidad"], fmt(it["cantidad"]), fmt(it["pu"]), fmt(it["total"])]
        filas = filas_presupuesto(self.p, cols, self.e_q.text, con_fuera=True)
        if self.e_q.text.strip():
            self.l_info.text = f"{len(filas)} partidas encontradas"
        else:
            for f in filas:
                if f.get("nivel") == 0 and f.get("abierto") is False:
                    f["abierto"] = True
            t = self.p.total_presupuesto()
            filas.append({"id": "__total", "vals": ["", "TOTAL", "", "", "", fmt(t)], "estilo": "total", "nivel": 0,
                          "abierto": None, "padre": ""})
            self.l_info.text = f"{len([i for i in self.p.partidas() if i['vigente']])} partidas · total {fmt(t)}"
        self.tabla.cargar(filas)

    def _totales(self):
        items = self.p.items()
        hijos = {}
        for i in items:
            hijos.setdefault(i["padre"], []).append(i)
        tot = {}

        def s(i):
            if i["tipo"] == "P":
                return i["total"] if i["vigente"] else 0
            tot[i["id"]] = sum(s(h) for h in hijos.get(i["id"], []))
            return tot[i["id"]]
        for i in items:
            if i["tipo"] == "T" and not i["padre"]:
                s(i)
        return tot


# =========================================================================
#  Ubicaciones
# =========================================================================
class PaginaUbicaciones(Pagina):
    clave = "ubicaciones"
    titulo = "Ubicaciones"
    subtitulo = ("Edificios con sus niveles y áreas sin nivel. Cada combinación es una ubicación donde se registra "
                 "el avance.")

    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        caja = BoxLayout(orientation="horizontal", spacing=dp(16))
        self.lista = Columna(espacio=10)
        caja.add_widget(Desplazable(self.lista))
        self.form = Columna(espacio=8, relleno=18)
        self.form_marco = Tarjeta(relleno=0, ajustar_alto=False, size_hint=(None, 1), width=dp(420))
        self.form_marco.add_widget(Desplazable(self.form))
        caja.add_widget(self.form_marco)
        self.cuerpo.add_widget(caja)
        self.editando = None
        self.tipo = "Nuevo edificio"
        self.n = 3
        self.niveles = []      # [id|None, texto]
        self.tramos_area = []  # [id|None, texto]  subdivisiones de un area (SECTOR I → TRAMO 1, TRAMO 2…)
        self._tiene_general = False
        self._regenerar()

    def _form(self):
        f = self.form
        f.clear_widgets()
        if self.editando:
            f.add_widget(Etiqueta(f"Editar {self.editando['nombre']}", 18, True))
        else:
            f.add_widget(Segmentado(["Nuevo edificio", "Nueva área sin nivel"], self.tipo,
                                    al_cambiar=lambda v: (setattr(self, "tipo", v), self._form())))
        es_area = self.editando.get("es_area") if self.editando else self.tipo != "Nuevo edificio"
        f.add_widget(Etiqueta("Nombre del área" if es_area else "Nombre del edificio", 14, True))
        self.e_nombre = Campo(getattr(self, "_nombre", ""), mayus=True,
                              al_cambiar=lambda t: setattr(self, "_nombre", t))
        f.add_widget(self.e_nombre)
        f.add_widget(Etiqueta("Se guarda siempre en mayúsculas.", 12, color="texto2"))
        if es_area:
            f.add_widget(Etiqueta("Un área sin nivel es una sola ubicación (por ejemplo OBRAS EXTERIORES). Si "
                                  "necesitás subdivisiones (SECTOR I → tramo 1, tramo 2…), agregá tramos: cada tramo "
                                  "es una ubicación y el área muestra el total.", 13, color="texto2"))
            r = Fila()
            r.add_widget(Etiqueta("Tramos (opcional)", 14, True))
            r.add_widget(Boton("+ tramo", ancho=120, al_tocar=self._mas_tramo))
            f.add_widget(r)
            for k, (nid, txt) in enumerate(self.tramos_area):
                r = Fila()
                e = Campo(txt, mayus=True)
                e.bind(text=lambda w, t, k=k: self.tramos_area[k].__setitem__(1, t))
                r.add_widget(e)
                r.add_widget(Boton("×", ancho=44, al_tocar=lambda k=k: self._quitar_tramo(k)))
                f.add_widget(r)
            if self.editando and self._tiene_general:
                f.add_widget(Etiqueta(f"El avance que ya estaba en {self.editando['nombre']} sin tramo queda en "
                                      f"«{self.editando['nombre']} {core.NOMBRE_GENERAL}» para que lo repartas.", 12,
                                      color="texto2"))
        else:
            if not self.editando:
                r = Fila()
                r.add_widget(Etiqueta("Cantidad de niveles", 14, True))
                r.add_widget(Contador(self.n, 1, 80, al_cambiar=self._cambiar_n))
                f.add_widget(r)
            r = Fila()
            r.add_widget(Boton("+ Agregar sótano", al_tocar=self._mas_sotano))
            r.add_widget(Boton("+ Agregar azotea" if not self.editando else "+ Agregar nivel",
                               al_tocar=self._mas_azotea if not self.editando else self._mas_nivel))
            f.add_widget(r)
            f.add_widget(Etiqueta("Niveles (de abajo hacia arriba, nombres editables)", 12, color="texto2"))
            for k, (nid, txt) in enumerate(self.niveles):
                r = Fila()
                e = Campo(txt, mayus=True)
                e.bind(text=lambda w, t, k=k: self.niveles[k].__setitem__(1, t))
                r.add_widget(e)
                r.add_widget(Boton("×", ancho=44, al_tocar=lambda k=k: self._quitar(k)))
                f.add_widget(r)
        f.add_widget(Espacio(8))
        if self.editando:
            r = Fila()
            r.add_widget(Boton("Cancelar", al_tocar=self.cancelar))
            r.add_widget(Boton("Guardar cambios", primario=True, al_tocar=self.guardar_edicion))
            f.add_widget(r)
        else:
            f.add_widget(Boton("Crear", primario=True, al_tocar=self.crear))

    def _mas_tramo(self):
        self.tramos_area.append([None, f"TRAMO {len(self.tramos_area) + 1}"])
        self._form()

    def _quitar_tramo(self, k):
        self.tramos_area.pop(k)
        self._form()

    def nuevo_tramo(self, e):
        def ok(v):
            try:
                self.p.agregar_subdivision(e["id"], v["nombre"])
            except core.ErrorCtrlP as ex:
                ui.info("Nuevo tramo", str(ex))
                return
            self.app.guardar()
            self.refrescar()
        ui.formulario("Nuevo tramo", f"Subdivisión de {e['nombre']}. Cada tramo es una ubicación (contractual, "
                      "registro, planos e informes) y el área muestra el total.",
                      [("nombre", "Nombre del tramo", False, f"TRAMO {self._n_tramos(e) + 1}", True)],
                      ["Cancelar", "Agregar tramo"], ok)

    def _n_tramos(self, e):
        return sum(1 for n in self.p.niveles_de(e["id"]) if n["nombre"] != core.NIVEL_UNICO)

    def _cambiar_n(self, v):
        self.n = v
        self._regenerar()

    def _regenerar(self):
        sot = [t for _, t in self.niveles if t.startswith("SÓTANO")]
        az = [t for _, t in self.niveles if t.startswith("AZOTEA")]
        self.niveles = [[None, s] for s in sot] + [[None, f"NIVEL {k}"] for k in range(1, self.n + 1)] + \
                       [[None, a] for a in az]
        self._form()

    def _mas_sotano(self):
        sot = [t for _, t in self.niveles if t.startswith("SÓTANO")]
        if len(sot) == 1 and sot[0] == "SÓTANO":
            for x in self.niveles:
                if x[1] == "SÓTANO":
                    x[1] = "SÓTANO 1"
            self.niveles.insert(0, [None, "SÓTANO 2"])
        elif sot:
            self.niveles.insert(0, [None, f"SÓTANO {len(sot) + 1}"])
        else:
            self.niveles.insert(0, [None, "SÓTANO"])
        self._form()

    def _mas_azotea(self):
        if not any(t.startswith("AZOTEA") for _, t in self.niveles):
            self.niveles.append([None, "AZOTEA"])
            self._form()

    def _mas_nivel(self):
        n = sum(1 for _, t in self.niveles if t.startswith("NIVEL")) + 1
        pos = next((k for k, (_, t) in enumerate(self.niveles) if t.startswith("AZOTEA")), len(self.niveles))
        self.niveles.insert(pos, [None, f"NIVEL {n}"])
        self._form()

    def _quitar(self, k):
        self.niveles.pop(k)
        self.n = max(1, sum(1 for _, t in self.niveles if t.startswith("NIVEL")))
        self._form()

    def crear(self):
        if self.p.solo_agregar:
            ui.info("Solo agregar avance", "En este archivo no se pueden modificar las ubicaciones.")
            return
        try:
            es_area = self.tipo != "Nuevo edificio"
            self.p.crear_edificio(self.e_nombre.text, [t for _, t in self.niveles], es_area=es_area,
                                  tramos=[t for _, t in self.tramos_area] if es_area else None)
        except core.ErrorCtrlP as e:
            ui.info("Ubicaciones", str(e))
            return
        self.app.guardar()
        self._nombre = ""
        self.niveles = []
        self.tramos_area = []
        self._regenerar()
        self.refrescar()

    def editar(self, e):
        self.editando = e
        self._nombre = e["nombre"]
        nvs = self.p.niveles_de(e["id"])
        self._tiene_general = False
        if e["es_area"]:
            # en un area solo se editan los tramos; la ubicacion general queda aparte
            self._tiene_general = any(n["nombre"] == core.NIVEL_UNICO for n in nvs) and len(nvs) > 1
            self.tramos_area = [[n["id"], n["nombre"]] for n in nvs if n["nombre"] != core.NIVEL_UNICO]
            self.niveles = []
        else:
            self.niveles = [[n["id"], n["nombre"]] for n in nvs]
        self._form()

    def cancelar(self):
        self.editando = None
        self._nombre = ""
        self.niveles = []
        self.tramos_area = []
        self._regenerar()

    def guardar_edicion(self):
        try:
            self.p.renombrar_edificio(self.editando["id"], self.e_nombre.text)
            lista = self.tramos_area if self.editando["es_area"] else self.niveles
            self.p.guardar_niveles(self.editando["id"], [(i, t) for i, t in lista])
        except core.ErrorCtrlP as e:
            ui.info("Ubicaciones", str(e))
            return
        self.app.guardar()
        self.cancelar()
        self.refrescar()

    def eliminar(self, e):
        def si(ok):
            if not ok:
                return
            try:
                self.p.eliminar_edificio(e["id"])
            except core.ErrorCtrlP as ex:
                ui.info("Ubicaciones", str(ex))
                return
            self.app.guardar()
            self.refrescar()
        ui.preguntar("Eliminar", f"¿Eliminar {e['nombre']}?", si, si="Eliminar")

    def refrescar(self):
        self.lista.clear_widgets()
        if not self.p:
            return
        self._proy_cargado = self.p
        self._rev_cargada = self.p.rev
        eds = self.p.edificios()
        edif = [e for e in eds if not e["es_area"]]
        areas = [e for e in eds if e["es_area"]]
        nniv = sum(len(self.p.niveles_de(e["id"])) for e in edif)
        self.lista.add_widget(Etiqueta(f"Edificios  ·  {len(edif)} edificios, {nniv} niveles", 16, True))
        if not edif:
            self.lista.add_widget(Etiqueta("Todavía no hay edificios. Creá el primero con el formulario de la derecha.",
                                           13, color="texto2"))
        for e in edif + [None] + areas:
            if e is None:
                self.lista.add_widget(Etiqueta("Áreas sin nivel", 16, True))
                continue
            t = Tarjeta(relleno=16, espacio=6)
            cab = Fila(alto=40)
            cab.add_widget(Etiqueta(e["nombre"], 18, True))
            if not self.p.solo_agregar:
                cab.add_widget(Boton("Editar", ancho=90, alto=38, al_tocar=lambda e=e: self.editar(e)))
                cab.add_widget(Boton("Eliminar", ancho=100, alto=38, al_tocar=lambda e=e: self.eliminar(e)))
            t.add_widget(cab)
            niv = self.p.niveles_de(e["id"])
            if e["es_area"] and self.p.area_simple(e, niv):
                r = Fila(alto=40)
                r.add_widget(Etiqueta("Una sola ubicación", 13, color="texto2"))
                if not self.p.solo_agregar:
                    r.add_widget(Boton("+ tramo", ancho=110, alto=38, al_tocar=lambda e=e: self.nuevo_tramo(e)))
                t.add_widget(r)
            elif e["es_area"]:
                ntr = sum(1 for n in niv if n["nombre"] != core.NIVEL_UNICO)
                r = Fila(alto=40)
                r.add_widget(Etiqueta(f"{ntr} tramo" + ("" if ntr == 1 else "s"), 13, color="texto2"))
                if not self.p.solo_agregar:
                    r.add_widget(Boton("+ tramo", ancho=110, alto=38, al_tocar=lambda e=e: self.nuevo_tramo(e)))
                t.add_widget(r)
                t.add_widget(Flujo([Chip(core.nombre_nivel(e, n)) for n in niv]))
            else:
                t.add_widget(Etiqueta(f"{len(niv)} niveles", 13, color="texto2"))
                t.add_widget(Flujo([Chip(n["nombre"]) for n in niv]))
            self.lista.add_widget(t)


# =========================================================================
#  Apariencia
# =========================================================================
class PaginaApariencia(Pagina):
    clave = "apariencia"
    titulo = "Apariencia"
    subtitulo = "Tema de colores y carpeta de documentos."

    def refrescar(self):
        self.cuerpo.clear_widgets()
        col = Columna(espacio=14)
        self.cuerpo.add_widget(Desplazable(col))
        t = Tarjeta()
        t.add_widget(Etiqueta("Tema", 16, True))
        f = Fila(alto=150, espacio=16)
        actual = self.app.cfg.get("apariencia", "Automático")
        for m in ("Claro", "Oscuro", "Automático"):
            c = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(170), spacing=dp(6))
            img = ui.imagen_kivy(dibujos.miniatura_tema(m, 192, 128), None)
            img.size = (dp(150), dp(100))
            anc = AnchorLayout(size_hint_y=None, height=dp(104))
            anc.add_widget(img)
            c.add_widget(anc)
            b = Boton(m + ("  ✓" if m == actual else ""), primario=(m == actual), al_tocar=lambda m=m: self.app.cambiar_apariencia(m))
            c.add_widget(b)
            f.add_widget(c)
        f.add_widget(Widget())
        t.add_widget(f)
        t.add_widget(Etiqueta("Automático sigue el modo claro u oscuro de la tablet.", 12, color="texto2"))
        col.add_widget(t)
        t = Tarjeta()
        t.add_widget(Etiqueta("Carpeta de documentos", 16, True))
        t.fila(ui.carpeta_docs(self.app.cfg), Boton("Cambiar…", ancho=140, al_tocar=self.cambiar_carpeta),
               "Donde se abren y guardan por defecto los proyectos, copias y exportaciones.")
        if self.app.cfg.get("carpeta_docs"):
            t.fila("Volver a la carpeta por defecto", Boton("Documentos/CTRL-P DOC", ancho=240, al_tocar=self.por_defecto))
        col.add_widget(t)
        import novedades
        t = Tarjeta()
        t.add_widget(Etiqueta("Actualizaciones", 16, True))
        t.fila(f"Ctrl-P {novedades.VERSION_INTERNA}",
               Boton("Buscar actualizaciones", primario=True, ancho=240,
                     al_tocar=lambda: self.app.buscar_actualizacion(silencioso=False)),
               "Al abrir, Ctrl-P revisa solo si hay una versión nueva. Los proyectos y la sesión de Google se "
               "mantienen al actualizar.")
        t.fila("Novedades", Boton("Ver novedades", ancho=180, al_tocar=self.ver_novedades))
        col.add_widget(t)

    def ver_novedades(self):
        import novedades
        ui.info("Novedades", "\n\n".join(f"{v}\n" + "\n".join("• " + c for c in cs) for v, cs in novedades.CAMBIOS))

    def cambiar_carpeta(self):
        def elegida(r):
            self.app.cfg = core.config_poner(carpeta_docs=r)
            self.refrescar()
        ui.elegir_carpeta("Carpeta de documentos", ui.carpeta_docs(self.app.cfg), elegida)

    def por_defecto(self):
        self.app.cfg = core.config_poner(carpeta_docs="")
        self.refrescar()


def clases():
    from pag_datos import PaginaDatosFijos
    from pag_registro import PaginaRegistro
    from pag_informes import PaginaInformes
    from pag_planos import PaginaPlanos
    from pag_enlinea import PaginaEnLinea
    return [PaginaProyecto, PaginaPresupuesto, PaginaUbicaciones, PaginaDatosFijos, PaginaRegistro, PaginaPlanos,
            PaginaInformes, PaginaEnLinea, PaginaApariencia]
