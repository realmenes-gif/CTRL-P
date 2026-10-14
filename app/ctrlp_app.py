"""
Ctrl-P v1 para Android (tablet)
===============================
Misma logica y mismo archivo .ctrlp que la version de escritorio: los modulos ctrlp_core.py
y ctrlp_excel.py son los mismos. Esta parte es solo la interfaz tactil.
"""

import os
import sys
import traceback

os.environ.setdefault("KIVY_LOG_MODE", "PYTHON")

from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

import ctrlp_core as core
import dibujos
import ui_k as ui
from ui_k import (Boton, Campo, Columna, Desplazable, Espacio, Etiqueta, Fila, Tarjeta, fmt, rgba)

VERSION = "v1"
NOMBRE_MASTER = "Registro_Semanal"
NOMBRE_ACTUALIZACION = "actualizacion_semanal"
PAGINAS_MANUALES = ("proyecto", "presupuesto", "ubicaciones", "informes")
RUTA_LOG = None
ARRANQUE = lambda texto: None  # main.py lo reemplaza para dejar rastro del arranque


def ruta_log():
    """errores.log en la carpeta de documentos (Documentos/CTRL-P DOC), donde se puede abrir y mandar.
    Si todavia no hay permiso de archivos, queda en la carpeta interna de la app."""
    app = App.get_running_app()
    try:
        carpeta = ui.carpeta_docs(getattr(app, "cfg", None))
        prueba = os.path.join(carpeta, "errores.log")
        with open(prueba, "a", encoding="utf-8"):
            pass
        return prueba
    except Exception:
        return RUTA_LOG


def registrar_error(titulo, texto):
    try:
        ARRANQUE(f"{titulo}\n{texto}")
    except Exception:
        pass
    ruta = ruta_log()
    try:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"\n===== {core.ahora()} · {titulo}\n{texto}\n")
    except Exception:
        pass
    return ruta


class _Errores(ExceptionHandler):
    """Un error en una accion no cierra la app: se registra y se avisa."""

    def handle_exception(self, inst):
        if isinstance(inst, KeyboardInterrupt):
            return ExceptionManager.RAISE
        detalle = "".join(traceback.format_exception(type(inst), inst, inst.__traceback__))
        ruta = registrar_error("Error en pantalla", detalle)
        # Las ultimas lineas del detalle van en el aviso: con una captura de pantalla alcanza.
        donde = []
        for fr in traceback.extract_tb(inst.__traceback__)[-3:]:
            donde.append(f"{os.path.basename(fr.filename)}:{fr.lineno} {fr.name}")
        app = App.get_running_app()
        if app is not None and not getattr(app, "_mostrando_error", False):
            app._mostrando_error = True

            def listo():
                app._mostrando_error = False
            try:
                ui.info("Ocurrió un error", f"Algo falló en esta acción ({type(inst).__name__}: {inst}). La app sigue "
                        "abierta y lo que ya estaba guardado está a salvo.\n\nDónde: " + " → ".join(donde) +
                        f"\n\nEl detalle quedó en:\n{ruta}", listo)
            except Exception:
                app._mostrando_error = False
        return ExceptionManager.PASS


# =========================================================================
#  Barra lateral
# =========================================================================
class ItemLateral(ButtonBehavior, BoxLayout):
    def __init__(self, clave, titulo, color, activo, seleccionado, compacto, extra="", **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(48), padding=[dp(12), 0, dp(10), 0],
                         spacing=dp(12), **kw)
        self.clave = clave
        if seleccionado:
            with self.canvas.before:
                Color(*rgba("lat_sel"))
                self._r = RoundedRectangle(radius=[dp(10)])
            self.bind(pos=lambda *_: setattr(self._r, "pos", self.pos), size=lambda *_: setattr(self._r, "size", self.size))
        anc = AnchorLayout(size_hint_x=None, width=dp(30))
        anc.add_widget(ui.imagen_kivy(dibujos.icono(clave, color, 56), 30))
        self.add_widget(anc)
        if not compacto:
            self.add_widget(Label(text=titulo, font_size=sp(15), bold=seleccionado, font_name=ui.FAM, halign="left",
                                  valign="middle", color=rgba("texto") if activo else rgba("texto2"),
                                  text_size=(dp(150), None)))
            if extra:
                self.add_widget(Label(text=extra, font_size=sp(12), color=rgba("texto2"), font_name=ui.FAM,
                                      size_hint_x=None, width=dp(30)))


class Lateral(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", size_hint_x=None, padding=[dp(14), dp(18), dp(14), dp(14)],
                         spacing=dp(6), **kw)
        self.app = app
        with self.canvas.before:
            Color(*rgba("lat_ini"))
            self._r = Rectangle()
            Color(*rgba("borde"))
            self._l = Line(width=1)
        self.bind(pos=self._fondo, size=self._fondo)

    def _fondo(self, *_):
        self._r.pos, self._r.size = self.pos, self.size
        self._l.points = [self.right - 1, self.y, self.right - 1, self.top]

    def dibujar(self):
        app = self.app
        self.clear_widgets()
        comp = app.lat_compacto
        self.width = dp(84) if comp else dp(262)
        if comp:
            self.add_widget(Etiqueta("C-P", 18, True, alinear="center"))
        else:
            t = Fila(alto=34, espacio=6)
            t.add_widget(Label(text="Ctrl-P", font_size=sp(24), bold=True, color=rgba("texto"), font_name=ui.FAM,
                               size_hint_x=None, width=dp(84), halign="left", text_size=(dp(84), None)))
            t.add_widget(Label(text=VERSION, font_size=sp(13), bold=True, color=rgba("acento"), font_name=ui.FAM,
                               size_hint_x=None, width=dp(26)))
            t.add_widget(Widget())
            self.add_widget(t)
            self.add_widget(Etiqueta("Control de avance detallado de obra", 11, color="texto2"))
        self.add_widget(Espacio(6))
        p = app.p
        if p and not comp:
            card = Tarjeta(relleno=12, espacio=2)
            card.add_widget(Etiqueta("Proyecto", 10, color="texto2"))
            card.add_widget(Etiqueta(p.nombre, 13, True, una_linea=True))
            card.add_widget(Etiqueta(f"Presupuesto V{p.version_presupuesto} · {fmt(p.total_presupuesto())}", 10,
                                     color="texto2", una_linea=True))
            self.add_widget(card)
        if p:
            f = Fila(alto=44, espacio=8)
            txt = getattr(app, "_txt_guardado", "")
            bg = Boton("✓" if (comp and txt.startswith("✓")) else (txt or "Guardar"), primario=True,
                       al_tocar=app.guardar_todo, tam=13 if not comp else 11)
            if txt.startswith("✓"):
                bg._c_normal = rgba("#16A34A")
                bg._estado()
            elif txt:
                bg._c_normal = rgba("rojo")
                bg._estado()
            br = Boton("↻" if comp else "↻ Refrescar", al_tocar=app.refrescar_actual, tam=13)
            if app.pagina_desactualizada():
                br._c_normal = rgba("#F59E0B")
                br.color = [1, 1, 1, 1]
                br._estado()
            if comp:
                caja = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(96), spacing=dp(8))
                caja.add_widget(bg)
                caja.add_widget(br)
                self.add_widget(caja)
            else:
                f.add_widget(bg)
                f.add_widget(br)
                self.add_widget(f)
        self.add_widget(Espacio(8))
        pend = len(p.descuadres()) if p else 0
        grupo_ant = 0
        for clave, titulo, color, grupo in dibujos.ICONOS:
            if grupo != grupo_ant:
                self.add_widget(ui.Separador())
                grupo_ant = grupo
            activo = p is not None or clave in ("proyecto", "apariencia")
            it = ItemLateral(clave, titulo, color, activo, clave == app.pagina, comp,
                             extra=(f"● {pend}" if clave == "datos" and pend else ""))
            it.bind(on_release=lambda w: app.clic_pagina(w.clave))
            self.add_widget(it)
        self.add_widget(Widget())
        if app.usuario:
            u = ItemUsuario(app, comp)
            self.add_widget(u)


class ItemUsuario(ButtonBehavior, BoxLayout):
    def __init__(self, app, comp, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(52), spacing=dp(10), **kw)
        if core.es_admin(app.usuario):
            img = ui.imagen_kivy(dibujos.husky(80), 40)
        else:
            ini = "".join(x[0] for x in app.usuario.split(" - ")[0].split()[:2])[:2]
            img = Label(text=ini, bold=True, font_size=sp(14), color=[1, 1, 1, 1], size_hint=(None, None),
                        size=(dp(40), dp(40)), font_name=ui.FAM)
            with img.canvas.before:
                Color(*rgba("acento"))
                from kivy.graphics import Ellipse
                e = Ellipse(pos=img.pos, size=img.size)
            img.bind(pos=lambda *_: setattr(e, "pos", img.pos), size=lambda *_: setattr(e, "size", img.size))
        anc = AnchorLayout(size_hint_x=None, width=dp(44))
        anc.add_widget(img)
        self.add_widget(anc)
        if not comp:
            col = BoxLayout(orientation="vertical")
            col.add_widget(Label(text=app.usuario, font_size=sp(12), bold=True, color=rgba("texto"), font_name=ui.FAM,
                                 halign="left", valign="bottom", shorten=True, text_size=(dp(180), dp(24))))
            if not app.p:
                sub = "Sin proyecto abierto"
            elif app.p.version_trabajo in ("", "creación"):
                sub = "Proyecto recién creado"
            else:
                sub = f"Guardando en {os.path.basename(app.p.ruta)}"
            col.add_widget(Label(text=sub, font_size=sp(10), color=rgba("texto2"), font_name=ui.FAM, halign="left",
                                 valign="top", shorten=True, text_size=(dp(180), dp(22))))
            self.add_widget(col)
        self.bind(on_release=lambda *_: app.dialogo_usuarios())


# =========================================================================
#  Login
# =========================================================================
class Login(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="horizontal", **kw)
        self.app = app
        izq = BoxLayout(orientation="vertical", size_hint_x=None, width=min(dp(460), Window.width * 0.42),
                        padding=[dp(40), dp(50), dp(40), dp(30)], spacing=dp(12))
        with izq.canvas.before:
            Color(*rgba("lat_ini"))
            r = Rectangle()
        izq.bind(pos=lambda *_: setattr(r, "pos", izq.pos), size=lambda *_: setattr(r, "size", izq.size))
        t = Fila(alto=60)
        t.add_widget(Widget())
        t.add_widget(Label(text="Ctrl-P", font_size=sp(44), bold=True, color=rgba("texto"), font_name=ui.FAM,
                           size_hint_x=None, width=dp(150)))
        t.add_widget(Label(text=VERSION, font_size=sp(18), bold=True, color=rgba("acento"), font_name=ui.FAM,
                           size_hint_x=None, width=dp(30)))
        t.add_widget(Widget())
        izq.add_widget(t)
        anc = AnchorLayout(size_hint_y=None, height=dp(200))
        anc.add_widget(ui.imagen_kivy(dibujos.logo(400), 190))
        izq.add_widget(anc)
        izq.add_widget(Etiqueta("Control de avance detallado de obra", 15, color="texto2", alinear="center"))
        rec = [r for r in app.cfg.get("recientes", []) if os.path.isfile(r.get("ruta", ""))][:3]
        if rec:
            izq.add_widget(Espacio(14))
            izq.add_widget(Etiqueta("Proyectos recientes", 12, True, color="texto2"))
            for rr in rec:
                c = TarjetaToque(relleno=12, espacio=2)
                c.add_widget(Etiqueta(rr.get("nombre", "")[:40], 14, True, una_linea=True))
                c.add_widget(Etiqueta(os.path.basename(rr["ruta"]) + "  ·  entrar y abrir", 11, color="texto2",
                                      una_linea=True))
                c.bind(on_release=lambda w, ruta=rr["ruta"]: self.entrar(ruta))
                izq.add_widget(c)
        izq.add_widget(Widget())
        self.add_widget(izq)
        der = AnchorLayout()
        f = Tarjeta(relleno=30, espacio=8, size_hint_x=None, width=dp(440))
        cab = Fila(alto=56)
        cab.add_widget(Etiqueta("Ingresar", 24, True))
        self.caja_husky = AnchorLayout(size_hint_x=None, width=dp(56))
        cab.add_widget(self.caja_husky)
        f.add_widget(cab)
        f.add_widget(Etiqueta("Tu nombre queda registrado en cada cambio que hagas.", 13, color="texto2"))
        f.add_widget(Espacio(6))
        f.add_widget(Etiqueta("Nombre", 14, True))
        self.e_nom = Campo(app.cfg.get("nombre", ""), mayus=True, alto=50, tam=17, negrita=True,
                           al_cambiar=lambda *_: self.actualizar(), al_enter=self.entrar)
        f.add_widget(self.e_nom)
        f.add_widget(Etiqueta("Empresa", 14, True))
        self.e_emp = Campo(app.cfg.get("empresa", ""), mayus=True, alto=50, tam=17, negrita=True,
                           al_cambiar=lambda *_: self.actualizar(), al_enter=self.entrar)
        f.add_widget(self.e_emp)
        self.caja_clave = Columna(espacio=6)
        f.add_widget(self.caja_clave)
        self.e_clave = Campo("", clave=True, alto=50, tam=17, al_enter=self.entrar)
        self.l_vista = Etiqueta("", 13, color="texto2")
        f.add_widget(self.l_vista)
        self.l_err = Etiqueta("", 13, color="rojo")
        f.add_widget(self.l_err)
        f.add_widget(Boton("Entrar", primario=True, alto=52, tam=16, al_tocar=self.entrar))
        f.add_widget(Boton("Crear usuario con contraseña", plano=True, alto=40, tam=13, al_tocar=self.crear_usuario))
        der.add_widget(f)
        self.add_widget(der)
        self.actualizar()

    def actualizar(self):
        n, e = core.mayus(self.e_nom.text), core.mayus(self.e_emp.text)
        self.l_vista.text = f"Se mostrará como  {n} - {e}" if n and e else ""
        req = core.requiere_clave(n, e)
        if req and not self.caja_clave.children:
            self.caja_clave.add_widget(Etiqueta("Contraseña", 14, True))
            self.caja_clave.add_widget(self.e_clave)
            self.caja_clave.add_widget(Etiqueta("Este usuario está protegido con contraseña.", 12, color="texto2"))
        elif not req and self.caja_clave.children:
            self.caja_clave.clear_widgets()
            self.e_clave.text = ""
        self.caja_husky.clear_widgets()
        if n and e and core.es_admin(f"{n} - {e}"):
            self.caja_husky.add_widget(ui.imagen_kivy(dibujos.husky(110), 52))

    def crear_usuario(self):
        def validar(v):
            if v["clave"] != v["clave2"]:
                return "Las contraseñas no coinciden."
            try:
                core.registrar_usuario(v["nombre"], v["empresa"], v["clave"])
            except core.ErrorCtrlP as ex:
                return str(ex)
            return ""

        def listo(r):
            self.e_nom.text = core.mayus(r["nombre"])
            self.e_emp.text = core.mayus(r["empresa"])
            self.actualizar()
            self.e_clave.text = r["clave"]
            self.l_err.text = ""
            ui.info("Usuario creado", f"Se creó {core.mayus(r['nombre'])} - {core.mayus(r['empresa'])}.\n\n"
                    "Al abrir un proyecto, tu usuario queda guardado también dentro del archivo, así te reconoce "
                    "en cualquier equipo.")
        ui.formulario("Crear usuario", "Con contraseña, nadie más puede entrar con tu nombre. Los nombres no se repiten.",
                      [("nombre", "Nombre", False, core.mayus(self.e_nom.text), True),
                       ("empresa", "Empresa", False, core.mayus(self.e_emp.text), True),
                       ("clave", "Contraseña (mínimo 4 caracteres)", True, ""),
                       ("clave2", "Repetir contraseña", True, "")],
                      ["Cancelar", "Crear usuario"], listo, validar=validar)

    def entrar(self, ruta=None):
        try:
            u = core.verificar_usuario(self.e_nom.text, self.e_emp.text, self.e_clave.text)
        except core.ErrorCtrlP as e:
            self.l_err.text = str(e)
            return
        app = self.app
        app.cfg = core.config_poner(nombre=core.mayus(self.e_nom.text), empresa=core.mayus(self.e_emp.text))
        app.con_clave = core.requiere_clave(self.e_nom.text, self.e_emp.text)
        app.llave = core.llave_admin(self.e_clave.text) if core.es_admin(u) else None
        app.entrar(u, ruta if isinstance(ruta, str) else None)


class TarjetaToque(ButtonBehavior, Tarjeta):
    pass


# =========================================================================
#  Aplicacion
# =========================================================================
class CtrlPApp(App):
    title = f"Ctrl-P {VERSION}"

    def build(self):
        global RUTA_LOG
        ARRANQUE("build: fuentes")
        ui.registrar_fuentes()
        ARRANQUE("build: cifrado")
        import cifrado
        cifrado.instalar(core)
        ARRANQUE(f"build: config en {core.carpeta_config()}")
        self.cfg = core.leer_config()
        RUTA_LOG = os.path.join(core.carpeta_config(), "errores.log")
        ExceptionManager.add_handler(_Errores())
        ARRANQUE("build: tema y ventana")
        self.usuario = None
        self.con_clave = False
        self.llave = None
        self.p = None
        self.pagina = None
        self.paginas = {}
        self.pila_deshacer = []
        self.lat_compacto = False
        self._aplicar_tema()
        self.raiz = FloatLayout()
        Window.bind(on_keyboard=self._tecla, size=lambda *_: Clock.schedule_once(self._revisar_ancho, 0.2))
        Window.softinput_mode = "below_target"
        Clock.schedule_once(lambda *_: self._login_inicial(), 0)
        Clock.schedule_once(lambda *_: self.pedir_permisos(), 0.5)
        ARRANQUE("build: listo")
        return self.raiz

    def _login_inicial(self):
        ARRANQUE("mostrando inicio de sesion")
        self.mostrar_login()
        ARRANQUE("inicio de sesion en pantalla")

    # ------------------------------------------------------------ tema
    def _aplicar_tema(self):
        modo = self.cfg.get("apariencia", "Automático")
        osc = {"Claro": False, "Oscuro": True}.get(modo, ui.sistema_oscuro())
        ui.poner_oscuro(osc)
        Window.clearcolor = rgba("fondo")

    def cambiar_apariencia(self, modo):
        self.cfg = core.config_poner(apariencia=modo)
        self._aplicar_tema()
        self.reconstruir()

    def reconstruir(self):
        """Vuelve a armar todo con los colores actuales (sin perder el proyecto abierto)."""
        if self.usuario is None:
            self.mostrar_login()
            return
        actual = self.pagina or "proyecto"
        self.construir()
        self.pagina = None
        self.ir(actual, forzar=True)

    # ------------------------------------------------------------ permisos (Android 11+)
    def pedir_permisos(self):
        if not ui.ANDROID:
            return
        try:
            from jnius import autoclass
            Environment = autoclass("android.os.Environment")
            if Environment.isExternalStorageManager():
                return
        except Exception:
            return

        def abrir(si):
            if not si:
                return
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Settings = autoclass("android.provider.Settings")
                Uri = autoclass("android.net.Uri")
                act = autoclass("org.kivy.android.PythonActivity").mActivity
                it = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                            Uri.parse("package:" + act.getPackageName()))
                act.startActivity(it)
            except Exception:
                pass
        ui.preguntar("Permiso de archivos",
                     "Ctrl-P necesita acceso a los archivos de la tablet para abrir y guardar los proyectos .ctrlp en "
                     "Documentos/CTRL-P DOC (igual que en la computadora).\n\nEn la pantalla que se abre, activá "
                     "«Permitir acceso para administrar todos los archivos» y volvé a Ctrl-P.", abrir, si="Dar permiso",
                     no="Ahora no")

    # ------------------------------------------------------------ login
    def mostrar_login(self):
        self.raiz.clear_widgets()
        self.raiz.add_widget(Login(self))

    def entrar(self, usuario, ruta=None):
        self.usuario = usuario
        self.construir()
        self.ir("proyecto")
        if ruta and os.path.isfile(ruta):
            Clock.schedule_once(lambda *_: self.abrir_proyecto(ruta), 0.2)

    def construir(self):
        import paginas
        self.raiz.clear_widgets()
        caja = BoxLayout(orientation="horizontal")
        self.lat_compacto = Window.width / (dp(1)) < 1180
        self.lateral = Lateral(self)
        caja.add_widget(self.lateral)
        self.contenido = BoxLayout()
        caja.add_widget(self.contenido)
        self.raiz.add_widget(caja)
        self.paginas = {cl.clave: cl(self) for cl in paginas.clases()}
        self.lateral.dibujar()

    def _revisar_ancho(self, *_):
        if not hasattr(self, "lateral"):
            return
        comp = Window.width / dp(1) < 1180
        if comp != self.lat_compacto:
            self.lat_compacto = comp
            self.lateral.dibujar()

    # ------------------------------------------------------------ navegacion
    def clic_pagina(self, clave):
        if self.p is None and clave not in ("proyecto", "apariencia"):
            ui.aviso("Primero abrí o creá un proyecto.")
            return
        self.ir(clave)

    def ir(self, clave, forzar=False):
        actual = self.paginas.get(self.pagina)

        def seguir():
            self.pagina = clave
            pg = self.paginas[clave]
            reusar = (not forzar and clave in PAGINAS_MANUALES and self.p is not None
                      and getattr(pg, "_proy_cargado", None) is self.p)
            if not reusar:
                pg.refrescar()
            self.contenido.clear_widgets()
            self.contenido.add_widget(pg)
            self.lateral.dibujar()
        if actual is not None and actual is not self.paginas.get(clave) and hasattr(actual, "antes_de_salir"):
            actual.antes_de_salir(seguir)
        else:
            seguir()

    def pagina_desactualizada(self):
        pg = self.paginas.get(self.pagina)
        return bool(self.p and self.pagina in PAGINAS_MANUALES and pg is not None
                    and getattr(pg, "_rev_cargada", None) != self.p.rev)

    def refrescar_actual(self):
        pg = self.paginas.get(self.pagina)
        if pg is None:
            return
        if self.pagina == "informes":
            pg.generar()
        else:
            pg.refrescar()
        self.lateral.dibujar()

    # ------------------------------------------------------------ guardar
    def guardar_todo(self):
        """Boton Guardar: guarda lo pendiente de la pantalla actual y el archivo .ctrlp (siempre el mismo)."""
        if not self.p:
            return
        pg = self.paginas.get(self.pagina)
        sin_guardar = False
        try:
            if hasattr(pg, "guardar_pendiente"):
                sin_guardar = not pg.guardar_pendiente()
        except Exception as ex:
            ui.info("Guardar", f"No se pudieron guardar los cambios de esta pantalla:\n{ex}")
            sin_guardar = True

        def marcar():
            import datetime as _dt
            self._txt_guardado = "Revisá datos" if sin_guardar else "✓ Guardado"
            self._hora_guardado = _dt.datetime.now().strftime("%H:%M")
            self.lateral.dibujar()
            Clock.unschedule(self._limpiar_guardado)
            Clock.schedule_once(self._limpiar_guardado, 3.5)
        if not self.p.solo_agregar and os.path.basename(self.p.ruta).lower() != (NOMBRE_MASTER + core.EXT).lower():
            def elegido(destino):
                try:
                    aviso = self.p.guardar_en(destino)
                except Exception as ex:
                    ui.info("No se pudo guardar", f"No se pudo crear el archivo master:\n{ex}")
                    return
                if aviso:
                    ui.info("Historial", aviso)
                pgp = self.paginas.get("proyecto")
                if pgp is not None:
                    pgp._proy_cargado = None
                marcar()

            def responder(k):
                if k == 1:
                    ui.guardar_archivo("Guardar archivo master", ui.carpeta_docs(self.cfg), f"{NOMBRE_MASTER}{core.EXT}",
                                       (core.EXT,), elegido)
                elif k == 0:
                    self.guardar()
                    marcar()
            ui.opciones("Archivo master",
                        f"Tu proyecto se guarda en «{os.path.basename(self.p.ruta)}». ¿Querés pasarlo a su archivo "
                        f"master «{NOMBRE_MASTER}{core.EXT}» (recomendado, como en la computadora)?",
                        ["Seguir en este archivo", "Elegir dónde guardar el master"], responder, primario=1)
            return
        self.guardar()
        marcar()

    def _limpiar_guardado(self, *_):
        self._txt_guardado = ""
        if hasattr(self, "lateral"):
            self.lateral.dibujar()

    def guardar(self):
        if not self.p:
            return
        try:
            aviso = self.p.guardar()
        except Exception as e:
            ui.info("No se pudo guardar", f"Ocurrió un error al guardar el proyecto:\n{e}")
            return
        if aviso:
            ui.info("Historial", aviso)
        if hasattr(self, "lateral"):
            self.lateral.dibujar()

    # ------------------------------------------------------------ proyecto
    def abrir_proyecto(self, ruta=None):
        if ruta is None:
            ui.elegir_archivo("Abrir proyecto", ui.carpeta_docs(self.cfg), (core.EXT,), self.abrir_proyecto)
            return
        carpeta = os.path.basename(os.path.dirname(os.path.abspath(ruta)))
        if carpeta.endswith(" - respaldos"):
            original = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(ruta))),
                                    carpeta[:-len(" - respaldos")] + core.EXT)
            hay = os.path.isfile(original)

            def resp(k):
                if k == 2:
                    self._abrir_paso2(original)
                elif k == 1:
                    self._abrir_paso2(ruta)
            ui.opciones("Es una copia de seguridad",
                        "Este archivo es una copia de seguridad (una foto del proyecto de ese día), no el proyecto con "
                        "el que trabajás.\n\nSi lo abrís y registrás, tu avance quedaría en la copia."
                        + (f"\n\nEl proyecto original está en:\n{original}" if hay else ""),
                        ["Cancelar", "Abrir la copia igual"] + (["Abrir el original"] if hay else []), resp,
                        primario=2 if hay else 0)
            return
        self._abrir_paso2(ruta)

    def _abrir_paso2(self, ruta):
        def seguir():
            carpeta = core.Proyecto.carpeta_respaldos(ruta)
            stem = os.path.splitext(os.path.basename(ruta))[0]
            hay_hoy = os.path.isdir(carpeta) and any(f.startswith(f"{stem}_{core.hoy_iso()}_") for f in os.listdir(carpeta))
            if hay_hoy:
                ui.opciones("Copia de seguridad",
                            "Ya abriste este proyecto hoy y existe una copia de seguridad del día.\n\n¿Querés crear una "
                            "nueva copia antes de seguir, o continuar con la copia de hoy?",
                            ["Seguir con la de hoy", "Crear nueva copia"], lambda k: self._abrir_paso3(ruta, k == 1),
                            primario=1)
            else:
                self._abrir_paso3(ruta, False)
        self.cerrar_proyecto(seguir)

    def _abrir_paso3(self, ruta, nueva_copia):
        try:
            p = core.Proyecto.abrir(ruta, self.usuario, lambda: nueva_copia)
        except core.ErrorCtrlP as e:
            ui.info("No se pudo abrir", str(e))
            return
        except Exception as e:
            ui.info("No se pudo abrir", f"No se pudo abrir el archivo:\n{e}")
            return
        if not self.con_clave and self.usuario in core.usuarios_registrados(p.usuarios_proyecto()):
            n, e = self.usuario.split(" - ", 1)

            def validar(v):
                try:
                    core.verificar_usuario(n, e, v["clave"], p.usuarios_proyecto())
                except core.ErrorCtrlP as ex:
                    return str(ex)
                return ""

            def ok(_):
                self.con_clave = True
                self._proyecto_listo(p)

            d = ui.formulario("Usuario protegido", f"En este proyecto, {self.usuario} tiene contraseña.",
                              [("clave", "Contraseña", True, "")], ["Cancelar", "Entrar"], ok, validar=validar)
            d.bind(on_dismiss=lambda *_: None if self.p is p else p.cerrar())
            return
        self._proyecto_listo(p)

    def _proyecto_listo(self, p):
        self.p = p
        try:
            self.p.sincronizar_usuarios()
        except Exception:
            pass
        for pg in self.paginas.values():
            if hasattr(pg, "al_cambiar_proyecto"):
                pg.al_cambiar_proyecto()
        self.ir("registro" if self.p.edificios() else "ubicaciones", forzar=True)
        if self.p.solo_agregar:
            ui.info("Copia para agregar avance",
                    "Este archivo fue exportado en modo «Solo agregar avance».\n\nPodés registrar avances nuevos, pero "
                    "no modificar registros anteriores, ubicaciones, datos fijos ni el presupuesto. Al terminar, "
                    "guardalo y devolvelo.")

    def cerrar_proyecto(self, seguir=None):
        if not self.p:
            if seguir:
                seguir()
            return
        pg = self.paginas.get(self.pagina)

        def cerrar():
            if self.p.sucio:
                self.guardar()
            self.p.cerrar()
            self.p = None
            self.pila_deshacer = []
            for pg2 in self.paginas.values():
                if hasattr(pg2, "al_cambiar_proyecto"):
                    pg2.al_cambiar_proyecto()
            if hasattr(self, "lateral"):
                self.lateral.dibujar()
            if seguir:
                seguir()
        if pg is not None and hasattr(pg, "antes_de_salir"):
            pg.antes_de_salir(cerrar)
        else:
            cerrar()

    def nuevo_proyecto(self):
        def elegido(ruta):
            import dialogos
            dialogos.AsistenteImportacion(self, ruta, modo="nuevo").open()
        ui.elegir_archivo("Elegí el Excel del presupuesto (una sola hoja)", ui.carpeta_docs(self.cfg),
                          (".xlsx", ".xlsm"), elegido)

    # ------------------------------------------------------------ deshacer (planos)
    def punto_deshacer(self, descripcion, datos_de=()):
        return (descripcion, self.p.instantanea(datos_de), self.p.rev)

    def confirmar_deshacer(self, ficha):
        desc, snap, rev0 = ficha
        if self.p.rev != rev0:
            self.pila_deshacer.append((desc, snap, self.p.rev))
            del self.pila_deshacer[:-30]

    def deshacer(self):
        if not self.pila_deshacer:
            return None, "No hay nada para deshacer."
        desc, snap, rev = self.pila_deshacer[-1]
        if self.p.rev != rev:
            self.pila_deshacer.clear()
            return None, ("Después de ese cambio se modificó el proyecto en otra parte (por ejemplo en Registro de "
                          "avance), así que ya no se puede deshacer desde aquí.")
        self.pila_deshacer.pop()
        self.p.restaurar(snap, desc)
        self.guardar()
        return desc, ""

    def dialogo_usuarios(self):
        import dialogos
        dialogos.DialogoUsuarios(self).open()

    # ------------------------------------------------------------ ciclo de vida Android
    def _tecla(self, window, key, *args):
        if key == 27:      # boton Atras
            if any(isinstance(w, ui.ModalView) for w in Window.children):
                for w in Window.children:
                    if isinstance(w, ui.ModalView) and not getattr(w, "_sin_atras", False):
                        w.dismiss()
                        break
                return True
            if self.pagina == "planos" and hasattr(self.paginas.get("planos"), "atras") and \
                    self.paginas["planos"].atras():
                return True
            ui.preguntar("Salir", "¿Cerrar Ctrl-P? Lo pendiente se guarda.", lambda si: si and self.salir(), si="Salir")
            return True
        return False

    def salir(self):
        self.cerrar_proyecto(self.stop)

    def on_pause(self):
        if self.p and self.p.sucio:
            try:
                self.p.guardar()
            except Exception:
                pass
        return True

    def on_resume(self):
        if self.cfg.get("apariencia", "Automático") == "Automático":
            antes = ui.oscuro()
            self._aplicar_tema()
            if antes != ui.oscuro():
                self.reconstruir()

    def on_stop(self):
        if self.p:
            try:
                if self.p.sucio:
                    self.p.guardar()
                self.p.cerrar()
            except Exception:
                pass


if __name__ == "__main__":
    CtrlPApp().run()
