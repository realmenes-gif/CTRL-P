"""
Ctrl-P Android - pagina «En línea» (mismo servidor de Google que la computadora).
En la tablet se trabaja siempre como usuario: los avances se envían y el administrador los aprueba en la
computadora. La clave del proyecto queda solo en memoria mientras la app está abierta (nunca en archivos).
"""

import os
import threading

from kivy.clock import Clock
from kivy.uix.widget import Widget

import ctrlp_core as core
import ctrlp_nube as nb
import ui_k as ui
from paginas import Pagina
from ui_k import Boton, Columna, Desplazable, Etiqueta, Fila, Tarjeta


# =========================================================================
#  Trabajo en segundo plano (internet) con ventanita de espera
# =========================================================================
class Red:
    """yield Red(texto, fn): corre fn() en un hilo; devuelve su resultado (o lanza su error) en el flujo."""

    def __init__(self, texto, fn, cancelar=None):
        self.texto, self.fn, self.cancelar = texto, fn, cancelar


class Espera(ui.Dialogo):
    def __init__(self, texto, cancelar=None):
        super().__init__("En línea", ancho=520)
        self._sin_atras = True                       # el boton Atras no la cierra a medio trabajo
        self.cuerpo.add_widget(Etiqueta(texto, 14, color="texto2"))
        self.puntos = Etiqueta("●", 18, True, color="acento")
        self.cuerpo.add_widget(self.puntos)
        self._n = 0
        self._ev = Clock.schedule_interval(self._latir, 0.4)
        if cancelar:
            self.botones(["Cancelar"], 0, lambda k: cancelar())
        else:
            self.pie.clear_widgets()

    def _latir(self, *_):
        self._n = self._n % 5 + 1
        self.puntos.text = "● " * self._n

    def cerrar(self):
        self._ev.cancel()
        self.dismiss()


def correr(flujo, al_fallar=None):
    """Ejecuta un flujo (generador). Cada yield es un Red(...) o una funcion f(seguir) que muestra un dialogo y
    llama seguir(valor) al responder. Los errores de internet se muestran y cortan el flujo."""
    def paso(valor=None, error=None):
        try:
            y = flujo.throw(error) if error is not None else flujo.send(valor)
        except StopIteration:
            return
        except nb.NecesitaSesion as e:
            ui.info("Google", str(e))
            if al_fallar:
                al_fallar()
            return
        except nb.ErrorNube as e:
            ui.info("En línea", str(e))
            if al_fallar:
                al_fallar()
            return
        except Exception as e:
            ui.info("En línea", f"Ocurrió un error: {e}")
            try:
                import traceback
                from ctrlp_app import registrar_error
                registrar_error("En línea", traceback.format_exc())
            except Exception:
                pass
            if al_fallar:
                al_fallar()
            return
        if isinstance(y, Red):
            dlg = Espera(y.texto, y.cancelar)
            dlg.open()
            res = {}

            def hilo():
                try:
                    res["v"] = y.fn()
                except BaseException as e:
                    res["e"] = e
                Clock.schedule_once(lambda *_: fin(), 0)

            def fin():
                dlg.cerrar()
                if "e" in res:
                    paso(error=res["e"])
                else:
                    paso(res.get("v"))
            threading.Thread(target=hilo, daemon=True).start()
        elif callable(y):
            y(lambda v=None: Clock.schedule_once(lambda *_: paso(v), 0))
        else:
            Clock.schedule_once(lambda *_: paso(y), 0)
    paso()


def pedir_clave(nombre, verif=""):
    """Para usar con yield: devuelve la clave escrita (o None si cancela)."""
    def mostrar(seguir):
        def validar(v):
            c = v["clave"].strip()
            if len(c) < 6:
                return "La clave debe tener al menos 6 caracteres."
            if verif and nb.clave_correcta(c, verif) is False:
                return "La clave del proyecto no es correcta."
            return ""
        respondio = {}

        def ok(v):
            respondio["si"] = True
            seguir(v["clave"].strip())
        d = ui.formulario("Clave del proyecto", (f"«{nombre}». " if nombre else "") +
                          "Escribí la clave del proyecto (te la da el administrador). No se guarda en la tablet.",
                          [("clave", "Clave del proyecto", True, "")], ["Cancelar", "Aceptar"], ok, validar=validar)
        d.bind(on_dismiss=lambda *_: None if respondio else seguir(None))
    return mostrar


def avisar(titulo, texto):
    """Para usar con yield: muestra el mensaje y sigue al aceptar."""
    return lambda seguir: ui.info(titulo, texto, al_cerrar=seguir)


# =========================================================================
#  Pagina
# =========================================================================
class PaginaEnLinea(Pagina):
    clave = "enlinea"
    titulo = "En línea"
    subtitulo = ("Trabajá el proyecto en línea con tu cuenta de Google. Tus avances se envían al administrador y "
                 "quedan pendientes (en naranja) hasta que los aprueba en la computadora.")

    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.lista = None
        self.yo = None
        self._auto = False

    def refrescar(self):
        self.cuerpo.clear_widgets()
        col = Columna(espacio=14)
        self.cuerpo.add_widget(Desplazable(col))
        if not nb.configurado():
            t = Tarjeta()
            t.add_widget(Etiqueta("Falta conectar Ctrl-P con Google", 16, True))
            t.add_widget(Etiqueta("El administrador crea el servidor de Google desde la computadora. Si te pasó los 3 "
                                  "datos, pegalos aquí. (Las próximas versiones de la app ya los traen puestos.)", 13,
                                  color="texto2"))
            f = Fila(alto=44)
            f.add_widget(Boton("Configurar…", primario=True, ancho=160, al_tocar=self.configurar))
            f.add_widget(Widget())
            t.add_widget(f)
            col.add_widget(t)
            return
        t = Tarjeta()
        if not nb.SESION.tiene_sesion():
            t.fila("Cuenta de Google", Boton("Iniciar sesión con Google", primario=True, ancho=250,
                                             al_tocar=self.iniciar_sesion),
                   "Se abre el navegador para elegir tu cuenta; al terminar volvé a Ctrl-P. Ctrl-P solo conoce tu "
                   "correo (nada de tu Gmail).")
            col.add_widget(t)
            return
        t.fila(f"Cuenta de Google: {nb.SESION.email or '(con sesión)'}",
               Boton("Cerrar sesión", ancho=150, al_tocar=self.cerrar_sesion),
               "Con esta cuenta te reconoce el administrador.")
        col.add_widget(t)
        if self.lista is None and not self._auto:
            self._auto = True
            Clock.schedule_once(lambda *_: self.cargar_lista(), 0.2)
        p = self.p
        if p is not None:
            v = nb.vinculo(p)
            t = Tarjeta()
            t.add_widget(Etiqueta("Proyecto abierto", 15, True))
            if v:
                pend = self.app.pendientes_nube
                t.fila(f"{p.nombre} · en línea",
                       Boton("Sincronizar ahora", primario=True, ancho=190, al_tocar=self.sincronizar),
                       f"Versión local v{v['version']}"
                       + (f" · {len(pend[0])} avances tuyos pendientes de aprobación" if pend and pend[0] else "")
                       + " · Al sincronizar: se envían tus cambios y recibís lo que el administrador aprobó.")
            else:
                t.fila(f"{p.nombre} · solo en esta tablet", None,
                       "Para trabajar en línea, abrí el proyecto desde la lista de abajo.")
            col.add_widget(t)
        col.add_widget(Etiqueta("Proyectos en línea", 15, True))
        t = Tarjeta()
        if self.lista is None:
            t.fila("Todavía no se consultó la lista.", Boton("Ver proyectos", ancho=160, al_tocar=self.cargar_lista))
        elif not self.lista:
            t.fila("No hay proyectos en línea.", Boton("Actualizar", ancho=130, al_tocar=self.cargar_lista),
                   "El administrador sube el proyecto desde la computadora.")
        else:
            for pr in self.lista:
                a = pr["acceso"]
                if a in ("admin", "aprobado"):
                    b = Boton("Abrir", primario=True, ancho=120, al_tocar=lambda pr=pr: self.abrir_en_linea(pr))
                    ayuda = f"v{pr['version']} · actualizado {pr.get('actualizado', '')}"
                elif a == "pendiente":
                    b = Etiqueta("Esperando aprobación", 12, color="texto2", ancho_fijo=180)
                    ayuda = "El administrador tiene que aceptar tu correo."
                else:
                    b = Boton("Pedir acceso", ancho=150, al_tocar=lambda pr=pr: self.pedir_acceso(pr))
                    ayuda = ("Rechazado: podés volver a pedirlo." if a == "rechazado" else
                             "Necesitás que el administrador acepte tu correo y la clave del proyecto.")
                t.fila(pr["nombre"], b, ayuda)
            t.fila("", Boton("Actualizar lista", ancho=170, al_tocar=self.cargar_lista))
        col.add_widget(t)

    # ------------------------------------------------------------ cuenta
    def configurar(self):
        cfg = core.leer_config()

        def ok(v):
            self.app.cfg = core.config_poner(nube_url=v["url"].strip(), nube_cliente=v["cliente"].strip(),
                                             nube_secreto=v["secreto"].strip())
            self.refrescar()
        ui.formulario("Conectar con Google", "Los 3 datos del servidor de Google (te los pasa el administrador).",
                      [("url", "URL de la aplicación web (Apps Script)", False, cfg.get("nube_url", "")),
                       ("cliente", "ID de cliente (OAuth)", False, cfg.get("nube_cliente", "")),
                       ("secreto", "Secreto del cliente", False, cfg.get("nube_secreto", ""))],
                      ["Cancelar", "Guardar"], ok,
                      validar=lambda v: "" if v["url"].strip().startswith("https://script.google.com/")
                      else "La URL debe empezar con https://script.google.com/")

    def iniciar_sesion(self):
        def flujo():
            yield Red("Se abrió el navegador: elegí tu cuenta de Google y aceptá. Después volvé a Ctrl-P.",
                      nb.SESION.iniciar_sesion, cancelar=nb.SESION.cancelar)
            self.lista = None
            self._auto = False
            self.refrescar()
        correr(flujo(), self.refrescar)

    def cerrar_sesion(self):
        def resp(si):
            if si:
                nb.SESION.cerrar_sesion()
                self.lista, self.yo = None, None
                self.refrescar()
        ui.preguntar("Cerrar sesión", "¿Cerrar la sesión de Google en esta tablet?", resp, si="Cerrar sesión")

    def _lista(self):
        r = yield Red("Consultando los proyectos en línea…", lambda: nb.llamar("proyectos"))
        self.lista = r["proyectos"]
        self.yo = {"email": r["email"], "admin": r["admin"]}
        nb.SESION.email = r["email"]
        return r

    def cargar_lista(self):
        def flujo():
            yield from self._lista()
            self.refrescar()
        correr(flujo(), self.refrescar)

    def pedir_acceso(self, pr):
        def flujo():
            yield Red("Pidiendo acceso…", lambda: nb.llamar("pedir_acceso", proyecto=pr["id"],
                                                             usuario=self.app.usuario or ""))
            yield avisar("Acceso pedido", "Listo. Cuando el administrador acepte tu correo, el proyecto se podrá abrir "
                                          "desde esta lista (pedile también la clave del proyecto).")
            yield from self._lista()
            self.refrescar()
        correr(flujo())

    def _clave(self, pid, nombre, verif):
        c = self.app.claves_nube.get(pid)
        if not c:
            c = yield pedir_clave(nombre, verif)
            if c:
                self.app.claves_nube[pid] = c
        return c

    # ------------------------------------------------------------ abrir desde la lista
    def abrir_en_linea(self, pr):
        def flujo():
            v0 = nb.vinculo(self.p) if self.p is not None else None
            if v0 and v0["proyecto"] == pr["id"]:
                yield avisar("En línea", "Ese proyecto ya está abierto. Usá «Sincronizar ahora».")
                return
            c = yield from self._clave(pr["id"], pr["nombre"], pr.get("verificador", ""))
            if not c:
                return
            nombre = "".join(ch for ch in pr["nombre"] if ch not in '\\/:*?"<>|').strip() or "Proyecto"
            ruta = os.path.join(nb.carpeta_en_linea(), f"{nombre}{core.EXT}")
            if os.path.isfile(ruta):
                try:
                    tmp = core.Proyecto(ruta, self.app.usuario)
                    ya = nb.vinculo(tmp)
                    tmp.cerrar()
                except Exception:
                    ya = None
                if ya and ya["proyecto"] == pr["id"] and os.path.isfile(nb.ruta_base(pr["id"])):
                    self.app.abrir_proyecto(ruta)           # ya lo tenías: se abre (y se sincroniza desde aquí)
                    return
                if not (ya and ya["proyecto"] == pr["id"]):
                    ruta = os.path.join(nb.carpeta_en_linea(), f"{nombre} ({pr['id'][:6]}){core.EXT}")
            r = yield Red("Bajando el proyecto…", lambda: nb.llamar("bajar", proyecto=pr["id"], timeout=180))
            try:
                datos = yield Red("Descifrando el proyecto…", lambda: nb.descifrar(nb.de_b64(r["datos"]), c))
            except nb.ClaveIncorrecta as e:
                self.app.claves_nube.pop(pr["id"], None)
                yield avisar("Clave", str(e))
                return
            with open(ruta, "wb") as f:
                f.write(datos)
            with open(nb.ruta_base(pr["id"]), "wb") as f:
                f.write(datos)
            tmp = core.Proyecto(ruta, self.app.usuario)
            nb.vincular(tmp, pr["id"], r["version"], "usuario", pr["nombre"])
            tmp.guardar()
            tmp.cerrar()
            self.app.abrir_proyecto(ruta)
        correr(flujo())

    # ------------------------------------------------------------ sincronizar (como usuario)
    def sincronizar(self):
        correr(self._sincronizar(), self.refrescar)

    def _reabrir(self, ruta, escribir):
        """Para usar con yield: cierra el proyecto, escribe los archivos y lo vuelve a abrir."""
        def hacer(seguir):
            def cerrado():
                escribir()
                self.app._abrir_paso3(ruta, False)
                Clock.schedule_once(lambda *_: seguir(self.app.p), 0.3)
            self.app.cerrar_proyecto(cerrado)
        return hacer

    def _sincronizar(self):
        p = self.p
        v = nb.vinculo(p) if p else None
        if not v:
            return
        lst = yield from self._lista()
        pr = next((x for x in lst["proyectos"] if x["id"] == v["proyecto"]), None)
        if pr is None:
            yield avisar("En línea", "Este proyecto ya no está en línea.")
            return
        if pr["acceso"] not in ("admin", "aprobado"):
            yield avisar("En línea", "Tu correo no tiene acceso aprobado a este proyecto.")
            return
        c = yield from self._clave(v["proyecto"], v["nombre"] or p.nombre, pr.get("verificador", ""))
        if not c:
            return
        pid = v["proyecto"]
        base_ruta = nb.ruta_base(pid)
        if not os.path.isfile(base_ruta):
            yield avisar("En línea", "Falta la copia base de este proyecto en la tablet. Abrilo de nuevo desde la lista "
                                     "de «Proyectos en línea».")
            return
        if p.sucio:
            self.app.guardar()
        me = yield Red("Consultando tus envíos…", lambda: nb.llamar("mis_envios", proyecto=pid, marcar_vistos=True))
        avisos = me.get("avisos", [])
        pendiente_srv = any(x["estado"] == "pendiente" for x in me.get("envios", []))
        mensajes = []
        # 1) traer lo aprobado (si no espera respuesta de un envio)
        if pr["version"] > v["version"] and not pendiente_srv:
            r = yield Red("Bajando la versión nueva…", lambda: nb.llamar("bajar", proyecto=pid, timeout=180))
            nuevo = yield Red("Descifrando…", lambda: nb.descifrar(nb.de_b64(r["datos"]), c))
            with open(base_ruta, "rb") as f:
                base_vieja = f.read()
            datos = nb.rebasar(p, base_vieja, nuevo, v["enviado_en"])
            ruta = p.ruta
            p.sucio = False
            usuario = self.app.usuario

            def escribir():
                with open(ruta, "wb") as f:
                    f.write(datos)
                with open(base_ruta, "wb") as f:
                    f.write(nuevo)
                tmp = core.Proyecto(ruta, usuario)
                nb.vincular(tmp, pid, r["version"], "usuario", v["nombre"])
                tmp.set_meta("nube_enviado_huella", "")
                tmp.guardar()
                tmp.cerrar()
            p = yield self._reabrir(ruta, escribir)
            if p is None:
                return
            v = nb.vinculo(p)
            mensajes.append(f"Recibiste la versión v{r['version']} con lo que aprobó el administrador.")
        # 2) enviar lo propio
        with open(base_ruta, "rb") as f:
            base = f.read()
        ids, imp = nb.pendientes_ids(p, base)
        self.app.pendientes_nube = (ids, {x["item"] for x in imp["nuevos"]} | {x["item"] for _l, x in imp["modificados"]})
        self.app._rev_pend = p.rev
        if nb.hay_cambios(imp):
            huella = nb.huella_cambios(imp)
            if huella != v["enviado_huella"] or not pendiente_srv:
                datos = nb.bytes_proyecto(p)
                rs = nb.resumen(imp)
                usuario = self.app.usuario or ""
                version = v["version"]
                yield Red("Enviando tus cambios…", lambda: nb.llamar(
                    "enviar", proyecto=pid, version_base=version, usuario=usuario, resumen=rs,
                    datos=nb.b64(nb.cifrar(datos, c)), timeout=180))
                p.set_meta("nube_enviado_en", core.ahora())
                p.set_meta("nube_enviado_huella", huella)
                self.app.guardar()
                mensajes.append(f"Se enviaron tus cambios ({rs['avances']} avances nuevos, {rs['modificados']} "
                                f"modificados, {rs['contractual']} contractuales, {rs['marcas']} marcas). Quedan "
                                "pendientes de aprobación.")
            else:
                mensajes.append("Tus cambios ya se habían enviado: siguen pendientes de aprobación.")
        elif pendiente_srv:
            mensajes.append("Tu envío anterior todavía espera la aprobación del administrador.")
        for a in avisos:
            res = a.get("resultado") or {}
            rech = res.get("rechazados") or []
            mensajes.append(f"Envío del {a.get('fecha', '')}: {res.get('aceptados', 0)} aceptados"
                            + (f", {len(rech)} rechazados:\n" + "\n".join("   • " + x for x in rech[:15])
                               + ("\n   …" if len(rech) > 15 else "") if rech else "."))
        yield from self._lista()
        if self.app.pagina == self.clave:
            self.refrescar()
        yield avisar("Sincronizado", "\n\n".join(mensajes) if mensajes else "Todo al día.")
