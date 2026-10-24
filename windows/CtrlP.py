"""
Ctrl-P v1 - Control de avance detallado de obra
================================================
Programa principal (interfaz). La logica esta en ctrlp_core.py y las
exportaciones en ctrlp_excel.py.
"""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import customtkinter as ctk

import ctrlp_core as core
import ctrlp_excel as xl
import ctrlp_memoria as mc
import ctrlp_ui as ui
import ctrlp_planos as pl
import ctrlp_actualizar as act_
import json
from ctrlp_ui import C, F, TF, boton, col, entrada, etiqueta, fmt, fmt_pct

VERSION = "v1.5"
VERSION_INTERNA = "1.5"
AUTOR = "Meneses999"

# Historial de cambios (se ve en Apariencia › «Novedades» y al actualizar)
CAMBIOS = [
    ("v1.5", [
        "Cortes semanales a elección (por defecto de viernes a jueves): en Proyecto › Datos del proyecto o tocando "
        "«Semanas: …» en Informes. Se usan en «+ Por semana» y en las memorias de cálculo.",
        "Corte de estimación: «Corte + memorias» agrega las memorias con una sola columna «ESTE PERÍODO» (la suma "
        "del período, sin semanas). Las memorias de «Memorias de cálculo» siguen por semana.",
        "Memorias: el cuadro de observaciones queda en blanco.",
        "Informes: opciones en orden (fechas, vista, detalle, qué mostrar); al tocar varias seguidas se calcula una "
        "sola vez y no se calcula si ya cambiaste de pantalla.",
        "Si el programa deja de responder, queda anotado en errores.log dónde se quedó (para poder corregirlo).",
    ]),
    ("v1.4", [
        "Instalador (Ctrl-P_instalador.exe): se instala para tu usuario sin pedir administrador, con acceso en el "
        "menú Inicio y el escritorio, doble clic en los proyectos .ctrlp y desinstalador. Instalado, los proyectos "
        "van a Documentos\\CTRL-P DOC. Se sigue actualizando solo desde el programa.",
        "Informes: la barra horizontal solo aparece cuando hay columnas que desplazar (antes se podía quedar "
        "«No responde» al tocarla).",
    ]),
    ("v1.3", [
        "Memorias de cálculo: con un solo nivel ya no sale la columna TOTAL extra, y las áreas exteriores van en "
        "la misma columna que el nivel I.",
    ]),
    ("v1.2", [
        "Informes › «Memorias de cálculo»: una pestaña por actividad del filtro elegido, con el formato de la "
        "memoria de estimación (logos, datos del proyecto, bloques por tipo, cantidades de diseño por edificio y "
        "nivel, período anterior, cada semana y lo pendiente y resumen), con fórmulas de Excel.",
        "Semanas cada 7 días desde el primer día del período (se incluyen el primero y el último).",
        "«Solo memorias» (archivo liviano) o «Informe + memorias».",
    ]),
    ("v1.1", [
        "Actualizaciones desde el programa (como PdFOL): avisa cuando hay una versión nueva, la descarga, "
        "la comprueba (SHA256) y se reinicia actualizado. Tus proyectos y la carpeta CTRL-P DOC no se tocan.",
        "Exportar a Excel mucho más rápido y con barra de avance: el programa ya no queda «No responde».",
        "Informes: columnas fijas a izquierda y derecha; solo se desplazan los días o semanas.",
        "Informes: «Mostrar» Presupuesto completo / Con avance / Con historial / Al 100 %, siempre con sus etapas.",
        "Informes: «Detallado por ubicación» también por día o por semana; el Excel sale con el mismo filtro.",
        "Actividades al 100 % (o más) de lo contractual en verde: Informes, Excel, lista de partidas y Registro.",
        "Enter como en Excel en Registro, Datos fijos y Ubicaciones: el cursor baja a la casilla de abajo.",
        "Ubicaciones: las áreas sin nivel pueden tener tramos (subdivisiones), cada uno es una ubicación.",
        "Informes: interruptor «Ver solo lo contractual» (también en Exportar a Excel y Corte de estimación).",
        "Registro de avance más rápido: al escribir solo se actualiza la fila; totales con Refrescar (F5) o Guardar.",
    ]),
]


def abrir_en_sistema(ruta):
    try:
        if os.name == "nt":
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception:
        pass


def mostrar_en_carpeta(ruta):
    """Abre el Explorador con el archivo seleccionado."""
    try:
        if os.name == "nt":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(ruta)])
        else:
            abrir_en_sistema(os.path.dirname(ruta))
    except Exception:
        abrir_en_sistema(os.path.dirname(ruta))


# =========================================================================
#  Aplicacion
# =========================================================================
class App(ctk.CTk):
    def __init__(self, archivo_inicial=None):
        self.cfg = core.leer_config()
        modo = self.cfg.get("apariencia", "Automático")
        ctk.set_appearance_mode({"Claro": "light", "Oscuro": "dark"}.get(modo, "system"))
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=C["fondo"])
        ui.registrar_fuentes()
        self.title(f"Ctrl-P {VERSION}")
        # tamanos en unidades logicas (CustomTkinter multiplica por la escala de Windows)
        esc = ctk.ScalingTracker.get_window_scaling(self)
        sw, sh = self.winfo_screenwidth() / esc, self.winfo_screenheight() / esc
        self.geometry(f"{int(min(1500, sw - 60))}x{int(min(940, sh - 90))}")
        self.minsize(int(min(1024, sw - 20)), int(min(620, sh - 80)))
        if os.name == "nt":
            self.after(10, lambda: self.state("zoomed"))
        ui.icono_ventana(self)
        self.usuario = None
        self.con_clave = False
        self.llave = None
        self.p = None
        self.pagina = None
        self.paginas = {}
        self.modo_actual = None
        self.archivo_inicial = archivo_inicial
        ui.estilo_tablas(self)
        self.protocol("WM_DELETE_WINDOW", self.al_cerrar)
        self.report_callback_exception = self._error_tk
        self.pila_deshacer = []
        for k in ("<Control-z>", "<Control-Z>"):
            self.bind_all(k, self._ctrl_z, add="+")
        self.mostrar_login()
        self.after(150, self.revisar_tema)
        self.after(1500, self.vigilar_tema)

    # ------------------------------------------------------------ tema
    def revisar_tema(self):
        actual = ui.oscuro()
        if actual != self.modo_actual:
            self.modo_actual = actual
            ui.estilo_tablas(self)
            ui.tenir_barra_titulo(self, actual)
            if hasattr(self, "lateral") and self.lateral.winfo_exists():
                self.dibujar_lateral()
            for pg in self.paginas.values():
                if hasattr(pg, "al_cambiar_tema"):
                    pg.al_cambiar_tema()

    def vigilar_tema(self):
        self.revisar_tema()
        self.after(1500, self.vigilar_tema)

    def cambiar_apariencia(self, modo):
        self.cfg = core.config_poner(apariencia=modo)
        ctk.set_appearance_mode({"Claro": "light", "Oscuro": "dark"}.get(modo, "system"))
        self.after(80, self.revisar_tema)

    # ------------------------------------------------------------ login
    def mostrar_login(self):
        for w in self.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        self.login = Login(self)
        self.login.pack(fill="both", expand=True)

    def entrar(self, usuario):
        self.usuario = usuario
        self.login.destroy()
        self.construir()
        ruta = self.archivo_inicial
        self.archivo_inicial = None
        if ruta and os.path.isfile(ruta):
            self.after(200, lambda: self.abrir_proyecto(ruta))

    # ------------------------------------------------------------ estructura
    def construir(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.lateral = tk.Canvas(self, width=252, highlightthickness=0, bd=0, cursor="hand2")
        self.lateral.grid(row=0, column=0, sticky="ns")
        self.iconos = {k: ui.foto_tk(ui.icono(k, c, 28)) for k, _, c, _ in ICONOS_LAT}
        self.lateral.bind("<Configure>", lambda _: self.dibujar_lateral())
        self.lateral.bind("<Button-1>", self.clic_lateral)
        self.lateral.bind("<Motion>", self._ayuda_lateral)
        self.lateral.bind("<Leave>", lambda _: self._ayuda_lat.place_forget())
        self._ayuda_lat = tk.Label(self, bg=col("texto"), fg=col("tarjeta"), font=(ui.FAM, 10), padx=8, pady=3)
        self.lat_compacto = False
        self.bind("<Configure>", self._revisar_ancho, add="+")
        for k in ("<Control-s>", "<Control-S>"):
            self.bind_all(k, self.guardar_todo, add="+")
        self.bind_all("<F5>", self.refrescar_actual, add="+")
        for k in ("<Return>", "<KP_Enter>"):
            self.bind_all(k, self._enter_baja, add="+")
        self.contenido = ctk.CTkFrame(self, fg_color=C["fondo"], corner_radius=0)
        self.contenido.grid(row=0, column=1, sticky="nsew")
        self.contenido.grid_columnconfigure(0, weight=1)
        self.contenido.grid_rowconfigure(1, weight=1)
        self._armar_franja()
        for clase in (PaginaProyecto, PaginaPresupuesto, PaginaUbicaciones, PaginaDatosFijos, PaginaRegistro,
                      PaginaPlanos, PaginaInformes, PaginaApariencia):
            pg = clase(self.contenido, self)
            self.paginas[pg.clave] = pg
        self.ir("proyecto")
        if not getattr(self, "_act_revisado", False):
            self._act_revisado = True
            self.after(3000, lambda: self.buscar_actualizacion(False))  # si no hay internet, no molesta

    def dibujar_lateral(self):
        cv = self.lateral
        cv.delete("all")
        h = max(cv.winfo_height(), 700)
        comp = getattr(self, "lat_compacto", False)
        w = 76 if comp else 252
        a, b = ui._hex(col("lat_ini")), ui._hex(col("lat_fin"))
        from PIL import Image
        grad = Image.new("RGB", (1, 256))
        for y in range(256):
            t = y / 255
            grad.putpixel((0, y), tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
        self._fondo_lat = ui.foto_tk(grad.resize((w, h)))
        cv.create_image(0, 0, image=self._fondo_lat, anchor="nw")
        cv.create_line(w - 1, 0, w - 1, h, fill=col("borde"))
        if comp:
            cv.create_text(w // 2, 34, text="C-P", fill=col("texto"), font=(ui.FAM, 15, "bold"))
            y = 70
        else:
            n = cv.create_text(24, 34, text="Ctrl-P", anchor="w", fill=col("texto"), font=(ui.FAM, 20, "bold"))
            nv = cv.create_text(cv.bbox(n)[2] + 6, 37, text=VERSION, anchor="w", fill=col("acento"), font=(ui.FAM, 11, "bold"))
            if getattr(self, "act", {}).get("info"):   # puntito naranja: hay una version nueva
                x1 = cv.bbox(nv)[2] + 6
                cv.create_oval(x1, 30, x1 + 9, 39, fill="#F97316", outline="")
            cv.create_text(24, 58, text="Control de avance detallado de obra", anchor="w", fill=col("texto2"),
                           font=(ui.FAM, 9))
            y = 82
        if self.p and comp:
            y += 4
            self._boton_guardar(cv, 10, y, w - 10, comp)
            y += 40
            self._boton_refrescar(cv, 10, y, w - 10, comp)
            y += 42
        elif self.p:
            cv.create_rectangle(16, y, w - 16, y + 62, fill=col("tarjeta"), outline=col("borde"), tags=("archivo",))
            cv.create_text(28, y + 13, text="Proyecto", anchor="w", fill=col("texto2"), font=(ui.FAM, 8))
            cv.create_text(28, y + 31, text=ui.recortar(self.p.nombre, (ui.FAM, 10, "bold"), w - 60), anchor="w",
                           fill=col("texto"), font=(ui.FAM, 10, "bold"))
            cv.create_text(28, y + 49, text=f"Presupuesto V{self.p.version_presupuesto} · {fmt(self.p.total_presupuesto())}",
                           anchor="w", fill=col("texto2"), font=(ui.FAM, 8))
            y += 72
            medio = (16 + w - 16) // 2
            self._boton_guardar(cv, 16, y, medio - 4, comp)
            self._boton_refrescar(cv, medio + 4, y, w - 16, comp)
            y += 50
        else:
            y += 8
        grupo_ant = 0
        pend = len(self.p.descuadres()) if self.p else 0
        for clave, titulo, _, grupo in ICONOS_LAT:
            if grupo != grupo_ant:
                cv.create_line(28, y + 2, w - 28, y + 2, fill=col("borde"))
                y += 12
                grupo_ant = grupo
            activo = self.p is not None or clave in ("proyecto", "apariencia")
            if comp:
                if clave == self.pagina:
                    cv.create_rectangle(10, y - 4, w - 10, y + 38, fill=col("lat_sel"), outline="")
                cv.create_image(w // 2, y + 17, image=self.iconos[clave], tags=("item", clave))
                if clave == "datos" and pend:
                    cv.create_oval(w - 22, y + 2, w - 15, y + 9, fill=col("punto"), outline="")
                cv.create_rectangle(10, y - 4, w - 10, y + 38, outline="", fill="", tags=("item", clave))
                y += 44
                continue
            if clave == self.pagina:
                cv.create_rectangle(14, y - 4, w - 14, y + 38, fill=col("lat_sel"), outline="")
            cv.create_image(28, y + 17, image=self.iconos[clave], anchor="w", tags=("item", clave))
            cv.create_text(68, y + 17, text=titulo, anchor="w",
                           fill=col("texto") if activo else col("texto2"),
                           font=(ui.FAM, 11, "bold" if clave == self.pagina else "normal"), tags=("item", clave))
            if clave == "datos" and pend:
                cv.create_oval(w - 48, y + 14, w - 42, y + 20, fill=col("punto"), outline="")
                cv.create_text(w - 36, y + 17, text=str(pend), anchor="w", fill=col("texto2"), font=(ui.FAM, 9))
            cv.create_rectangle(14, y - 4, w - 14, y + 38, outline="", fill="", tags=("item", clave))
            y += 44
        if self.usuario:
            cv.create_rectangle(14, h - 60, w - 14, h - 12, fill="", outline="", tags=("usuario",))
            if core.es_admin(self.usuario):
                if not hasattr(self, "_img_husky"):
                    self._img_husky = ui.foto_tk(ui.husky(36))
                cv.create_image(40, h - 36, image=self._img_husky, tags=("usuario",))
            else:
                ini = "".join(x[0] for x in self.usuario.split(" - ")[0].split()[:2])[:2]
                cv.create_oval(24, h - 52, 56, h - 20, fill=col("acento"), outline="", tags=("usuario",))
                cv.create_text(40, h - 36, text=ini, fill="#FFFFFF", font=(ui.FAM, 10, "bold"), tags=("usuario",))
            if comp:
                return
            cv.create_text(66, h - 44, text=ui.recortar(self.usuario, (ui.FAM, 9, "bold"), w - 80), anchor="w", fill=col("texto"), font=(ui.FAM, 9, "bold"))
            if not self.p:
                sub = "Sin proyecto abierto"
            elif self.p.version_trabajo in ("", "creación"):
                sub = "Proyecto recién creado"
            else:
                sub = f"Guardando en {os.path.basename(self.p.ruta)}"
            cv.create_text(66, h - 27, text=ui.recortar(sub, (ui.FAM, 8), w - 80), anchor="w", fill=col("texto2"), font=(ui.FAM, 8))

    def _boton_guardar(self, cv, x0, y, x1, comp):
        txt = getattr(self, "_txt_guardado", "")
        ok = txt.startswith("✓")
        fondo = "#16A34A" if ok else (col("acento") if not txt else col("rojo"))
        r = 8
        pts = [x0 + r, y, x1 - r, y, x1, y, x1, y + r, x1, y + 34 - r, x1, y + 34, x1 - r, y + 34, x0 + r, y + 34,
               x0, y + 34, x0, y + 34 - r, x0, y + r, x0, y]
        cv.create_polygon(pts, smooth=True, fill=fondo, outline="", tags=("guardar",))
        if comp:
            etq = "✓" if ok else "Guardar"
            cv.create_text((x0 + x1) // 2, y + 17, text=etq, fill="#FFFFFF", font=(ui.FAM, 8 if not ok else 12, "bold"),
                           tags=("guardar",))
        else:
            cv.create_text((x0 + x1) // 2, y + 17, text=txt or "Guardar", fill="#FFFFFF", font=(ui.FAM, 10, "bold"),
                           tags=("guardar",))

    def pagina_desactualizada(self):
        pg = self.paginas.get(self.pagina)
        return bool(self.p and self.pagina in PAGINAS_MANUALES and pg is not None
                    and getattr(pg, "_rev_cargada", None) != self.p.rev)

    def _boton_refrescar(self, cv, x0, y, x1, comp):
        viejo = self.pagina_desactualizada()
        fondo = "#F59E0B" if viejo else col("suave")
        texto = "#FFFFFF" if viejo else col("texto")
        r = 8
        pts = [x0 + r, y, x1 - r, y, x1, y, x1, y + r, x1, y + 34 - r, x1, y + 34, x1 - r, y + 34, x0 + r, y + 34,
               x0, y + 34, x0, y + 34 - r, x0, y + r, x0, y]
        cv.create_polygon(pts, smooth=True, fill=fondo, outline="", tags=("refrescar",))
        cv.create_text((x0 + x1) // 2, y + 17, text="↻" if comp else "↻ Refrescar", fill=texto,
                       font=(ui.FAM, 12 if comp else 10, "bold"), tags=("refrescar",))

    PAGINAS_ENTER = ("registro", "datos", "ubicaciones")

    def _enter_baja(self, e=None):
        """Enter como en Excel: el valor queda en la casilla y el cursor baja a la casilla de abajo de la misma
        columna (salta las bloqueadas y las ocultas). En la ultima casilla se queda ahi."""
        w = self.focus_get()
        if not isinstance(w, tk.Entry) or self.pagina not in self.PAGINAS_ENTER:
            return None
        if w.bind("<Return>") or w.bind("<KP_Enter>"):
            return None                     # el campo tiene su propio Enter (fecha, busqueda...)
        pg = self.paginas.get(self.pagina)
        if pg is None or not str(w).startswith(str(pg)):
            return None
        try:
            x0, y0 = w.winfo_rootx(), w.winfo_rooty()
        except tk.TclError:
            return None
        mejor, my = None, None
        pila = [pg]
        while pila:
            c = pila.pop()
            for h in c.winfo_children():
                pila.append(h)
                if h is w or not isinstance(h, tk.Entry):
                    continue
                try:
                    if str(h.cget("state")) == "disabled" or not h.winfo_ismapped():
                        continue
                    hx, hy = h.winfo_rootx(), h.winfo_rooty()
                except tk.TclError:
                    continue
                if abs(hx - x0) <= 3 and hy > y0 + 2 and (my is None or hy < my):
                    mejor, my = h, hy
        if mejor is None:
            return "break"
        mejor.focus_set()
        try:
            mejor.select_range(0, "end")
            mejor.icursor("end")
        except tk.TclError:
            pass
        self._ver_campo(mejor)
        return "break"

    def _ver_campo(self, w):
        """Desplaza la tabla (el lienzo con barra vertical que la contiene) para que el campo quede a la vista."""
        c = w.master
        while c is not None:
            if isinstance(c, tk.Canvas):
                try:
                    a, b = c.yview()
                    if b - a < 0.999:
                        c.update_idletasks()
                        caja = c.bbox("all")
                        if caja:
                            alto_total = caja[3] - caja[1]
                            y = c.canvasy(w.winfo_rooty() - c.winfo_rooty())
                            vis0, vis1 = c.canvasy(0), c.canvasy(c.winfo_height())
                            if y < vis0 + 10 or y + w.winfo_height() > vis1 - 10:
                                c.yview_moveto(max(0.0, (y - c.winfo_height() / 3) / max(alto_total, 1)))
                        return
                except tk.TclError:
                    return
            c = c.master

    def refrescar_actual(self, e=None):
        """Vuelve a armar la pantalla actual con los datos de ahora (presupuesto, ubicaciones, informes…)."""
        pg = self.paginas.get(self.pagina)
        if pg is None:
            return
        if self.pagina == "informes":
            pg.generar()
        else:
            with ui.congelar(self):
                pg.refrescar()
        self.dibujar_lateral()
        return "break"

    def guardar_todo(self, e=None):
        """Botón Guardar (y Ctrl+S): guarda lo que está a medio editar en la pantalla actual y el archivo .ctrlp.
        Siempre en el mismo archivo: no crea copias ni pregunta dónde guardar."""
        if not self.p:
            return
        pg = self.paginas.get(self.pagina)
        sin_guardar = False
        try:
            if self.pagina == "datos" and pg.it and pg._cambios():
                pg.guardar()
                sin_guardar = bool(pg.it and pg._cambios())
            elif self.pagina == "registro" and pg.it and pg.pendientes():
                pg.guardar(preguntar_plano=False)
                sin_guardar = bool(pg.pendientes())
            elif self.pagina == "registro" and pg.it and pg.totales_viejos:
                pg.recalcular()             # Guardar también deja los totales al día
        except Exception as ex:
            ui.info(self, "Guardar", f"No se pudieron guardar los cambios de esta pantalla:\n{ex}")
            sin_guardar = True
        if not self.p.solo_agregar and os.path.basename(self.p.ruta).lower() != (NOMBRE_MASTER + core.EXT).lower():
            # primera vez: el proyecto pasa a su archivo master Registro_Semanal.ctrlp (elegís dónde)
            destino = filedialog.asksaveasfilename(
                title="Guardar archivo master", defaultextension=core.EXT, initialfile=f"{NOMBRE_MASTER}{core.EXT}",
                initialdir=ui.carpeta_docs(), filetypes=[("Proyecto Ctrl-P", "*.ctrlp")])
            if destino:
                try:
                    aviso = self.p.guardar_en(destino)
                except Exception as ex:
                    ui.info(self, "No se pudo guardar", f"No se pudo crear el archivo master:\n{ex}")
                    return "break"
                if aviso:
                    ui.info(self, "Historial", aviso)
                self.title(f"Ctrl-P {VERSION} — {os.path.basename(self.p.ruta)}")
                pg = self.paginas.get("proyecto")
                if pg is not None:
                    pg._proy_cargado = None          # que muestre la ruta nueva
            else:
                self.guardar()
        else:
            self.guardar()
        import datetime as _dt
        self._txt_guardado = "Revisá datos" if sin_guardar else "✓ Guardado"
        self._hora_guardado = _dt.datetime.now().strftime("%H:%M")
        self.dibujar_lateral()
        if getattr(self, "_job_guardado", None):
            self.after_cancel(self._job_guardado)
        self._job_guardado = self.after(3500, self._limpiar_guardado)
        return "break"

    def _limpiar_guardado(self):
        self._job_guardado = None
        self._txt_guardado = ""
        if hasattr(self, "lateral") and self.lateral.winfo_exists():
            self.dibujar_lateral()

    def _revisar_ancho(self, e=None):
        """Ventana angosta (laptops): el menu lateral pasa a solo iconos para dejar lugar al contenido."""
        if not hasattr(self, "lateral") or not self.lateral.winfo_exists():
            return
        esc = ctk.ScalingTracker.get_window_scaling(self)
        compacto = self.winfo_width() / esc < 1240
        if compacto != self.lat_compacto:
            self.lat_compacto = compacto
            self.lateral.configure(width=76 if compacto else 252)
            self.dibujar_lateral()

    def _ayuda_lateral(self, ev):
        if not self.lat_compacto:
            tags = {tg for it in self.lateral.find_overlapping(ev.x, ev.y, ev.x, ev.y) for tg in self.lateral.gettags(it)}
            if not tags & {"guardar", "refrescar", "archivo"}:
                self._ayuda_lat.place_forget()
                return
        for it in reversed(self.lateral.find_overlapping(ev.x, ev.y, ev.x, ev.y)):
            for tg in self.lateral.gettags(it):
                if tg == "archivo" and self.p:
                    self._ayuda_lat.configure(text=f"Se guarda en: {self.p.ruta}  (clic para abrir la carpeta)",
                                              bg=col("texto"), fg=col("tarjeta"))
                    self._ayuda_lat.place(x=self.lateral.winfo_width() + 6, y=ev.y - 12)
                    self._ayuda_lat.lift()
                    return
                if tg in self.paginas or tg in ("usuario", "guardar", "refrescar"):
                    txt = (self.usuario if tg == "usuario" else "Guardar (Ctrl+S)" if tg == "guardar"
                           else "Refrescar (F5)" if tg == "refrescar" else self.paginas[tg].titulo)
                    if tg == "guardar" and getattr(self, "_hora_guardado", None):
                        txt += f" · último: {self._hora_guardado}"
                    self._ayuda_lat.configure(text=txt, bg=col("texto"), fg=col("tarjeta"))
                    self._ayuda_lat.place(x=self.lateral.winfo_width() + 6, y=ev.y - 12)
                    self._ayuda_lat.lift()
                    return
        self._ayuda_lat.place_forget()

    def clic_lateral(self, ev):
        for it in reversed(self.lateral.find_overlapping(ev.x, ev.y, ev.x, ev.y)):
            if "guardar" in self.lateral.gettags(it):
                self.guardar_todo()
                return
            if "refrescar" in self.lateral.gettags(it):
                self.refrescar_actual()
                return
            if "archivo" in self.lateral.gettags(it) and self.p:
                mostrar_en_carpeta(self.p.ruta)
                return
            if "usuario" in self.lateral.gettags(it):
                DialogoUsuarios(self)
                return
            for t in self.lateral.gettags(it):
                if t in self.paginas:
                    if self.p is None and t not in ("proyecto", "apariencia"):
                        return
                    self.ir(t)
                    return

    def ir(self, clave):
        if self.pagina and self.pagina in self.paginas:
            pg = self.paginas[self.pagina]
            if hasattr(pg, "puede_salir") and not pg.puede_salir():
                return
        # la pantalla nueva se arma sin mostrarse y aparece completa (sin rayas mientras se arma)
        if self.pagina and self.pagina in self.paginas:
            self.paginas[self.pagina].grid_forget()
        self.pagina = clave
        pg = self.paginas[clave]
        reusar = (clave in PAGINAS_MANUALES and self.p is not None and getattr(pg, "_proy_cargado", None) is self.p
                  and not getattr(pg, "_sin_calcular", False))
        if not reusar:
            pg.refrescar()
        try:
            pg.update_idletasks()
        except tk.TclError:
            pass
        pg.grid(row=1, column=0, sticky="nsew")
        self.dibujar_lateral()

    # ------------------------------------------------------------ actualizaciones (igual que PdFOL)
    def _armar_franja(self):
        self.act = {"info": None, "nuevo": None, "tmp": None, "bajando": False, "cancelar": threading.Event(),
                    "cola": queue.Queue()}
        self.franja = ctk.CTkFrame(self.contenido, fg_color=("#E3EDFB", "#22324A"), corner_radius=0, height=46)
        self.franja.grid_columnconfigure(0, weight=1)
        self.v_franja = tk.StringVar(value="")
        ctk.CTkLabel(self.franja, textvariable=self.v_franja, font=F(13, "bold"), text_color=C["texto"],
                     anchor="w", justify="left", wraplength=700).grid(row=0, column=0, sticky="ew", padx=(22, 10), pady=6)
        self.caja_franja = ctk.CTkFrame(self.franja, fg_color="transparent")
        self.caja_franja.grid(row=0, column=1, sticky="e", padx=(0, 18), pady=5)

    def _franja_mostrar(self, texto, botones):
        self.v_franja.set(texto)
        for w in self.caja_franja.winfo_children():
            w.destroy()
        for txt, cmd, prim in botones:
            boton(self.caja_franja, txt, primario=prim, ancho=max(90, 8 * len(txt) + 30), alto=30,
                  command=cmd).pack(side="left", padx=4)
        self.franja.grid(row=0, column=0, sticky="ew")

    def _franja_ocultar(self):
        self.franja.grid_forget()

    def buscar_actualizacion(self, manual=False):
        if self.act["bajando"]:
            return
        cola = self.act["cola"]

        def hilo():
            try:
                cola.put(("version", act_.ultima_version(VERSION_INTERNA), manual))
            except Exception as e:
                cola.put(("version_error", str(e), manual))
        threading.Thread(target=hilo, daemon=True).start()
        self._mirar_cola()

    def _mirar_cola(self):
        try:
            while True:
                ev = self.act["cola"].get_nowait()
                self._evento_act(ev)
        except queue.Empty:
            pass
        if self.act["bajando"] or not self.act.get("visto_version"):
            self.after(200, self._mirar_cola)

    def _evento_act(self, ev):
        tipo = ev[0]
        if tipo == "version":
            self.act["visto_version"] = True
            info, manual = ev[1], ev[2]
            if act_.hay_version_nueva(info, VERSION_INTERNA):
                self.ofrecer_version(info)
            elif manual:
                ui.info(self, "Actualizaciones", f"Tenés la última versión de Ctrl-P ({VERSION}).")
        elif tipo == "version_error":
            self.act["visto_version"] = True
            if ev[2]:
                ui.info(self, "Actualizaciones", "No se pudo revisar si hay actualizaciones "
                                                 "(sin internet o GitHub no responde).\n\n" + ev[1][:200])
        elif tipo == "act_prog":
            h, t = ev[1], ev[2]
            pct = int(h * 100 / t) if t else 0
            self.v_franja.set(f"Descargando Ctrl-P {self.act['info']['tag']}… {pct} %  ({h / 1048576:.1f} MB)")
        elif tipo == "act_listo":
            self.act["nuevo"], self.act["bajando"] = ev[1], False
            self._franja_mostrar(f"Ctrl-P {self.act['info']['tag']} está descargado y comprobado (SHA256): "
                                 "listo para instalarse.",
                                 [("Reiniciar ahora", self.reiniciar_para_actualizar, True),
                                  ("Después", self._franja_ocultar, False)])
        elif tipo == "act_error":
            self.act["bajando"] = False
            self._franja_ocultar()
            if ev[1] is not None:
                ui.info(self, "Actualizaciones", f"No se pudo actualizar. Seguís con tu versión.\n\n{ev[1]}")

    def ofrecer_version(self, info):
        self.act["info"] = info
        self.dibujar_lateral()
        self._franja_mostrar(f"Hay una versión nueva de Ctrl-P ({info['tag']}).",
                             [("Ver cambios", self.ver_cambios, False), ("Actualizar", self.empezar_actualizacion, True),
                              ("Más tarde", self._franja_ocultar, False)])

    def ver_cambios(self):
        info = self.act["info"] or {}
        puntos = act_.notas_en_puntos(info.get("notas")) or ["(Esta versión no trae notas.)"]
        r = ui.dialogo_texto(self, f"Novedades de {info.get('tag', 'la versión nueva')}",
                             "\n".join("•  " + x for x in puntos), ("Cerrar", "Actualizar ahora"), 1)
        if r == 1:
            self.empezar_actualizacion()

    def novedades(self):
        texto = []
        for ver, puntos in CAMBIOS:
            texto.append(ver)
            texto += ["•  " + x for x in puntos]
            texto.append("")
        ui.dialogo_texto(self, f"Novedades de Ctrl-P {VERSION}", "\n".join(texto).strip(), ("Cerrar",), 0)

    def empezar_actualizacion(self):
        if not self.act["info"] or self.act["bajando"]:
            return
        if not getattr(sys, "frozen", False):
            ui.info(self, "Actualizaciones", "La actualización automática funciona en el programa instalado o "
                                             "portable (Ctrl-P.exe).\n\nEstás usando el .py: bajá la versión nueva desde "
                                             f"GitHub ({self.act['info'].get('web', '')}).")
            return
        app_dir = os.path.dirname(sys.executable)
        if not act_.carpeta_escribible(app_dir):
            ui.info(self, "Actualizaciones", f"No se puede escribir en la carpeta del programa:\n{app_dir}\n\n"
                                             "Copiá la carpeta de Ctrl-P a un lugar tuyo (Documentos, Escritorio o una "
                                             "USB) y actualizá desde ahí.")
            return
        import tempfile
        self.act["tmp"] = tempfile.mkdtemp(prefix="CtrlP_actualizacion_")
        self.act["bajando"] = True
        self.act["cancelar"].clear()
        self._franja_mostrar(f"Descargando Ctrl-P {self.act['info']['tag']}…",
                             [("Cancelar", lambda: self.act["cancelar"].set(), False)])
        info, cola = self.act["info"], self.act["cola"]

        def hilo():
            try:
                nuevo = act_.descargar_actualizacion(info, self.act["tmp"], lambda h, t: cola.put(("act_prog", h, t)),
                                                     self.act["cancelar"])
                cola.put(("act_listo", nuevo))
            except act_.Cancelado:
                cola.put(("act_error", None))
            except Exception as e:
                cola.put(("act_error", str(e)))
        threading.Thread(target=hilo, daemon=True).start()
        self._mirar_cola()

    def reiniciar_para_actualizar(self):
        # el proyecto se cierra como siempre (pregunta si guardar lo pendiente)
        if self.p and not self.cerrar_proyecto():
            return
        try:
            act_.lanzar_actualizador(self.act["nuevo"], self.act["tmp"])
        except Exception as e:
            ui.info(self, "Actualizaciones", f"No se pudo iniciar el actualizador:\n{e}")
            return
        # Ctrl-P se cierra del todo y al instante: la ventana desaparece y el proceso termina (sin quedar una
        # ventana negra a medio cerrar). El actualizador reemplaza los archivos y lo vuelve a abrir.
        try:
            self.withdraw()
            self.update_idletasks()
        except Exception:
            pass
        try:
            import ctrlp_render
            ctrlp_render.cerrar(forzar=True)
        except Exception:
            pass
        try:
            marca = os.path.join(core.carpeta_config(), "sesion_abierta")
            if os.path.exists(marca):
                os.remove(marca)
        except Exception:
            pass
        os._exit(0)

    # ------------------------------------------------------------ proyecto
    def decidir_copia(self):
        r = ui.dialogo_texto(self, "Copia de seguridad",
                             "Ya abriste este proyecto hoy y existe una copia de seguridad del día.\n\n"
                             "¿Querés crear una nueva copia antes de seguir, o continuar con la copia de hoy?",
                             ("Seguir con la de hoy", "Crear nueva copia"), primario=1)
        return r == 1

    def abrir_proyecto(self, ruta=None):
        if ruta is None:
            ruta = filedialog.askopenfilename(title="Abrir proyecto", initialdir=ui.carpeta_docs(), filetypes=[("Proyecto Ctrl-P", "*.ctrlp")])
            if not ruta:
                return
        carpeta = os.path.basename(os.path.dirname(os.path.abspath(ruta)))
        if carpeta.endswith(" - respaldos"):
            original = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(ruta))),
                                    carpeta[:-len(" - respaldos")] + core.EXT)
            r = ui.dialogo_texto(self, "Es una copia de seguridad",
                                 "Este archivo es una copia de seguridad (una foto del proyecto de ese día), no el "
                                 "proyecto con el que trabajás.\n\nSi lo abrís y registrás, tu avance quedaría en la copia."
                                 + (f"\n\nEl proyecto original está en:\n{original}" if os.path.isfile(original) else ""),
                                 ("Cancelar", "Abrir la copia igual") + (("Abrir el original",) if os.path.isfile(original) else ()),
                                 2 if os.path.isfile(original) else 0)
            if r == 2:
                ruta = original
            elif r != 1:
                return
        if not self.cerrar_proyecto():
            return
        try:
            p = core.Proyecto.abrir(ruta, self.usuario, self.decidir_copia)
        except core.ErrorCtrlP as e:
            ui.info(self, "No se pudo abrir", str(e))
            return
        if not self.con_clave and self.usuario in core.usuarios_registrados(p.usuarios_proyecto()):
            n, e = self.usuario.split(" - ", 1)

            def validar(v):
                try:
                    core.verificar_usuario(n, e, v["clave"], p.usuarios_proyecto())
                except core.ErrorCtrlP as ex:
                    return str(ex)
                return ""
            r = ui.dialogo_form(self, "Usuario protegido",
                                f"En este proyecto, {self.usuario} tiene contraseña.",
                                [("clave", "Contraseña", True, "")], ("Cancelar", "Entrar"), validar=validar)
            if not r:
                p.cerrar()
                return
            self.con_clave = True
        self.p = p
        try:
            self.p.sincronizar_usuarios()
        except Exception:
            pass
        self.proyecto_cargado()

    def proyecto_cargado(self):
        self.title(f"Ctrl-P {VERSION} — {os.path.basename(self.p.ruta)}")
        for pg in self.paginas.values():
            if hasattr(pg, "al_cambiar_proyecto"):
                pg.al_cambiar_proyecto()
        self.ir("registro" if self.p.edificios() else "ubicaciones")
        if self.p.solo_agregar:
            ui.info(self, "Copia para agregar avance",
                    "Este archivo fue exportado en modo «Solo agregar avance».\n\n"
                    "Podés registrar avances nuevos, pero no modificar registros anteriores, ubicaciones, "
                    "datos fijos ni el presupuesto. Al terminar, guardalo y devolvelo (por ejemplo como V2).")

    def cerrar_proyecto(self):
        if not self.p:
            return True
        for pg in self.paginas.values():
            if hasattr(pg, "puede_salir") and not pg.puede_salir():
                return False
        if self.p.sucio:
            self.guardar()
        self.p.cerrar()
        self.p = None
        self.title(f"Ctrl-P {VERSION}")
        self.pila_deshacer = []
        for pg in self.paginas.values():
            if hasattr(pg, "al_cambiar_proyecto"):
                pg.al_cambiar_proyecto()
        return True

    # ------------------------------------------------------------ deshacer (planos)
    def punto_deshacer(self, descripcion, datos_de=()):
        """Antes de un cambio en planos: devuelve la ficha para confirmar_deshacer."""
        return (descripcion, self.p.instantanea(datos_de), self.p.rev)

    def confirmar_deshacer(self, ficha):
        desc, snap, rev0 = ficha
        if self.p.rev != rev0:
            self.pila_deshacer.append((desc, snap, self.p.rev))
            del self.pila_deshacer[:-30]

    def _ctrl_z(self, e=None):
        if not self.p or self.pagina != "planos":
            return
        w = self.focus_get()
        if isinstance(w, (tk.Entry, ctk.CTkEntry)) or (w is not None and w.winfo_class() in ("Entry", "Text")):
            return
        if w is not None and w.winfo_toplevel() is not self:
            return
        self.paginas["planos"].deshacer()
        return "break"

    def _error_tk(self, tp, val, tb):
        import traceback
        registrar_error("Error en pantalla", "".join(traceback.format_exception(tp, val, tb)))
        if getattr(self, "_mostrando_error", False):
            return
        self._mostrando_error = True
        try:
            r = ui.dialogo_texto(self, "Ocurrió un error",
                                 f"Algo falló en esta acción ({tp.__name__}). El programa sigue abierto y lo que ya "
                                 "estaba guardado está a salvo.\n\nEl detalle quedó en el registro de errores; si se "
                                 "repite, mandámelo.", ("Seguir", "Abrir carpeta del registro"), 0)
            if r == 1 and RUTA_LOG:
                abrir_en_sistema(os.path.dirname(RUTA_LOG))
        finally:
            self._mostrando_error = False

    def avisar_cierre_inesperado(self):
        r = ui.dialogo_texto(self, "Cierre inesperado",
                             "La última vez Ctrl-P se cerró sin que lo cerraras.\n\nSi ves que se repite, mandame el "
                             "archivo «errores.log» de la carpeta del registro para ver qué pasó. Tu proyecto quedó como "
                             "estaba en el último guardado (y tenés la copia de seguridad del día).",
                             ("Seguir", "Abrir carpeta del registro"), 0)
        if r == 1 and RUTA_LOG:
            abrir_en_sistema(os.path.dirname(RUTA_LOG))

    def deshacer(self):
        """Devuelve la descripcion de lo deshecho, o un texto de error."""
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

    def guardar(self, silencioso=True):
        if not self.p:
            return
        try:
            aviso = self.p.guardar()
        except Exception as e:
            ui.info(self, "No se pudo guardar", f"Ocurrió un error al guardar el proyecto:\n{e}")
            return
        if aviso:
            ui.info(self, "Historial", aviso)
        self.dibujar_lateral()

    def nuevo_proyecto(self):
        ruta = filedialog.askopenfilename(title="Elegí el Excel del presupuesto (una sola hoja)", initialdir=ui.carpeta_docs(),
                                          filetypes=[("Excel", "*.xlsx *.xlsm")])
        if ruta:
            AsistenteImportacion(self, ruta, modo="nuevo")

    def al_cerrar(self):
        if self.p and not self.cerrar_proyecto():
            return
        try:
            import ctrlp_render
            ctrlp_render.cerrar()
        except Exception:
            pass
        self.destroy()


ICONOS_LAT = [(k.replace("datos", "datos"), t, c, g) for k, t, c, g in ui.ICONOS]


# =========================================================================
#  Login
# =========================================================================
class Login(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=C["fondo"], corner_radius=0)
        self.app = app
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        izq = ctk.CTkFrame(self, fg_color=C["lat_ini"], corner_radius=0, width=500)
        izq.grid(row=0, column=0, sticky="ns")
        izq.grid_propagate(False)
        izq.pack_propagate(False)
        cab = ctk.CTkFrame(izq, fg_color="transparent")
        cab.pack(pady=(60, 10))
        fila = ctk.CTkFrame(cab, fg_color="transparent")
        fila.pack()
        ctk.CTkLabel(fila, text="Ctrl-P", font=F(46, "bold"), text_color=C["texto"]).pack(side="left")
        ctk.CTkLabel(fila, text=VERSION, font=F(18, "bold"), text_color=C["acento"]).pack(side="left", padx=(8, 0), pady=(14, 0))
        self.img_logo = ctk.CTkImage(ui.logo(220), size=(220, 220))
        ctk.CTkLabel(cab, text="", image=self.img_logo).pack(pady=(18, 16))
        ctk.CTkLabel(cab, text="Control de avance detallado de obra", font=F(15), text_color=C["texto2"]).pack()
        rec = [r for r in app.cfg.get("recientes", []) if os.path.isfile(r.get("ruta", ""))][:3]
        if rec:
            etiqueta(izq, "Proyectos recientes", 12, "bold", "texto2").pack(anchor="w", padx=48, pady=(30, 6))
            for r in rec:
                t = ui.Tarjeta(izq, cursor="hand2")
                t.pack(fill="x", padx=44, pady=4)
                a = etiqueta(t, r.get("nombre", "")[:40], 13, "bold", cursor="hand2")
                a.grid(row=0, column=0, sticky="w", padx=16, pady=(10, 0))
                b = etiqueta(t, os.path.basename(r["ruta"]) + "  ·  entrar y abrir", 11, color="texto2", cursor="hand2")
                b.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))
                for w in (t, a, b):
                    w.bind("<Button-1>", lambda _, ruta=r["ruta"]: self.entrar(ruta))
        der = ctk.CTkFrame(self, fg_color="transparent")
        der.grid(row=0, column=1, sticky="nsew")
        der.grid_rowconfigure(0, weight=1)
        der.grid_columnconfigure(0, weight=1)
        f = ctk.CTkFrame(der, fg_color=C["tarjeta"], corner_radius=16, border_width=1, border_color=C["borde"])
        f.grid(row=0, column=0)
        cab_f = ctk.CTkFrame(f, fg_color="transparent")
        cab_f.pack(fill="x", padx=34, pady=(30, 2))
        etiqueta(cab_f, "Ingresar", 22, "bold").pack(side="left")
        self.img_husky = ctk.CTkImage(ui.husky(96), size=(52, 52))
        self.lbl_husky = ctk.CTkLabel(cab_f, text="", image=self.img_husky)
        etiqueta(f, "Tu nombre queda registrado en cada cambio que hagas.", 12, color="texto2").pack(anchor="w", padx=34)
        self.v_nom = tk.StringVar(value=app.cfg.get("nombre", ""))
        self.v_emp = tk.StringVar(value=app.cfg.get("empresa", ""))
        self.v_clave = tk.StringVar()
        for txt, var in (("Nombre", self.v_nom), ("Empresa", self.v_emp)):
            etiqueta(f, txt, 13, "bold").pack(anchor="w", padx=34, pady=(16, 4))
            e = ui.entrada_mayus(f, var, 360)
            e.configure(height=40, font=F(15, "bold"))
            e.pack(padx=34)
            e.bind("<Return>", lambda _: self.entrar())
        self.caja_clave = ctk.CTkFrame(f, fg_color="transparent")
        etiqueta(self.caja_clave, "Contraseña", 13, "bold").pack(anchor="w", pady=(16, 4))
        self.e_clave = ui.CampoClave(self.caja_clave, self.v_clave, 360, alto=40)
        self.e_clave.pack()
        self.e_clave.bind("<Return>", lambda _: self.entrar())
        etiqueta(self.caja_clave, "Este usuario está protegido con contraseña.", 11, color="texto2").pack(anchor="w", pady=(4, 0))
        self.v_vista = tk.StringVar()
        self.lbl_vista = etiqueta(f, "", 12, color="texto2", textvariable=self.v_vista)
        self.lbl_vista.pack(anchor="w", padx=34, pady=(14, 0))
        self.v_err = tk.StringVar()
        ctk.CTkLabel(f, textvariable=self.v_err, font=F(12), text_color=C["rojo"]).pack(anchor="w", padx=34)
        self.b = boton(f, "Entrar", primario=True, ancho=360, alto=44, command=self.entrar)
        self.b.pack(padx=34, pady=(10, 8))
        ctk.CTkButton(f, text="Crear usuario con contraseña", font=F(12), fg_color="transparent",
                      hover_color=C["suave"], text_color=C["acento"], height=28, width=10,
                      command=self.crear_usuario).pack(pady=(0, 24))
        for v in (self.v_nom, self.v_emp):
            v.trace_add("write", lambda *_: self.actualizar())
        self.actualizar()

    def actualizar(self):
        n, e = core.mayus(self.v_nom.get()), core.mayus(self.v_emp.get())
        self.v_vista.set(f"Se mostrará como  {n} - {e}" if n and e else "")
        if core.requiere_clave(n, e):
            self.caja_clave.pack(padx=34, fill="x", before=self.lbl_vista)
        else:
            self.caja_clave.pack_forget()
            self.v_clave.set("")
        if n and e and core.es_admin(f"{n} - {e}"):
            self.lbl_husky.pack(side="right")
        else:
            self.lbl_husky.pack_forget()

    def crear_usuario(self):
        def validar(v):
            if v["clave"] != v["clave2"]:
                return "Las contraseñas no coinciden."
            try:
                core.registrar_usuario(v["nombre"], v["empresa"], v["clave"])
            except core.ErrorCtrlP as ex:
                return str(ex)
            return ""
        r = ui.dialogo_form(self.app, "Crear usuario",
                            "Con contraseña, nadie más puede entrar con tu nombre. Los nombres no se repiten.",
                            [("nombre", "Nombre", False, core.mayus(self.v_nom.get())),
                             ("empresa", "Empresa", False, core.mayus(self.v_emp.get())),
                             ("clave", "Contraseña (mínimo 4 caracteres)", True, ""),
                             ("clave2", "Repetir contraseña", True, "")],
                            ("Cancelar", "Crear usuario"), validar=validar)
        if r:
            self.v_nom.set(core.mayus(r["nombre"]))
            self.v_emp.set(core.mayus(r["empresa"]))
            self.v_clave.set(r["clave"])
            self.v_err.set("")
            ui.info(self.app, "Usuario creado", f"Se creó {core.mayus(r['nombre'])} - {core.mayus(r['empresa'])}.\n\n"
                    "Al abrir un proyecto, tu usuario queda guardado también dentro del archivo, así te reconoce "
                    "en cualquier computadora.")

    def entrar(self, ruta=None):
        try:
            u = core.verificar_usuario(self.v_nom.get(), self.v_emp.get(), self.v_clave.get())
        except core.ErrorCtrlP as e:
            self.v_err.set(str(e))
            return
        self.app.cfg = core.config_poner(nombre=core.mayus(self.v_nom.get()), empresa=core.mayus(self.v_emp.get()))
        if ruta:
            self.app.archivo_inicial = ruta
        self.app.con_clave = core.requiere_clave(self.v_nom.get(), self.v_emp.get())
        self.app.llave = core.llave_admin(self.v_clave.get()) if core.es_admin(u) else None
        self.app.entrar(u)


# =========================================================================
#  Base de paginas
# =========================================================================
class Pagina(ctk.CTkFrame):
    clave = ""
    titulo = ""
    subtitulo = ""

    def __init__(self, master, app):
        super().__init__(master, fg_color=C["fondo"], corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=34, pady=(24, 12))
        cab.grid_columnconfigure(0, weight=1)
        self.cab = cab
        etiqueta(cab, self.titulo, 26, "bold").grid(row=0, column=0, sticky="w")
        self.v_sub = tk.StringVar(value=self.subtitulo)
        sub = etiqueta(cab, "", 12, color="texto2", textvariable=self.v_sub, justify="left")
        sub.grid(row=1, column=0, sticky="w", pady=(2, 0))
        ui.ajustar_texto(sub, cab, lambda: 30 + max([w.winfo_reqwidth() for w in cab.grid_slaves(column=1)] or [0]), 240)
        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.grid(row=1, column=0, sticky="nsew", padx=34, pady=(0, 0))

    @property
    def p(self):
        return self.app.p

    def refrescar(self):
        pass

    def barra_inferior(self):
        b = ctk.CTkFrame(self, fg_color=C["tarjeta"], corner_radius=0, height=70)
        b.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        ctk.CTkFrame(b, height=1, fg_color=C["borde"], corner_radius=0).pack(fill="x", side="top")
        cont = ctk.CTkFrame(b, fg_color="transparent")
        cont.pack(fill="x", padx=34, pady=14)
        return cont


# =========================================================================
#  Proyecto
# =========================================================================
class PaginaProyecto(Pagina):
    clave = "proyecto"
    titulo = "Proyecto"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.cuerpo.grid_columnconfigure(0, weight=1)
        self.cuerpo.grid_rowconfigure(0, weight=1)
        self.scroll = ui.Desplazable(self.cuerpo, scrollbar_button_color=C["borde"], scrollbar_button_hover_color=C["texto2"], fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure((0, 1), weight=1, uniform="c")

    def al_cambiar_proyecto(self):
        pass

    def refrescar(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        if not self.p:
            self.v_sub.set("Creá un proyecto nuevo importando el presupuesto, o abrí uno existente.")
            self._sin_proyecto()
        else:
            self.v_sub.set(f"Se guarda en: {self.p.ruta}")
            self._con_proyecto()

    def _sin_proyecto(self):
        t = ui.Tarjeta(self.scroll)
        t.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 16))
        etiqueta(t, "Nuevo proyecto", 16, "bold").grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        lb = ctk.CTkLabel(t, text="Importá el presupuesto desde un Excel de una sola hoja. El presupuesto queda de solo "
                                  "lectura y es la base del proyecto.", font=F(12), text_color=C["texto2"],
                          wraplength=420, justify="left", anchor="w")
        lb.grid(row=1, column=0, columnspan=2, sticky="w", padx=20)
        ui.ajustar_texto(lb, t, 44, 160)
        boton(t, "Importar presupuesto…", primario=True, ancho=200, command=self.app.nuevo_proyecto).grid(
            row=2, column=0, sticky="w", padx=20, pady=(14, 20))
        t = ui.Tarjeta(self.scroll)
        t.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 16))
        etiqueta(t, "Abrir proyecto", 16, "bold").grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        lb = ctk.CTkLabel(t, text="Abrí un archivo .ctrlp. Al abrirlo se guarda una copia de seguridad del día.",
                          font=F(12), text_color=C["texto2"], wraplength=420, justify="left", anchor="w")
        lb.grid(row=1, column=0, columnspan=2, sticky="w", padx=20)
        ui.ajustar_texto(lb, t, 44, 160)
        boton(t, "Abrir .ctrlp…", ancho=160, command=self.app.abrir_proyecto).grid(row=2, column=0, sticky="w", padx=20, pady=(14, 20))
        rec = [r for r in core.leer_config().get("recientes", []) if os.path.isfile(r.get("ruta", ""))]
        if rec:
            etiqueta(self.scroll, "Recientes", 15, "bold").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 8))
            t = ui.Tarjeta(self.scroll)
            t.grid(row=2, column=0, columnspan=2, sticky="ew")
            for r in rec:
                caja = t.fila(r.get("nombre", ""), boton(t, "Abrir", ancho=90, command=lambda r=r: self.app.abrir_proyecto(r["ruta"])),
                              f"{r['ruta']}  ·  abierto {r.get('abierto', '')}")

    def _con_proyecto(self):
        p = self.p
        # datos
        etiqueta(self.scroll, "Datos del proyecto", 15, "bold").grid(row=0, column=0, sticky="w", pady=(0, 8))
        t = ui.Tarjeta(self.scroll)
        t.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.vars = {}
        for k, txt in (("nombre", "Nombre del proyecto"), ("propietario", "Propietario"),
                       ("contratista", "Contratista"), ("moneda", "Moneda")):
            v = tk.StringVar(value=p.get_meta(k))
            self.vars[k] = v
            e = ui.entrada_mayus(t, v, 520) if k == "nombre" else entrada(t, v, 520 if k != "moneda" else 120)
            if p.solo_agregar:
                e.configure(state="disabled")
            t.fila(txt, e)
        self.v_sem_proy = tk.StringVar(value=f"De {core.texto_semana(p.inicio_semana)}")
        fs = ctk.CTkFrame(t, fg_color="transparent")
        etiqueta(fs, "", 13, "bold", textvariable=self.v_sem_proy).pack(side="left", padx=(0, 12))
        bs = boton(fs, "Cambiar…", ancho=100, command=self.cambiar_semana)
        bs.pack(side="left")
        if p.solo_agregar:
            bs.configure(state="disabled")
        t.fila("Cortes semanales", fs, "Para Informes («+ Por semana») y las memorias de cálculo.")
        fila = ctk.CTkFrame(t, fg_color="transparent")
        fila.grid(row=99, column=0, columnspan=2, sticky="e", padx=16, pady=(0, 14))
        b = boton(fila, "Guardar cambios", primario=True, ancho=150, command=self.guardar_datos)
        b.pack(side="right")
        if p.solo_agregar:
            b.configure(state="disabled")
        # presupuesto
        etiqueta(self.scroll, "Presupuesto", 15, "bold").grid(row=2, column=0, sticky="w", pady=(20, 8))
        t = ui.Tarjeta(self.scroll)
        t.ancho_ayuda = 260
        t.grid(row=3, column=0, sticky="nsew", padx=(0, 8))
        partidas = [i for i in p.partidas() if i["vigente"]]
        t.fila(f"Versión V{p.version_presupuesto}", etiqueta(t, f"{p.get_meta('moneda', 'US$')} {fmt(p.total_presupuesto())}", 14, "bold"),
               f"{len(partidas)} partidas vigentes")
        b = boton(t, "Actualizar…", ancho=120, command=self.actualizar_presupuesto)
        if p.solo_agregar:
            b.configure(state="disabled")
        t.fila("Presupuesto nuevo", b, "Se vinculan las partidas para no perder avances ni contractuales.")
        # intercambio
        t2 = ui.Tarjeta(self.scroll)
        t2.ancho_ayuda = 260
        t2.grid(row=3, column=1, sticky="nsew", padx=(8, 0))
        self.v_solo = tk.BooleanVar(value=True)
        t2.fila("Solo agregar avance", ui.Interruptor(t2, self.v_solo),
                "Quien reciba la copia podrá registrar avances nuevos, pero no modificar lo anterior.")
        t2.fila("Exportar copia", boton(t2, "Exportar…", ancho=120, command=self.exportar),
                "Un archivo .ctrlp para otra computadora. Tu archivo sigue siendo editable.")
        b = boton(t2, "Importar…", ancho=120, command=self.importar)
        if p.solo_agregar:
            b.configure(state="disabled")
        t2.fila("Importar archivo recibido", b, "Por ejemplo la actualizacion_semanal que te devolvieron. Antes de aplicar se muestra el resumen de cambios.")
        # respaldos
        etiqueta(self.scroll, "Respaldos e historial", 15, "bold").grid(row=4, column=0, sticky="w", pady=(20, 8))
        t = ui.Tarjeta(self.scroll)
        t.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        t.fila("Archivo del proyecto (aquí se guarda tu avance)",
               boton(t, "Mostrar archivo", ancho=130, command=lambda: mostrar_en_carpeta(p.ruta)),
               p.ruta)
        t.fila("Copias de seguridad",
               boton(t, "Abrir carpeta", ancho=130, command=lambda: abrir_en_sistema(core.Proyecto.carpeta_respaldos(p.ruta))),
               "Una foto del proyecto tal como estaba al abrirlo cada día (por si hay que volver atrás). "
               "Ahí NO se guarda lo que registrás después: tu trabajo va al archivo del proyecto.")
        t.fila("Historial de cambios (Excel)",
               boton(t, "Abrir historial", ancho=130, command=lambda: abrir_en_sistema(p.ruta_historial())),
               "Fecha, usuario, versión, qué se modificó, valor anterior y nuevo.")
        f = ctk.CTkFrame(t, fg_color="transparent")
        boton(f, "Abrir otro proyecto…", ancho=170, command=self.app.abrir_proyecto).pack(side="left", padx=(0, 8))
        boton(f, "Nuevo proyecto…", ancho=150, command=self.nuevo).pack(side="left")
        t.fila("Otros proyectos", f)

    def nuevo(self):
        if self.app.cerrar_proyecto():
            self.app.dibujar_lateral()
            self.refrescar()
            self.app.nuevo_proyecto()

    def cambiar_semana(self):
        if elegir_inicio_semana(self.app):
            self.v_sem_proy.set(f"De {core.texto_semana(self.p.inicio_semana)}")
            inf = self.app.paginas.get("informes")
            if inf is not None:
                inf._sin_calcular = True

    def guardar_datos(self):
        self.p.cambiar_datos({k: v.get() for k, v in self.vars.items()})
        self.app.guardar()
        self.app.title(f"Ctrl-P {VERSION} — {os.path.basename(self.p.ruta)}")
        ui.info(self.app, "Datos guardados", "Los datos del proyecto se actualizaron.")

    def actualizar_presupuesto(self):
        ruta = filedialog.askopenfilename(title="Elegí el Excel del presupuesto actualizado", initialdir=ui.carpeta_docs(),
                                          filetypes=[("Excel", "*.xlsx *.xlsm")])
        if ruta:
            AsistenteImportacion(self.app, ruta, modo="actualizar")

    def exportar(self):
        base = os.path.splitext(os.path.basename(self.p.ruta))[0]
        destino = filedialog.asksaveasfilename(title="Exportar copia", defaultextension=core.EXT,
                                               initialfile=(f"{NOMBRE_ACTUALIZACION}{core.EXT}" if self.v_solo.get()
                                                            else f"{base} copia{core.EXT}"),
                                               initialdir=ui.carpeta_docs(),
                                               filetypes=[("Proyecto Ctrl-P", "*.ctrlp")])
        if not destino:
            return
        if os.path.abspath(destino) == os.path.abspath(self.p.ruta):
            ui.info(self.app, "Exportar", "Elegí un nombre distinto al del proyecto abierto.")
            return
        try:
            core.exportar_copia(self.p, destino, self.v_solo.get())
            self.app.guardar()
        except Exception as e:
            ui.info(self.app, "No se pudo exportar", str(e))
            return
        ui.info(self.app, "Copia exportada", f"Se creó:\n{destino}\n\nPodés seguir trabajando normalmente en tu archivo.")

    def importar(self):
        ruta = filedialog.askopenfilename(title="Importar archivo recibido", initialdir=ui.carpeta_docs(), filetypes=[("Proyecto Ctrl-P", "*.ctrlp")])
        if not ruta:
            return
        if os.path.abspath(ruta) == os.path.abspath(self.p.ruta):
            ui.info(self.app, "Importar", "Ese es el archivo que tenés abierto.")
            return
        try:
            imp = core.analizar_importacion(self.p, ruta)
        except core.ErrorCtrlP as e:
            ui.info(self.app, "No se pudo importar", str(e))
            return
        DialogoImportacion(self.app, imp)


# =========================================================================
#  Presupuesto
# =========================================================================
class PaginaPresupuesto(Pagina):
    clave = "presupuesto"
    titulo = "Presupuesto"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.cuerpo.grid_columnconfigure(0, weight=1)
        self.cuerpo.grid_rowconfigure(1, weight=1)
        f = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        f.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.e_buscar = entrada(f, None, 320, placeholder_text="Buscar por código o descripción")
        self.e_buscar.pack(side="left")
        self._job = None
        self.e_buscar.bind("<KeyRelease>", lambda _: self._programar())
        self.v_info = tk.StringVar()
        boton(f, "Agrupar todo", ancho=120, command=lambda: ui.desplegar(self.tv, False)).pack(side="right")
        boton(f, "Desplegar todo", ancho=130, command=lambda: ui.desplegar(self.tv, True)).pack(side="right", padx=8)
        etiqueta(f, "", 12, color="texto2", textvariable=self.v_info).pack(side="left", padx=16)
        cols = [("codigo", "Código", 120, "w"), ("descripcion", "Descripción", 380, "w"), ("unidad", "Unid.", 64, "center"),
                ("cantidad", "Cantidad", 120, "e"), ("pu", "Precio unitario", 120, "e"), ("total", "Total", 140, "e")]
        self.marco, self.tv = ui.tabla(self.cuerpo, cols)
        self.marco.grid(row=1, column=0, sticky="nsew", pady=(0, 24))

    def al_cambiar_tema(self):
        ui.etiquetas_tabla(self.tv)

    def refrescar(self):
        if self.p:
            self.v_sub.set(f"Versión V{self.p.version_presupuesto} · solo lectura · respeta el orden del Excel")
        self.cargar()

    def _programar(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(300, self.cargar)

    def cargar(self):
        self._job = None
        self.tv.delete(*self.tv.get_children())
        if not self.p:
            return
        q = core.clave_texto(self.e_buscar.get())
        items = self.p.items()
        n = 0
        if q:
            for it in items:
                if it["tipo"] == "P" and (q in core.clave_texto(it["descripcion"]) or q in core.clave_texto(it["codigo"])):
                    self._fila("", it)
                    n += 1
            self.v_info.set(f"{n} partidas encontradas")
            return
        nodo = {}
        fuera = None
        for it in items:
            if not it["vigente"]:
                if fuera is None:
                    fuera = self.tv.insert("", "end", values=("", "FUERA DEL PRESUPUESTO VIGENTE (con avance)", "", "", "", ""),
                                           tags=("titulo0",), open=True)
                self._fila(fuera, it, ("fuera",))
                continue
            padre = nodo.get(it["padre"], "")
            nodo[it["id"]] = self._fila(padre, it)
        t = self.p.total_presupuesto()
        self.tv.insert("", "end", values=("", "TOTAL", "", "", "", fmt(t)), tags=("total",))
        self.v_info.set(f"{len([i for i in items if i['tipo'] == 'P' and i['vigente']])} partidas · total {fmt(t)}")

    def _fila(self, padre, it, extra=()):
        if it["tipo"] == "T":
            return self.tv.insert(padre, "end", iid=it["id"], open=it["nivel"] < 1,
                                  values=(it["codigo"], it["descripcion"], "", "", "", fmt(self._total_titulo(it["id"]))),
                                  tags=("titulo0" if not it["padre"] else "titulo",))
        return self.tv.insert(padre, "end", iid=it["id"], values=(
            it["codigo"], it["descripcion"], it["unidad"], fmt(it["cantidad"]), fmt(it["pu"]), fmt(it["total"])), tags=extra)

    def _total_titulo(self, iid):
        if not hasattr(self, "_tot_cache") or self._tot_cache[0] is not self.p or self._tot_cache[2] != self.p.version_presupuesto:
            hijos = {}
            items = self.p.items()
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
            self._tot_cache = (self.p, tot, self.p.version_presupuesto)
        return self._tot_cache[1].get(iid, 0.0)


# =========================================================================
#  Ubicaciones
# =========================================================================
class PaginaUbicaciones(Pagina):
    clave = "ubicaciones"
    titulo = "Ubicaciones"
    subtitulo = "Edificios con sus niveles y áreas sin nivel. Cada combinación es una ubicación donde se registra el avance."

    def __init__(self, master, app):
        super().__init__(master, app)
        self.cuerpo.grid_columnconfigure(0, weight=1)
        self.cuerpo.grid_rowconfigure(0, weight=1)
        self.lista = ui.Desplazable(self.cuerpo, scrollbar_button_color=C["borde"], scrollbar_button_hover_color=C["texto2"], fg_color="transparent")
        self.lista.grid(row=0, column=0, sticky="nsew", padx=(0, 16), pady=(0, 20))
        self.lista.grid_columnconfigure(0, weight=1)
        self.form = ui.Desplazable(self.cuerpo, scrollbar_button_color=C["borde"], scrollbar_button_hover_color=C["texto2"], fg_color=C["tarjeta"], corner_radius=12, border_width=1,
                                           border_color=C["borde"], width=400)
        self.form.grid(row=0, column=1, sticky="ns", pady=(0, 20))
        self.editando = None
        self._tiene_general = False
        self.tramos_area = []
        self.v_tipo = tk.StringVar(value="Nuevo edificio")
        self.v_nombre = tk.StringVar()
        self.v_n = tk.StringVar(value="3")
        self.niveles = []  # lista de [id|None, StringVar]
        self.sotanos = 0
        self.azotea = False
        self._form()

    def _form(self):
        f = self.form
        for w in f.winfo_children():
            w.destroy()
        self.seg = ui.segmentado(f, ["Nuevo edificio", "Nueva área sin nivel"], self.v_tipo, 360, cmd=lambda _: self._form())
        if self.editando:
            etiqueta(f, f"Editar {self.editando['nombre']}", 16, "bold").pack(anchor="w", padx=20, pady=(18, 4))
        else:
            self.seg.pack(padx=20, pady=(18, 8))
        es_area = (self.editando or {}).get("es_area") if self.editando else self.v_tipo.get() != "Nuevo edificio"
        etiqueta(f, "Nombre del área" if es_area else "Nombre del edificio", 13, "bold").pack(anchor="w", padx=20, pady=(10, 4))
        ui.entrada_mayus(f, self.v_nombre, 360).pack(padx=20)
        etiqueta(f, "Se guarda siempre en mayúsculas.", 11, color="texto2").pack(anchor="w", padx=20, pady=(3, 0))
        if es_area:
            etiqueta(f, "Un área sin nivel es una sola ubicación (por ejemplo OBRAS EXTERIORES). Si necesitás "
                        "subdivisiones (SECTOR I → tramo 1, tramo 2…), agregá tramos: cada tramo es una ubicación "
                        "y el área muestra el total.", 12,
                     color="texto2", wraplength=360, justify="left").pack(anchor="w", padx=20, pady=(14, 0))
            fila = ctk.CTkFrame(f, fg_color="transparent")
            fila.pack(fill="x", padx=20, pady=(12, 4))
            etiqueta(fila, "Tramos (opcional)", 13, "bold").pack(side="left")
            boton(fila, "+ tramo", ancho=100, command=self._mas_tramo).pack(side="right")
            for k, (nid, var) in enumerate(self.tramos_area):
                fila = ctk.CTkFrame(f, fg_color="transparent")
                fila.pack(fill="x", padx=20, pady=2)
                ui.entrada_mayus(fila, var, 300).pack(side="left")
                ctk.CTkButton(fila, text="×", width=30, height=30, corner_radius=8, font=F(14), fg_color=C["suave"],
                              hover_color=C["suave_h"], text_color=C["texto"],
                              command=lambda k=k: self._quitar_tramo(k)).pack(side="right")
            if self.editando and self._tiene_general:
                etiqueta(f, f"El avance que ya estaba en {self.editando['nombre']} sin tramo queda en "
                            f"«{self.editando['nombre']} {core.NOMBRE_GENERAL}» para que lo repartas.", 11,
                         color="texto2", wraplength=360, justify="left").pack(anchor="w", padx=20, pady=(6, 0))
        else:
            if not self.editando:
                fila = ctk.CTkFrame(f, fg_color="transparent")
                fila.pack(fill="x", padx=20, pady=(16, 6))
                etiqueta(fila, "Cantidad de niveles", 13, "bold").pack(side="left")
                ui.Contador(fila, self.v_n, 1, 80, cmd=self._regenerar).pack(side="right")
            fila = ctk.CTkFrame(f, fg_color="transparent")
            fila.pack(fill="x", padx=20, pady=(8, 6))
            boton(fila, "+ Agregar sótano", ancho=170, command=self._mas_sotano).pack(side="left")
            boton(fila, "+ Agregar azotea" if not self.editando else "+ Agregar nivel", ancho=170,
                  command=self._mas_azotea if not self.editando else self._mas_nivel).pack(side="right")
            etiqueta(f, "Niveles (de abajo hacia arriba, nombres editables)", 11, color="texto2").pack(anchor="w", padx=20, pady=(8, 4))
            for k, (nid, var) in enumerate(self.niveles):
                fila = ctk.CTkFrame(f, fg_color="transparent")
                fila.pack(fill="x", padx=20, pady=2)
                ui.entrada_mayus(fila, var, 300).pack(side="left")
                ctk.CTkButton(fila, text="×", width=30, height=30, corner_radius=8, font=F(14), fg_color=C["suave"],
                              hover_color=C["suave_h"], text_color=C["texto"],
                              command=lambda k=k: self._quitar(k)).pack(side="right")
        fila = ctk.CTkFrame(f, fg_color="transparent")
        fila.pack(fill="x", padx=20, pady=(18, 20))
        if self.editando:
            boton(fila, "Cancelar", ancho=110, command=self.cancelar).pack(side="left")
            boton(fila, "Guardar cambios", primario=True, ancho=160, command=self.guardar_edicion).pack(side="right")
        else:
            boton(fila, "Crear", primario=True, ancho=360, command=self.crear).pack(fill="x")

    def _mas_tramo(self):
        self.tramos_area.append([None, tk.StringVar(value=f"TRAMO {len(self.tramos_area) + 1}")])
        self._form()

    def _quitar_tramo(self, k):
        self.tramos_area.pop(k)
        self._form()

    def _regenerar(self):
        try:
            n = int(self.v_n.get())
        except ValueError:
            n = 1
        sot = [v.get() for _, v in self.niveles if v.get().startswith("SÓTANO")]
        az = [v.get() for _, v in self.niveles if v.get().startswith("AZOTEA")]
        self.niveles = [[None, tk.StringVar(value=s)] for s in sot]
        self.niveles += [[None, tk.StringVar(value=f"NIVEL {k}")] for k in range(1, n + 1)]
        self.niveles += [[None, tk.StringVar(value=a)] for a in az]
        self._form()

    def _mas_sotano(self):
        sot = [v.get() for _, v in self.niveles if v.get().startswith("SÓTANO")]
        if len(sot) == 1 and sot[0] == "SÓTANO":
            for _, v in self.niveles:
                if v.get() == "SÓTANO":
                    v.set("SÓTANO 1")
            self.niveles.insert(0, [None, tk.StringVar(value="SÓTANO 2")])
        elif sot:
            self.niveles.insert(0, [None, tk.StringVar(value=f"SÓTANO {len(sot) + 1}")])
        else:
            self.niveles.insert(0, [None, tk.StringVar(value="SÓTANO")])
        self._form()

    def _mas_azotea(self):
        if not any(v.get().startswith("AZOTEA") for _, v in self.niveles):
            self.niveles.append([None, tk.StringVar(value="AZOTEA")])
            self._form()

    def _mas_nivel(self):
        n = sum(1 for _, v in self.niveles if v.get().startswith("NIVEL")) + 1
        pos = next((k for k, (_, v) in enumerate(self.niveles) if v.get().startswith("AZOTEA")), len(self.niveles))
        self.niveles.insert(pos, [None, tk.StringVar(value=f"NIVEL {n}")])
        self._form()

    def _quitar(self, k):
        self.niveles.pop(k)
        self.v_n.set(str(sum(1 for _, v in self.niveles if v.get().startswith("NIVEL"))))
        self._form()

    def crear(self):
        if self.p.solo_agregar:
            ui.info(self.app, "Solo agregar avance", "En este archivo no se pueden modificar las ubicaciones.")
            return
        try:
            es_area = self.v_tipo.get() != "Nuevo edificio"
            self.p.crear_edificio(self.v_nombre.get(), [v.get() for _, v in self.niveles], es_area=es_area,
                                  tramos=[v.get() for _, v in self.tramos_area] if es_area else None)
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Ubicaciones", str(e))
            return
        self.app.guardar()
        self.v_nombre.set("")
        self.niveles = []
        self.tramos_area = []
        self._regenerar()
        self.refrescar()

    def editar(self, e):
        self.editando = e
        self.v_nombre.set(e["nombre"])
        nvs = self.p.niveles_de(e["id"])
        self._tiene_general = False
        if e["es_area"]:
            # en un area solo se editan los tramos; la ubicacion general queda aparte
            self._tiene_general = any(n["nombre"] == core.NIVEL_UNICO for n in nvs) and len(nvs) > 1
            self.tramos_area = [[n["id"], tk.StringVar(value=n["nombre"])] for n in nvs
                                if n["nombre"] != core.NIVEL_UNICO]
            self.niveles = []
        else:
            self.niveles = [[n["id"], tk.StringVar(value=n["nombre"])] for n in nvs]
        self._form()

    def cancelar(self):
        self.editando = None
        self.v_nombre.set("")
        self.niveles = []
        self.tramos_area = []
        self._regenerar()

    def guardar_edicion(self):
        try:
            self.p.renombrar_edificio(self.editando["id"], self.v_nombre.get())
            lista = self.tramos_area if self.editando["es_area"] else self.niveles
            self.p.guardar_niveles(self.editando["id"], [(i, v.get()) for i, v in lista])
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Ubicaciones", str(e))
            return
        self.app.guardar()
        self.cancelar()
        self.refrescar()

    def nuevo_tramo(self, e):
        r = ui.dialogo_form(self.app, "Nuevo tramo", f"Subdivisión de {e['nombre']}. Cada tramo es una ubicación "
                            "(contractual, registro, planos e informes) y el área muestra el total.",
                            [("nombre", "Nombre del tramo", False, "")], ("Cancelar", "Agregar tramo"))
        if not r:
            return
        try:
            self.p.agregar_subdivision(e["id"], r["nombre"])
        except core.ErrorCtrlP as ex:
            ui.info(self.app, "Nuevo tramo", str(ex))
            return
        self.app.guardar()
        self.refrescar()

    def eliminar(self, e):
        if not ui.preguntar(self.app, "Eliminar", f"¿Eliminar {e['nombre']}?", si="Eliminar"):
            return
        try:
            self.p.eliminar_edificio(e["id"])
        except core.ErrorCtrlP as ex:
            ui.info(self.app, "Ubicaciones", str(ex))
            return
        self.app.guardar()
        self.refrescar()

    def refrescar(self):
        if not self.niveles and not self.editando:
            self._regenerar()
        for w in self.lista.winfo_children():
            w.destroy()
        if not self.p:
            return
        eds = self.p.edificios()
        edif = [e for e in eds if not e["es_area"]]
        areas = [e for e in eds if e["es_area"]]
        nniv = sum(len(self.p.niveles_de(e["id"])) for e in edif)
        etiqueta(self.lista, f"Edificios  ·  {len(edif)} edificios, {nniv} niveles", 15, "bold").grid(
            row=0, column=0, sticky="w", pady=(0, 8))
        r = 1
        if not edif:
            etiqueta(self.lista, "Todavía no hay edificios. Creá el primero con el formulario de la derecha.", 12,
                     color="texto2").grid(row=r, column=0, sticky="w")
            r += 1
        for e in edif + [None] + areas:
            if e is None:
                etiqueta(self.lista, "Áreas sin nivel", 15, "bold").grid(row=r, column=0, sticky="w", pady=(14, 8))
                r += 1
                continue
            t = ui.Tarjeta(self.lista)
            t.grid(row=r, column=0, sticky="ew", pady=5)
            r += 1
            cab = ctk.CTkFrame(t, fg_color="transparent")
            cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(14, 6))
            nom = etiqueta(cab, e["nombre"], 17, "bold", justify="left")
            if not self.p.solo_agregar:
                boton(cab, "Eliminar", ancho=80, alto=28, command=lambda e=e: self.eliminar(e)).pack(side="right")
                boton(cab, "Editar", ancho=70, alto=28, command=lambda e=e: self.editar(e)).pack(side="right", padx=6)
            nom.pack(side="left", fill="x", expand=True)
            ui.ajustar_texto(nom, cab, lambda c=cab, n=nom: sum(w.winfo_reqwidth() + 8 for w in c.pack_slaves() if w is not n), 100)
            niv = self.p.niveles_de(e["id"])
            if e["es_area"] and self.p.area_simple(e, niv):
                fila_a = ctk.CTkFrame(t, fg_color="transparent")
                fila_a.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 14))
                etiqueta(fila_a, "Una sola ubicación", 12, color="texto2").pack(side="left")
                if not self.p.solo_agregar:
                    boton(fila_a, "+ tramo", ancho=90, alto=28, command=lambda e=e: self.nuevo_tramo(e)).pack(side="right")
            elif e["es_area"]:
                fila_a = ctk.CTkFrame(t, fg_color="transparent")
                fila_a.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 6))
                ntr = sum(1 for n in niv if n["nombre"] != core.NIVEL_UNICO)
                etiqueta(fila_a, f"{ntr} tramo" + ("" if ntr == 1 else "s"), 12, color="texto2").pack(side="left")
                if not self.p.solo_agregar:
                    boton(fila_a, "+ tramo", ancho=90, alto=28, command=lambda e=e: self.nuevo_tramo(e)).pack(side="right")
                chips = ctk.CTkFrame(t, fg_color="transparent", height=1)
                chips.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
                ui.flujo(chips, [ctk.CTkLabel(chips, text=f"   {core.nombre_nivel(e, n)}   ", font=F(11, "bold"),
                                              fg_color=C["suave"], corner_radius=12, text_color=C["texto"], height=26,
                                              width=60) for n in niv], sep=6)
            else:
                etiqueta(t, f"{len(niv)} niveles", 12, color="texto2").grid(row=1, column=0, columnspan=2, sticky="w",
                                                                           padx=18, pady=(0, 6))
                chips = ctk.CTkFrame(t, fg_color="transparent", height=1)
                chips.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
                ui.flujo(chips, [ctk.CTkLabel(chips, text=f"   {n['nombre']}   ", font=F(11, "bold"), fg_color=C["suave"],
                                              corner_radius=12, text_color=C["texto"], height=26, width=60)
                                 for n in niv], sep=6)


# =========================================================================
#  Datos fijos
# =========================================================================
def ancho_arbol(cuerpo):
    """La columna del arbol de partidas toma ~1/3 del ancho: angosta en ventanas chicas, mas descripcion en grandes."""
    def f(_=None):
        w = cuerpo.winfo_width()
        if w > 1:
            esc = ctk.ScalingTracker.get_widget_scaling(cuerpo)
            cuerpo.grid_columnconfigure(0, minsize=int(max(300 * esc, min(520 * esc, w * 0.36))))
    cuerpo.bind("<Configure>", f, add="+")


class ArbolPartidas(ctk.CTkFrame):
    """Arbol del presupuesto con buscador (para elegir partida)."""

    def __init__(self, master, app, al_elegir, columna_extra=None):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.al_elegir = al_elegir
        self.extra = columna_extra
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        fq = ctk.CTkFrame(self, fg_color="transparent")
        fq.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        fq.grid_columnconfigure(0, weight=1)
        self.e_q = entrada(fq, None, 160, placeholder_text="Buscar partida")
        self.e_q.grid(row=0, column=0, sticky="ew")
        for k, (txt, abrir) in enumerate((("Desplegar", True), ("Agrupar", False))):
            ctk.CTkButton(fq, text=txt, width=78, height=30, corner_radius=8, font=F(11), fg_color=C["suave"],
                          hover_color=C["suave_h"], text_color=C["texto"],
                          command=lambda a=abrir: ui.desplegar(self.tv, a)).grid(row=0, column=k + 1, padx=(6, 0))
        self._q = ""
        self._job = None
        self.e_q.bind("<KeyRelease>", lambda _: self._buscar())
        cols = [("codigo", "Código", 90, "w"), ("descripcion", "Descripción", 140, "w")]
        if columna_extra:
            cols.append(("extra", columna_extra, 58, "center"))
        self.marco, self.tv = ui.tabla(self, cols)
        self.tv.column("#0", width=44, minwidth=30, stretch=False)
        for c, *_ in cols:
            self.tv.column(c, stretch=(c == "descripcion"))
        fijas = [c for c, *_ in cols if c != "descripcion"]

        def ajustar_desc(e):
            otras = sum(int(self.tv.column(c, "width")) for c in fijas) + int(self.tv.column("#0", "width"))
            nuevo = max(120, e.width - otras - 4)
            if abs(nuevo - int(self.tv.column("descripcion", "width"))) > 3:
                self.tv.column("descripcion", width=nuevo)
        self.tv.bind("<Configure>", ajustar_desc, add="+")
        self.marco.grid(row=1, column=0, sticky="nsew")
        self.tv.bind("<<TreeviewSelect>>", self._sel)
        self.marcas = {}
        self._ignorar = False

    def _buscar(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self._buscar_ya)

    def _buscar_ya(self):
        self._job = None
        q = self.e_q.get().strip()
        if q != self._q:
            self._q = q
            self.cargar()

    def cargar(self):
        p = self.app.p
        sel = self.tv.selection()
        self.tv.delete(*self.tv.get_children())
        if not p:
            return
        q = core.clave_texto(self._q)
        nodo = {}
        # partidas al 100 % (o mas) de su cantidad: en verde
        ej = {i: sum(v.values()) for i, v in p.ejecutado().items()}
        self.completas = {it["id"] for it in p.items() if it["tipo"] == "P" and (it["cantidad"] or 0) > 1e-9
                          and ej.get(it["id"], 0.0) >= it["cantidad"] * (1 - 5e-5)}
        for it in p.items():
            if not it["vigente"]:
                continue
            ex = (self.marcas.get(it["id"], ""),) if self.extra else ()
            tg = ("completa",) if it["id"] in self.completas else ()
            if q:
                if it["tipo"] == "P" and (q in core.clave_texto(it["descripcion"]) or q in core.clave_texto(it["codigo"])):
                    self.tv.insert("", "end", iid=it["id"], values=(it["codigo"], it["descripcion"]) + ex, tags=tg)
                continue
            padre = nodo.get(it["padre"], "")
            if it["tipo"] == "T":
                nodo[it["id"]] = self.tv.insert(padre, "end", iid=it["id"], values=(it["codigo"], it["descripcion"]) + (("",) if self.extra else ()),
                                                tags=("negrita",), open=False)
            else:
                self.tv.insert(padre, "end", iid=it["id"], values=(it["codigo"], it["descripcion"]) + ex, tags=tg)
        if sel and self.tv.exists(sel[0]):
            self._ignorar = True
            self.ver(sel[0])

    def ver(self, iid):
        if not self.tv.exists(iid):
            return
        p = self.tv.parent(iid)
        while p:
            self.tv.item(p, open=True)
            p = self.tv.parent(p)
        self.tv.selection_set(iid)
        self.tv.see(iid)

    def _sel(self, _=None):
        if self._ignorar:
            self._ignorar = False
            return
        s = self.tv.selection()
        if s:
            it = self.app.p.item(s[0])
            if it and it["tipo"] == "P":
                self.al_elegir(it)

    def actualizar_completa(self, iid):
        p = self.app.p
        it = p.item(iid) if p else None
        if not it or not self.tv.exists(iid):
            return
        tot = sum(p.ejecutado().get(iid, {}).values())
        listo = (it["cantidad"] or 0) > 1e-9 and tot >= it["cantidad"] * (1 - 5e-5)
        tags = [t for t in self.tv.item(iid, "tags") if t != "completa"] + (["completa"] if listo else [])
        self.tv.item(iid, tags=tags)

    def poner_marca(self, iid, texto):
        self.marcas[iid] = texto
        if self.extra and self.tv.exists(iid):
            vals = list(self.tv.item(iid, "values"))
            vals[-1] = texto
            self.tv.item(iid, values=vals)


class PaginaDatosFijos(Pagina):
    clave = "datos"
    titulo = "Datos fijos"
    subtitulo = ("Cantidad contractual de cada actividad por ubicación. Es opcional: donde no se asigne, "
                 "el avance se mide contra el total de la partida.")

    def __init__(self, master, app):
        super().__init__(master, app)
        self.v_modo = tk.StringVar(value="Carga inicial")
        ui.segmentado(self.cab, ["Carga inicial", "Editar datos fijos"], self.v_modo, 300,
                      cmd=lambda _: self.mostrar()).grid(row=0, column=1, rowspan=2, sticky="e")
        self.cuerpo.grid_columnconfigure(1, weight=1)
        self.cuerpo.grid_rowconfigure(0, weight=1)
        self.arbol = ArbolPartidas(self.cuerpo, app, self.elegir, "Estado")
        self.arbol.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        ancho_arbol(self.cuerpo)
        self.panel = ui.Desplazable(self.cuerpo, scrollbar_button_color=C["borde"], scrollbar_button_hover_color=C["texto2"], fg_color="transparent")
        self.panel.grid(row=0, column=1, sticky="nsew")
        self.panel.grid_columnconfigure((0, 1), weight=1, uniform="e")
        b = self.barra_inferior()
        self.v_estado = tk.StringVar()
        le = etiqueta(b, "", 12, color="texto2", textvariable=self.v_estado, justify="left")
        boton(b, "Guardar", primario=True, ancho=130, command=self.guardar).pack(side="right")
        boton(b, "Sugerir ubicaciones…", ancho=180, command=self.sugerir).pack(side="right", padx=8)
        le.pack(side="left", fill="x", expand=True)
        ui.ajustar_texto(le, b, lambda: sum(w.winfo_reqwidth() + 10 for w in b.pack_slaves() if w is not le) + 20, 160)
        self.it = None
        self.vars = {}
        self.hitos_ed, self.tramos_ed, self.equipos_ed = [], {}, {}

    def al_cambiar_tema(self):
        ui.etiquetas_tabla(self.arbol.tv)

    def al_cambiar_proyecto(self):
        self.it = None
        self.arbol.marcas = {}

    def refrescar(self):
        if not self.p:
            return
        self._marcas()
        self.arbol.cargar()
        self.mostrar()

    def _marcas(self):
        cont = self.p.todo_contractual()
        desc = {it["id"] for it, _ in self.p.descuadres()}
        self.arbol.marcas = {}
        for it in self.p.partidas():
            if it["id"] in desc:
                self.arbol.marcas[it["id"]] = "•"
            elif it["id"] in cont:
                self.arbol.marcas[it["id"]] = "✓"

    def elegir(self, it):
        if not self.puede_salir():
            return
        self.it = it
        self.mostrar()

    def puede_salir(self):
        if self.it and self._cambios():
            r = ui.dialogo_texto(self.app, "Cambios sin guardar", "Hay cantidades contractuales sin guardar.",
                                 ("Descartar", "Guardar"), primario=1)
            if r == 1:
                self.guardar()
            elif r is None:
                return False
        return True

    def _cambios(self):
        if self._hitos_cambiados() or self._tramos_cambiados() or self._equipos_cambiados():
            return True
        for v, orig in list(self.vars.values()) + [(x[0], x[1]) for x in getattr(self, "vars_tipo", {}).values()]:
            n = ui.leer_num(v.get())
            if n == "error":
                return True
            if (n is None) != (orig is None) or (n is not None and abs(n - orig) > 1e-9):
                return True
        return False

    # ---- más detalles de la actividad (tramos e hitos)
    def _mas_detalles(self, it, r, bloqueado, fija):
        det = self.p.detalle_de(it["id"])
        t = ui.Tarjeta(self.panel)
        t.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        r += 1
        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(14, 4))
        etiqueta(cab, "Más detalles de la actividad", 14, "bold").pack(side="left")
        caja = ctk.CTkFrame(t, fg_color="transparent")
        caja.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 14))
        self.v_det_tramos = tk.BooleanVar(value=bool(det["tramos"]))
        self.v_det_hitos = tk.BooleanVar(value=bool(det["hitos"]))
        self.v_det_equipos = tk.BooleanVar(value=bool(det["equipos"]))
        for txt, var, ayuda, cmd in (
                ("Desglose por equipos", self.v_det_equipos, "La cantidad de cada ubicación se reparte entre equipos "
                                                             "(ej. UMA-01: 100 ML de ductos). Cada equipo con cantidad "
                                                             "asignada tiene su propio tope de cobro.", self._toggle_equipos),
                ("Por tramos", self.v_det_tramos, "Tuberías, excavaciones, muros… El avance se puede llevar por tramo "
                                                 "(también se dibujan en los planos). Donde no haya tramos, se pone solo la cantidad.",
                 self._toggle_tramos),
                ("Pago por hitos", self.v_det_hitos, "La actividad se reconoce por etapas con su porcentaje (ej. estructura 50 %, "
                                                     "primer forro 17 %…). El avance se ingresa por hito.", self._toggle_hitos)):
            f = ctk.CTkFrame(caja, fg_color="transparent")
            f.pack(anchor="w", fill="x", pady=3)
            cb = ctk.CTkCheckBox(f, text=txt, variable=var, font=F(13, "bold"), text_color=C["texto"],
                                 fg_color=C["acento"], hover_color=C["acento_h"], border_color=C["campo_borde"],
                                 checkbox_width=20, checkbox_height=20, corner_radius=5, command=cmd)
            cb.pack(anchor="w")
            if bloqueado:
                cb.configure(state="disabled")
            lb = ctk.CTkLabel(f, text=ayuda, font=F(11), text_color=C["texto2"], wraplength=560, justify="left",
                              anchor="w")
            lb.pack(anchor="w", padx=(30, 0))
            ui.ajustar_texto(lb, t, 30 + 36 + 20, 200)
        if det["hitos"]:
            r = self._editor_hitos(it, r, bloqueado, det)
        if det["equipos"]:
            r = self._editor_lista(it, r, bloqueado, fija, "equipos")
        if det["tramos"]:
            r = self._editor_lista(it, r, bloqueado, fija, "tramos")
        return r

    def _toggle_equipos(self):
        try:
            self.p.activar_equipos(self.it["id"], self.v_det_equipos.get())
        except core.ErrorCtrlP as e:
            self.v_det_equipos.set(not self.v_det_equipos.get())
            ui.info(self.app, "Desglose por equipos", str(e))
            return
        self.app.guardar()
        self._redibujar()

    def _toggle_tramos(self):
        try:
            self.p.activar_tramos(self.it["id"], self.v_det_tramos.get())
        except core.ErrorCtrlP as e:
            self.v_det_tramos.set(not self.v_det_tramos.get())
            ui.info(self.app, "Por tramos", str(e))
            return
        self.app.guardar()
        self._redibujar()

    def _toggle_hitos(self):
        try:
            self.p.activar_hitos(self.it["id"], self.v_det_hitos.get())
        except core.ErrorCtrlP as e:
            self.v_det_hitos.set(not self.v_det_hitos.get())
            ui.info(self.app, "Pago por hitos", str(e))
            return
        self.app.guardar()
        self._redibujar()

    def _editor_hitos(self, it, r, bloqueado, det):
        t = ui.Tarjeta(self.panel)
        t.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        r += 1
        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(14, 6))
        etiqueta(cab, "Hitos de pago", 14, "bold").pack(side="left")
        self.v_bloq = tk.BooleanVar(value=bool(det["hitos_bloq"]))
        cb = ctk.CTkCheckBox(cab, text="Bloquear porcentajes", variable=self.v_bloq, font=F(12), text_color=C["texto"],
                             fg_color=C["acento"], hover_color=C["acento_h"], border_color=C["campo_borde"],
                             checkbox_width=18, checkbox_height=18, corner_radius=5, command=self._toggle_bloqueo)
        cb.pack(side="right")
        if bloqueado:
            cb.configure(state="disabled")
        self.v_suma_hitos = tk.StringVar()
        etiqueta(cab, "", 12, "bold", "texto2", textvariable=self.v_suma_hitos).pack(side="right", padx=16)
        self.hitos_orig = [(h["id"], h["nombre"], h["pct"], h.get("tipo") or "") for h in self.p.hitos_de(it["id"])]
        if not self.hitos_ed:
            # grupos: [nombre del tipo (StringVar), [[id, nombre, %], ...], suma (StringVar)]
            for tp, hs in self.p.tipos_hito(it["id"]):
                self.hitos_ed.append([tk.StringVar(value=tp), [[h["id"], tk.StringVar(value=h["nombre"]),
                                                               tk.StringVar(value=f"{h['pct']:g}")] for h in hs],
                                      tk.StringVar()])
            if not self.hitos_ed:
                self.hitos_ed = [[tk.StringVar(), [[None, tk.StringVar(), tk.StringVar()]], tk.StringVar()]]
        con_tipos = len(self.hitos_ed) > 1 or bool(self.hitos_ed[0][0].get().strip())
        lista = ctk.CTkFrame(t, fg_color="transparent")
        lista.grid(row=1, column=0, columnspan=2, sticky="w", padx=18)
        fijo = bloqueado or det["hitos_bloq"]
        fila = 0
        for g, (vt, hitos, vsum) in enumerate(self.hitos_ed):
            if con_tipos:
                ft = ctk.CTkFrame(lista, fg_color="transparent")
                ft.grid(row=fila, column=0, columnspan=5, sticky="w", pady=(12 if g else 0, 4))
                etiqueta(ft, "Tipo", 12, "bold").pack(side="left")
                et = entrada(ft, vt, 230, placeholder_text="Nombre del tipo (ej. TABIQUE 1 CARA)")
                et.pack(side="left", padx=(8, 0))
                bt = ctk.CTkButton(ft, text="Quitar tipo", width=96, height=30, corner_radius=8, font=F(12),
                                   fg_color=C["suave"], hover_color=C["suave_h"], text_color=C["texto"],
                                   command=lambda g=g: self._quitar_tipo(g))
                bt.pack(side="left", padx=(10, 0))
                etiqueta(ft, "", 12, "bold", "texto2", textvariable=vsum).pack(side="left", padx=(14, 0))
                if fijo:
                    for w in (et, bt):
                        w.configure(state="disabled")
                fila += 1
            ind = 24 if con_tipos else 0
            etiqueta(lista, "Hito", 11, color="texto2").grid(row=fila, column=0, sticky="w", padx=(ind, 0))
            etiqueta(lista, "% reconocido", 11, color="texto2").grid(row=fila, column=1, sticky="w", padx=8)
            fila += 1
            for k, (hid, vn, vp) in enumerate(hitos):
                en = entrada(lista, vn, 260, placeholder_text="Nombre del hito")
                en.grid(row=fila, column=0, pady=2, padx=(ind, 0), sticky="w")
                ep = entrada(lista, vp, 90, justify="right")
                ep.grid(row=fila, column=1, padx=8, pady=2)
                etiqueta(lista, "%", 12, color="texto2").grid(row=fila, column=2, sticky="w")
                b = ctk.CTkButton(lista, text="×", width=30, height=30, corner_radius=8, font=F(14), fg_color=C["suave"],
                                  hover_color=C["suave_h"], text_color=C["texto"],
                                  command=lambda g=g, k=k: self._quitar_hito(g, k))
                b.grid(row=fila, column=3, padx=(10, 0))
                vp.trace_add("write", lambda *_: self._sumar_hitos())
                if fijo:
                    for w in (en, ep, b):
                        w.configure(state="disabled")
                fila += 1
            if con_tipos:
                b = boton(lista, "+ Agregar hito a este tipo", ancho=200, command=lambda g=g: self._agregar_hito(g))
                b.grid(row=fila, column=0, sticky="w", padx=(ind, 0), pady=(4, 0))
                if fijo:
                    b.configure(state="disabled")
                fila += 1
        pie = ctk.CTkFrame(t, fg_color="transparent")
        pie.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(8, 14))
        botones = []
        if not con_tipos:
            botones.append(boton(pie, "+ Agregar hito", ancho=140, command=lambda: self._agregar_hito(0)))
        botones.append(boton(pie, "+ Agregar tipo", ancho=140, command=self._agregar_tipo))
        for b in botones:
            b.pack(side="left", padx=(0, 8))
            if fijo:
                b.configure(state="disabled")
        ayuda = ("Cada tipo tiene sus hitos y debe sumar 100 %. En cada ubicación, avance equivalente = Σ de todos los tipos "
                 "(cantidad de cada hito × su %). Se guarda con «Guardar»." if con_tipos else
                 "Avance equivalente = Σ (cantidad de cada hito × su %). Con «+ Agregar tipo» se separa por tipos "
                 "(ej. tres tipos de tabique), cada uno con sus hitos. Se guarda con «Guardar».")
        la = ctk.CTkLabel(pie, text=ayuda, font=F(11), text_color=C["texto2"], wraplength=520, justify="left", anchor="w")
        la.pack(side="left", padx=6, fill="x", expand=True)
        ui.ajustar_texto(la, t, lambda: sum(b.winfo_reqwidth() + 8 for b in botones) + 36 + 20, 200)
        self._sumar_hitos()
        return r

    def _sumar_hitos(self):
        con_tipos = len(self.hitos_ed) > 1 or bool(self.hitos_ed[0][0].get().strip())
        todos = True
        tot = 0.0
        for _, hitos, vsum in self.hitos_ed:
            tot = 0.0
            for _, _, vp in hitos:
                n = ui.leer_num(vp.get())
                if isinstance(n, float):
                    tot += n
            ok = abs(tot - 100) < 0.005
            todos = todos and ok
            vsum.set(f"Suma {tot:,.2f} %" + ("  ✓" if ok else "  · debe ser 100 %"))
        if con_tipos:
            self.v_suma_hitos.set(f"{len(self.hitos_ed)} tipos" + ("  ✓" if todos else "  · cada tipo debe sumar 100 %"))
        else:
            self.v_suma_hitos.set(self.hitos_ed[0][2].get())

    def _agregar_hito(self, g):
        self.hitos_ed[g][1].append([None, tk.StringVar(), tk.StringVar()])
        self._redibujar()

    def _agregar_tipo(self):
        self.hitos_ed.append([tk.StringVar(), [[None, tk.StringVar(), tk.StringVar()]], tk.StringVar()])
        self._redibujar()

    def _quitar_tipo(self, g):
        self.hitos_ed.pop(g)
        if not self.hitos_ed:
            self.hitos_ed = [[tk.StringVar(), [[None, tk.StringVar(), tk.StringVar()]], tk.StringVar()]]
        self._redibujar()

    def _quitar_hito(self, g, k):
        self.hitos_ed[g][1].pop(k)
        if not self.hitos_ed[g][1]:
            self.hitos_ed[g][1].append([None, tk.StringVar(), tk.StringVar()])
        self._redibujar()

    def _redibujar(self):
        h, t, e = self.hitos_ed, self.tramos_ed, self.equipos_ed
        vals = {nv: (v.get(), o) for nv, (v, o) in self.vars.items()}
        vals_t = {k: x[0].get() for k, x in getattr(self, "vars_tipo", {}).items()}
        self.mostrar_conservando(h, t, vals, e)
        for k, txt in vals_t.items():
            if k in self.vars_tipo:
                self.vars_tipo[k][0].set(txt)

    def mostrar_conservando(self, hitos, tramos, vals, equipos=None):
        self.hitos_ed, self.tramos_ed, self.equipos_ed = hitos, tramos, equipos or {}
        self.mostrar(conservar=True)
        for nv, (txt, _) in vals.items():
            if nv in self.vars:
                self.vars[nv][0].set(txt)

    def _toggle_bloqueo(self):
        si = self.v_bloq.get()
        if not si:
            ok = ui.preguntar(self.app, "Desbloquear porcentajes",
                              "Si cambiás los porcentajes de los hitos, cambia el avance equivalente de todo lo ya "
                              "registrado en esta partida, incluso de períodos ya estimados.\n\n¿Desbloquear?",
                              si="Desbloquear")
            if not ok:
                self.v_bloq.set(True)
                return
        elif self._hitos_cambiados():
            ui.info(self.app, "Bloquear porcentajes", "Primero guardá los cambios de los hitos.")
            self.v_bloq.set(False)
            return
        self.p.bloquear_hitos(self.it["id"], si)
        self.app.guardar()
        self.mostrar()

    def _lista_hitos(self):
        res = []
        for vt, hitos, _ in self.hitos_ed:
            tp = vt.get().strip()
            for hid, vn, vp in hitos:
                n = ui.leer_num(vp.get())
                if n == "error":
                    raise core.ErrorCtrlP(f"Porcentaje no válido: «{vp.get()}».")
                if vn.get().strip() or n:
                    res.append((hid, vn.get().strip(), n, tp))
        return res

    def _hitos_cambiados(self):
        if not getattr(self, "hitos_ed", None) or not getattr(self, "v_det_hitos", None) or not self.v_det_hitos.get() \
                or not hasattr(self, "hitos_orig"):
            return False
        try:
            nuevo = self._lista_hitos()
        except core.ErrorCtrlP:
            return True
        orig = self.hitos_orig
        if len(nuevo) != len(orig):
            return True
        return any(a[0] != b[0] or a[1] != b[1] or abs((a[2] or 0) - (b[2] or 0)) > 1e-9
                   or core.mayus(a[3]) != core.mayus(b[3]) for a, b in zip(nuevo, orig))

    # ---- equipos y tramos (listas por ubicación con cantidad opcional)
    def _editor_lista(self, it, r, bloqueado, fija, tipo):
        es_eq = tipo == "equipos"
        con_eq = bool(self.p.detalle_de(it["id"])["equipos"])
        t = ui.Tarjeta(self.panel)
        t.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        r += 1
        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(14, 2))
        etiqueta(cab, "Equipos" if es_eq else "Tramos", 14, "bold").pack(anchor="w")
        la = etiqueta(cab, ("Equipos de referencia para el cobro de esta partida (ej. UMA-01, FC-01). Si asignás cantidad, "
                            "es su tope; si no, toma lo disponible del nivel." if es_eq else
                            "Se crean aquí o al marcar en los planos. Si asignás cantidad, es su tope; si no, toma lo "
                            "disponible."), 11, color="texto2", wraplength=640, justify="left")
        la.pack(anchor="w", pady=(2, 0))
        ui.ajustar_texto(la, t, 40, 200)
        orig = {}
        for x in (self.p.equipos_de(it["id"]) if es_eq else self.p.tramos_de(it["id"])):
            orig.setdefault(x["nivel"], []).append(x)
        nombres_eq = {e["id"]: e["nombre"] for e in self.p.equipos_de(it["id"])}
        if es_eq:
            self.equipos_orig = orig
            if not self.equipos_ed:
                self.equipos_ed = {nv: [[x["id"], tk.StringVar(value=x["nombre"]),
                                         tk.StringVar(value=ui.txt_num(x["contractual"]))]
                                        for x in l] for nv, l in orig.items()}
            datos = self.equipos_ed
        else:
            self.tramos_orig = orig
            if not self.tramos_ed:
                self.tramos_ed = {nv: [[x["id"], tk.StringVar(value=x["nombre"]),
                                        tk.StringVar(value=ui.txt_num(x["contractual"])),
                                        tk.StringVar(value=nombres_eq.get(x["equipo"], "(sin equipo)"))]
                                       for x in l] for nv, l in orig.items()}
            datos = self.tramos_ed
        cont = self.p.contractual_de(it["id"])
        lista = ctk.CTkFrame(t, fg_color="transparent")
        lista.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(4, 14))
        fila = 0
        palabra = "equipos" if es_eq else "tramos"
        for u in self.p.ubicaciones():
            if fija and u["nivel"] != fija:
                continue
            nv = u["nivel"]
            filas = datos.get(nv, [])
            f = ctk.CTkFrame(lista, fg_color="transparent")
            f.grid(row=fila, column=0, sticky="w", pady=(6, 2))
            fila += 1
            etiqueta(f, u["etiqueta"], 13, "bold").pack(side="left")
            suma = sum(x for x in (ui.leer_num(fl[2].get()) for fl in filas) if isinstance(x, float))
            info = f"{len(filas)} {palabra}" if filas else f"sin {palabra}"
            if suma:
                info += f" · suman {fmt(suma)}"
                if nv in cont:
                    info += f" de {fmt(cont[nv])} contractual"
                    if es_eq and abs(suma - cont[nv]) > 0.005:
                        info += "  ●"
            etiqueta(f, f"   {info}", 11, color="texto2").pack(side="left")
            b = ctk.CTkButton(f, text="+ Equipo" if es_eq else "+ Tramo", width=84, height=26, corner_radius=8, font=F(12),
                              fg_color=C["suave"], hover_color=C["suave_h"], text_color=C["texto"],
                              command=lambda nv=nv: self._agregar_fila(tipo, nv))
            b.pack(side="left", padx=12)
            if bloqueado:
                b.configure(state="disabled")
            ops_eq = ["(sin equipo)"] + [fl[1].get().strip().upper() for fl in self.equipos_ed.get(nv, [])
                                          if fl[1].get().strip()] if con_eq and not es_eq else None
            for k, fl in enumerate(filas):
                xid, vn, vc = fl[0], fl[1], fl[2]
                ff = ctk.CTkFrame(lista, fg_color="transparent")
                ff.grid(row=fila, column=0, sticky="w", padx=(18, 0), pady=1)
                fila += 1
                en = ui.entrada_mayus(ff, vn, 220, placeholder_text="Nombre")
                en.pack(side="left")
                ec = entrada(ff, vc, 110, justify="right")
                ec.pack(side="left", padx=8)
                ws = [en, ec]
                if ops_eq is not None:
                    if fl[3].get() not in ops_eq:
                        fl[3].set("(sin equipo)")
                    m = ui.menu(ff, ops_eq, fl[3], 150)
                    m.pack(side="left", padx=(0, 8))
                    ws.append(m)
                extra = ""
                if not es_eq and xid:
                    tr = self.p.tramo(xid)
                    extra = " · dibujado en plano" if tr and tr["geom"] else ""
                etiqueta(ff, it["unidad"] + extra, 11, color="texto2").pack(side="left")
                bx = ctk.CTkButton(ff, text="×", width=28, height=28, corner_radius=8, font=F(14), fg_color=C["suave"],
                                   hover_color=C["suave_h"], text_color=C["texto"],
                                   command=lambda nv=nv, k=k: self._quitar_fila(tipo, nv, k))
                bx.pack(side="left", padx=(10, 0))
                ws.append(bx)
                if bloqueado:
                    for w in ws:
                        w.configure(state="disabled")
        return r

    def _agregar_fila(self, tipo, nv):
        if tipo == "equipos":
            self.equipos_ed.setdefault(nv, []).append([None, tk.StringVar(), tk.StringVar()])
        else:
            self.tramos_ed.setdefault(nv, []).append([None, tk.StringVar(), tk.StringVar(), tk.StringVar(value="(sin equipo)")])
        self._redibujar()

    def _quitar_fila(self, tipo, nv, k):
        datos = self.equipos_ed if tipo == "equipos" else self.tramos_ed
        xid = datos[nv][k][0]
        if xid:
            nombre = self.p.nombre_equipo(xid) if tipo == "equipos" else self.p.nombre_tramo(xid)
            if not ui.preguntar(self.app, "Eliminar", f"¿Eliminar {'el equipo' if tipo == 'equipos' else 'el tramo'} "
                                f"{nombre}?", si="Eliminar"):
                return
            try:
                if tipo == "equipos":
                    self.p.eliminar_equipo(xid)
                else:
                    self.p.eliminar_tramo(xid)
            except core.ErrorCtrlP as e:
                ui.info(self.app, "Eliminar", str(e))
                return
            self.app.guardar()
        datos[nv].pop(k)
        self._redibujar()

    def _lista_cambiada(self, datos, orig_por_nv, con_equipo=False):
        orig = {x["id"]: x for l in (orig_por_nv or {}).values() for x in l}
        nombres_eq = {e["id"]: e["nombre"] for e in self.p.equipos_de(self.it["id"])} if con_equipo else {}
        for nv, filas in (datos or {}).items():
            for fl in filas:
                xid, vn, vc = fl[0], fl[1], fl[2]
                c = ui.leer_num(vc.get())
                if xid is None:
                    if vn.get().strip() or c is not None:
                        return True
                    continue
                o = orig.get(xid)
                if not o or core.mayus(vn.get()) != o["nombre"] or c == "error" or \
                        (c is None) != (o["contractual"] is None) or (c is not None and abs(c - o["contractual"]) > 1e-9):
                    return True
                if con_equipo and len(fl) > 3 and fl[3].get() != nombres_eq.get(o.get("equipo"), "(sin equipo)"):
                    return True
        return False

    def _tramos_cambiados(self):
        return self._lista_cambiada(getattr(self, "tramos_ed", None), getattr(self, "tramos_orig", None), True)

    def _equipos_cambiados(self):
        return self._lista_cambiada(getattr(self, "equipos_ed", None), getattr(self, "equipos_orig", None))

    def _guardar_detalles(self):
        n = 0
        iid = self.it["id"]
        if self.v_det_hitos.get() and self.hitos_ed and self._hitos_cambiados():
            if self.p.guardar_hitos(iid, self._lista_hitos()):
                n += 1
        if self.v_det_equipos.get() and self.equipos_ed:
            for nv, filas in self.equipos_ed.items():
                for eid, vn, vc in filas:
                    c = ui.leer_num(vc.get())
                    if c == "error":
                        raise core.ErrorCtrlP(f"Cantidad de equipo no válida: «{vc.get()}».")
                    if eid is None:
                        if vn.get().strip():
                            self.p.crear_equipo(iid, nv, vn.get(), c)
                            n += 1
                        elif c is not None:
                            raise core.ErrorCtrlP("Hay un equipo con cantidad pero sin nombre.")
                    else:
                        o = self.p.equipo(eid)
                        if core.mayus(vn.get()) != o["nombre"] or (c is None) != (o["contractual"] is None) or \
                                (c is not None and abs(c - o["contractual"]) > 1e-9):
                            self.p.editar_equipo(eid, vn.get(), c)
                            n += 1
        if self.v_det_tramos.get() and self.tramos_ed:
            for nv, filas in self.tramos_ed.items():
                ids_eq = {e["nombre"]: e["id"] for e in self.p.equipos_de(iid, nv)}
                for fl in filas:
                    tid, vn, vc = fl[0], fl[1], fl[2]
                    eq = ids_eq.get(fl[3].get(), "") if len(fl) > 3 else ""
                    c = ui.leer_num(vc.get())
                    if c == "error":
                        raise core.ErrorCtrlP(f"Cantidad de tramo no válida: «{vc.get()}».")
                    if tid is None:
                        if vn.get().strip():
                            self.p.crear_tramo(iid, nv, vn.get(), c, equipo=eq)
                            n += 1
                        elif c is not None:
                            raise core.ErrorCtrlP("Hay un tramo con cantidad pero sin nombre.")
                    else:
                        o = self.p.tramo(tid)
                        if core.mayus(vn.get()) != o["nombre"] or (c is None) != (o["contractual"] is None) or \
                                (c is not None and abs(c - o["contractual"]) > 1e-9) or eq != (o["equipo"] or ""):
                            self.p.editar_tramo(tid, vn.get(), c, equipo=eq)
                            n += 1
        return n

    def mostrar(self, conservar=False):
        for w in self.panel.winfo_children():
            w.destroy()
        if not conservar:
            self.hitos_ed, self.tramos_ed, self.equipos_ed = [], {}, {}
        self.vars = {}
        self.vars_tipo = {}
        if not self.p:
            return
        if not self.p.edificios():
            etiqueta(self.panel, "Primero creá las ubicaciones (edificios y áreas).", 14, color="texto2").grid(row=0, column=0, sticky="w")
            return
        if not self.it:
            etiqueta(self.panel, "Elegí una partida en la lista de la izquierda.", 14, color="texto2").grid(row=0, column=0, sticky="w")
            self.v_estado.set(f"{len(self.p.descuadres())} actividades con contractual descuadrado")
            return
        it = self.p.item(self.it["id"])
        self.it = it
        editar = self.v_modo.get() == "Editar datos fijos"
        bloqueado = self.p.solo_agregar
        cont = self.p.contractual_de(it["id"])
        fija = self.p.ubic_fija_de(it["id"])
        asign = sum(cont.values())
        t = ui.Tarjeta(self.panel)
        t.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=14)
        cab.grid_columnconfigure(0, weight=1)
        lc = etiqueta(cab, f"{it['codigo']} · {it['unidad']} · {self.p.get_meta('moneda', 'US$')} {fmt(it['pu'])}", 12,
                      "bold", "acento", justify="left")
        lc.grid(row=0, column=0, sticky="nw")
        ld = ctk.CTkLabel(cab, text=it["descripcion"], font=F(13, "bold"), text_color=C["texto"], wraplength=520,
                          justify="left", anchor="w")
        ld.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ui.ajustar_texto(ld, cab, 12, 240)
        res = ctk.CTkFrame(cab, fg_color="transparent")
        res.grid(row=0, column=1, sticky="e", padx=(16, 0))
        ui.ajustar_texto(lc, cab, lambda: res.winfo_reqwidth() + 24, 90)
        dif = (it["cantidad"] or 0) - asign
        for k, (txt, val) in enumerate((("Cantidad de la partida", it["cantidad"]), ("Asignado", asign),
                                         ("Sin asignar", dif))):
            c = ctk.CTkFrame(res, fg_color="transparent")
            c.grid(row=0, column=k, padx=10)
            etiqueta(c, txt, 11, color="texto2").pack(anchor="e")
            fila = ctk.CTkFrame(c, fg_color="transparent")
            fila.pack(anchor="e")
            if k == 2 and cont and abs(dif) > 0.005:
                ctk.CTkLabel(fila, text="●", font=F(9), text_color=C["punto"]).pack(side="left", padx=(0, 4))
            etiqueta(fila, fmt(val), 15, "bold").pack(side="left")
        # ubicacion fija
        opciones = ["Ninguna (por ubicación)"] + [u["etiqueta"] for u in self.p.ubicaciones()]
        self.v_fija = tk.StringVar(value=self.p.etiqueta_ubicacion(fija) if fija else opciones[0])
        t._base = 2
        m = ui.menu(t, opciones, self.v_fija, 230)
        if bloqueado or (not editar and fija):
            m.configure(state="disabled")
        t.fila("Ubicación fija", m, "Para presupuestos que ya vienen separados: la partida pertenece a una sola ubicación.")
        r = 1
        if fija:
            etiqueta(self.panel, f"Esta partida pertenece solo a {self.p.etiqueta_ubicacion(fija)}; su contractual es la "
                                 f"cantidad de la partida.", 12, color="texto2").grid(row=r, column=0, columnspan=2, sticky="w",
                                                                                      pady=(0, 8))
            r += 1
        r = self._mas_detalles(it, r, bloqueado, fija)
        if fija:
            self.v_estado.set("")
            return
        # tipos de hito (ej. tres tipos de tabique): cantidad por tipo en cada ubicación; la del nivel es la suma
        tipos = [(tp, hs[0]["id"]) for tp, hs in self.p.tipos_hito(it["id"]) if tp]
        cant_t = self.p.cant_tipos_de(it["id"]) if tipos else {}
        k = 0
        for e in self.p.edificios():
            niv = self.p.niveles_de(e["id"])
            tt = ui.Tarjeta(self.panel)
            tt.grid(row=r + k // 2, column=k % 2, sticky="new", padx=(0 if k % 2 == 0 else 6, 6 if k % 2 == 0 else 0), pady=6)
            k += 1
            s = sum(cont.get(n["id"], 0) for n in niv if n["id"] in cont)
            hay = any(n["id"] in cont for n in niv)
            cab = ctk.CTkFrame(tt, fg_color="transparent")
            cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 4))
            etiqueta(cab, e["nombre"], 15, "bold").pack(side="left")
            etiqueta(cab, fmt(s) if hay else "Sin asignar", 14, "bold", "texto" if hay else "texto2").pack(side="right")
            for j, n in enumerate(niv, start=1):
                orig = cont.get(n["id"])
                v = tk.StringVar(value=ui.txt_num(orig))
                self.vars[n["id"]] = (v, orig)
                fila = ctk.CTkFrame(tt, fg_color="transparent")
                fila.grid(row=j, column=0, columnspan=2, sticky="ew", padx=16,
                          pady=(2, 14) if j == len(niv) else (2, 8 if tipos else 2))
                fila.grid_columnconfigure(0, weight=1)
                ln = etiqueta(fila, "Área sin nivel" if self.p.area_simple(e, niv) else core.nombre_nivel(e, n), 13, "bold" if tipos else "normal")
                ln.grid(row=0, column=0, sticky="w")
                en = entrada(fila, v, 130, placeholder_text="Sin asignar", justify="right")
                en.grid(row=0, column=1, sticky="e")
                if bloqueado or (not editar and orig is not None):
                    en.configure(state="disabled")
                if tipos:
                    vt_nv = []
                    for q, (tp, hid0) in enumerate(tipos, start=1):
                        o_t = cant_t.get((n["id"], tp))
                        vt = tk.StringVar(value=ui.txt_num(o_t))
                        self.vars_tipo[(n["id"], hid0)] = (vt, o_t, tp)
                        vt_nv.append(vt)
                        lt = etiqueta(fila, tp, 12, color="texto2", justify="left")
                        lt.grid(row=q, column=0, sticky="w", padx=(18, 8), pady=1)
                        ui.ajustar_texto(lt, fila, 130 + 18 + 16, 80)
                        et = entrada(fila, vt, 110, placeholder_text="Sin asignar", justify="right")
                        et.grid(row=q, column=1, sticky="e", pady=1)
                        if bloqueado or (not editar and o_t is not None):
                            et.configure(state="disabled")

                    def sumar_tipos(*_, v=v, en=en, vt_nv=vt_nv, orig=orig):
                        nums = [ui.leer_num(x.get()) for x in vt_nv]
                        if any(isinstance(x, float) for x in nums):
                            tot = sum(x for x in nums if isinstance(x, float))
                            v.set(ui.txt_num(round(tot, 6)))
                            en.configure(state="disabled")
                        elif not (bloqueado or (not editar and orig is not None)):
                            en.configure(state="normal")
                    for x in vt_nv:
                        x.trace_add("write", sumar_tipos)
                    sumar_tipos()
        if not editar:
            self.v_estado.set("Carga inicial: las cantidades ya guardadas solo se modifican en «Editar datos fijos».")
        else:
            self.v_estado.set("Editar datos fijos: cada cambio queda en el historial.")
        if bloqueado:
            self.v_estado.set("Archivo de «Solo agregar avance»: los datos fijos no se pueden modificar.")

    def guardar(self):
        if not self.p or not self.it or self.p.solo_agregar:
            return
        n_cambios = 0
        try:
            fija_txt = self.v_fija.get() if hasattr(self, "v_fija") else None
            if fija_txt is not None:
                nueva = None
                for u in self.p.ubicaciones():
                    if u["etiqueta"] == fija_txt:
                        nueva = u["nivel"]
                if nueva != self.p.ubic_fija_de(self.it["id"]):
                    self.p.set_ubic_fija(self.it["id"], nueva)
                    n_cambios += 1
            n_cambios += self._guardar_detalles()
            tipo_de = {h["id"]: h.get("tipo") or "" for h in self.p.hitos_de(self.it["id"])}
            for (nv, hid0), (vt, _, _) in getattr(self, "vars_tipo", {}).items():
                tp = tipo_de.get(hid0)
                if not tp:
                    continue
                n = ui.leer_num(vt.get())
                if n == "error":
                    raise core.ErrorCtrlP(f"Cantidad no válida: «{vt.get()}».")
                if self.p.set_cant_tipo(self.it["id"], nv, tp, n):
                    n_cambios += 1
            # con ubicacion fija, el contractual es toda la partida en esa ubicacion
            for nv, (v, orig) in ({} if self.p.ubic_fija_de(self.it["id"]) else self.vars).items():
                n = ui.leer_num(v.get())
                if n == "error":
                    raise core.ErrorCtrlP(f"Cantidad no válida: «{v.get()}».")
                if self.p.set_contractual(self.it["id"], nv, n):
                    n_cambios += 1
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Datos fijos", str(e))
            return
        if n_cambios:
            self.app.guardar()
        self._marcas()
        self.arbol.poner_marca(self.it["id"], self.arbol.marcas.get(self.it["id"], ""))
        self.vars = {}
        self.vars_tipo = {}
        self.mostrar()
        self.app.dibujar_lateral()

    def sugerir(self):
        if not self.p or self.p.solo_agregar:
            return
        sug = self.p.sugerir_ubicaciones()
        if not sug:
            ui.info(self.app, "Sugerir ubicaciones",
                    "No se encontraron partidas cuya descripción mencione una ubicación.\n\n"
                    "Esta opción sirve para presupuestos que ya vienen separados por edificio y nivel.")
            return
        DialogoSugerencias(self.app, sug, self.refrescar)


# =========================================================================
#  Registro de avance
# =========================================================================
class PaginaRegistro(Pagina):
    clave = "registro"
    titulo = "Registro de avance"
    subtitulo = "Elegí la fecha, ingresá lo ejecutado en cada ubicación y guardá."

    def __init__(self, master, app):
        super().__init__(master, app)
        self.totales_viejos = False
        caja = ctk.CTkFrame(self.cab, fg_color="transparent")
        caja.grid(row=0, column=1, rowspan=2, sticky="e")
        etiqueta(caja, "Fecha de registro", 11, color="texto2").grid(row=0, column=1, sticky="w")
        self.v_fecha = tk.StringVar(value=core.fecha_txt(core.hoy_iso()))
        ctk.CTkButton(caja, text="‹", width=32, height=34, corner_radius=8, font=F(16), fg_color=C["suave"],
                      hover_color=C["suave_h"], text_color=C["texto"], command=lambda: self.mover_fecha(-1)).grid(row=1, column=0)
        self.e_fecha = entrada(caja, self.v_fecha, 130, justify="center")
        self.e_fecha.configure(font=F(14, "bold"), height=34)
        self.e_fecha.grid(row=1, column=1, padx=4)
        self.e_fecha.bind("<Return>", lambda _: self.cambiar_fecha())
        self.e_fecha.bind("<FocusOut>", lambda _: self.cambiar_fecha())
        ctk.CTkButton(caja, text="›", width=32, height=34, corner_radius=8, font=F(16), fg_color=C["suave"],
                      hover_color=C["suave_h"], text_color=C["texto"], command=lambda: self.mover_fecha(1)).grid(row=1, column=2)
        boton(caja, "Hoy", ancho=56, command=self.hoy).grid(row=1, column=3, padx=(6, 0))
        self.fecha = core.hoy_iso()
        self.cuerpo.grid_columnconfigure(1, weight=1)
        self.cuerpo.grid_rowconfigure(0, weight=1)
        self.arbol = ArbolPartidas(self.cuerpo, app, self.elegir, "Hoy")
        self.arbol.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        ancho_arbol(self.cuerpo)
        self.panel = ui.Desplazable(self.cuerpo, scrollbar_button_color=C["borde"], scrollbar_button_hover_color=C["texto2"], fg_color="transparent")
        self.panel.grid(row=0, column=1, sticky="nsew")
        self.panel.grid_columnconfigure(0, weight=1)
        b = self.barra_inferior()
        self.v_estado = tk.StringVar(value="")
        self.v_monto = tk.StringVar(value="")
        caja = ctk.CTkFrame(b, fg_color="transparent")
        e1 = etiqueta(caja, "", 13, "bold", textvariable=self.v_estado, justify="left")
        e1.pack(anchor="w")
        e2 = etiqueta(caja, "", 12, color="texto2", textvariable=self.v_monto, justify="left")
        e2.pack(anchor="w")
        derecha = lambda: sum(w.winfo_reqwidth() + 24 for w in b.pack_slaves() if w is not caja)
        ui.ajustar_texto(e1, b, derecha, 160)
        ui.ajustar_texto(e2, b, derecha, 160)
        self.b_guardar = boton(b, "Guardar", primario=True, ancho=130, command=self.guardar)
        self.b_guardar.pack(side="right")
        boton(b, "Descartar", ancho=110, command=self.descartar).pack(side="right", padx=8)
        self.v_obs = tk.BooleanVar(value=app.cfg.get("ver_observaciones", True))
        sw = ctk.CTkFrame(b, fg_color="transparent")
        sw.pack(side="right", padx=(0, 24))
        ui.Interruptor(sw, self.v_obs, comando=self._toggle_obs).pack(side="right")
        etiqueta(sw, "Observaciones", 12, color="texto2").pack(side="right", padx=(0, 8))
        caja.pack(side="left", fill="x", expand=True)
        self.it = None
        self.filas = {}

    def _toggle_obs(self):
        self.app.cfg = core.config_poner(ver_observaciones=bool(self.v_obs.get()))
        if self.it:
            if self.pendientes():
                # conservar lo escrito
                vals = {nv: (f["v"].get(), f["obs"].get()) for nv, f in self.filas.items()}
                self.mostrar()
                for nv, (v, o) in vals.items():
                    if nv in self.filas:
                        self.filas[nv]["v"].set(v)
                        self.filas[nv]["obs"].set(o)
            else:
                self.mostrar()

    def al_cambiar_tema(self):
        ui.etiquetas_tabla(self.arbol.tv)
        if self.it:
            self.mostrar()

    def al_cambiar_proyecto(self):
        self.it = None
        self.filas = {}

    def refrescar(self):
        if not self.p:
            return
        if self.it and self.filas and self.pendientes():
            # hay cantidades escritas sin guardar: se recalculan los totales sin borrar lo escrito
            self.recalcular()
            return
        self._marcas_dia()
        self.arbol.cargar()
        self.mostrar()

    def _marcas_dia(self):
        self.arbol.marcas = {r[0]: "✓" for r in self.p.con.execute(
            "SELECT DISTINCT item FROM avances WHERE fecha=?", (self.fecha,))}

    # ---- fecha
    def cambiar_fecha(self):
        try:
            f = core.txt_a_iso(self.v_fecha.get())
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Fecha", str(e))
            self.v_fecha.set(core.fecha_txt(self.fecha))
            return
        if f == self.fecha:
            self.v_fecha.set(core.fecha_txt(f))
            return
        if not self.puede_salir():
            self.v_fecha.set(core.fecha_txt(self.fecha))
            return
        self.fecha = f
        self.v_fecha.set(core.fecha_txt(f))
        self.refrescar()

    def mover_fecha(self, d):
        import datetime as dt
        nueva = (core.iso_a_fecha(self.fecha) + dt.timedelta(days=d)).isoformat()
        self.v_fecha.set(core.fecha_txt(nueva))
        self.cambiar_fecha()

    def hoy(self):
        self.v_fecha.set(core.fecha_txt(core.hoy_iso()))
        self.cambiar_fecha()

    # ---- partida
    def elegir(self, it):
        if self.it and it["id"] == self.it["id"]:
            return
        if not self.puede_salir():
            self.arbol.ver(self.it["id"])
            return
        self.it = it
        self.mostrar()

    def pendientes(self):
        n = 0
        for f in self.filas.values():
            v = ui.leer_num(f["v"].get())
            o = f["obs"].get().strip()
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

    def puede_salir(self):
        if self.it and self.pendientes():
            r = ui.dialogo_texto(self.app, "Avances sin guardar", f"Hay {self.pendientes()} avances sin guardar en esta partida.",
                                 ("Descartar", "Guardar"), primario=1)
            if r == 1:
                return self.guardar(preguntar_plano=False)
            if r is None:
                return False
            self.filas = {}
        return True

    def mostrar(self):
        for w in self.panel.winfo_children():
            w.destroy()
        self.filas = {}
        self.cabeceras = []
        if not self.p:
            return
        if not self.p.edificios():
            etiqueta(self.panel, "Primero creá las ubicaciones (edificios y áreas) en la sección Ubicaciones.", 14,
                     color="texto2").grid(row=0, column=0, sticky="w")
            self._estado()
            return
        if not self.it:
            etiqueta(self.panel, "Elegí una partida en la lista de la izquierda.", 14, color="texto2").grid(row=0, column=0, sticky="w")
            self._estado()
            return
        p = self.p
        it = p.item(self.it["id"])
        self.it = it
        iid = it["id"]
        calc = core.Calculo(p, self.fecha, self.fecha)
        self.calc_base = calc
        hitos = p.hitos_de(iid)
        con_tramos = bool(p.detalle_de(iid)["tramos"])
        ant_h = p.ejecutado_hojas(iid, hasta=core.dia_anterior(self.fecha))
        plano_h = p.ejecutado_hojas(iid, desde=self.fecha, hasta=self.fecha, marcas=True)
        # cabecera
        t = ui.Tarjeta(self.panel)
        t.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=14)
        cab.grid_columnconfigure(0, weight=1)
        etiqueta(cab, it["codigo"], 12, "bold", "acento").grid(row=0, column=0, sticky="nw")
        ld = ctk.CTkLabel(cab, text=it["descripcion"], font=F(13, "bold"), text_color=C["texto"], wraplength=520,
                          justify="left", anchor="w")
        ld.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ui.ajustar_texto(ld, cab, 12, 240)
        res = ctk.CTkFrame(cab, fg_color="transparent")
        res.grid(row=0, column=1, sticky="e", padx=(16, 0))
        self.v_gen = tk.StringVar()
        for k, (txt, val) in enumerate((("Unidad", it["unidad"]), ("Cantidad total", fmt(it["cantidad"])),
                                         ("Precio unitario", fmt(it["pu"])))):
            c = ctk.CTkFrame(res, fg_color="transparent")
            c.grid(row=0, column=k, padx=10)
            etiqueta(c, txt, 11, color="texto2").pack(anchor="e")
            etiqueta(c, val, 14, "bold").pack(anchor="e")
        c = ctk.CTkFrame(res, fg_color="transparent")
        c.grid(row=0, column=3, padx=10)
        etiqueta(c, "Avance general", 11, color="texto2").pack(anchor="e")
        self.l_gen = etiqueta(c, "", 14, "bold", textvariable=self.v_gen)
        self.l_gen.pack(anchor="e")
        if hitos or con_tramos:
            det = []
            if hitos:
                grupos_h = p.tipos_hito(iid)
                det.append("Pago por hitos: " + "  ·  ".join(
                    (f"{tp}: " if tp else "") + ", ".join(f"{h['nombre']} {h['pct']:.2f} %" for h in hs)
                    for tp, hs in grupos_h))
            if con_tramos:
                det.append("Por tramos")
            ld = ctk.CTkLabel(cab, text="  ·  ".join(det), font=F(11), text_color=C["texto2"], wraplength=640,
                              justify="left", anchor="w")
            ld.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
            ui.ajustar_texto(ld, cab, 16, 200)
        # tabla editable (widgets tk para que sea rapido); con desplazamiento horizontal si la ventana es angosta
        bg = col("tarjeta")
        envol = ui.ScrollH(self.panel, col("fondo"))
        envol.grid(row=1, column=0, sticky="ew")
        tab = tk.Frame(envol.interior, bg=bg, highlightthickness=1, highlightbackground=col("borde"))
        tab.pack(fill="both", expand=True)
        ver_obs = bool(self.v_obs.get())
        anchos = (96, 0, 0, 0, 0, 0, 0, 0, 80)
        titulos = ("Ubicación", "Contractual", "Acum. ant.", "Del día", "Acum. total", "% avance", "",
                   "Saldo", "Observación")
        for k, (tt, a) in enumerate(zip(titulos, anchos)):
            if k == 8 and not ver_obs:
                break
            if k == 6:
                continue
            tab.grid_columnconfigure(k, weight=1 if k == (8 if ver_obs else 0) else 0, minsize=a)
            tk.Label(tab, text=tt, bg=col("subtotal"), fg=col("acento") if k == 3 else col("texto2"),
                     font=TF(9, "bold"), anchor="w" if k in (0, 8) else "e", padx=6, pady=8).grid(row=0, column=k, sticky="nsew")
        self._fila_tab = 1
        self.labels_grupo = {}
        self.label_general = {}
        self.tab = tab
        hoy = p.avances_del_dia(iid, self.fecha)
        cont = p.contractual_de(iid)
        H = hitos or [None]

        def fila_resumen(texto, fondo, bold=True, indent=0):
            r = self._fila_tab
            lab = {}
            lab[0] = tk.Label(tab, text=" " * indent + texto, bg=fondo, fg=col("texto"),
                              font=TF(10, "bold" if bold else "normal"), anchor="w", padx=6, pady=6)
            lab[0].grid(row=r, column=0, sticky="nsew")
            for k in [c for c in range(1, 9 if ver_obs else 8) if c != 6]:
                lab[k] = tk.Label(tab, text="", bg=fondo, fg=col("texto"), font=TF(10, "bold" if bold else "normal"),
                                  anchor="e", padx=6)
                lab[k].grid(row=r, column=k, sticky="nsew")
            self._fila_tab += 1
            return lab

        def fila_hoja(texto, key, base, factor, edificio, indent, contractual_txt, bold=False):
            r = self._fila_tab
            nv, eq, tr, hi = key
            orig = hoy.get(key)
            v = tk.StringVar(value="" if orig is None else ui.txt_num(orig["cantidad"]))
            o = tk.StringVar(value="" if orig is None else (orig["obs"] or ""))
            pl = plano_h.get(key, 0.0)
            etq = " " * indent + texto + (f"  (+{fmt(pl)} en plano)" if abs(pl) > 1e-9 else "")
            tk.Label(tab, text=etq, bg=bg, fg=col("texto"), font=TF(10, "bold" if bold else "normal"), anchor="w",
                     padx=6).grid(row=r, column=0, sticky="nsew")
            tk.Label(tab, text=contractual_txt, bg=bg, fg=col("texto") if contractual_txt not in ("—", "") else col("texto2"),
                     font=TF(10), anchor="e", padx=6).grid(row=r, column=1, sticky="nsew")
            ant = ant_h.get(key, 0.0)
            tk.Label(tab, text=fmt(ant), bg=bg, fg=col("texto"), font=TF(10), anchor="e", padx=6).grid(row=r, column=2, sticky="nsew")
            e = tk.Entry(tab, textvariable=v, justify="right", font=TF(10, "bold"), relief="flat", bg=col("campo"),
                         fg=col("texto"), insertbackground=col("texto"), highlightthickness=1,
                         highlightbackground=col("campo_borde"), highlightcolor=col("acento"), width=9,
                         disabledbackground=col("suave"), disabledforeground=col("texto2"))
            e.grid(row=r, column=3, sticky="ew", padx=6, pady=4, ipady=3)
            lab = {}
            for k in (4, 5, 7):
                lab[k] = tk.Label(tab, text="", bg=bg, fg=col("texto"), font=TF(10), anchor="e", padx=6)
                lab[k].grid(row=r, column=k, sticky="nsew")
            eo = tk.Entry(tab, textvariable=o, font=TF(10), relief="flat", bg=bg, fg=col("texto"), width=6,
                          disabledbackground=col("suave"), disabledforeground=col("texto2"),
                          insertbackground=col("texto"), highlightthickness=1, highlightbackground=col("borde"),
                          highlightcolor=col("acento"))
            if ver_obs:
                eo.grid(row=r, column=8, sticky="ew", padx=6, pady=4, ipady=3)
            if orig is not None and not p.puede_editar_avance(orig):
                e.configure(state="disabled")
                eo.configure(state="disabled")
            self.filas[key] = {"v": v, "obs": o, "orig": orig, "lab": lab, "ant": ant, "plano": pl, "factor": factor,
                               "base": base, "nivel": nv, "edificio": edificio, "entry": e, "es_hito": bool(hi)}
            v.trace_add("write", lambda *_, key=key: self._cambio_fila(key))
            o.trace_add("write", lambda *_: self._estado())
            self._fila_tab += 1
            tk.Frame(tab, height=1, bg=col("linea")).grid(row=self._fila_tab, column=0, columnspan=9, sticky="ew")
            self._fila_tab += 1

        con_equipos = bool(p.detalle_de(iid)["equipos"])
        cant_tipos = p.cant_tipos_de(iid)

        def boton_mas(texto, fila_tk, cmd, fondo):
            b = tk.Label(tab, text=texto, bg=fondo, fg=col("acento"), font=TF(9, "bold"), cursor="hand2", padx=4)
            b.grid(row=fila_tk, column=0, sticky="e", padx=4)
            b.bind("<Button-1>", lambda _: cmd())

        def bloque(nv, eq, base_grupo, edificio, indent):
            """Filas de un grupo (nivel o equipo): tramos (si hay) y dentro hitos (si hay). Devuelve las claves."""
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
                    fila_hoja(txt_tr or "Cantidad", k, base, 1.0, edificio, indent,
                              fmt(tr["contractual"]) if tr else "—")
                    keys.append(k)
                else:
                    keys_tr = []
                    if len(T) > 1:
                        labt = fila_resumen(txt_tr, col("subtotal"), bold=True, indent=indent)
                    ind_h = indent + 3 if len(T) > 1 else indent
                    for tp, hs in p.tipos_hito(iid):
                        ind_t = ind_h
                        base_t = base
                        if tp:
                            labtp = fila_resumen(tp, col("subtotal"), bold=True, indent=ind_h)
                            ind_t = ind_h + 3
                            # sin equipos ni tramos, cada tipo tiene su cantidad contractual en la ubicación
                            if not eid and not tid:
                                base_t = cant_tipos.get((nv, tp))
                        keys_tp = []
                        for h in hs:
                            k = (nv, eid, tid, h["id"])
                            fila_hoja(f"{h['nombre']}", k, base_t, h["pct"] / 100.0, edificio, ind_t, f"{h['pct']:.2f} %")
                            keys_tp.append(k)
                        if tp:
                            self.cabeceras.append({"lab": labtp, "keys": keys_tp,
                                                   "base": base_t if not eid and not tid else None})
                        keys_tr += keys_tp
                    if len(T) > 1:
                        self.cabeceras.append({"lab": labt, "keys": keys_tr, "base": base if tr else None})
                    keys += keys_tr
            return keys

        rangos_nv = []
        for g in calc.detalle_ubicaciones(iid):
            for fl in g["filas"]:
                nv = fl["nivel"]
                nombre = g["nombre"] if g["es_area"] else f"{g['nombre']}  {fl['nombre']}"
                c_nv = fl["contractual"]
                tramos_nv = p.tramos_de(iid, nv, "") if con_tramos else []
                if not con_equipos and not tramos_nv and len(H) == 1:
                    fila_hoja(nombre, (nv, "", "", ""), c_nv, 1.0, g["edificio"], 0, fmt(c_nv), bold=g["es_area"])
                    if con_tramos:
                        boton_mas("+ tramo", self._fila_tab - 2, lambda nv=nv: self.agregar_tramo(nv), bg)
                    continue
                labn = fila_resumen(nombre, col("titulo"))
                fila_nv = self._fila_tab - 1
                if con_equipos:
                    boton_mas("+ equipo", fila_nv, lambda nv=nv: self.agregar_equipo(nv), col("titulo"))
                elif con_tramos:
                    boton_mas("+ tramo", fila_nv, lambda nv=nv: self.agregar_tramo(nv), col("titulo"))
                keys_nv = []
                r0_nv = self._fila_tab
                if not con_equipos:
                    keys_nv = bloque(nv, None, c_nv, g["edificio"], 3)
                else:
                    for eq in [None] + p.equipos_de(iid, nv):
                        txt_eq = f"Equipo {eq['nombre']}" if eq else "Sin equipo"
                        base_eq = (eq["contractual"] or None) if eq else None
                        tiene_tr = bool(p.tramos_de(iid, nv, eq["id"] if eq else "")) if con_tramos else False
                        if not tiene_tr and len(H) == 1:
                            k = (nv, eq["id"] if eq else "", "", "")
                            fila_hoja(txt_eq, k, base_eq if eq else None, 1.0, g["edificio"], 3,
                                      fmt(eq["contractual"]) if eq else "—", bold=bool(eq))
                            if eq and con_tramos:
                                boton_mas("+ tramo", self._fila_tab - 2,
                                          lambda nv=nv, e=eq["id"]: self.agregar_tramo(nv, e), bg)
                            keys_nv.append(k)
                            continue
                        labe = fila_resumen(txt_eq, col("subtotal"), bold=True, indent=3)
                        if eq and con_tramos:
                            boton_mas("+ tramo", self._fila_tab - 1,
                                      lambda nv=nv, e=eq["id"]: self.agregar_tramo(nv, e), col("subtotal"))
                        ks = bloque(nv, eq, base_eq, g["edificio"], 6)
                        self.cabeceras.append({"lab": labe, "keys": ks, "base": base_eq})
                        keys_nv += ks
                self.cabeceras.append({"lab": labn, "keys": keys_nv, "base": c_nv})
                rangos_nv.append((nv, nombre, labn[0], r0_nv, self._fila_tab, len(keys_nv)))
            if not g["es_area"] and len(g["filas"]) > 1:
                self.labels_grupo[g["edificio"]] = fila_resumen(f"Total {g['nombre']}", col("subtotal"))
        self.label_general = fila_resumen("General", col("titulo0"))
        self._plegar_niveles(tab, iid, rangos_nv, {k[0] for k in hoy})
        self.v_nota = tk.StringVar()
        ln = etiqueta(self.panel, "", 12, color="texto2", textvariable=self.v_nota, wraplength=900, justify="left")
        ln.grid(row=2, column=0, sticky="w", pady=(10, 0))
        ui.ajustar_texto(ln, cab, 0, 200)        # cab se borra con la partida: no se acumulan escuchadores
        self.recalcular()

    # Windows no dibuja una ventana de más de 32 767 px de alto: con muchos niveles y detalle (tipos, hitos,
    # tramos…) la tabla se pasaba de eso y se veía en blanco. Entonces el detalle de cada nivel se pliega y se
    # abre con un clic en el nombre del nivel; los niveles con avance en la fecha quedan abiertos.
    ALTO_MAX_TABLA = 22000      # px estimados de detalle a partir de los cuales se pliega

    def _plegar_niveles(self, tab, iid, rangos, con_avance):
        self._pliegue = {}
        n_hojas = sum(r[5] for r in rangos)
        n_resumen = sum(r[4] - r[3] for r in rangos) - 2 * n_hojas
        if n_hojas * 38 + n_resumen * 31 <= self.ALTO_MAX_TABLA:
            return
        por_fila = {}
        for w in tab.grid_slaves():
            por_fila.setdefault(int(w.grid_info()["row"]), []).append(w)
        abiertos = getattr(self, "_abiertos", {}).get(iid)
        if abiertos is None:
            abiertos = set()
            self._abiertos = {iid: abiertos}
        abiertos |= set(con_avance)
        for nv, nombre, lab0, r0, r1, _ in rangos:
            ws = [w for r in range(r0, r1) for w in por_fila.get(r, [])]
            self._pliegue[nv] = (ws, lab0, nombre)
            lab0.configure(cursor="hand2")
            lab0.bind("<Button-1>", lambda _, nv=nv, iid=iid: self._alternar_nivel(iid, nv))
            self._mostrar_nivel(nv, nv in abiertos)

    def _mostrar_nivel(self, nv, abierto):
        ws, lab0, nombre = self._pliegue[nv]
        lab0.configure(text=("▾ " if abierto else "▸ ") + nombre)
        for w in ws:
            if abierto:
                w.grid()
            else:
                w.grid_remove()

    def _alternar_nivel(self, iid, nv):
        abiertos = self._abiertos.setdefault(iid, set())
        abierto = nv not in abiertos
        if abierto:
            abiertos.add(nv)
        else:
            abiertos.discard(nv)
        self._mostrar_nivel(nv, abierto)

    def _guardar_antes(self, titulo):
        if self.pendientes():
            if not ui.preguntar(self.app, titulo, "Primero se guardan los avances escritos. ¿Continuar?", si="Guardar"):
                return False
            if not self.guardar(preguntar_plano=False):
                return False
        return True

    def agregar_equipo(self, nv):
        if not self._guardar_antes("Nuevo equipo"):
            return
        r = ui.dialogo_form(self.app, "Nuevo equipo", f"{self.it['codigo']} · {self.p.etiqueta_ubicacion(nv)}",
                            [("nombre", "Nombre del equipo (ej. UMA-01)", False, ""),
                             ("cant", f"Cantidad asignada en {self.it['unidad']} (opcional, es su tope de cobro)", False, "")],
                            ("Cancelar", "Crear equipo"))
        if not r:
            return
        c = ui.leer_num(r["cant"])
        try:
            if c == "error":
                raise core.ErrorCtrlP("Cantidad no válida.")
            self.p.crear_equipo(self.it["id"], nv, r["nombre"], c)
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Nuevo equipo", str(e))
            return
        self.app.guardar()
        self.mostrar()

    def agregar_tramo(self, nv, equipo=""):
        if not self._guardar_antes("Nuevo tramo"):
            return
        ub = self.p.etiqueta_ubicacion(nv) + (f" · equipo {self.p.nombre_equipo(equipo)}" if equipo else "")
        r = ui.dialogo_form(self.app, "Nuevo tramo", f"{self.it['codigo']} · {ub}",
                            [("nombre", "Nombre del tramo (ej. PV-3 a PV-4)", False, ""),
                             ("cant", f"Cantidad del tramo en {self.it['unidad']} (opcional, es su tope de cobro)", False, "")],
                            ("Cancelar", "Crear tramo"))
        if not r:
            return
        c = ui.leer_num(r["cant"])
        try:
            if c == "error":
                raise core.ErrorCtrlP("Cantidad no válida.")
            self.p.crear_tramo(self.it["id"], nv, r["nombre"], c, equipo=equipo)
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Nuevo tramo", str(e))
            return
        self.app.guardar()
        self.mostrar()

    def _pintar_fila(self, f):
        """Acum. total, % avance y Saldo de una sola fila. Devuelve (ant, del dia, total)."""
        rojo = col("rojo")
        v = ui.leer_num(f["v"].get())
        hoy = 0.0 if v in (None, "error") else v
        raw_tot = f["ant"] + f["plano"] + hoy
        base = f["base"]
        listo = bool(base) and raw_tot >= base * (1 - 5e-5)      # al 100 % o mas: en verde
        verde = col("verde")
        f["lab"][4].configure(text=fmt(raw_tot), fg=verde if listo else col("texto"))
        f["lab"][5].configure(text=fmt_pct(core.pct(raw_tot, base)) if base else "—",
                              fg=verde if listo else (col("texto") if base else col("texto2")))
        saldo = (base - raw_tot) if base else None
        f["lab"][7].configure(text=fmt(saldo), fg=verde if listo else (rojo if saldo is not None and saldo < -1e-9 else
                              (col("texto") if saldo is not None else col("texto2"))),
                              font=TF(10, "bold" if (saldo is not None and saldo < -1e-9) else "normal"))
        f["entry"].configure(highlightbackground=rojo if v == "error" else (col("acento") if hoy else col("campo_borde")))
        return f["ant"], f["plano"] + hoy, raw_tot

    def _cambio_fila(self, key):
        """Al escribir: solo se actualiza esa fila. Los totales se recalculan con Refrescar (F5) o Guardar."""
        f = self.filas.get(key)
        if f is None:
            return
        self._pintar_fila(f)
        self.totales_viejos = True
        self._estado()

    def recalcular(self):
        if not self.it or not self.filas:
            self._estado()
            return
        it = self.it
        cant = it["cantidad"] or 0
        rojo = col("rojo")

        def pinta_saldo(lab, saldo, bold=False):
            lab.configure(text=fmt(saldo), fg=rojo if saldo is not None and saldo < -1e-9 else
                          (col("texto") if saldo is not None else col("texto2")),
                          font=TF(10, "bold" if bold or (saldo is not None and saldo < -1e-9) else "normal"))

        def pinta_listo(labs, total, base):
            """Al 100 % (o mas) de lo contractual: acumulado, % y saldo en verde."""
            if base and total >= base * (1 - 5e-5):
                for k in (4, 5, 7):
                    labs[k].configure(fg=col("verde"))
            else:
                labs[4].configure(fg=col("texto"))
                labs[5].configure(fg=col("texto"))

        vals = {key: self._pintar_fila(f) for key, f in self.filas.items()}
        self.totales_viejos = False

        def eq(keys):
            a = sum(vals[k][0] * self.filas[k]["factor"] for k in keys)
            d = sum(vals[k][1] * self.filas[k]["factor"] for k in keys)
            return a, d, a + d

        for c in self.cabeceras:
            a, d, t_ = eq(c["keys"])
            base = c["base"]
            lab = c["lab"]
            lab[1].configure(text=fmt(base))
            lab[2].configure(text=fmt(a))
            lab[3].configure(text=fmt(d))
            lab[4].configure(text=fmt(t_))
            lab[5].configure(text=fmt_pct(core.pct(t_, base)) if base else "—")
            pinta_saldo(lab[7], (base - t_) if base else None, True)
            pinta_listo(lab, t_, base)
        # por nivel (equivalente)
        por_nv_ant, por_nv_tot = {}, {}
        for key, f in self.filas.items():
            nv = f["nivel"]
            por_nv_ant[nv] = por_nv_ant.get(nv, 0.0) + vals[key][0] * f["factor"]
            por_nv_tot[nv] = por_nv_tot.get(nv, 0.0) + vals[key][2] * f["factor"]
        cont = self.p.contractual_de(it["id"])
        for ed, gl in self.labels_grupo.items():
            nvs = {f["nivel"] for f in self.filas.values() if f["edificio"] == ed}
            conts = [cont[n] for n in nvs if n in cont]
            sc = sum(conts) if conts else None
            a = sum(por_nv_ant[n] for n in nvs)
            t_ = sum(por_nv_tot[n] for n in nvs)
            gl[1].configure(text=fmt(sc))
            gl[2].configure(text=fmt(a))
            gl[3].configure(text=fmt(t_ - a))
            gl[4].configure(text=fmt(t_))
            gl[5].configure(text=fmt_pct(core.pct(t_, sc)) if sc else "—")
            pinta_saldo(gl[7], (sc - t_) if sc is not None else None, True)
            pinta_listo(gl, t_, sc)
        a = sum(por_nv_ant.values())
        t_ = sum(por_nv_tot.values())
        g = self.label_general
        g[1].configure(text=fmt(cant))
        g[2].configure(text=fmt(a))
        g[3].configure(text=fmt(t_ - a))
        g[4].configure(text=fmt(t_))
        g[5].configure(text=fmt_pct(core.pct(t_, cant)))
        pinta_saldo(g[7], cant - t_, True)
        pinta_listo(g, t_, cant)
        self.v_gen.set(fmt_pct(core.pct(t_, cant)))
        self.l_gen.configure(text_color=C["verde"] if cant and t_ >= cant * (1 - 5e-5) else C["texto"])
        # cobrable del dia con topes en cadena (nivel › equipo › tramo)
        eqs, trs = self.p.estructura_topes()
        eqs, trs = eqs.get(it["id"], {}), trs.get(it["id"], {})
        dg_ant, dg_tot = {}, {}
        for key, f in self.filas.items():
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
        if any(f["es_hito"] for f in self.filas.values()):
            notas.append("Con hitos, «Acum.» y «Del día» de las filas de cada ubicación son cantidades equivalentes "
                         "(cantidad × % del hito).")
        if exc_t - exc_a > 1e-9:
            notas.append(f"Con este registro quedan {fmt(exc_t - exc_a)} {it['unidad']} como excedente no cobrable.")
        self.v_nota.set("     ".join(notas))
        self._estado()

    def _estado(self):
        n = self.pendientes() if self.filas else 0
        self.v_estado.set((f"{n} avances sin guardar · {core.fecha_txt(self.fecha)}" if n else
                           f"Fecha de registro: {core.fecha_txt(self.fecha)}") +
                          ("   ·   Totales sin actualizar: tocá Refrescar (F5) o Guardar"
                           if getattr(self, "totales_viejos", False) and self.filas else ""))
        if self.it and self.filas:
            if not getattr(self, "_tp", None) or not getattr(self, "totales_viejos", False):
                self._tp = self.p.total_presupuesto() or 1
            tp = self._tp
            self.v_monto.set(f"Monto cobrable del día en esta partida: {self.p.get_meta('moneda', 'US$')} "
                             f"{fmt(getattr(self, 'monto_dia', 0))} · {fmt_pct(getattr(self, 'monto_dia', 0) / tp, 3)} del presupuesto")
        else:
            self.v_monto.set("")

    def descartar(self):
        self.mostrar()

    def guardar(self, preguntar_plano=True):
        if not self.it:
            return True
        errores = [f["v"].get() for f in self.filas.values() if ui.leer_num(f["v"].get()) == "error"]
        if errores:
            ui.info(self.app, "Registro de avance", f"Hay cantidades no válidas: {', '.join(errores[:3])}")
            return False
        n = 0
        try:
            for (nv, eq, tr, hi), f in self.filas.items():
                v = ui.leer_num(f["v"].get())
                o = f["obs"].get()
                if f["orig"] is None and (v is None or abs(v) < 1e-12) and not o.strip():
                    continue
                if f["orig"] is not None and not self.p.puede_editar_avance(f["orig"]):
                    continue
                if self.p.guardar_avance(self.it["id"], nv, self.fecha, v, o, hito=hi, tramo=tr, equipo=eq):
                    n += 1
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Registro de avance", str(e))
            return False
        if n:
            self.app.guardar()
        self._marcas_dia()
        self.arbol.poner_marca(self.it["id"], self.arbol.marcas.get(self.it["id"], ""))
        self.arbol.actualizar_completa(self.it["id"])
        guardados = list(self.filas.items())
        self.mostrar()
        self.v_estado.set((f"{n} avance guardado" if n == 1 else f"{n} avances guardados") + f" · {core.fecha_txt(self.fecha)}" if n else "Sin cambios para guardar.")
        if n and preguntar_plano:
            niveles = []
            for (nv, eq, tr, hi), f in guardados:
                v = ui.leer_num(f["v"].get())
                if isinstance(v, float) and v > 0 and nv not in niveles and self.p.planos(nv):
                    niveles.append(nv)
            if niveles:
                it = self.it
                r = ui.dialogo_texto(self.app, "¿Marcar en el plano?",
                                     f"{it['codigo']} tiene plano en {', '.join(self.p.etiqueta_ubicacion(x) for x in niveles)}."
                                     "\n\nPodés marcar ahora por dónde va este avance, o dejarlo pendiente y marcarlo "
                                     "después desde Planos.", ("Después", "Marcar ahora"), primario=1)
                if r == 1:
                    self.app.ir("planos")
                    self.app.paginas["planos"].preparar(it["id"], niveles[0], self.fecha)
        return True

# =========================================================================
#  Informes
# =========================================================================
class PaginaInformes(Pagina):
    clave = "informes"
    titulo = "Informes de avance"

    def __init__(self, master, app):
        super().__init__(master, app)
        bot = ctk.CTkFrame(self.cab, fg_color="transparent")
        bot.grid(row=0, column=1, rowspan=2, sticky="e")
        boton(bot, "Corte de estimación", ancho=170, command=self.exportar_corte).pack(side="left", padx=(0, 8))
        boton(bot, "Memorias de cálculo", ancho=170, command=self.memorias).pack(side="left", padx=(0, 8))
        boton(bot, "Exportar a Excel", primario=True, ancho=160, command=self.exportar).pack(side="left")
        self.cuerpo.grid_columnconfigure(0, weight=1)
        self.cuerpo.grid_rowconfigure(3, weight=1)
        # controles
        ctl = ui.Tarjeta(self.cuerpo)
        ctl.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        caja = ctk.CTkFrame(ctl, fg_color="transparent", height=1)
        caja.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=10)
        grupos = []

        def grupo():
            g = ctk.CTkFrame(caja, fg_color="transparent", height=1)
            grupos.append(g)
            return g
        self.v_modo = tk.StringVar(value="Período")
        ui.segmentado(grupo(), ["Estado al", "Período"], self.v_modo, 170, cmd=lambda _: self._modo()).pack(side="left")
        hoy = core.hoy_iso()
        import datetime as dt
        dh = core.iso_a_fecha(hoy)
        inicio_sem = (dh - dt.timedelta(days=(dh.weekday() - core.INICIO_SEMANA) % 7)).isoformat()
        self.v_desde = tk.StringVar(value=core.fecha_txt(inicio_sem))
        self.v_hasta = tk.StringVar(value=core.fecha_txt(hoy))
        fila = grupo()
        self.l_desde = etiqueta(fila, "Desde", 12, color="texto2")
        self.l_desde.pack(side="left", padx=(8, 6))
        self.e_desde = entrada(fila, self.v_desde, 110, justify="center")
        self.e_desde.pack(side="left")
        self.l_hasta = etiqueta(fila, "Hasta", 12, color="texto2")
        self.l_hasta.pack(side="left", padx=(12, 6))
        self.e_hasta = entrada(fila, self.v_hasta, 110, justify="center")
        self.e_hasta.pack(side="left")
        g = grupo()
        etiqueta(g, "Vista", 12, color="texto2").pack(side="left", padx=(8, 6))
        self.v_vista = tk.StringVar(value="Por partida")
        ui.segmentado(g, ["Por partida", "Detallado por ubicación", "Planos marcados"], self.v_vista, 420,
                      cmd=lambda _: self.pedir_generar()).pack(side="left")
        g = grupo()
        self.l_det = etiqueta(g, "Detalle", 12, color="texto2")
        self.l_det.pack(side="left", padx=(8, 6))
        self.v_det = tk.StringVar(value="Sumatoria")
        self.s_det = ui.segmentado(g, ["Sumatoria", "+ Por día", "+ Por semana"], self.v_det, 260,
                                   cmd=lambda _: self.pedir_generar())
        self.s_det.pack(side="left")
        # de que dia a que dia van las semanas (se cambia aqui o en Proyecto; se guarda en el proyecto)
        self.v_sem = tk.StringVar(value="")
        self.l_sem = etiqueta(g, "", 11, color="acento", textvariable=self.v_sem, cursor="hand2")
        self.l_sem.pack(side="left", padx=(8, 0))
        self.l_sem.bind("<Button-1>", lambda _: self.cambiar_semana())
        g = grupo()
        etiqueta(g, "Mostrar", 12, color="texto2").pack(side="left", padx=(8, 6))
        self.v_filtro = tk.StringVar(value="Presupuesto completo")
        ui.segmentado(g, [t for _, t in core.FILTROS], self.v_filtro, 470,
                      cmd=lambda _: self.pedir_generar()).pack(side="left")
        g = grupo()
        self.v_contr = tk.BooleanVar(value=False)
        etiqueta(g, "Ver solo lo contractual", 12, color="texto2").pack(side="left", padx=(8, 8))
        ui.Interruptor(g, self.v_contr, comando=self.pedir_generar).pack(side="left")
        g = grupo()
        boton(g, "Desplegar", ancho=96, command=lambda: self.tv and ui.desplegar(self.tv, True)).pack(
            side="left", padx=(4, 6))
        boton(g, "Agrupar", ancho=90, command=lambda: self.tv and ui.desplegar(self.tv, False)).pack(side="left")
        g = grupo()
        self.b_cols = boton(g, "Columnas", ancho=104, command=self.columnas)
        self.b_cols.pack(side="left", padx=(0, 8))
        boton(g, "Actualizar", primario=True, ancho=110, command=self.generar).pack(side="left")
        self._reflujo = ui.flujo(caja, grupos, sep=10, sep_y=10)
        self.visibles = set(k for k, _ in xl.COLUMNAS_OPCIONALES)
        for e in (self.e_desde, self.e_hasta):
            e.bind("<Return>", lambda _: self.generar())
        # grafica de pastel: anterior / periodo / falta (en monto cobrable)
        self.t_graf = ui.Tarjeta(self.cuerpo)
        self.t_graf.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.cv_pastel = tk.Canvas(self.t_graf, width=118, height=118, highlightthickness=0, bd=0, bg=col("tarjeta"))
        self.cv_pastel.grid(row=0, column=0, rowspan=2, padx=(16, 18), pady=10, sticky="w")
        self.f_ley = ctk.CTkFrame(self.t_graf, fg_color="transparent")
        self.f_ley.grid(row=0, column=1, sticky="w", pady=(14, 0))
        self.v_graf_tit = tk.StringVar()
        etiqueta(self.t_graf, "", 11, color="texto2", textvariable=self.v_graf_tit).grid(row=1, column=1, sticky="nw",
                                                                                        pady=(4, 10))
        fg = ctk.CTkFrame(self.t_graf, fg_color="transparent")
        fg.grid(row=0, column=2, rowspan=2, sticky="ne", padx=14, pady=12)
        etiqueta(fg, "Gráfica", 11, color="texto2").pack(anchor="e")
        self.v_tipo_graf = tk.StringVar(value=app.cfg.get("tipo_grafica", "Dona"))
        ui.menu(fg, list(self.TIPOS_GRAFICA), self.v_tipo_graf, 140, cmd=self._cambiar_tipo_graf).pack(anchor="e")
        self._graf_datos = None
        # indicadores
        kp = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        kp.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        kp.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="k")
        self.kpis = []
        for k in range(5):
            t = ui.Tarjeta(kp)
            t.grid(row=0, column=k, sticky="ew", padx=(0 if k == 0 else 5, 0 if k == 4 else 5))
            a, b, c = tk.StringVar(), tk.StringVar(), tk.StringVar()
            la = etiqueta(t, "", 12, color="texto2", textvariable=a, justify="left")
            la.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
            lb = etiqueta(t, "", 24, "bold", textvariable=b)
            lb.grid(row=1, column=0, sticky="w", padx=16)
            lc = etiqueta(t, "", 12, color="texto2", textvariable=c, justify="left")
            lc.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))
            ui.ajustar_texto(la, t, 34, 80)
            ui.ajustar_texto(lc, t, 34, 80)
            self._kpi_num = getattr(self, "_kpi_num", []) + [lb]
            self.kpis.append((a, b, c))

        def tam_kpi(e):
            tam = 22 if e.width / ctk.ScalingTracker.get_widget_scaling(kp) > 1050 else 17
            if getattr(self, "_tam_kpi", None) != tam:
                self._tam_kpi = tam
                for l in self._kpi_num:
                    l.configure(font=F(tam, "bold"))
        kp.bind("<Configure>", tam_kpi, add="+")
        self.contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self.contenedor.grid(row=3, column=0, sticky="nsew", pady=(0, 20))
        self.contenedor.grid_columnconfigure(0, weight=1)
        self.contenedor.grid_rowconfigure(0, weight=1)
        self.tv = None
        self.marco = None

    def al_cambiar_tema(self):
        if self.tv:
            ui.etiquetas_tabla(self.tv)
        if self._graf_datos:
            self._grafica(*self._graf_datos)

    COLORES_PASTEL = ("#4E79A7", "#16A34A", "#CBD5E1")
    TIPOS_GRAFICA = ("Dona", "Pastel", "Barra 100 %", "Columnas", "Medidor")

    def _cambiar_tipo_graf(self, v):
        self.app.cfg = core.config_poner(tipo_grafica=v)
        if self._graf_datos:
            self._grafica(*self._graf_datos)

    def _grafica(self, partes, mon, titulo):
        """Grafica de porcentajes: ejecutado antes del periodo, cobrado en el periodo y lo que falta."""
        self._graf_datos = (partes, mon, titulo)
        tipo = self.v_tipo_graf.get()
        cv = self.cv_pastel
        fondo, txt, txt2 = col("tarjeta"), col("texto"), col("texto2")
        cv.delete("all")
        total = sum(max(v, 0.0) for _, v in partes) or 1.0
        fr = [max(v, 0.0) / total for _, v in partes]
        avance = fr[0] + fr[1]
        C = self.COLORES_PASTEL
        if tipo in ("Dona", "Pastel"):
            cv.configure(width=118, height=118, bg=fondo)
            ini = 90.0
            for f, c in zip(fr, C):
                ext = 360.0 * f
                if ext >= 359.99:
                    cv.create_oval(6, 6, 112, 112, fill=c, outline="")
                elif ext > 0.05:
                    cv.create_arc(6, 6, 112, 112, start=ini, extent=-ext, fill=c, outline=fondo, width=1)
                ini -= ext
            if tipo == "Dona":
                cv.create_oval(27, 27, 91, 91, fill=fondo, outline="")
                cv.create_text(59, 54, text=f"{avance * 100:,.2f} %", fill=txt, font=(ui.FAM, 9, "bold"))
                cv.create_text(59, 69, text="avance", fill=txt2, font=(ui.FAM, 7))
        elif tipo == "Barra 100 %":
            W, H = 360, 118
            cv.configure(width=W, height=H, bg=fondo)
            x, y0, y1 = 4, 40, 74
            for f, c in zip(fr, C):
                w = (W - 8) * f
                if w > 0.5:
                    cv.create_rectangle(x, y0, x + w, y1, fill=c, outline="")
                x += w
            cv.create_rectangle(4, y0, W - 4, y1, outline=col("borde"))
            cv.create_text(4, 22, text=f"Avance {avance * 100:,.2f} %", anchor="w", fill=txt, font=(ui.FAM, 11, "bold"))
            for k in range(0, 101, 25):
                xx = 4 + (W - 8) * k / 100
                cv.create_line(xx, y1 + 2, xx, y1 + 7, fill=txt2)
                cv.create_text(xx, y1 + 16, text=f"{k} %", fill=txt2, font=(ui.FAM, 7),
                               anchor="w" if k == 0 else ("e" if k == 100 else "center"))
        elif tipo == "Columnas":
            W, H = 230, 118
            cv.configure(width=W, height=H, bg=fondo)
            base, alto = H - 18, H - 34
            cv.create_line(6, base, W - 6, base, fill=col("borde"))
            for k, (f, c) in enumerate(zip(fr, C)):
                x0 = 18 + k * 72
                h = max(2, alto * f) if f > 0 else 0
                if h:
                    cv.create_rectangle(x0, base - h, x0 + 44, base, fill=c, outline="")
                cv.create_text(x0 + 22, base - h - 8, text=f"{f * 100:,.2f} %", fill=txt, font=(ui.FAM, 8, "bold"))
        else:   # Medidor
            W, H = 180, 118
            cv.configure(width=W, height=H, bg=fondo)
            x0, y0, x1, y1 = 10, 14, 170, 174
            ini = 180.0
            for f, c in zip(fr, C):
                ext = 180.0 * f
                if ext > 0.05:
                    cv.create_arc(x0, y0, x1, y1, start=ini, extent=-ext, fill=c, outline=fondo, width=1)
                ini -= ext
            cv.create_arc(x0 + 34, y0 + 34, x1 - 34, y1 - 34, start=0, extent=180, fill=fondo, outline=fondo)
            cv.create_text(90, 78, text=f"{avance * 100:,.2f} %", fill=txt, font=(ui.FAM, 12, "bold"))
            cv.create_text(90, 98, text="avance", fill=txt2, font=(ui.FAM, 8))
        for w in self.f_ley.winfo_children():
            w.destroy()
        for k, ((nombre, v), f, c) in enumerate(zip(partes, fr, C)):
            g = ctk.CTkFrame(self.f_ley, fg_color="transparent")
            g.grid(row=0, column=k, sticky="w", padx=(0, 28))
            fila = ctk.CTkFrame(g, fg_color="transparent")
            fila.pack(anchor="w")
            ctk.CTkFrame(fila, width=12, height=12, corner_radius=3, fg_color=c).pack(side="left", padx=(0, 6))
            etiqueta(fila, nombre, 12, color="texto2").pack(side="left")
            etiqueta(g, f"{f * 100:,.2f} %", 20, "bold").pack(anchor="w")
        self.v_graf_tit.set(titulo)

    def pedir_generar(self, *_):
        """Al tocar varias opciones seguidas se calcula una sola vez, al final (no se amontonan los calculos)."""
        if getattr(self, "_pendiente", None):
            try:
                self.after_cancel(self._pendiente)
            except Exception:
                pass
        self._pendiente = self.after(250, self._generar_pendiente)

    def _generar_pendiente(self):
        self._pendiente = None
        self.generar()

    def _texto_semana(self):
        if self.p:
            self.v_sem.set(f"Semanas: {core.texto_semana(self.p.inicio_semana)} ›")
        else:
            self.v_sem.set("")

    def cambiar_semana(self):
        if not self.p:
            return
        if elegir_inicio_semana(self.app):
            self._texto_semana()
            self.pedir_generar()

    def _modo(self):
        self.after(10, self._reflujo)
        estado = self.v_modo.get() == "Estado al"
        if estado:
            self.l_desde.pack_forget()
            self.e_desde.pack_forget()
            self.l_hasta.configure(text="Fecha")
            self.s_det.configure(state="disabled")
        else:
            self.l_desde.pack(side="left", padx=(8, 6), before=self.l_hasta)
            self.e_desde.pack(side="left", before=self.l_hasta)
            self.l_hasta.configure(text="Hasta")
            self.s_det.configure(state="normal")
        self.pedir_generar()

    def _rango(self):
        hasta = core.txt_a_iso(self.v_hasta.get())
        if self.v_modo.get() == "Estado al":
            return "estado", hasta, hasta
        desde = core.txt_a_iso(self.v_desde.get())
        if desde > hasta:
            raise core.ErrorCtrlP("La fecha «Desde» es posterior a «Hasta».")
        return "periodo", desde, hasta

    def refrescar(self):
        self._texto_semana()
        if self.p:
            self.generar()

    def columnas(self):
        DialogoColumnas(self.app, self.visibles, self._cols_ok)

    def _cols_ok(self, vis):
        self.visibles = vis
        self.b_cols.configure(text=f"Columnas · {len(vis)} de {len(xl.COLUMNAS_OPCIONALES)}")
        self.generar()

    def generar(self):
        if getattr(self, "_pendiente", None):              # un calculo pedido antes ya no hace falta
            try:
                self.after_cancel(self._pendiente)
            except Exception:
                pass
            self._pendiente = None
        if not self.p:
            return
        self._texto_semana()
        if self.app.pagina != "informes":
            # se cambio de pantalla antes de calcular: se calcula al volver (no trabaja escondido)
            self._sin_calcular = True
            return
        self._sin_calcular = False
        try:
            modo, desde, hasta = self._rango()
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Informes", str(e))
            return
        if modo != "estado":
            self.v_desde.set(core.fecha_txt(desde))
        self.v_hasta.set(core.fecha_txt(hasta))
        contr = self.v_contr.get()
        calc = core.Calculo(self.p, desde, hasta, contr)
        t = calc.totales()
        mon = self.p.get_meta("moneda", "US$")
        estado = modo == "estado"
        self.v_sub.set((f"Estado al {core.fecha_txt(hasta)}" if estado else
                        f"Período del {core.fecha_txt(desde)} al {core.fecha_txt(hasta)}") +
                       f" · presupuesto V{self.p.version_presupuesto}" + (" · solo lo contractual" if contr else ""))
        datos = [("Acumulado anterior", fmt_pct(t["p_ant"], 2), f"{mon} {fmt(t['m_ant'])}"),
                 ("Avance financiero del día" if estado else "Avance financiero del período", fmt_pct(t["p_per"], 2), f"{mon} {fmt(t['m_per'])}"),
                 ("Acumulado total", fmt_pct(t["p_tot"], 2), f"{mon} {fmt(t['m_tot'])}"),
                 ("Saldo por ejecutar", fmt_pct(t["p_saldo"], 2), f"{mon} {fmt(t['total'] - t['m_tot'])}"),
                 ("Fuera de lo contractual" if contr else "Excedente no cobrable", f"{mon} {fmt(t['m_exc'])}",
                  f"{sum(1 for i in calc.items if i['tipo'] == 'P' and calc.res[i['id']]['exc_tot'] > 1e-9)} partidas "
                  + ("con avance que no cuenta" if contr else "sobre su contractual"))]
        for (a, b, c), (x, y, z) in zip(self.kpis, datos):
            a.set(x)
            b.set(y)
            c.set(z)
        falta = max(t["total"] - t["m_tot"], 0.0)
        self._grafica([("Ejecutado antes" if not estado else "Ejecutado antes del día", t["m_ant"]),
                       ("Cobrado en el período" if not estado else "Cobrado en el día", t["m_per"]),
                       ("Falta por ejecutar", falta)], mon,
                      "Porcentaje del presupuesto total · montos cobrables (con tope contractual)")
        det = {"+ Por día": "dia", "+ Por semana": "semana"}.get(self.v_det.get(), "")
        cortes = core.buckets(desde, hasta, det, self.p.inicio_semana) if (det and not estado) else []
        if len(cortes) > 62:
            cortes = []
            self.v_det.set("Sumatoria")
            ui.info(self.app, "Detalle", "El período es muy largo para el detalle por día; elegí por semana.")
        if self.v_vista.get() == "Planos marcados":
            self._planos(estado, desde, hasta)
            return
        if getattr(self, "panel_pl", None):
            self.panel_pl.grid_remove()
        if self.v_vista.get() == "Por partida":
            self._por_partida(calc, estado, cortes)
        else:
            self._detallado(calc, estado, cortes)

    # ---- planos marcados por fecha
    def _panel_planos(self):
        if getattr(self, "panel_pl", None):
            return
        self.panel_pl = ctk.CTkFrame(self.contenedor, fg_color=C["tarjeta"], corner_radius=12, border_width=1,
                                     border_color=C["borde"])
        self.panel_pl.grid_columnconfigure(0, weight=1)
        self.panel_pl.grid_rowconfigure(1, weight=1)
        f = ctk.CTkFrame(self.panel_pl, fg_color="transparent")
        f.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        self.v_hoja = tk.StringVar()
        self.m_hoja = ui.menu(f, [""], self.v_hoja, 420, cmd=lambda _: self.generar())
        self.m_hoja.pack(side="left")
        self.v_ub_pl = tk.StringVar(value="Todas las ubicaciones")
        self.m_ub_pl = ui.menu(f, ["Todas las ubicaciones"], self.v_ub_pl, 180, cmd=lambda _: self.generar())
        self.m_ub_pl.pack(side="left", padx=8)
        boton(f, "Exportar…", ancho=104, command=self._exportar_plano).pack(side="right")
        self.v_notas_pl = tk.BooleanVar(value=True)
        ui.Interruptor(f, self.v_notas_pl, comando=self._notas_pl).pack(side="right", padx=(4, 12))
        etiqueta(f, "Notas", 11, color="texto2").pack(side="right", padx=(10, 0))
        f.bind("<Configure>", lambda e: self._ancho_menu_hoja(f), add="+")
        self.b_c_ant = ctk.CTkButton(f, text="Anterior", width=86, height=28, corner_radius=8, font=F(11, "bold"),
                                     text_color="#FFFFFF", command=lambda: self._color_pl("anterior"))
        self.b_c_ant.pack(side="right", padx=(4, 10))
        self.b_c_per = ctk.CTkButton(f, text="Período", width=86, height=28, corner_radius=8, font=F(11, "bold"),
                                     text_color="#FFFFFF", command=lambda: self._color_pl("periodo"))
        self.b_c_per.pack(side="right")
        self.visor_pl = pl.Visor(self.panel_pl, lambda *a: None, lambda *a: None, lambda t: None)
        self.visor_pl.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.v_pl_info = tk.StringVar()
        etiqueta(self.panel_pl, "", 11, color="texto2", textvariable=self.v_pl_info).grid(row=2, column=0, sticky="w",
                                                                                          padx=12, pady=(0, 8))
        self._img_pl = {}

    def _ancho_menu_hoja(self, f):
        """El menu de hojas usa el espacio que dejan los demas controles (sin tapar los botones de color)."""
        try:
            otros = sum(w.winfo_reqwidth() + 12 for w in f.pack_slaves() if w is not self.m_hoja)
            nuevo = int(max(200, min(520, f.winfo_width() - otros - 10)) / ctk.ScalingTracker.get_widget_scaling(f))
            if abs(nuevo - getattr(self, "_ancho_hoja", 0)) > 4:
                self._ancho_hoja = nuevo
                self.m_hoja.configure(width=nuevo)
        except tk.TclError:
            pass

    def _notas_pl(self):
        self.visor_pl.notas = bool(self.v_notas_pl.get())
        self.visor_pl.dibujar()

    def _colores_pl(self):
        cfg = core.leer_config()
        return cfg.get("color_periodo", pl.COLOR_PERIODO), cfg.get("color_anterior", pl.COLOR_ANTERIOR)

    def _color_pl(self, cual):
        cp, ca = self._colores_pl()
        c = pl.elegir_color(self.app, cp if cual == "periodo" else ca,
                            "Color de lo " + ("de la fecha o período" if cual == "periodo" else "anterior"))
        if c:
            self.app.cfg = core.config_poner(**({"color_periodo": c} if cual == "periodo" else {"color_anterior": c}))
            self.generar()

    def _planos(self, estado, desde, hasta):
        self._panel_planos()
        if self.marco:
            self.marco.destroy()
            self.marco, self.tv = None, None
        self.panel_pl.grid(row=0, column=0, sticky="nsew")
        p = self.p
        items = {i["id"]: i for i in p.items()}
        hojas = [h for h in p.hojas_de() if h["item"] in items and p.plano(h["plano"])]
        etqs = {f"{items[h['item']]['codigo']} {items[h['item']]['descripcion'][:34]} · {p.plano(h['plano'])['nombre']}": h
                for h in hojas}
        self.m_hoja.configure(values=list(etqs) or ["(no hay hojas marcadas)"])
        if self.v_hoja.get() not in etqs:
            self.v_hoja.set(next(iter(etqs), "(no hay hojas marcadas)"))
        cp, ca = self._colores_pl()
        self.b_c_per.configure(fg_color=cp, hover_color=cp)
        self.b_c_ant.configure(fg_color=ca, hover_color=ca)
        h = etqs.get(self.v_hoja.get())
        self.hoja_pl = h
        if not h:
            self.visor_pl.limpiar()
            self.v_pl_info.set("Todavía no hay hojas de marcado. Se marcan en la pestaña Planos.")
            return
        nvs = p.plano_niveles(h["plano"])
        ops = ["Todas las ubicaciones"] + [p.etiqueta_ubicacion(n) for n in nvs]
        self.m_ub_pl.configure(values=ops)
        if self.v_ub_pl.get() not in ops:
            self.v_ub_pl.set(ops[0])
        filtro = next((n for n in nvs if p.etiqueta_ubicacion(n) == self.v_ub_pl.get()), None)
        if h["plano"] not in self._img_pl:
            self._img_pl = {h["plano"]: pl.imagen_de(p, h["plano"])}
        if getattr(self, "_pl_cargado", None) != h["plano"] or not self.visor_pl.piramide:
            x = p.plano(h["plano"])
            self.visor_pl.cargar(self._img_pl[h["plano"]], x["escala"], x["unidad"])
            self._pl_cargado = h["plano"]
        hitos = {x["id"]: p.etiqueta_hito(dict(x), False) for x in p.con.execute("SELECT id, nombre, tipo FROM hitos")}
        varias = len(nvs) > 1
        vis = []
        n_per = 0
        for m in p.marcas(h["plano"], item=h["item"]):
            if m["fecha"] > hasta or (filtro and m["nivel"] != filtro):
                continue
            m["color"] = cp if m["fecha"] >= desde else ca
            n_per += m["fecha"] >= desde
            m["nota_txt"] = pl.texto_nota(p, m, items, hitos, p.etiqueta_ubicacion(m["nivel"]) if varias else None)
            vis.append(m)
        tol = max(self.visor_pl.tam) / 300
        for k, a in enumerate(vis):
            for b in vis[k + 1:]:
                if pl.coinciden(a, b, tol):
                    a["color"] = b["color"]
        self.marcas_pl = vis
        self.estilos_pl = {h["item"]: p.estilo_de(h["item"])}
        self.visor_pl.poner_marcas(vis, self.estilos_pl)
        per = core.fecha_txt(hasta) if estado else f"del {core.fecha_txt(desde)} al {core.fecha_txt(hasta)}"
        self.v_pl_info.set(f"{len(vis)} marcas · {n_per} {'de ese día' if estado else 'del período'} ({per}) en el color "
                           "de fecha/período, el resto anterior. Las posteriores no se muestran.")

    def _exportar_plano(self):
        h = getattr(self, "hoja_pl", None)
        if not h:
            return
        try:
            modo, desde, hasta = self._rango()
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Informes", str(e))
            return
        p = self.p
        x = p.plano(h["plano"])
        it = p.item(h["item"])
        ruta = filedialog.asksaveasfilename(title="Exportar plano marcado", defaultextension=".pdf",
                                            initialfile=f"{it['codigo']} - {x['nombre']} - {hasta}.pdf",
                                            initialdir=ui.carpeta_docs(),
                                            filetypes=[("PDF", "*.pdf"), ("Imagen PNG", "*.png")])
        if not ruta:
            return
        cp, ca = self._colores_pl()
        per = core.fecha_txt(hasta) if modo == "estado" else f"Del {core.fecha_txt(desde)} al {core.fecha_txt(hasta)}"
        try:
            pl.exportar_imagen(p, h["plano"], self.marcas_pl, self.estilos_pl, ruta, p.nombre,
                               f"{it['codigo']} {it['descripcion'][:70]} · {x['nombre']} · {p.etiqueta_plano_ubic(h['plano'])}"
                               + ("" if self.v_ub_pl.get().startswith("Todas") else f" · {self.v_ub_pl.get()}"),
                               [(cp, per), (ca, "Anterior")], notas=bool(self.v_notas_pl.get()))
        except Exception as e:
            ui.info(self.app, "Exportar", f"No se pudo exportar:\n{e}")
            return
        if ui.preguntar(self.app, "Plano exportado", f"Se guardó:\n{ruta}", si="Abrir", no="Cerrar"):
            abrir_en_sistema(ruta)

    def _filtro(self):
        return {t: k for k, t in core.FILTROS}.get(self.v_filtro.get(), "completo")

    def _nueva_tabla(self, izq, centro, der):
        if getattr(self, "panel_pl", None):
            self.panel_pl.grid_remove()
        if self.marco:
            self.marco.destroy()
        self.marco, self.tv = ui.tabla_fija(self.contenedor, izq, centro, der)
        self.marco.grid(row=0, column=0, sticky="nsew")

    def _por_partida(self, calc, estado, cortes):
        vis = self.visibles
        izq = [("codigo", "Código", 82, "w"), ("descripcion", "Descripción", 280, "w")]
        if "unidad" in vis:
            izq.append(("unidad", "Unid.", 48, "center"))
        if "cantidad" in vis:
            izq.append(("cantidad", "Cantidad", 88, "e"))
        if not estado and "ant" in vis:
            izq.append(("ant", "Acum. anterior", 100, "e"))
        if not estado and "p_ant" in vis:
            izq.append(("p_ant", "% ant.", 72, "e"))
        centro, ex_b = [], []
        contr = self.v_contr.get()
        for k, (et, b0, b1) in enumerate(cortes):
            centro.append((f"b{k}", et, 88, "e"))
            ex_b.append(self.p.ejecutado_periodo(b0, b1, contr))
        if not estado and "p_per" in vis:
            centro.append(("p_per", "% período", 76, "e"))
        centro.append(("aporte", "% aporte", 74, "e"))
        der = [("per", "Ejecutado del día" if estado else "Período", 92, "e")]
        if "tot" in vis:
            der.append(("tot", "Acum. a la fecha" if estado else "Acum. total", 100, "e"))
        if "p_tot" in vis:
            der.append(("p_tot", "%", 72, "e"))
        if "saldo" in vis:
            der.append(("saldo", "Saldo", 88, "e"))
        der.append(("m_per", "Monto del día" if estado else "Monto período", 106, "e"))
        self._nueva_tabla(izq, centro, der)
        tv = self.tv
        keys = [c[0] for c in izq + centro + der]
        tp = calc.total_presu or 1
        filtro = self._filtro()
        visibles = calc.visibles(filtro)
        nodo = {}
        for it in calc.items:
            if it["id"] not in visibles:
                continue
            r = calc.res[it["id"]]
            padre = nodo.get(it["padre"], "") if it["padre"] else ""
            if padre and not tv.exists(padre):
                padre = ""
            if it["tipo"] == "T":
                vals = {k: "" for k in keys}
                vals.update(codigo=it["codigo"], descripcion=it["descripcion"], m_per=fmt(r["m_per"]),
                            aporte=fmt_pct(r["m_per"] / tp, 3))
                nodo[it["id"]] = tv.insert(padre, "end", iid=it["id"], values=[vals[k] for k in keys],
                                           tags=("titulo0" if not it["padre"] else "titulo",),
                                           open=(filtro != "completo") or not it["padre"])
                continue
            vals = {"codigo": it["codigo"], "descripcion": it["descripcion"] + ("" if it["vigente"] else "  [fuera del presupuesto]"),
                    "unidad": it["unidad"], "cantidad": fmt(r["cantidad"]), "ant": fmt(r["ant"]), "p_ant": fmt_pct(r["p_ant"]),
                    "per": fmt(r["per"]), "p_per": fmt_pct(r["p_per"]), "tot": fmt(r["tot"]), "p_tot": fmt_pct(r["p_tot"]),
                    "saldo": fmt(r["saldo"]), "m_per": fmt(r["m_per"]), "aporte": fmt_pct(r["m_per"] / tp, 3)}
            for k in range(len(cortes)):
                vals[f"b{k}"] = fmt(sum(ex_b[k].get(it["id"], {}).values()))
            tags = []
            if core.completa(r):
                tags.append("completa")
            elif r["saldo"] < -1e-9:
                tags.append("neg")
            if not it["vigente"]:
                tags.append("fuera")
            tv.insert(padre, "end", iid=it["id"], values=[vals.get(k, "") for k in keys], tags=tuple(tags))
        if not any(i in visibles for i in calc.res if calc.por_id[i]["tipo"] == "P"):
            vals = {k: "" for k in keys}
            vals["descripcion"] = "No hay actividades con este filtro en estas fechas."
            tv.insert("", "end", values=[vals[k] for k in keys])
        t = calc.totales()
        vals = {k: "" for k in keys}
        vals.update(descripcion="TOTAL DEL PROYECTO", m_per=fmt(t["m_per"]), aporte=fmt_pct(t["p_per"], 3))
        tv.insert("", "end", values=[vals[k] for k in keys], tags=("total",))

    def _detallado(self, calc, estado, cortes):
        vis = self.visibles
        izq = [("codigo", "Código", 82, "w"), ("descripcion", "Actividad / ubicación", 280, "w")]
        if "unidad" in vis:
            izq.append(("unidad", "Unid.", 48, "center"))
        if "cantidad" in vis:
            izq.append(("cont", "Contractual", 88, "e"))
        if not estado and "ant" in vis:
            izq.append(("ant", "Acum. anterior", 100, "e"))
        centro, ex_b = [], []
        contr = self.v_contr.get()
        for k, (et, b0, b1) in enumerate(cortes):
            centro.append((f"b{k}", et, 88, "e"))
            ex_b.append(self.p.ejecutado_periodo(b0, b1, contr))
        if "p_tot" in vis:
            centro += [("p_ed", "% edificio", 78, "e"), ("p_gen", "% general", 78, "e")]
        if "obs" in vis:
            centro.append(("obs", "Observaciones", 260, "w"))
        der = [("per", "Ejecutado del día" if estado else "Período", 92, "e")]
        if "tot" in vis:
            der.append(("tot", "Acum. a la fecha" if estado else "Acum. total", 100, "e"))
        if "p_tot" in vis:
            der.append(("p_nivel", "%", 72, "e"))
        if "saldo" in vis:
            der.append(("saldo", "Saldo", 88, "e"))
        self._nueva_tabla(izq, centro, der)
        tv = self.tv
        keys = [c[0] for c in izq + centro + der]
        obs = self.p.observaciones(calc.desde, calc.hasta) if "obs" in vis else {}
        filtro = self._filtro()
        visibles = calc.visibles(filtro)

        def cubetas(iid, niveles):
            return {f"b{k}": fmt(sum(ex_b[k].get(iid, {}).get(nv, 0.0) for nv in niveles)) for k in range(len(cortes))}
        nodo = {}
        n = 0
        for it in calc.items:
            if it["id"] not in visibles:
                continue
            padre = nodo.get(it["padre"], "") if it["padre"] else ""
            if padre and not tv.exists(padre):
                padre = ""
            if it["tipo"] == "T":
                vals = {k: "" for k in keys}
                vals.update(codigo=it["codigo"], descripcion=it["descripcion"])
                nodo[it["id"]] = tv.insert(padre, "end", iid=it["id"], values=[vals[k] for k in keys],
                                           tags=("titulo0" if not it["padre"] else "titulo",),
                                           open=(filtro != "completo") or not it["padre"])
                continue
            r = calc.res[it["id"]]
            n += 1
            vals = {"codigo": it["codigo"], "descripcion": it["descripcion"], "unidad": it["unidad"], "cont": fmt(r["cantidad"]),
                    "ant": fmt(r["ant"]), "per": fmt(r["per"]), "tot": fmt(r["tot"]), "p_gen": fmt_pct(r["p_tot"]),
                    "saldo": fmt(r["saldo"])}
            vals.update(cubetas(it["id"], set(r["nv_tot"]) | set(r["cont"])))
            tags = ("negrita", "completa") if core.completa(r) else ("negrita",)
            pid = tv.insert(padre, "end", iid=it["id"], values=[vals.get(k, "") for k in keys], tags=tags,
                            open=filtro != "completo")
            for g in calc.detalle_ubicaciones(it["id"]):
                for fl in g["filas"]:
                    if abs(fl["tot"]) < 1e-9 and abs(fl["per"]) < 1e-9 and fl["contractual"] is None:
                        continue
                    nombre = g["nombre"] if g["es_area"] else f"{g['nombre']} {fl['nombre']}"
                    o = " | ".join(obs.get((it["id"], fl["nivel"]), []))
                    vals = {"descripcion": "   " + nombre, "unidad": it["unidad"], "cont": fmt(fl["contractual"]),
                            "ant": fmt(fl["ant"]), "per": fmt(fl["per"]), "tot": fmt(fl["tot"]),
                            "p_nivel": fmt_pct(fl["p_nivel"]), "saldo": fmt(fl["saldo"]), "obs": o}
                    vals.update(cubetas(it["id"], [fl["nivel"]]))
                    if fl["contractual"] and fl["tot"] >= fl["contractual"] * (1 - 5e-5):
                        tags = ("completa",)
                    else:
                        tags = ("neg",) if fl["saldo"] is not None and fl["saldo"] < -1e-9 else ()
                    nid = tv.insert(pid, "end", values=[vals.get(k, "") for k in keys], tags=tags, open=True)
                    for h in fl.get("hojas", []):
                        base = h["contractual"] if h["contractual"] else (fl["contractual"] if not h["tramo"] else None)
                        sal = (base - h["tot"]) if base else None
                        vals = {"descripcion": "         " + h["nombre"], "unidad": it["unidad"],
                                "cont": f"{h['factor'] * 100:.2f} %" if h["hito"] else fmt(h["contractual"]),
                                "ant": fmt(h["ant"]), "per": fmt(h["per"]), "tot": fmt(h["tot"]),
                                "p_nivel": fmt_pct(core.pct(h["tot"], base)) if base else "", "saldo": fmt(sal) if base else ""}
                        tv.insert(nid, "end", values=[vals.get(k, "") for k in keys],
                                  tags=("fuera",) + (("neg",) if sal is not None and sal < -1e-9 else ()))
                if not g["es_area"] and (abs(g["tot"]) > 1e-9 or g["contractual"]):
                    vals = {"descripcion": f"   Total {g['nombre']}", "unidad": it["unidad"], "cont": fmt(g["contractual"]),
                            "ant": fmt(g["ant"]), "per": fmt(g["per"]), "tot": fmt(g["tot"]),
                            "p_ed": fmt_pct(g["p_edificio"]), "p_gen": fmt_pct(g["p_general"]), "saldo": fmt(g["saldo"])}
                    vals.update(cubetas(it["id"], [fl["nivel"] for fl in g["filas"]]))
                    tags = ("subtotal", "neg") if g["saldo"] is not None and g["saldo"] < -1e-9 else ("subtotal",)
                    tv.insert(pid, "end", values=[vals.get(k, "") for k in keys], tags=tags)
        if not n:
            vals = {k: "" for k in keys}
            vals["descripcion"] = "No hay actividades con este filtro en estas fechas."
            tv.insert("", "end", values=[vals[k] for k in keys])

    def exportar(self):
        if not self.p:
            return
        try:
            modo, desde, hasta = self._rango()
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Informes", str(e))
            return
        base = os.path.splitext(os.path.basename(self.p.ruta))[0]
        nombre = (f"{base} - Estado al {hasta}" if modo == "estado" else f"{base} - Período {desde} a {hasta}") + ".xlsx"
        ruta = filedialog.asksaveasfilename(title="Exportar informe", defaultextension=".xlsx", initialfile=nombre,
                                            initialdir=ui.carpeta_docs(), filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        det = {"+ Por día": "dia", "+ Por semana": "semana"}.get(self.v_det.get(), "")
        dlg = DialogoProgreso(self.app, "Exportar a Excel", "Preparando el informe…")
        try:
            xl.exportar_informe(self.p, ruta, modo, desde, hasta, det, self.visibles, self._filtro(),
                                self.v_contr.get(), progreso=dlg.avanzar, guardar=dlg.guardar_en_fondo)
        except PermissionError:
            dlg.cerrar()
            ui.info(self.app, "Exportar", "No se pudo guardar: el archivo está abierto en Excel. Cerralo y volvé a intentar.")
            return
        except Exception:
            dlg.cerrar()
            raise
        dlg.cerrar()
        if ui.preguntar(self.app, "Informe exportado", f"Se guardó:\n{ruta}", si="Abrir", no="Cerrar"):
            abrir_en_sistema(ruta)

    def memorias(self):
        """Memorias de cálculo: una pestaña por actividad del filtro elegido, con cortes cada 7 días."""
        if not self.p:
            return
        try:
            modo, desde, hasta = self._rango()
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Memorias de cálculo", str(e))
            return
        if modo == "estado":
            desde = hasta
        n = xl.contar_memorias(self.p, modo, desde, hasta, self._filtro(), self.v_contr.get())
        if not n:
            ui.info(self.app, "Memorias de cálculo", f"No hay actividades con «{self.v_filtro.get()}» en estas fechas.")
            return
        sem = mc.semanas(desde, hasta, self.p.inicio_semana)
        r = ui.dialogo_texto(
            self.app, "Memorias de cálculo",
            f"Una pestaña por cada actividad de «Mostrar: {self.v_filtro.get()}»: {n} actividad"
            f"{'es' if n != 1 else ''}.\n\nPeríodo del {core.fecha_txt(desde)} al {core.fecha_txt(hasta)} "
            f"(se incluyen los dos días), {len(sem)} semana{'s' if len(sem) != 1 else ''} "
            f"de {core.texto_semana(self.p.inicio_semana)}."
            + ("\nSolo lo contractual: activado." if self.v_contr.get() else "")
            + ("\n\nSon muchas pestañas: el archivo puede quedar pesado. Con «Mostrar: Con avance» salen menos."
               if n > 150 else "")
            + "\n\n«Solo memorias» saca un archivo liviano solo con las memorias. «Informe + memorias» agrega "
              "las memorias al informe de siempre.",
            ("Cancelar", "Informe + memorias", "Solo memorias"), 2)
        if r not in (1, 2):
            return
        r += 1                      # 2 = informe + memorias, 3 = solo memorias
        base = os.path.splitext(os.path.basename(self.p.ruta))[0]
        nombre = (f"{base} - Memorias de cálculo {desde} a {hasta}" if r == 3 else
                  f"{base} - Informe y memorias {desde} a {hasta}") + ".xlsx"
        ruta = filedialog.asksaveasfilename(title="Memorias de cálculo", defaultextension=".xlsx", initialfile=nombre,
                                            initialdir=ui.carpeta_docs(), filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        dlg = DialogoProgreso(self.app, "Memorias de cálculo", "Preparando las memorias…")
        try:
            if r == 3:
                xl.exportar_memorias(self.p, ruta, modo, desde, hasta, self._filtro(), self.v_contr.get(),
                                     progreso=dlg.avanzar, guardar=dlg.guardar_en_fondo)
            else:
                det = {"+ Por día": "dia", "+ Por semana": "semana"}.get(self.v_det.get(), "")
                xl.exportar_informe(self.p, ruta, modo, desde, hasta, det, self.visibles, self._filtro(),
                                    self.v_contr.get(), progreso=dlg.avanzar, guardar=dlg.guardar_en_fondo,
                                    memorias=True)
        except PermissionError:
            dlg.cerrar()
            ui.info(self.app, "Exportar", "No se pudo guardar: el archivo está abierto en Excel. Cerralo y volvé a intentar.")
            return
        except Exception:
            dlg.cerrar()
            raise
        dlg.cerrar()
        if ui.preguntar(self.app, "Memorias de cálculo", f"Se guardó:\n{ruta}", si="Abrir", no="Cerrar"):
            abrir_en_sistema(ruta)

    def exportar_corte(self):
        if not self.p:
            return
        try:
            modo, desde, hasta = self._rango()
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Corte de estimación", str(e))
            return
        n = xl.contar_memorias(self.p, modo, desde, hasta, self._filtro(), self.v_contr.get())
        r = ui.dialogo_texto(
            self.app, "Corte de estimación",
            "El corte lleva el presupuesto completo con la cantidad y el monto cobrables "
            + (f"del día {core.fecha_txt(hasta)}" if desde == hasta else
               f"del {core.fecha_txt(desde)} al {core.fecha_txt(hasta)}") + "."
            + (f"\n\n«Corte + memorias» agrega la memoria de cálculo de cada actividad de «Mostrar: "
               f"{self.v_filtro.get()}» ({n}), con una sola columna «ESTE PERÍODO» (la suma del período, sin "
               "semanas)." if n else "")
            + ("\n\nSon muchas pestañas: con «Mostrar: Con avance» salen menos." if n > 150 else ""),
            ("Cancelar", "Corte + memorias", "Solo el corte") if n else ("Cancelar", "Solo el corte"),
            2 if n else 1)
        if not r:
            return
        con_memorias = bool(n) and r == 1
        base = os.path.splitext(os.path.basename(self.p.ruta))[0]
        ruta = filedialog.asksaveasfilename(title="Corte de estimación", defaultextension=".xlsx",
                                            initialfile=(f"{base} - Corte de estimación del día {hasta}"
                                                         if desde == hasta else
                                                         f"{base} - Corte de estimación {desde} a {hasta}")
                                            + (" con memorias" if con_memorias else "") + ".xlsx",
                                            initialdir=ui.carpeta_docs(), filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        dlg = DialogoProgreso(self.app, "Corte de estimación", "Preparando el corte…")
        try:
            xl.exportar_corte(self.p, ruta, desde, hasta, self.v_contr.get(), progreso=dlg.avanzar,
                              guardar=dlg.guardar_en_fondo, memorias=con_memorias, filtro=self._filtro())
        except PermissionError:
            dlg.cerrar()
            ui.info(self.app, "Exportar", "No se pudo guardar: el archivo está abierto en Excel. Cerralo y volvé a intentar.")
            return
        except Exception:
            dlg.cerrar()
            raise
        dlg.cerrar()
        if ui.preguntar(self.app, "Corte de estimación",
                        "Se guardó el presupuesto completo con la cantidad y el monto cobrables " +
                        (f"del día {core.fecha_txt(hasta)}" if desde == hasta else
                         f"del {core.fecha_txt(desde)} al {core.fecha_txt(hasta)}") + f":\n{ruta}", si="Abrir", no="Cerrar"):
            abrir_en_sistema(ruta)


# =========================================================================
#  Planos
# =========================================================================
class PaginaPlanos(Pagina):
    clave = "planos"
    titulo = "Planos"
    subtitulo = ("Librería de planos y registro de avance. Cada actividad marca en su propia hoja; los colores son por "
                 "edificio (en Informes se ven por fecha).")

    def __init__(self, master, app):
        super().__init__(master, app)
        bot = ctk.CTkFrame(self.cab, fg_color="transparent")
        bot.grid(row=0, column=1, rowspan=2, sticky="e")
        self.b_lib = boton(bot, "Librería de planos…", primario=True, ancho=190, command=lambda: DialogoLibreria(app, self))
        self.b_lib.pack(side="left")
        self.cuerpo.grid_columnconfigure(1, weight=1)
        self.cuerpo.grid_rowconfigure(1, weight=1)
        # ---- panel izquierdo
        izq = ui.Tarjeta(self.cuerpo)
        izq.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 12), pady=(0, 6))
        izq.grid_columnconfigure(0, weight=1)
        izq.grid_rowconfigure(2, weight=3, minsize=130)
        izq.grid_rowconfigure(5, weight=1, minsize=80)
        f = ctk.CTkFrame(izq, fg_color="transparent")
        f.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
        self.v_lbl_fecha = tk.StringVar(value="Fecha")
        etiqueta(f, "", 11, color="texto2", textvariable=self.v_lbl_fecha).pack(side="left")
        self.v_fecha = tk.StringVar(value=core.fecha_txt(core.hoy_iso()))
        self.e_fecha = entrada(f, self.v_fecha, 104, justify="center")
        self.e_fecha.pack(side="left", padx=(8, 0))
        self.v_acum = tk.BooleanVar(value=False)
        etiqueta(f, "Por acumulado", 11, color="texto2").pack(side="right")
        ui.Interruptor(f, self.v_acum, comando=self._cambiar_acum).pack(side="right", padx=(0, 6))
        for ev in ("<Return>", "<FocusOut>"):
            self.e_fecha.bind(ev, lambda _: self.cargar_actividades())
        self.v_resumen = tk.StringVar()
        etiqueta(izq, "", 11, color="texto2", textvariable=self.v_resumen, wraplength=300, justify="left").grid(
            row=1, column=0, sticky="w", padx=14, pady=(4, 2))
        cols = [("desc", "Actividad del día", 200, "w"), ("falta", "Sin marcar", 80, "e")]
        m1, self.tv_act = ui.tabla(izq, cols)
        self.tv_act.configure(height=3)       # alto minimo chico: el espacio extra se reparte con los pesos
        self.tv_act.column("#0", width=26, minwidth=22)
        m1.grid(row=2, column=0, sticky="nsew", padx=8)
        self.tv_act.bind("<<TreeviewSelect>>", lambda _: self._elegir_act())
        boton(izq, "Otra actividad…", ancho=150, command=self.otra_actividad).grid(row=3, column=0, sticky="w", padx=14, pady=(6, 4))
        etiqueta(izq, "Hojas de la actividad", 13, "bold").grid(row=4, column=0, sticky="w", padx=14, pady=(6, 2))
        cols = [("plano", "Plano · alcance", 200, "w"), ("n", "Marcas", 70, "e")]
        m2, self.tv_hojas = ui.tabla(izq, cols, arbol=False)
        self.tv_hojas.configure(height=2)
        m2.grid(row=5, column=0, sticky="nsew", padx=8)
        self.tv_hojas.bind("<<TreeviewSelect>>", lambda _: self._elegir_hoja())
        fb = ctk.CTkFrame(izq, fg_color="transparent")
        fb.grid(row=6, column=0, sticky="ew", padx=14, pady=(6, 4))
        self.b_nueva = boton(fb, "Nueva hoja limpia…", ancho=150, command=self.nueva_hoja)
        self.b_nueva.pack(side="left")
        self.b_estilo = boton(fb, "Estilo…", ancho=76, command=self.estilo)
        self.b_estilo.pack(side="right")
        self.b_quitar_hoja = boton(fb, "Quitar hoja", ancho=86, command=self.quitar_hoja)
        self.b_quitar_hoja.pack(side="right", padx=(0, 6))
        self.tv_hojas.bind("<Delete>", lambda _: self.quitar_hoja())
        self.f_nivel = ctk.CTkFrame(izq, fg_color="transparent")
        self.f_nivel.grid(row=7, column=0, sticky="ew", padx=14, pady=(4, 12))
        etiqueta(self.f_nivel, "Marcando en", 11, color="texto2").pack(side="left")
        self.v_nivel = tk.StringVar()
        self.m_nivel = ui.menu(self.f_nivel, [""], self.v_nivel, 200, cmd=lambda _: self._estado_hoja())
        self.m_nivel.pack(side="left", padx=(6, 0))
        izq.configure(width=340)
        # ---- barra del plano
        ctl = ui.Tarjeta(self.cuerpo)
        ctl.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        f1 = ctk.CTkFrame(ctl, fg_color="transparent")
        f1.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 2))
        self.v_titulo = tk.StringVar()
        lt = etiqueta(f1, "", 13, "bold", textvariable=self.v_titulo, justify="left")
        lt.pack(side="left", fill="x", expand=True)
        for txt, cmd in (("+", lambda: self.visor.zoom_centro(1.4)), ("Ajustar", lambda: self.visor.ajustar()),
                         ("−", lambda: self.visor.zoom_centro(1 / 1.4))):
            ctk.CTkButton(f1, text=txt, width=34 if len(txt) == 1 else 70, height=28, corner_radius=8, font=F(13),
                          fg_color=C["suave"], hover_color=C["suave_h"], text_color=C["texto"], command=cmd).pack(
                side="right", padx=(6, 0))
        self.v_escala = tk.StringVar()
        etiqueta(f1, "", 11, color="texto2", textvariable=self.v_escala).pack(side="right", padx=10)
        lt.pack_forget()
        lt.pack(side="left", fill="x", expand=True)
        ui.ajustar_texto(lt, f1, lambda: sum(w.winfo_reqwidth() + 10 for w in f1.pack_slaves() if w is not lt) + 10, 120)
        f2 = ctk.CTkFrame(ctl, fg_color="transparent", height=1)
        f2.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 8))
        self.v_herr = tk.StringVar(value="Mover")
        usar = lambda v: self.visor.usar(dict(pl.HERRAMIENTAS)[v])
        grupos = (("Mover", "Editar"), ("Línea", "Línea libre", "Polígono", "Área libre"), ("Rectángulo", "Círculo", "Punto"),
                  ("Calibrar",))
        ui.flujo(f2, [ui.segmentado(f2, list(g), self.v_herr, cmd=usar) for g in grupos], sep=8)
        self.f_leyenda = ctk.CTkFrame(ctl, fg_color="transparent", height=1)
        self.f_leyenda.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        f3 = ctk.CTkFrame(ctl, fg_color="transparent", height=1)
        f3.grid(row=2, column=1, sticky="e", padx=12, pady=(0, 8))
        self.v_iman = tk.BooleanVar(value=True)
        etiqueta(f3, "Imán", 11, color="texto2").pack(side="left", padx=(0, 6))
        ui.Interruptor(f3, self.v_iman, comando=self._iman).pack(side="left")
        self.v_notas = tk.BooleanVar(value=True)
        etiqueta(f3, "Notas", 11, color="texto2").pack(side="left", padx=(16, 6))
        ui.Interruptor(f3, self.v_notas, comando=self._notas).pack(side="left")
        marco = ctk.CTkFrame(self.cuerpo, fg_color=C["tarjeta"], corner_radius=12, border_width=1, border_color=C["borde"])
        marco.grid(row=1, column=1, sticky="nsew", pady=(0, 6))
        marco.grid_columnconfigure(0, weight=1)
        marco.grid_rowconfigure(0, weight=1)
        self.visor = pl.Visor(marco, self.al_terminar, self.al_seleccionar, self.al_estado)
        self.visor.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.visor.al_editar = self.al_mover_marca
        self.visor.al_borrar = self.anular
        self.visor.al_doble = self.editar
        self.vacio = etiqueta(marco, "", 14, color="texto2", justify="center")
        b = self.barra_inferior()
        self.v_estado = tk.StringVar()
        self.l_estado = etiqueta(b, "", 12, color="texto2", textvariable=self.v_estado, wraplength=560, justify="left")
        ui.ajustar_texto(self.l_estado, b, lambda: sum(w.winfo_reqwidth() + 10 for w in b.pack_slaves()
                                                       if w is not self.l_estado) + 20, 200)
        self.b_anular = boton(b, "Borrar marca", ancho=130, command=self.anular)
        self.b_anular.pack(side="right")
        self.b_editar = boton(b, "Datos de la marca", ancho=150, command=self.editar)
        self.b_editar.pack(side="right", padx=8)
        self.b_deshacer = boton(b, "Deshacer (Ctrl+Z)", ancho=150, command=self.deshacer)
        self.b_deshacer.pack(side="right")
        self.l_estado.pack(side="left", fill="x", expand=True)
        self.pid = None
        self.item = None
        self.act = None
        self.sel = None
        self.marcas_vis = []
        self._img_cache = {}
        self._acts = {}

    # ---- estado general
    def al_cambiar_tema(self):
        self.visor.configure(bg=col("suave"))
        self.visor.dibujar()
        ui.etiquetas_tabla(self.tv_act)

    def al_cambiar_proyecto(self):
        self.pid = self.item = self.act = self.sel = None
        self._img_cache = {}
        self.visor.limpiar()

    def _iman(self):
        self.visor.iman = bool(self.v_iman.get())
        self.visor.snap = None
        self.visor._dibujar_temporal()

    def _notas(self):
        self.visor.notas = bool(self.v_notas.get())
        self.visor.dibujar()

    def _fecha(self):
        try:
            f = core.txt_a_iso(self.v_fecha.get())
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Fecha", str(e))
            return None
        self.v_fecha.set(core.fecha_txt(f))
        return f

    @property
    def nivel(self):
        if not self.pid:
            return None
        nvs = self.p.plano_niveles(self.pid)
        if len(nvs) == 1:
            return nvs[0]
        for nv in nvs:
            if self.p.etiqueta_ubicacion(nv) == self.v_nivel.get():
                return nv
        return None

    def refrescar(self):
        if not self.p:
            return
        self.b_lib.configure(state="normal")
        self.cargar_actividades()
        self._hojas()
        if not self.p.planos():
            self._vacio("La librería está vacía.\n\nAbrí «Librería de planos…» y cargá los planos (PDF o imagen), "
                        "vinculados por nivel, por edificio o generales.\nEs opcional: solo si querés llevar ese control.")
        elif not self.pid:
            self._vacio("Elegí una actividad a la izquierda y abrí una de sus hojas,\no empezá una «Nueva hoja limpia…» "
                        "con un plano de la librería.")
        else:
            self.vacio.place_forget()
            self.cargar_marcas()

    def _vacio(self, txt):
        self.visor.limpiar()
        self.v_titulo.set("")
        self.v_escala.set("")
        self.vacio.configure(text=txt)
        self.vacio.place(relx=0.5, rely=0.45, anchor="center")
        for w in self.f_leyenda.winfo_children():
            w.destroy()

    # ---- actividades del día
    def cargar_actividades(self):
        tv = self.tv_act
        sel_prev = tv.selection()[0] if tv.selection() else None
        tv.delete(*tv.get_children())
        self._acts = {}
        if not self.p:
            return
        f = self._fecha()
        if not f:
            return
        if self.v_acum.get():
            return self._cargar_acumulado(f, sel_prev)
        items = {i["id"]: i for i in self.p.items()}
        niveles_con_plano = {r[0] for r in self.p.con.execute("SELECT DISTINCT nivel FROM plano_ubic")}
        cortes = self.p.cortes_acumulado()
        pend = [dict(r) for r in self.p.con.execute(
            "SELECT * FROM avances WHERE marca='' AND cantidad>0 AND fecha=? ORDER BY item", (f,))]
        orden = []
        for x in pend:
            ub = self.p.con.execute("SELECT COALESCE(SUM(cantidad),0) FROM marcas WHERE ref=? AND anulada=0 AND visual=1",
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
        for iid in orden:
            it = items.get(iid)
            if not it:
                continue
            falta = sum(x["pendiente"] for x in pend if x["item"] == iid and x["nivel"] in niveles_con_plano)
            n_pend += 1 if falta > 1e-9 else 0
            raiz = tv.insert("", "end", iid=f"i:{iid}", open=True, tags=("negrita",),
                             values=(f"{it['codigo']} {it['descripcion'][:40]}", f"{fmt(falta)} {it['unidad']}" if falta else "✓"))
            self._acts[f"i:{iid}"] = {"item": iid, "ref": "", "fecha": f}
            for x in pend:
                if x["item"] != iid:
                    continue
                partes = [self.p.etiqueta_ubicacion(x["nivel"])]
                if x["equipo"]:
                    partes.append(self.p.nombre_equipo(x["equipo"]))
                if x["tramo"]:
                    partes.append("T " + self.p.nombre_tramo(x["tramo"]))
                if x["hito"]:
                    partes.append(self.p.nombre_hito(x["hito"]))
                partes.append(f"{fmt(x['cantidad'])} {it['unidad']}")
                sin_plano = x["nivel"] not in niveles_con_plano
                k = f"r:{x['id']}"
                tv.insert(raiz, "end", iid=k, values=(" · ".join(partes),
                                                     "sin plano" if sin_plano else ("en acum." if x["en_acum"] else
                                                     (fmt(x["pendiente"]) if x["pendiente"] > 1e-9 else "✓"))),
                          tags=("fuera",) if (sin_plano or x["pendiente"] <= 1e-9) else ())
                self._acts[k] = {"item": iid, "nivel": x["nivel"], "equipo": x["equipo"], "tramo": x["tramo"],
                                 "hito": x["hito"], "ref": x["id"], "pendiente": x["pendiente"],
                                 "cantidad_reg": x["cantidad"], "fecha": x["fecha"]}
        self.v_resumen.set(f"{core.fecha_txt(f)} · {len(orden)} actividades" +
                           (f", {n_pend} con avance sin marcar" if n_pend else ""))
        if not orden:
            tv.insert("", "end", values=("Sin avance este día.", ""), tags=("fuera",))
        if sel_prev and tv.exists(sel_prev) and sel_prev in self._acts:
            tv.selection_set(sel_prev)
        elif self.item and tv.exists(f"i:{self.item}"):
            tv.selection_set(f"i:{self.item}")

    def _cambiar_acum(self):
        on = bool(self.v_acum.get())
        self.v_lbl_fecha.set("Corte al" if on else "Fecha")
        self.tv_act.heading("desc", text="Acumulado al corte" if on else "Actividad del día")
        self.act = None
        self.cargar_actividades()
        if on:
            self.v_estado.set("Marcar por acumulado: elegí la actividad y ubicación y dibujá todo lo ejecutado hasta la "
                              "fecha de corte. No crea avance nuevo: ubica en el plano lo que ya está registrado.")

    def _cargar_acumulado(self, f, sel_prev):
        """Lista lo acumulado hasta el corte por actividad y ubicacion, con lo que falta marcar."""
        tv = self.tv_act
        items = {i["id"]: i for i in self.p.items()}
        niveles_con_plano = {r[0] for r in self.p.con.execute("SELECT DISTINCT nivel FROM plano_ubic")}
        filas = self.p.acumulado_plano(f)
        orden = sorted({x["item"] for x in filas} | ({self.item} if self.item in items else set()),
                       key=lambda i: items[i]["orden"] if i in items else 0)
        n_pend = 0
        for iid in orden:
            it = items.get(iid)
            if not it:
                continue
            mias = [x for x in filas if x["item"] == iid]
            falta = sum(x["pendiente"] for x in mias if x["nivel"] in niveles_con_plano)
            n_pend += 1 if falta > 1e-9 else 0
            raiz = tv.insert("", "end", iid=f"i:{iid}", open=True, tags=("negrita",),
                             values=(f"{it['codigo']} {it['descripcion'][:40]}", f"{fmt(falta)} {it['unidad']}" if falta else "✓"))
            self._acts[f"i:{iid}"] = {"item": iid, "ref": "", "fecha": f}
            for x in sorted(mias, key=lambda x: self.p.etiqueta_ubicacion(x["nivel"])):
                partes = [self.p.etiqueta_ubicacion(x["nivel"])]
                if x["equipo"]:
                    partes.append(self.p.nombre_equipo(x["equipo"]))
                if x["tramo"]:
                    partes.append("T " + self.p.nombre_tramo(x["tramo"]))
                if x["hito"]:
                    partes.append(self.p.nombre_hito(x["hito"]))
                partes.append(f"acum. {fmt(x['acumulado'])} {it['unidad']}")
                sin_plano = x["nivel"] not in niveles_con_plano
                k = "a:" + "|".join((iid, x["nivel"], x["equipo"], x["tramo"], x["hito"]))
                tv.insert(raiz, "end", iid=k, values=(" · ".join(partes), "sin plano" if sin_plano else (
                    fmt(x["pendiente"]) if x["pendiente"] > 1e-9 else "✓")),
                          tags=("fuera",) if (sin_plano or x["pendiente"] <= 1e-9) else ())
                self._acts[k] = {"item": iid, "nivel": x["nivel"], "equipo": x["equipo"], "tramo": x["tramo"],
                                 "hito": x["hito"], "ref": core.ACUM, "pendiente": x["pendiente"],
                                 "cantidad_reg": x["acumulado"], "fecha": f, "clave": k}
        self.v_resumen.set(f"Acumulado al {core.fecha_txt(f)} · {len(orden)} actividades" +
                           (f", {n_pend} con avance sin marcar" if n_pend else ""))
        if not orden:
            tv.insert("", "end", values=("Sin avance a esa fecha.", ""), tags=("fuera",))
        if sel_prev and tv.exists(sel_prev) and sel_prev in self._acts:
            tv.selection_set(sel_prev)
        elif self.item and tv.exists(f"i:{self.item}"):
            tv.selection_set(f"i:{self.item}")

    def _elegir_act(self):
        s = self.tv_act.selection()
        if not s or s[0] not in self._acts:
            return
        act = dict(self._acts[s[0]])
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
            self.v_estado.set(f"Por acumulado: {it['codigo']} en {self.p.etiqueta_ubicacion(act['nivel'])}, acumulado "
                              f"{fmt(act['cantidad_reg'])} {it['unidad']} al {core.fecha_txt(act['fecha'])}; falta marcar "
                              f"{fmt(act['pendiente'])}. Dibujá todo lo ejecutado hasta esa fecha.")
        elif act.get("ref"):
            self.v_estado.set(f"Marcando {it['codigo']} en {self.p.etiqueta_ubicacion(act['nivel'])}: falta ubicar "
                              f"{fmt(act['pendiente'])} {it['unidad']}. Elegí una herramienta y dibujá.")

    def otra_actividad(self):
        iid = DialogoPartida(self.app).res
        if not iid:
            return
        f = self._fecha() or core.hoy_iso()
        self.item = iid
        self.act = {"item": iid, "ref": "", "fecha": f}
        self.pid = None
        self.cargar_actividades()
        self._hojas(auto=True)

    # ---- hojas
    def _hojas(self, auto=False):
        tv = self.tv_hojas
        tv.delete(*tv.get_children())
        if not self.p or not self.item:
            self.b_nueva.configure(state="disabled")
            return
        self.b_nueva.configure(state="normal")
        hojas = self.p.hojas_de(self.item)
        for h in hojas:
            x = self.p.plano(h["plano"])
            tv.insert("", "end", iid=h["plano"], values=(f"{x['nombre']} · {self.p.etiqueta_plano_ubic(h['plano'])}",
                                                         f"{h['n_marcas']}"))
        if not hojas:
            tv.insert("", "end", values=("Sin hojas: «Nueva hoja limpia…»", ""), tags=("fuera",))
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
        elif self.pid and tv.exists(self.pid):
            tv.selection_set(self.pid)

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

    def _elegir_hoja(self):
        s = self.tv_hojas.selection()
        if s and s[0] != self.pid and self.p.plano(s[0]):
            self.abrir_hoja(s[0])

    def quitar_hoja(self):
        """Quita la hoja de esta actividad en el plano elegido (por si se asignó un plano equivocado)."""
        s = self.tv_hojas.selection()
        pid = s[0] if s and self.p.plano(s[0]) else self.pid
        if not self.item or not pid:
            ui.info(self.app, "Quitar hoja", "Elegí la hoja en la lista «Hojas de la actividad».")
            return
        h = self.p.hoja(pid, self.item)
        if not h:
            return
        if self.p.solo_agregar:
            ui.info(self.app, "Quitar hoja", "En un archivo de «Solo agregar avance» no se pueden quitar hojas.")
            return
        it = self.p.item(self.item)
        r = preguntar_borrado(self.app, "Quitar hoja", f"la hoja de {it['codigo']} en «{self.p.plano(pid)['nombre']}» "
                              "(el plano queda limpio en la librería)", self.p.marcas(pid, item=self.item))
        if not r:
            return
        ficha = self.app.punto_deshacer("Quitar hoja")
        try:
            self.p.eliminar_hoja(h["id"], conservar=(r == 1))
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Hoja", str(e))
            return
        self.app.confirmar_deshacer(ficha)
        self.app.guardar()
        if self.pid == pid:
            self.pid = None
            self.visor.limpiar()
        self.visor.sel = None
        self.al_seleccionar(None)
        self.refrescar()
        self.v_estado.set(f"Se quitó la hoja de {it['codigo']}. Ctrl+Z para deshacer.")

    def nueva_hoja(self):
        if not self.item:
            ui.info(self.app, "Hoja", "Elegí primero la actividad.")
            return
        DialogoLibreria(self.app, self, elegir=True)

    def usar_plano(self, pid):
        """Desde la libreria: abre la hoja de esta actividad en ese plano (limpia si es nueva)."""
        if self.p.hoja(pid, self.item):
            ui.info(self.app, "Hoja existente", "Esta actividad ya tiene hoja en ese plano: se continúa con su historial.")
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
        if self.tv_hojas.exists(pid):
            self.tv_hojas.selection_set(pid)
        self.v_estado.set("Abriendo plano…")
        self.update_idletasks()
        try:
            if pid not in self._img_cache:
                self._img_cache = {pid: pl.imagen_de(self.p, pid)}
            img = self._img_cache[pid]
        except Exception as e:
            ui.info(self.app, "Plano", f"No se pudo abrir el plano:\n{e}")
            return
        self.vacio.place_forget()
        self.visor.cargar(img, x["escala"], x["unidad"])
        self.sel = None
        self._estado_hoja()
        self.al_seleccionar(None)

    def _estado_hoja(self):
        if not self.pid:
            return
        x = self.p.plano(self.pid)
        it = self.p.item(self.item)
        self.v_titulo.set(f"{it['codigo']} · {x['nombre']} · {self.p.etiqueta_plano_ubic(self.pid)}")
        self.v_escala.set(f"100 px = {x['escala'] * 100:,.4g} {x['unidad']}" if x["escala"] else "Sin calibrar")
        nvs = self.p.plano_niveles(self.pid)
        ops = [self.p.etiqueta_ubicacion(n) for n in nvs]
        self.m_nivel.configure(values=ops or [""])
        nv_act = (self.act or {}).get("nivel")
        if nv_act in nvs:
            self.v_nivel.set(self.p.etiqueta_ubicacion(nv_act))
        elif self.v_nivel.get() not in ops:
            self.v_nivel.set(ops[0] if ops else "")
        self.m_nivel.configure(state="normal" if len(ops) > 1 else "disabled")
        self.cargar_marcas()

    def estilo(self):
        if not self.item:
            ui.info(self.app, "Estilo", "Elegí primero una actividad.")
            return
        r = pl.DialogoEstilo(self.app, self.p, self.item).res
        if r:
            self.app.guardar()
            self.visor.estilo_temp = r
            self.cargar_marcas()

    # ---- marcas (color por edificio)
    def cargar_marcas(self):
        for w in self.f_leyenda.winfo_children():
            w.destroy()
        if not self.p or not self.pid or not self.item:
            return
        colores = self.p.colores_edificios()
        marcas = self.p.marcas(self.pid, item=self.item)
        items = {i["id"]: i for i in self.p.items()}
        hitos = {x["id"]: self.p.etiqueta_hito(dict(x), False)
                 for x in self.p.con.execute("SELECT id, nombre, tipo FROM hitos")}
        varias = len(self.p.plano_niveles(self.pid)) > 1
        eds = []
        for m in marcas:
            ed = self.p.edificio_de_nivel(m["nivel"])
            m["color"] = colores.get(ed, "#2563EB")
            m["nota_txt"] = pl.texto_nota(self.p, m, items, hitos, self.p.etiqueta_ubicacion(m["nivel"]) if varias else None)
            if ed not in eds:
                eds.append(ed)
        for nv in self.p.plano_niveles(self.pid):
            ed = self.p.edificio_de_nivel(nv)
            if ed not in eds:
                eds.append(ed)
        nombres = {e["id"]: e["nombre"] for e in self.p.edificios()}
        if varias or len(eds) > 1:
            etiqueta(self.f_leyenda, "Colores por edificio:", 11, color="texto2").pack(side="left", padx=(0, 6))
            for ed in eds:
                if ed not in nombres:
                    continue
                ctk.CTkButton(self.f_leyenda, text=nombres[ed], width=60, height=22, corner_radius=6, font=F(11, "bold"),
                              fg_color=colores.get(ed), hover_color=colores.get(ed), text_color="#FFFFFF",
                              command=lambda e=ed: self._color_edificio(e)).pack(side="left", padx=2)
        tramos = []
        for t in self.p.con.execute("SELECT * FROM tramos WHERE plano=? AND item=? AND geom IS NOT NULL", (self.pid, self.item)):
            t = dict(t)
            try:
                t["geom_pts"] = json.loads(t["geom"])
            except Exception:
                t["geom_pts"] = []
            tramos.append(t)
        self.marcas_vis = marcas
        self.visor.poner_marcas(marcas, {self.item: self.p.estilo_de(self.item)}, tramos)
        if not self.sel and not (self.act or {}).get("ref"):
            self.v_estado.set(f"{len(marcas)} marcas en esta hoja. Elegí una herramienta para marcar.")

    def _color_edificio(self, ed):
        c = pl.elegir_color(self.app, self.p.colores_edificios().get(ed), "Color del edificio")
        if c:
            self.p.poner_color_edificio(ed, c)
            self.app.guardar()
            self.cargar_marcas()

    def al_estado(self, txt):
        if not self.sel:
            self.v_estado.set(txt)

    def al_seleccionar(self, mid):
        self.sel = mid
        for b in (self.b_editar, self.b_anular):
            b.configure(state="normal" if mid else "disabled")
        if not mid:
            return
        m = self.p.marca(mid)
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
        self.v_estado.set("  ·  ".join(partes))

    def _coincidentes(self, tipo, pts):
        nueva = {"tipo": tipo, "geom": pts}
        tol = max(self.visor.tam) / 300
        return [m["nota_txt"] for m in self.marcas_vis if pl.coinciden(nueva, m, tol) or pl.coinciden(m, nueva, tol)]

    def _empezar_vacios(self, ext, huecos, fin):
        """Modo de dibujo de vacios sobre el area, con botones flotantes Listo / Cancelar."""
        marco = self.visor.master
        f = ctk.CTkFrame(marco, fg_color=C["tarjeta"], corner_radius=10, border_width=1, border_color=C["borde"])
        etiqueta(f, "Vacíos del área", 12, "bold").pack(side="left", padx=(12, 10), pady=8)
        boton(f, "Quitar último", ancho=110, command=self.visor.deshacer_vacio).pack(side="left", padx=(0, 6))
        boton(f, "Cancelar", ancho=90, command=lambda: self.visor.terminar_vacios(False)).pack(side="left", padx=(0, 6))
        boton(f, "Listo", primario=True, ancho=80, command=lambda: self.visor.terminar_vacios(True)).pack(
            side="left", padx=(0, 10))
        f.place(relx=0.5, y=14, anchor="n")
        self._f_vacios = f

        def al_fin(h):
            try:
                f.destroy()
            except Exception:
                pass
            self.v_herr.set(next((n for n, k in pl.HERRAMIENTAS if k == self.visor.herr), "Mover"))
            fin(h)
        self.visor.iniciar_vacios(ext, huecos, al_fin)
        self.visor.focus_set()

    def al_terminar(self, tipo, pts, huecos=None, previo=None):
        if not self.p or not self.pid:
            return
        plano = self.p.plano(self.pid)
        if tipo == "calibrar":
            if self.p.solo_agregar:
                ui.info(self.app, "Calibrar", "En un archivo de «Solo agregar avance» no se puede calibrar.")
                return
            px = pl.largo_px(pts)
            if px < 5:
                return

            def validar(v):
                n = ui.leer_num(v["d"])
                return "" if isinstance(n, float) and n > 0 else "Escribí la distancia real (mayor que cero)."
            r = ui.dialogo_form(self.app, "Calibrar plano",
                                f"Marcaste {px:,.1f} px en el plano. ¿Cuánto mide en la realidad? (acepta decimales)",
                                [("d", "Distancia real", False, ""), ("u", "Unidad", False, plano["unidad"] or "m")],
                                ("Cancelar", "Calibrar"), validar=validar)
            if not r:
                return
            esc = ui.leer_num(r["d"]) / px
            ficha = self.app.punto_deshacer("Calibrar plano")
            self.p.calibrar_plano(self.pid, esc, (r["u"] or "m").strip())
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            self.visor.escala, self.visor.unidad = esc, (r["u"] or "m").strip()
            self._estado_hoja()
            self.v_herr.set("Mover")
            self.visor.usar("mover")
            return
        if not self.item:
            ui.info(self.app, "Marcar", "Elegí primero la actividad.")
            return
        act = dict(self.act or {"item": self.item, "ref": "", "fecha": self._fecha() or core.hoy_iso()})
        if act.get("ref") == core.ACUM and act.get("pendiente", 0) <= 1e-9:
            ui.info(self.app, "Por acumulado", "Lo acumulado de esa actividad y ubicación ya está todo marcado al corte. "
                                               "Para marcar más, cambiá la fecha de corte o registrá el avance.")
            return
        if self.v_acum.get() and not act.get("ref"):
            ui.info(self.app, "Por acumulado", "Con «Por acumulado» elegí en la lista la ubicación (fila de abajo de la "
                                               "actividad) que vas a marcar.")
            return
        if act.get("ref") and act.get("pendiente", 0) <= 1e-9:
            act = {"item": act["item"], "ref": "", "fecha": act["fecha"], "equipo": act.get("equipo"),
                   "tramo": act.get("tramo"), "hito": act.get("hito"), "nivel": act.get("nivel")}
        if act.get("ref"):
            if act["nivel"] not in self.p.plano_niveles(self.pid):
                ui.info(self.app, "Ubicación", f"Este registro es de {self.p.etiqueta_ubicacion(act['nivel'])}, que no está en "
                                               f"el alcance de este plano ({self.p.etiqueta_plano_ubic(self.pid)}).")
                return
        else:
            act["nivel"] = self.nivel
            act["fecha"] = self._fecha() or act.get("fecha")
            if not act["nivel"]:
                ui.info(self.app, "Ubicación", "Elegí en «Marcando en» qué edificio-nivel estás marcando.")
                return
        r = pl.DialogoMarca(self.app, self.p, plano, tipo, pts, act, coincidentes=self._coincidentes(tipo, pts),
                            huecos=huecos, previo=previo).res
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
            ui.info(self.app, "Marca", str(e))
            return
        self.app.confirmar_deshacer(ficha)
        self.app.guardar()
        it = self.p.item(act["item"])
        ref = act.get("ref")
        self.cargar_actividades()
        k = act.get("clave") or f"r:{ref}"
        if ref and k in self._acts:
            self.act = dict(self._acts[k])
            self.tv_act.selection_set(k)
        self._hojas()
        self.cargar_marcas()
        accion = {"ubicar": "Se ubicó", "reemplazar": "Se reemplazó por la medida del plano:", "avance": "Se registró",
                  "acumulado": "Se marcó del acumulado"}[r["modo"]]
        self.v_estado.set(f"{accion} {fmt(r['cantidad'])} {it['unidad']} de {it['codigo']} en "
                          f"{self.p.etiqueta_ubicacion(act['nivel'])} ({core.fecha_txt(r['fecha'])}).")

    def preparar(self, iid, nivel, fecha):
        """Viene del Registro de avance: elige la actividad y abre su hoja para esa ubicacion."""
        self.v_fecha.set(core.fecha_txt(fecha))
        self.item = None
        self.cargar_actividades()
        hijos = [k for k in (self.tv_act.get_children(f"i:{iid}") if self.tv_act.exists(f"i:{iid}") else [])
                 if self._acts.get(k, {}).get("nivel") == nivel and self._acts[k].get("pendiente", 0) > 1e-9]
        objetivo = hijos[0] if hijos else (f"i:{iid}" if self.tv_act.exists(f"i:{iid}") else None)
        if objetivo:
            self.tv_act.selection_set(objetivo)
            self.tv_act.see(objetivo)
            self._elegir_act()
        if not self.pid:
            libres = self.p.planos(nivel)
            if len(libres) == 1:
                if ui.preguntar(self.app, "Nueva hoja", f"{self.p.item(iid)['codigo']} todavía no tiene hoja para "
                                f"{self.p.etiqueta_ubicacion(nivel)}.\n\n¿Empezar una hoja limpia con el plano "
                                f"«{libres[0]['nombre']}» ({self.p.etiqueta_plano_ubic(libres[0]['id'])})?", si="Empezar"):
                    self.usar_plano(libres[0]["id"])
            elif libres:
                DialogoLibreria(self.app, self, elegir=True, nivel=nivel)
        unidad = self.p.item(iid)["unidad"]
        herr = "Línea" if unidad in ("ML", "M") else ("Polígono" if unidad == "M2" else "Punto")
        self.v_herr.set(herr)
        self.visor.usar(dict(pl.HERRAMIENTAS)[herr])

    def editar(self):
        if not self.sel:
            return
        m = self.p.marca(self.sel)
        plano = self.p.plano(self.pid)
        act = {"item": m["item"], "nivel": m["nivel"], "ref": "", "fecha": m["fecha"]}
        r = pl.DialogoMarca(self.app, self.p, plano, m["tipo"], m["geom"], act, marca=m).res
        if not r:
            return
        if r.get("accion") == "vacios":
            mid = m["id"]
            self._empezar_vacios(m["geom"], m.get("huecos") or [],
                                 lambda h: None if h is None else self.al_mover_marca(mid, m["geom"], h))
            return
        ficha = self.app.punto_deshacer("Editar datos de la marca")
        try:
            tramo = r["tramo"]
            if r.get("tramo_nuevo"):
                tramo = self.p.crear_tramo(m["item"], m["nivel"], r["tramo_nuevo"], None, plano=self.pid,
                                           geom=m["geom"] if m["tipo"] == "linea" else None, equipo=r.get("equipo", ""))
            self.p.editar_marca(self.sel, cantidad=r["cantidad"], fecha=r["fecha"], nota=r["nota"], altura=r["altura"],
                                hito=r["hito"], tramo=tramo, equipo=r.get("equipo", ""))
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Marca", str(e))
            return
        self.app.confirmar_deshacer(ficha)
        self.app.guardar()
        self.cargar_actividades()
        self.cargar_marcas()
        self.al_seleccionar(self.sel)

    def al_mover_marca(self, mid, geom, huecos=None):
        """La herramienta Editar movio la marca o cambio su forma (o se cambiaron sus vacios)."""
        m = self.p.marca(mid)
        plano = self.p.plano(self.pid)
        nueva = pl.medida(m["tipo"], geom, plano["escala"], m.get("huecos") if huecos is None else huecos)
        cambios = {"geom": geom}
        if huecos is not None:
            cambios["huecos"] = huecos
        tol = max(0.005, abs(m["medida"] or 0) * 1e-4)
        if nueva is not None and m["tipo"] != "punto" and abs(nueva - (m["medida"] or 0)) > tol:
            cambios["medida"] = nueva
            f = m["factor"] or 1
            del_plano = m["medida"] is not None and abs((m["medida"] or 0) * f - (m["cantidad"] or 0)) < 0.005
            if not m.get("visual") and del_plano and abs(nueva * f - m["cantidad"]) > 0.005:
                it = self.p.item(m["item"])
                r = ui.dialogo_texto(self.app, "Cambió la medida",
                                     f"La marca medía {fmt(m['cantidad'])} {it['unidad']} y ahora mide "
                                     f"{fmt(nueva * f)} {it['unidad']}.\n\n¿Actualizar la cantidad del avance con la "
                                     "nueva medida?", ("Deshacer", "Solo mover", "Actualizar cantidad"), 2)
                if r is None or r == 0:
                    self.cargar_marcas()
                    return False
                if r == 2:
                    cambios["cantidad"] = round(nueva * f, 4)
                else:
                    cambios.pop("medida")
        ficha = self.app.punto_deshacer("Vacíos del área" if huecos is not None and "geom" in cambios and
                                        geom == m["geom"] else "Mover o cambiar forma de la marca")
        try:
            self.p.editar_marca(mid, **cambios)
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Marca", str(e))
            self.cargar_marcas()
            return False
        self.app.confirmar_deshacer(ficha)
        self.app.guardar()
        if "cantidad" in cambios:
            self.cargar_actividades()
        self.cargar_marcas()
        self.visor.sel = mid
        self.visor.dibujar()
        self.al_seleccionar(mid)
        return True

    def anular(self):
        if not self.sel:
            return
        m = self.p.marca(self.sel)
        it = self.p.item(m["item"])
        if m.get("visual"):
            r = ui.dialogo_texto(self.app, "Borrar marca", "Esta marca solo ubica un registro manual. Al borrarla, ese "
                                 "registro vuelve a quedar sin marcar (la cantidad no cambia).", ("Cancelar", "Borrar"), 1)
            r = 1 if r == 1 else 0
        else:
            r = ui.dialogo_texto(self.app, "Borrar marca",
                                 f"{fmt(m['cantidad'])} {it['unidad']} del {core.fecha_txt(m['fecha'])} en "
                                 f"{self.p.etiqueta_ubicacion(m['nivel'])}.\n\n«Quitar del plano»: se borra el dibujo y "
                                 "la cantidad queda como registro manual sin marcar.\n«Borrar también el avance»: la "
                                 "cantidad deja de contar (queda en el historial).",
                                 ("Cancelar", "Quitar del plano", "Borrar también el avance"), 1)
        if not r:
            return
        ficha = self.app.punto_deshacer("Borrar marca")
        try:
            if r == 1 and not m.get("visual"):
                self.p.quitar_del_plano(self.sel)
            else:
                self.p.anular_marca(self.sel)
        except core.ErrorCtrlP as e:
            ui.info(self.app, "Marca", str(e))
            return
        self.app.confirmar_deshacer(ficha)
        self.app.guardar()
        self.visor.sel = None
        self.al_seleccionar(None)
        self.cargar_actividades()
        self._hojas()
        self.cargar_marcas()

    def deshacer(self):
        if self.visor.pts:
            self.visor.deshacer_punto()
            return
        desc, err = self.app.deshacer()
        if err:
            self.v_estado.set(err)
            return
        if self.pid and not self.p.plano(self.pid):
            self.pid = None
            self.visor.limpiar()
        self.visor.sel = None
        self.al_seleccionar(None)
        self.refrescar()
        self.v_estado.set(f"Se deshizo: {desc}.")


# =========================================================================
#  Apariencia
# =========================================================================
class PaginaApariencia(Pagina):
    clave = "apariencia"
    titulo = "Apariencia"

    def __init__(self, master, app):
        super().__init__(master, app)
        t = ui.Tarjeta(self.cuerpo)
        t.grid(row=0, column=0, sticky="nw")
        caja = ctk.CTkFrame(t, fg_color="transparent")
        caja.grid(row=0, column=0, padx=20, pady=18)
        self.botones = {}
        for k, modo in enumerate(("Claro", "Oscuro", "Automático")):
            img = ctk.CTkImage(ui.miniatura_tema(modo), size=(96, 64))
            b = ctk.CTkButton(caja, text="", image=img, width=110, height=76, corner_radius=10, fg_color="transparent",
                              hover_color=C["suave"], border_width=2, border_color=C["tarjeta"],
                              command=lambda m=modo: self.elegir(m))
            b.grid(row=0, column=k, padx=10)
            etiqueta(caja, modo, 12).grid(row=1, column=k, pady=(4, 0))
            self.botones[modo] = b
        etiqueta(t, "Automático sigue el modo de Windows (claro u oscuro).", 11, color="texto2").grid(
            row=1, column=0, sticky="w", padx=22, pady=(0, 16))
        t2 = ui.Tarjeta(self.cuerpo)
        t2.grid(row=1, column=0, sticky="nw", pady=(16, 0))
        etiqueta(t2, "Actualizaciones", 15, "bold").grid(row=0, column=0, columnspan=3, sticky="w", padx=22, pady=(16, 2))
        etiqueta(t2, f"Versión {'instalada' if act_.es_instalado() else 'portable'}: {VERSION}  ·  by {AUTOR}", 13).grid(row=1, column=0, sticky="w", padx=22, pady=(4, 0))
        boton(t2, "Buscar actualizaciones", ancho=190, command=lambda: app.buscar_actualizacion(True)).grid(
            row=1, column=1, padx=(24, 8), pady=(4, 0))
        boton(t2, "Novedades", ancho=120, command=app.novedades).grid(row=1, column=2, padx=(0, 22), pady=(4, 0))
        etiqueta(t2, "Al abrir, Ctrl-P revisa si hay una versión nueva (si no hay internet, no molesta). Actualizar "
                     "nunca es obligatorio y no toca tus proyectos ni la carpeta CTRL-P DOC.", 11, color="texto2",
                 wraplength=560, justify="left").grid(row=2, column=0, columnspan=3, sticky="w", padx=22, pady=(8, 16))

    def refrescar(self):
        actual = self.app.cfg.get("apariencia", "Automático")
        for m, b in self.botones.items():
            b.configure(border_color=C["acento"] if m == actual else C["tarjeta"])

    def elegir(self, m):
        self.app.cambiar_apariencia(m)
        self.refrescar()


# =========================================================================
#  Dialogos
# =========================================================================
class Ventana(ctk.CTkToplevel):
    def __init__(self, app, titulo, ancho=980, alto=700):
        super().__init__(app, fg_color=C["fondo"])
        self.app = app
        self.title(titulo)
        # que nunca quede mas grande que la pantalla (laptops de 768 px de alto)
        esc = ctk.ScalingTracker.get_window_scaling(self)
        sw, sh = self.winfo_screenwidth() / esc, self.winfo_screenheight() / esc
        ancho, alto = int(min(ancho, sw - 40)), int(min(alto, sh - 90))
        self.geometry(f"{ancho}x{alto}")
        self.minsize(min(820, ancho), min(560, alto))
        self.transient(app)
        ui.icono_ventana(self)
        self.after(80, lambda: ui.tenir_barra_titulo(self, ui.oscuro()))
        self.after(120, self._centrar)
        try:
            self.after(150, self.grab_set)
        except Exception:
            pass

    def _centrar(self):
        self.update_idletasks()
        x = self.app.winfo_rootx() + (self.app.winfo_width() - self.winfo_width()) // 2
        y = self.app.winfo_rooty() + (self.app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")


def elegir_inicio_semana(app):
    """Ventanita para elegir el dia en que empiezan los cortes semanales del proyecto. True si cambio."""
    p = app.p
    if p is None:
        return False
    if p.solo_agregar:
        ui.info(app, "Cortes semanales", "Esta copia es «solo agregar avance»: el día de corte lo cambia quien "
                                         "tiene el proyecto completo.")
        return False
    res = {"ok": False}
    dlg = ctk.CTkToplevel(app, fg_color=C["tarjeta"])
    dlg.title("Cortes semanales")
    dlg.resizable(False, False)
    dlg.transient(app)
    etiqueta(dlg, "Cortes semanales", 16, "bold").pack(anchor="w", padx=24, pady=(20, 4))
    etiqueta(dlg, "Día en que empieza cada semana en Informes («+ Por semana») y en las memorias de cálculo.\n"
                  "Se guarda en el proyecto.", 12, color="texto2", justify="left").pack(anchor="w", padx=24)
    fila = ctk.CTkFrame(dlg, fg_color="transparent")
    fila.pack(anchor="w", padx=24, pady=(14, 0))
    etiqueta(fila, "La semana empieza el", 13).pack(side="left", padx=(0, 8))
    v = tk.StringVar(value=core.DIAS_SEMANA[p.inicio_semana])
    v_txt = tk.StringVar()

    def mostrar(*_):
        k = core.DIAS_SEMANA.index(v.get())
        v_txt.set(f"Cada semana va de {core.texto_semana(k)}.")
    ui.menu(fila, core.DIAS_SEMANA, v, 150, cmd=mostrar).pack(side="left")
    etiqueta(dlg, "", 13, "bold", textvariable=v_txt).pack(anchor="w", padx=24, pady=(10, 0))
    mostrar()

    def ok():
        res["ok"] = p.cambiar_inicio_semana(core.DIAS_SEMANA.index(v.get()))
        dlg.destroy()
    pie = ctk.CTkFrame(dlg, fg_color="transparent")
    pie.pack(fill="x", padx=24, pady=(18, 20))
    boton(pie, "Guardar", primario=True, ancho=110, command=ok).pack(side="right")
    boton(pie, "Cancelar", ancho=100, command=dlg.destroy).pack(side="right", padx=8)
    dlg.bind("<Escape>", lambda _: dlg.destroy())
    dlg.update_idletasks()
    x = app.winfo_rootx() + (app.winfo_width() - dlg.winfo_width()) // 2
    y = app.winfo_rooty() + (app.winfo_height() - dlg.winfo_height()) // 3
    dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    dlg.after(60, lambda: ui.tenir_barra_titulo(dlg, ui.oscuro()))
    ui.icono_ventana(dlg)
    try:
        dlg.grab_set()
    except Exception:
        pass
    app.wait_window(dlg)
    if res["ok"]:
        try:
            app.dibujar_lateral()
        except Exception:
            pass
    return res["ok"]


class DialogoProgreso(ctk.CTkToplevel):
    """Ventanita «Exportando…» con barra. El trabajo corre en la ventana principal y llama a avanzar();
    el guardado del archivo va en segundo plano. Asi Windows nunca marca el programa como «No responde»."""

    def __init__(self, app, titulo, texto):
        super().__init__(app, fg_color=C["fondo"])
        self.app = app
        self.title(titulo)
        self.resizable(False, False)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", lambda: None)       # no se cierra a medio trabajo
        ui.icono_ventana(self)
        caja = ctk.CTkFrame(self, fg_color="transparent")
        caja.pack(padx=28, pady=22)
        self.l = etiqueta(caja, texto, 13)
        self.l.pack(anchor="w")
        self.barra = ctk.CTkProgressBar(caja, width=380, progress_color=C["acento"])
        self.barra.pack(pady=(12, 0))
        self.barra.set(0)
        self._t = 0.0
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        try:
            ui.tenir_barra_titulo(self, ui.oscuro())
        except Exception:
            pass
        self.update()
        try:
            self.grab_set()
        except Exception:
            pass

    def avanzar(self, fraccion, texto=None):
        import time
        ahora_ = time.monotonic()
        if ahora_ - self._t < 0.08 and fraccion < 1:
            return
        self._t = ahora_
        self.barra.set(max(0.0, min(1.0, fraccion)))
        if texto:
            self.l.configure(text=texto)
        self.update()

    def guardar_en_fondo(self, wb, ruta):
        """wb.save, avisando cada pocas filas escritas para que la ventana siga respondiendo
        (en un hilo aparte no sirve: la libreria que escribe el Excel no suelta el programa)."""
        from openpyxl.worksheet import _writer as escritor
        total = max(1, sum(ws.max_row for ws in wb.worksheets))
        hechas = [0]
        original = escritor.WorksheetWriter.write_row

        def fila(this, xf, row, row_idx):
            original(this, xf, row, row_idx)
            hechas[0] += 1
            if hechas[0] % 40 == 0:
                self.avanzar(0.7 + 0.29 * min(1.0, hechas[0] / total))
        escritor.WorksheetWriter.write_row = fila
        try:
            wb.save(ruta)
        finally:
            escritor.WorksheetWriter.write_row = original
        self.barra.set(1)
        self.update()

    def cerrar(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class DialogoAlcance(Ventana):
    """Cargar un plano a la librería (ruta) o cambiar el alcance de uno existente (pid)."""

    ALCANCES = ["Por nivel", "Por edificio", "General"]

    def __init__(self, app, ruta=None, pid=None, al_terminar=None):
        super().__init__(app, "Cargar plano" if ruta else "Alcance del plano", 680, 680)
        self.ruta, self.pid, self.al_terminar = ruta, pid, al_terminar
        p = app.p
        x = p.plano(pid) if pid else None
        c = ui.Desplazable(self, fg_color="transparent", scrollbar_button_color=C["borde"])
        c.pack(fill="both", expand=True, padx=20, pady=(16, 0))
        etiqueta(c, "Cargar plano a la librería" if ruta else "Alcance del plano", 20, "bold").pack(anchor="w")
        if ruta:
            etiqueta(c, os.path.basename(ruta), 12, color="texto2").pack(anchor="w")
        etiqueta(c, "Nombre del plano", 12, "bold").pack(anchor="w", pady=(12, 4))
        self.v_nom = tk.StringVar(value=x["nombre"] if x else os.path.splitext(os.path.basename(ruta))[0][:60])
        entrada(c, self.v_nom, 420).pack(anchor="w")
        etiqueta(c, "¿A qué se vincula?", 12, "bold").pack(anchor="w", pady=(14, 4))
        ini = {"nivel": "Por nivel", "edificio": "Por edificio", "general": "General"}.get((x or {}).get("alcance") or "nivel")
        self.v_alc = tk.StringVar(value=ini)
        ui.segmentado(c, self.ALCANCES, self.v_alc, 360, cmd=lambda _: self._opciones()).pack(anchor="w")
        self.ayuda = etiqueta(c, "", 11, color="texto2", wraplength=600, justify="left")
        self.ayuda.pack(anchor="w", pady=(6, 0))
        ui.ajustar_texto(self.ayuda, c, 20, 200)
        self.caja = ctk.CTkFrame(c, fg_color="transparent")
        self.caja.pack(fill="x", pady=(8, 0))
        self.ubs = p.ubicaciones()
        self.eds = [e for e in p.edificios() if not p.area_simple(e)]
        actuales = p.plano_niveles(pid) if pid else []
        self.v_nivel = tk.StringVar(value=p.etiqueta_ubicacion(actuales[0]) if actuales else (self.ubs[0]["etiqueta"] if self.ubs else ""))
        ed_ini = p.edificio_de_nivel(actuales[0]) if actuales else (self.eds[0]["id"] if self.eds else None)
        self.v_ed = tk.StringVar(value=next((e["nombre"] for e in self.eds if e["id"] == ed_ini), self.eds[0]["nombre"] if self.eds else ""))
        self.v_nom_alc = tk.StringVar(value=(x or {}).get("nombre_alcance") if (x or {}).get("alcance") == "general" else "GENERAL")
        self.v_ubs = {u["nivel"]: tk.BooleanVar(value=u["nivel"] in actuales) for u in self.ubs}
        self.v_pag = tk.StringVar(value="1")
        self.v_aplanar = tk.BooleanVar(value=True)
        self.v_dpi = tk.StringVar(value="200 dpi")
        if ruta:
            if ruta.lower().endswith(".pdf"):
                try:
                    n = pl.paginas_pdf(ruta)
                except Exception:
                    n = 1
                if n > 1:
                    etiqueta(c, f"Página (el PDF tiene {n})", 12, "bold").pack(anchor="w", pady=(12, 4))
                    ui.Contador(c, self.v_pag, 1, n).pack(anchor="w")
            t = ui.Tarjeta(c)
            t.pack(fill="x", pady=(14, 0))
            t.fila("Aplanar y comprimir con PdFOL", ui.Interruptor(t, self.v_aplanar),
                   "Convierte el plano en una imagen liviana: abre y se mueve mucho más rápido. Recomendado para planos "
                   "pesados de AutoCAD.")
            t.fila("Resolución", ui.segmentado(t, ["150 dpi", "200 dpi", "300 dpi"], self.v_dpi, 240),
                   "Más resolución = más detalle al acercar, archivo más pesado.")
        self.v_msg = tk.StringVar()
        etiqueta(c, "", 12, color="texto2", textvariable=self.v_msg).pack(anchor="w", pady=(10, 0))
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=24, pady=(8, 18))
        self.b_ok = boton(pie, "Cargar" if ruta else "Guardar", primario=True, ancho=130, command=self.ok)
        self.b_ok.pack(side="right")
        boton(pie, "Cancelar", ancho=110, command=self.destroy).pack(side="right", padx=8)
        self._opciones()

    def _opciones(self):
        for w in self.caja.winfo_children():
            w.destroy()
        a = self.v_alc.get()
        if a == "Por nivel":
            self.ayuda.configure(text="El plano es de un solo edificio-nivel (ej. B1 NIVEL 1). Todas sus marcas son de esa ubicación.")
            ui.menu(self.caja, [u["etiqueta"] for u in self.ubs] or [""], self.v_nivel, 300).pack(anchor="w")
        elif a == "Por edificio":
            self.ayuda.configure(text="El plano es de un edificio completo (ej. un isométrico o una fachada de B1). Al marcar "
                                      "elegís el nivel del edificio.")
            ui.menu(self.caja, [e["nombre"] for e in self.eds] or [""], self.v_ed, 200).pack(anchor="w")
        else:
            self.ayuda.configure(text="El plano muestra varios edificios (ej. GENERAL NIVEL 1). El programa no sabe dónde queda "
                                      "cada edificio: al marcar elegís a qué ubicación corresponde.")
            f = ctk.CTkFrame(self.caja, fg_color="transparent")
            f.pack(anchor="w")
            etiqueta(f, "Nombre del alcance", 11, color="texto2").pack(side="left")
            ui.entrada_mayus(f, self.v_nom_alc, 240).pack(side="left", padx=(8, 0))
            nombres_nv = []
            for u in self.ubs:
                if u["nv_nombre"] and u["nv_nombre"] not in nombres_nv:
                    nombres_nv.append(u["nv_nombre"])
            f2 = ctk.CTkFrame(self.caja, fg_color="transparent")
            f2.pack(anchor="w", pady=(8, 4))
            self.v_rapido = tk.StringVar(value=nombres_nv[0] if nombres_nv else "")
            if nombres_nv:
                etiqueta(f2, "Marcar todos los", 11, color="texto2").pack(side="left")
                ui.menu(f2, nombres_nv, self.v_rapido, 140).pack(side="left", padx=6)
                boton(f2, "Marcar", ancho=80, alto=28, command=self._rapido).pack(side="left")
            g = ctk.CTkFrame(self.caja, fg_color="transparent")
            g.pack(anchor="w")
            for k, u in enumerate(self.ubs):
                ctk.CTkCheckBox(g, text=u["etiqueta"], variable=self.v_ubs[u["nivel"]], font=F(12), text_color=C["texto"],
                                fg_color=C["acento"], checkbox_width=18, checkbox_height=18, corner_radius=5).grid(
                    row=k // 3, column=k % 3, sticky="w", padx=(0, 16), pady=2)

    def _rapido(self):
        n = self.v_rapido.get()
        for u in self.ubs:
            if u["nv_nombre"] == n:
                self.v_ubs[u["nivel"]].set(True)
        if self.v_nom_alc.get() in ("", "GENERAL"):
            self.v_nom_alc.set(f"GENERAL {n}")

    def _seleccion(self):
        a = self.v_alc.get()
        p = self.app.p
        if a == "Por nivel":
            nv = next((u["nivel"] for u in self.ubs if u["etiqueta"] == self.v_nivel.get()), None)
            return "nivel", [nv] if nv else [], ""
        if a == "Por edificio":
            e = next((x for x in self.eds if x["nombre"] == self.v_ed.get()), None)
            return "edificio", [n["id"] for n in p.niveles_de(e["id"])] if e else [], e["nombre"] if e else ""
        return "general", [u["nivel"] for u in self.ubs if self.v_ubs[u["nivel"]].get()], self.v_nom_alc.get()

    def ok(self):
        p = self.app.p
        alc, niveles, nom = self._seleccion()
        if not niveles:
            ui.info(self, "Plano", "Elegí la ubicación (o las ubicaciones) del plano.")
            return
        if self.ruta:
            self.v_msg.set("Procesando el plano… (los planos grandes pueden tardar unos segundos)")
            self.b_ok.configure(state="disabled")
            self.update()
            try:
                tipo, datos, w, h = pl.importar_archivo(self.ruta, self.v_aplanar.get(), int(self.v_dpi.get().split()[0]),
                                                         int(self.v_pag.get() or 1) - 1)
                ficha = self.app.punto_deshacer("Cargar plano")
                pid = p.agregar_plano(niveles[0], self.v_nom.get(), tipo, datos, w, h, alcance=alc, nombre_alcance=nom)
                p.vincular_plano(pid, niveles, alc, nom)
                self.app.confirmar_deshacer(ficha)
                self.app.guardar()
            except Exception as e:
                self.b_ok.configure(state="normal")
                self.v_msg.set("")
                ui.info(self, "No se pudo cargar el plano", str(e))
                return
            self.destroy()
            ui.info(self.app, "Plano cargado", f"{self.v_nom.get()} · {p.etiqueta_plano_ubic(pid)} · "
                                               f"{len(datos) / 1048576:,.1f} MB.\n\nAl abrirlo por primera vez, usá «Calibrar» "
                                               "(dos puntos de una cota conocida) para poder medir.")
        else:
            ficha = self.app.punto_deshacer("Cambiar alcance del plano")
            try:
                p.renombrar_plano(self.pid, self.v_nom.get())
                p.vincular_plano(self.pid, niveles, alc, nom)
            except core.ErrorCtrlP as e:
                ui.info(self, "Alcance", str(e))
                return
            self.app.confirmar_deshacer(ficha)
            self.app.guardar()
            self.destroy()
        if self.al_terminar:
            self.al_terminar()


def preguntar_borrado(raiz, titulo, que, marcas):
    """0 cancelar, 1 conservar avances, 2 borrar tambien el avance."""
    con_av = [m for m in marcas if not m.get("visual")]
    if not con_av:
        msg = f"¿Eliminar {que}?" + (f"\n\nSus {len(marcas)} marcas solo ubican registros manuales: esos registros "
                                     "vuelven a quedar sin marcar." if marcas else "")
        return 1 if ui.dialogo_texto(raiz, titulo, msg, ("Cancelar", "Eliminar"), 1) == 1 else 0
    r = ui.dialogo_texto(raiz, titulo, f"¿Eliminar {que}?\n\nTiene {len(marcas)} marcas; {len(con_av)} registraron "
                         "avance al marcar.\n«Conservar avances»: se borran los dibujos y las cantidades quedan como "
                         "registros manuales sin marcar.\n«Borrar también el avance»: esas cantidades dejan de "
                         "contar (quedan en el historial).",
                         ("Cancelar", "Conservar avances", "Borrar también el avance"), 1)
    return r or 0


class DialogoLibreria(Ventana):
    """Librería de planos. Con elegir=True sirve para empezar o continuar la hoja de la actividad actual."""

    def __init__(self, app, pagina, elegir=False, nivel=None):
        super().__init__(app, "Librería de planos", 980, 660)
        self.pagina, self.elegir, self.nivel = pagina, elegir, nivel
        p = app.p
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(3, weight=2)
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 6))
        it = p.item(pagina.item) if (elegir and pagina.item) else None
        etiqueta(cab, "Elegí el plano para la hoja de " + it["codigo"] if it else "Librería de planos", 18, "bold").pack(anchor="w")
        etiqueta(cab, ("Cada actividad tiene su hoja en cada plano: si el plano ya tiene marcas de otras actividades, para "
                       "esta se abre limpio." if it else "Los planos de la librería siempre quedan limpios; las marcas van en "
                       "las hojas de cada actividad."), 12, color="texto2", wraplength=900, justify="left").pack(anchor="w")
        ui.ajustar_texto(cab.pack_slaves()[-1], cab, 10, 200)
        cols = [("nombre", "Plano", 260, "w"), ("alcance", "Alcance", 220, "w"), ("escala", "Calibrado", 90, "center"),
                ("hojas", "Hojas (actividades marcadas)", 300, "w")]
        m, self.tv = ui.tabla(self, cols, arbol=False)
        m.grid(row=1, column=0, sticky="nsew", padx=24)
        self.tv.bind("<Double-1>", lambda _: self.usar() if elegir else self.alcance())
        etiqueta(self, "Todas las hojas de marcado", 13, "bold").grid(row=2, column=0, sticky="w", padx=24, pady=(10, 2))
        cols = [("act", "Actividad", 380, "w"), ("plano", "Plano · alcance", 330, "w"), ("n", "Marcas", 70, "e"),
                ("ult", "Última", 90, "center")]
        m2, self.tv_h = ui.tabla(self, cols, arbol=False)
        m2.grid(row=3, column=0, sticky="nsew", padx=24)
        self.tv_h.bind("<Double-1>", lambda _: self.usar_hoja())
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.grid(row=4, column=0, sticky="ew", padx=24, pady=(10, 18))
        bloq = p.solo_agregar
        for txt, cmd in (("Cargar plano…", self.cargar), ("Alcance…", self.alcance), ("Eliminar plano", self.eliminar),
                         ("Eliminar hoja", self.eliminar_hoja)):
            b = boton(pie, txt, ancho=130, command=cmd)
            b.pack(side="left", padx=(0, 8))
            if bloq:
                b.configure(state="disabled")
        if elegir:
            boton(pie, "Usar para " + (it["codigo"] if it else "la actividad"), primario=True, ancho=200,
                  command=self.usar).pack(side="right")
        boton(pie, "Cerrar", ancho=100, command=self.destroy).pack(side="right", padx=8)
        self.cargar_listas()

    def cargar_listas(self):
        p = self.app.p
        self.tv.delete(*self.tv.get_children())
        self.tv_h.delete(*self.tv_h.get_children())
        items = {i["id"]: i for i in p.items()}
        for x in p.planos():
            if self.nivel and self.nivel not in x["niveles"]:
                continue
            hojas = p.hojas_de(pid=x["id"])
            txt = ", ".join(f"{items[h['item']]['codigo']} ({h['n_marcas']})" for h in hojas if h["item"] in items) or "—"
            self.tv.insert("", "end", iid=x["id"], values=(x["nombre"], p.etiqueta_plano_ubic(x["id"]),
                                                           "✓" if x["escala"] else "—", txt))
        for h in p.hojas_de():
            it = items.get(h["item"])
            x = p.plano(h["plano"])
            if not it or not x:
                continue
            self.tv_h.insert("", "end", iid=h["id"], values=(f"{it['codigo']} {it['descripcion'][:50]}",
                                                             f"{x['nombre']} · {p.etiqueta_plano_ubic(h['plano'])}",
                                                             h["n_marcas"], core.fecha_txt(h["ultima"]) if h["ultima"] else ""))
        if not self.tv.get_children():
            self.tv.insert("", "end", values=("La librería está vacía: «Cargar plano…».", "", "", ""))

    def _sel(self):
        s = self.tv.selection()
        return s[0] if s and self.app.p.plano(s[0]) else None

    def cargar(self):
        ruta = filedialog.askopenfilename(parent=self, title="Cargar plano", initialdir=ui.carpeta_docs(), filetypes=[
            ("Planos", "*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp"), ("PDF", "*.pdf"),
            ("Imágenes", "*.png *.jpg *.jpeg *.tif *.tiff")])
        if ruta:
            DialogoAlcance(self.app, ruta=ruta, al_terminar=self._actualizado)

    def _actualizado(self):
        if self.winfo_exists():
            self.cargar_listas()
        self.pagina.refrescar()

    def alcance(self):
        pid = self._sel()
        if pid:
            DialogoAlcance(self.app, pid=pid, al_terminar=self._actualizado)

    def eliminar(self):
        pid = self._sel()
        if not pid:
            ui.info(self, "Eliminar plano", "Elegí un plano de la librería (lista de arriba).")
            return
        x = self.app.p.plano(pid)
        r = preguntar_borrado(self, "Eliminar plano", f"«{x['nombre']}» de la librería, con todas sus hojas",
                                    self.app.p.marcas(pid))
        if not r:
            return
        ficha = self.app.punto_deshacer("Eliminar plano", datos_de=[pid])
        try:
            self.app.p.eliminar_plano(pid, conservar=(r == 1))
        except core.ErrorCtrlP as e:
            ui.info(self, "Plano", str(e))
            return
        self.app.confirmar_deshacer(ficha)
        self.app.guardar()
        if self.pagina.pid == pid:
            self.pagina.pid = None
            self.pagina.visor.limpiar()
        self._actualizado()

    def eliminar_hoja(self):
        s = self.tv_h.selection()
        if not s:
            ui.info(self, "Eliminar hoja", "Elegí una hoja en la lista «Todas las hojas de marcado».")
            return
        p = self.app.p
        h = next((x for x in p.hojas_de() if x["id"] == s[0]), None)
        if not h:
            return
        it = p.item(h["item"])
        r = preguntar_borrado(self, "Eliminar hoja", f"la hoja de {it['codigo']} en «{p.plano(h['plano'])['nombre']}» "
                                    "(el plano queda limpio en la librería)", p.marcas(h["plano"], item=h["item"]))
        if not r:
            return
        ficha = self.app.punto_deshacer("Eliminar hoja")
        try:
            p.eliminar_hoja(h["id"], conservar=(r == 1))
        except core.ErrorCtrlP as e:
            ui.info(self, "Hoja", str(e))
            return
        self.app.confirmar_deshacer(ficha)
        self.app.guardar()
        if self.pagina.pid == h["plano"] and self.pagina.item == h["item"]:
            self.pagina.pid = None
            self.pagina.visor.limpiar()
        self._actualizado()

    def usar(self):
        pid = self._sel()
        if not pid or not self.elegir:
            return
        self.destroy()
        self.pagina.usar_plano(pid)

    def usar_hoja(self):
        s = self.tv_h.selection()
        if not s:
            return
        h = next((x for x in self.app.p.hojas_de() if x["id"] == s[0]), None)
        if not h:
            return
        pg = self.pagina
        if pg.item and h["item"] != pg.item:
            p = self.app.p
            otra = p.item(h["item"])
            act = p.item(pg.item)
            r = ui.dialogo_texto(self, "Esta hoja es de otra actividad",
                                 f"La hoja de «{p.plano(h['plano'])['nombre']}» ya está marcada con {otra['codigo']} "
                                 f"{otra['descripcion'][:50]}: no pertenece a {act['codigo']}.\n\n¿Abrir ese mismo plano "
                                 f"limpio para {act['codigo']}, o pasar a trabajar en {otra['codigo']}?",
                                 ("Cancelar", f"Ir a {otra['codigo']}", f"Limpio para {act['codigo']}"), primario=2)
            if r == 2:
                self.destroy()
                pg.usar_plano(h["plano"])
            elif r == 1:
                self.destroy()
                pg.item = h["item"]
                pg.act = {"item": h["item"], "ref": "", "fecha": pg._fecha() or core.hoy_iso()}
                pg.cargar_actividades()
                pg._hojas()
                pg.abrir_hoja(h["plano"])
            return
        self.destroy()
        if not pg.item:
            pg.item = h["item"]
            pg.act = {"item": h["item"], "ref": "", "fecha": pg._fecha() or core.hoy_iso()}
            pg.cargar_actividades()
        pg._hojas()
        pg.abrir_hoja(h["plano"])


class DialogoPartida(Ventana):
    """Elegir cualquier partida del presupuesto. Resultado en self.res (id) o None."""

    def __init__(self, app):
        super().__init__(app, "Otra actividad", 640, 520)
        self.res = None
        c = ctk.CTkFrame(self, fg_color="transparent")
        c.pack(fill="both", expand=True, padx=20, pady=(16, 0))
        etiqueta(c, "Elegí la actividad a marcar", 16, "bold").pack(anchor="w")
        self.e = entrada(c, None, 580, placeholder_text="Buscar por código o descripción")
        self.e.pack(anchor="w", pady=(8, 6))
        self.lst = tk.Listbox(c, activestyle="none", font=TF(10), relief="flat", highlightthickness=1,
                              highlightbackground=col("borde"), bg=col("campo"), fg=col("texto"),
                              selectbackground=col("sel"), selectforeground=col("texto"))
        self.lst.pack(fill="both", expand=True)
        self.partidas = [i for i in app.p.partidas() if i["vigente"]]
        self.e.bind("<KeyRelease>", lambda _: self._filtrar())
        self.lst.bind("<Double-1>", lambda _: self.ok())
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=20, pady=(8, 18))
        boton(pie, "Elegir", primario=True, ancho=120, command=self.ok).pack(side="right")
        boton(pie, "Cancelar", ancho=110, command=self.destroy).pack(side="right", padx=8)
        self._filtrar()
        self.after(150, self.e.focus_set)
        app.wait_window(self)

    def _filtrar(self):
        q = core.clave_texto(self.e.get())
        self.vis = [i for i in self.partidas if not q or q in core.clave_texto(i["codigo"] + " " + i["descripcion"])][:400]
        self.lst.delete(0, "end")
        for it in self.vis:
            self.lst.insert("end", f"{it['codigo']:<12} {it['descripcion'][:80]}  [{it['unidad']}]")

    def ok(self):
        s = self.lst.curselection()
        if s:
            self.res = self.vis[s[0]]["id"]
            self.destroy()


class AsistenteImportacion(Ventana):
    """Nuevo proyecto (o actualizacion): archivo -> columnas -> revision."""

    def __init__(self, app, ruta, modo="nuevo"):
        super().__init__(app, "Importar presupuesto" if modo == "nuevo" else "Actualizar presupuesto", 1080, 760)
        self.ruta, self.modo = ruta, modo
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 8))
        cab.grid_columnconfigure(0, weight=1)
        etiqueta(cab, "Revisión de importación" if modo == "nuevo" else "Actualización de presupuesto", 22, "bold").grid(row=0, column=0, sticky="w")
        etiqueta(cab, os.path.basename(ruta), 12, color="texto2").grid(row=1, column=0, sticky="w")
        self.v_paso = tk.StringVar()
        etiqueta(cab, "", 13, "bold", "acento", textvariable=self.v_paso).grid(row=0, column=1, rowspan=2, sticky="e")
        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.grid(row=1, column=0, sticky="nsew", padx=28)
        self.cuerpo.grid_columnconfigure(0, weight=1)
        self.cuerpo.grid_rowconfigure(1, weight=1)
        pie = ctk.CTkFrame(self, fg_color=C["tarjeta"], corner_radius=0)
        pie.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        self.v_pie = tk.StringVar()
        lp = etiqueta(pie, "", 12, color="texto2", textvariable=self.v_pie, wraplength=600, justify="left")
        lp.pack(side="left", padx=28, pady=16)
        self.b_sig = boton(pie, "Siguiente", primario=True, ancho=160)
        self.b_sig.pack(side="right", padx=(8, 28), pady=16)
        ui.ajustar_texto(lp, pie, lambda: 90 + sum(w.winfo_reqwidth() + 10 for w in pie.pack_slaves() if w is not lp), 200)
        self.b_atras = boton(pie, "Cancelar", ancho=110, command=self.destroy)
        self.b_atras.pack(side="right", pady=16)
        try:
            self.hoja, self.filas = core.leer_excel(ruta)
        except core.ErrorCtrlP as e:
            self.after(200, lambda: (ui.info(self, "No se puede importar", str(e)), self.destroy()))
            return
        self.mapa, self.inicio = core.detectar_columnas(self.filas)
        self.correcciones = {}  # (fila, campo) -> (original, nuevo)
        self.obs_sel = 0
        self.paso_columnas()

    def _limpiar(self):
        for w in self.cuerpo.winfo_children():
            w.destroy()

    # ---- paso 2: columnas
    def paso_columnas(self):
        self._limpiar()
        self.v_paso.set("Paso 2 de 3 · Columnas")
        letras = [f"{chr(65 + k)}" for k in range(min(26, max(len(r) for r in self.filas[:200] if r) if self.filas else 6))]
        enc = {}
        for r in self.filas[max(0, self.inicio - 3):self.inicio]:
            for k, v in enumerate(r or []):
                if v not in (None, "") and k < len(letras):
                    enc[k] = f"{letras[k]} · {str(v)[:18]}"
        opciones = ["(ninguna)"] + [enc.get(k, letras[k]) for k in range(len(letras))]
        t = ui.Tarjeta(self.cuerpo)
        t.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        grid = ctk.CTkFrame(t, fg_color="transparent")
        grid.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=14)
        self.v_cols = {}
        for k, (campo, nombre) in enumerate(core.CAMPOS):
            c = ctk.CTkFrame(grid, fg_color="transparent")
            c.grid(row=k // 3, column=k % 3, sticky="w", padx=(0, 18), pady=4)
            etiqueta(c, nombre, 12, "bold").pack(anchor="w")
            col_ = self.mapa.get(campo)
            v = tk.StringVar(value=opciones[col_ + 1] if col_ is not None and col_ + 1 < len(opciones) else "(ninguna)")
            ui.menu(c, opciones, v, 230, cmd=lambda _: self._preview()).pack(anchor="w")
            self.v_cols[campo] = (v, opciones)
        c = ctk.CTkFrame(grid, fg_color="transparent")
        c.grid(row=2, column=0, sticky="w", pady=(8, 0))
        etiqueta(c, "Fila donde empiezan los datos", 12, "bold").pack(anchor="w")
        self.v_ini = tk.StringVar(value=str(self.inicio + 1))
        ui.Contador(c, self.v_ini, 1, max(1, len(self.filas)), cmd=self._preview).pack(anchor="w")
        cols = [("fila", "Fila", 60, "e")] + [(c, n, 220 if c == "descripcion" else 110, "w" if c in ("codigo", "descripcion") else "e")
                                             for c, n in core.CAMPOS]
        self.marco_prev, self.tv_prev = ui.tabla(self.cuerpo, cols, arbol=False)
        self.marco_prev.grid(row=1, column=0, sticky="nsew")
        self._preview()
        self.v_pie.set("Revisá que cada columna esté bien identificada. El programa ya propuso las que encontró en el encabezado.")
        self.b_sig.configure(text="Siguiente", command=self.paso_revision)
        self.b_atras.configure(text="Cancelar", command=self.destroy)

    def _mapa_actual(self):
        m = {}
        for campo, (v, opciones) in self.v_cols.items():
            i = opciones.index(v.get()) if v.get() in opciones else 0
            if i > 0:
                m[campo] = i - 1
        try:
            ini = max(0, int(self.v_ini.get()) - 1)
        except ValueError:
            ini = self.inicio
        return m, ini

    def _preview(self):
        m, ini = self._mapa_actual()
        self.tv_prev.delete(*self.tv_prev.get_children())
        for k in range(ini, min(ini + 40, len(self.filas))):
            r = self.filas[k]
            vals = [k + 1]
            for campo, _ in core.CAMPOS:
                c = m.get(campo)
                v = r[c] if c is not None and c < len(r) else ""
                vals.append(fmt(v) if isinstance(v, float) else ("" if v is None else str(v)[:80]))
            self.tv_prev.insert("", "end", values=vals)

    # ---- paso 3: revision
    def paso_revision(self):
        m, ini = self._mapa_actual()
        faltan = [n for c, n in core.CAMPOS if c not in m and c != "total"]
        if faltan:
            ui.info(self, "Columnas", "Falta indicar: " + ", ".join(faltan))
            return
        self.m_rev, self.ini_rev = m, ini
        self.an = core.analizar_presupuesto(self.filas, m, ini, self.ruta)
        if self.an["partidas"] == 0:
            ui.info(self, "Revisión", "No se encontraron partidas con esas columnas.")
            return
        self._limpiar()
        self.v_paso.set("Paso 3 de 3 · Revisión")
        if self.modo == "nuevo":
            self._revision_nuevo(ini)
        else:
            self._revision_actualizacion()
        self.b_atras.configure(text="Atrás", command=self.paso_columnas)
        if not hasattr(self, "b_recargar"):
            self.b_recargar = boton(self.b_atras.master, "Cargar Excel corregido…", ancho=200, command=self.recargar)
        self.b_recargar.pack(side="right", padx=(0, 8), pady=16, before=self.b_atras)

    def recargar(self):
        ruta = filedialog.askopenfilename(parent=self, title="Excel corregido", initialdir=os.path.dirname(self.ruta),
                                          filetypes=[("Excel", "*.xlsx *.xlsm")])
        if not ruta:
            return
        try:
            hoja, filas = core.leer_excel(ruta)
        except core.ErrorCtrlP as e:
            ui.info(self, "No se puede cargar", str(e))
            return
        # se conservan las correcciones hechas aqui, si esa celda no cambio en el Excel nuevo
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
        m, ini = self.m_rev, self.ini_rev
        self.an = core.analizar_presupuesto(self.filas, m, ini, self.ruta)
        self._limpiar()
        if self.modo == "nuevo":
            self._revision_nuevo(ini)
        else:
            self._revision_actualizacion()
        msg = f"Se cargó {os.path.basename(ruta)}."
        if quedan:
            msg += f"\n{len(quedan)} correcciones hechas aquí se mantienen."
        if ya:
            msg += f"\n{ya} correcciones ya vienen en el Excel."
        if perdidas:
            msg += f"\n{perdidas} correcciones ya no aplican porque esas celdas cambiaron en el Excel."
        ui.info(self, "Excel corregido", msg)

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

    def _editar_obs(self, ev):
        tv = self.tv_obs
        iid = tv.identify_row(ev.y)
        col_id = tv.identify_column(ev.x)
        if not iid or not col_id:
            return
        k = int(col_id[1:]) - 1
        campos = ["fila", "codigo", "descripcion", "unidad", "cantidad", "pu", "total"]
        campo = campos[k] if k < len(campos) else None
        if campo in (None, "fila", "total") or campo not in self.m_rev:
            return
        fila = int(tv.item(iid, "values")[0])
        actual = self.filas[fila - 1][self.m_rev[campo]] if self.m_rev[campo] < len(self.filas[fila - 1]) else None
        nombre = dict(core.CAMPOS)[campo]
        r = ui.dialogo_form(self, "Corregir celda", f"Fila {fila} del Excel · {nombre}.\nLa corrección queda anotada "
                            "en el historial del proyecto.",
                            [("v", nombre, False, "" if actual is None else (fmt(actual) if isinstance(actual, float)
                                                                            else str(actual)))],
                            ("Cancelar", "Corregir"))
        if r is None:
            return
        v = r["v"].strip()
        if campo in ("cantidad", "pu"):
            n = ui.leer_num(v)
            if n == "error" or n is None:
                ui.info(self, "Corregir", "Escribí un número válido.")
                return
            v = n
        elif campo == "unidad":
            v = v.upper()
        self._aplicar_correccion(fila, campo, v)
        self.an = core.analizar_presupuesto(self.filas, self.m_rev, self.ini_rev, self.ruta)
        sel = self.obs_sel
        self._limpiar()
        self._revision_nuevo(self.ini_rev)
        if self.an["observaciones"]:
            self._ver_obs(min(sel, len(self.an["observaciones"])))

    def _kpis(self, datos):
        kp = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        kp.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        kp.grid_columnconfigure(tuple(range(len(datos))), weight=1, uniform="k")
        for k, (a, b, c, ok) in enumerate(datos):
            t = ui.Tarjeta(kp)
            t.grid(row=0, column=k, sticky="ew", padx=(0 if k == 0 else 6, 0 if k == len(datos) - 1 else 6))
            etiqueta(t, a, 12, color="texto2").grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
            etiqueta(t, b, 20, "bold").grid(row=1, column=0, sticky="w", padx=16)
            etiqueta(t, c, 11, "bold" if ok else "normal", "acento" if ok else "texto2").grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))

    def _revision_nuevo(self, ini):
        an = self.an
        enc = core.datos_encabezado(self.filas, ini)
        self._kpis([("Partidas", f"{an['partidas']:,}", "Cantidad × precio revisado", False),
                    ("Títulos", f"{an['titulos']:,}", f"{an['capitulos']} capítulos, hasta {an['profundidad']} niveles", False),
                    ("Total importado", fmt(an["total_importado"]),
                     "Cuadra con el total de la hoja" if an["total_hoja"] is not None and an["cuadra"] else
                     ("No hay fila TOTAL para comparar" if an["total_hoja"] is None else f"La hoja dice {fmt(an['total_hoja'])}"),
                     an["cuadra"] and an["total_hoja"] is not None),
                    ("Observaciones", f"{len(an['observaciones'])} tipos", "No impiden crear el proyecto", False)])
        medio = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        medio.grid(row=1, column=0, sticky="nsew")
        medio.grid_columnconfigure(1, weight=1)
        medio.grid_rowconfigure(0, weight=1)
        self._observaciones(medio)
        t = ui.Tarjeta(self.cuerpo)
        t.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.v_datos = {"nombre": tk.StringVar(value=enc.get("nombre_corto") or enc["nombre"]),
                        "contratista": tk.StringVar(value=enc["contratista"]),
                        "propietario": tk.StringVar(value=enc["propietario"]),
                        "moneda": tk.StringVar(value=enc["moneda"])}
        g = ctk.CTkFrame(t, fg_color="transparent")
        g.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=12)
        for k, (cl, n, w) in enumerate((("nombre", "Nombre del proyecto (editable)", 330), ("contratista", "Contratista", 230),
                                        ("propietario", "Propietario", 230), ("moneda", "Moneda", 80))):
            c = ctk.CTkFrame(g, fg_color="transparent")
            c.grid(row=0, column=k, sticky="w", padx=(0, 12))
            etiqueta(c, n, 11, color="texto2").pack(anchor="w")
            (ui.entrada_mayus(c, self.v_datos[cl], w) if cl == "nombre" else entrada(c, self.v_datos[cl], w)).pack(anchor="w")
        self.v_pie.set("El presupuesto quedará de solo lectura. Nada se crea hasta presionar «Crear proyecto».")
        self.b_sig.configure(text="Crear proyecto", command=self.crear)

    def _observaciones(self, medio):
        an = self.an
        izq = ui.Tarjeta(medio)
        izq.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        etiqueta(izq, "Observaciones", 14, "bold").grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))
        self.obs_vars = []
        r = 1
        if not an["observaciones"]:
            etiqueta(izq, "Sin observaciones.", 12, color="texto2").grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        for k, o in enumerate(an["observaciones"]):
            b = ctk.CTkButton(izq, text=f"{o['tipo']}  ·  {o['cantidad']}", anchor="w", width=360, height=30, corner_radius=8,
                              font=F(12, "bold"), fg_color=C["suave"] if k == 0 else "transparent", hover_color=C["suave_h"],
                              text_color=C["texto"], command=lambda k=k: self._ver_obs(k))
            b.grid(row=r, column=0, sticky="w", padx=10, pady=(2, 0))
            ctk.CTkLabel(izq, text=o["detalle"], font=F(11), text_color=C["texto2"], wraplength=340, justify="left",
                         anchor="w").grid(row=r + 1, column=0, sticky="w", padx=20, pady=(0, 6))
            self.obs_vars.append(b)
            r += 2
        cols = [("fila", "Fila", 56, "e"), ("codigo", "Código", 110, "w"), ("descripcion", "Descripción", 300, "w"),
                ("unidad", "Unid.", 56, "center"), ("cantidad", "Cantidad", 90, "e"), ("pu", "P. unitario", 90, "e"),
                ("total", "Total", 110, "e")]
        b = ctk.CTkButton(izq, text="Todas las partidas", anchor="w", width=360, height=30, corner_radius=8,
                          font=F(12, "bold"), fg_color="transparent", hover_color=C["suave_h"], text_color=C["texto"],
                          command=lambda: self._ver_obs(len(self.an["observaciones"])))
        b.grid(row=r, column=0, sticky="w", padx=10, pady=(8, 0))
        self.obs_vars.append(b)
        ctk.CTkLabel(izq, text="Doble clic en una celda de la tabla para corregirla.", font=F(11),
                     text_color=C["texto2"]).grid(row=r + 1, column=0, sticky="w", padx=20, pady=(0, 4))
        if self.correcciones:
            ctk.CTkLabel(izq, text=f"✎ {len(self.correcciones)} correcciones hechas aquí", font=F(12, "bold"),
                         text_color=C["acento"]).grid(row=r + 2, column=0, sticky="w", padx=20, pady=(0, 12))
        self.marco_obs, self.tv_obs = ui.tabla(medio, cols, arbol=False)
        self.marco_obs.grid(row=0, column=1, sticky="nsew")
        self.tv_obs.bind("<Double-1>", self._editar_obs)
        self._ver_obs(0 if an["observaciones"] else len(an["observaciones"]))

    def _ver_obs(self, k):
        self.obs_sel = k
        for j, b in enumerate(self.obs_vars):
            b.configure(fg_color=C["suave"] if j == k else "transparent")
        self.tv_obs.delete(*self.tv_obs.get_children())
        if k < len(self.an["observaciones"]):
            filas = self.an["observaciones"][k]["filas"][:500]
        else:
            filas = [(i["fila"], i["codigo"], i["descripcion"], i["unidad"], i["cantidad"], i["pu"], i["total"])
                     for i in self.an["items"] if i["tipo"] == "P"]
        corr = {f for f, _ in self.correcciones}
        for f in filas:
            self.tv_obs.insert("", "end", values=[f[0], f[1], f[2], f[3]] + [fmt(x) if isinstance(x, float) else "" for x in f[4:]],
                               tags=("subtotal",) if f[0] in corr else ())

    def crear(self):
        nombre = core.mayus(self.v_datos["nombre"].get()) or "PROYECTO"
        ruta = filedialog.asksaveasfilename(parent=self, title="Guardar proyecto", defaultextension=core.EXT,
                                            initialfile=f"{nombre[:50]}{core.EXT}",
                                            initialdir=ui.carpeta_docs(),
                                            filetypes=[("Proyecto Ctrl-P", "*.ctrlp")])
        if not ruta:
            return
        datos = {k: v.get() for k, v in self.v_datos.items()}
        datos["nombre"] = nombre
        if not self.app.cerrar_proyecto():
            return
        try:
            self.app.p = core.Proyecto.crear(ruta, self.app.usuario, self.an, datos)
            self.app.p.sincronizar_usuarios()
            if self.correcciones:
                por_fila = {i["fila"]: i for i in self.an["items"]}
                for (fila, campo), (orig, nuevo) in sorted(self.correcciones.items()):
                    it = por_fila.get(fila)
                    self.app.p.registrar(f"Corrección al importar (fila {fila}): {dict(core.CAMPOS)[campo]}",
                                         self.app.p.etiqueta_item(it) if it else "", "", orig, nuevo)
                self.app.p.guardar()
        except Exception as e:
            ui.info(self, "No se pudo crear", str(e))
            return
        self.destroy()
        self.app.proyecto_cargado()
        ui.info(self.app, "Proyecto creado", f"Se creó «{nombre}».\n\nSiguiente paso: creá las ubicaciones (edificios, niveles y áreas).")

    # ---- actualizacion
    def _revision_actualizacion(self):
        p = self.app.p
        self.comp = core.comparar_presupuestos(p, self.an)
        c = self.comp
        if not c["mismo"]:
            self._kpis([("Coincidencia de partidas", f"{c['coincidencia'] * 100:.2f} %", "Con el presupuesto actual", False),
                        ("Coincidencia de capítulos", f"{c['coincidencia_capitulos'] * 100:.2f} %", "Títulos principales", False)])
            t = ui.Tarjeta(self.cuerpo)
            t.grid(row=1, column=0, sticky="new")
            ctk.CTkLabel(t, text="Este Excel no es el mismo presupuesto del proyecto.", font=F(16, "bold"),
                         text_color=C["rojo"]).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
            ctk.CTkLabel(t, text="La mayoría de sus partidas y capítulos no coinciden con las del proyecto. Cargarlo "
                                 "provocaría errores (avances y cantidades contractuales quedarían sin su partida), "
                                 "por eso no se puede aplicar.\n\nRevisá que sea el archivo correcto, o creá un proyecto "
                                 "nuevo con este presupuesto.", font=F(13), text_color=C["texto"], wraplength=820,
                         justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))
            self.v_pie.set("No se aplicó ningún cambio.")
            self.b_sig.configure(text="Cerrar", command=self.destroy)
            return
        con_av = sum(1 for _, av in c["eliminadas"] if av)
        self._kpis([("Sin cambios", f"{len(c['sin_cambios']):,}", "Se mantienen igual", False),
                    ("Modificadas", f"{len(c['modificadas'])}", "Conservan avance y contractual", False),
                    ("Por confirmar", f"{len(c['probables'])}", "Doble clic para aceptar o rechazar", bool(c["probables"])),
                    ("Nuevas / eliminadas", f"{len(c['nuevas'])} / {len(c['eliminadas'])}",
                     f"{con_av} con avance quedan como «fuera»", False)])
        cols = [("estado", "Resultado", 170, "w"), ("codigo", "Código", 170, "w"), ("descripcion", "Descripción", 300, "w"),
                ("antes", "Antes", 190, "w"), ("despues", "Después", 190, "w")]
        marco, self.tv_comp = ui.tabla(self.cuerpo, cols, arbol=False)
        marco.grid(row=1, column=0, sticky="nsew")
        self.aceptar = {}
        tv = self.tv_comp
        for a, n, s in c["probables"]:
            self.aceptar[n["id"]] = True
            tv.insert("", "end", iid="P" + n["id"], values=("✓ Vincular (probable)", f"{a['codigo']} → {n['codigo']}", n["descripcion"],
                                                            f"{fmt(a['cantidad'])} × {fmt(a['pu'])}", f"{fmt(n['cantidad'])} × {fmt(n['pu'])}"))
        for a, n in c["modificadas"]:
            tv.insert("", "end", values=("Modificada", n["codigo"], n["descripcion"],
                                         f"{fmt(a['cantidad'])} {a['unidad']} × {fmt(a['pu'])}",
                                         f"{fmt(n['cantidad'])} {n['unidad']} × {fmt(n['pu'])}"))
        for n in c["nuevas"]:
            tv.insert("", "end", values=("Nueva", n["codigo"], n["descripcion"], "", f"{fmt(n['cantidad'])} {n['unidad']} × {fmt(n['pu'])}"))
        for a, av in c["eliminadas"]:
            tv.insert("", "end", values=("Eliminada" + (" (con avance)" if av else ""), a["codigo"], a["descripcion"],
                                         f"{fmt(a['cantidad'])} {a['unidad']} × {fmt(a['pu'])}",
                                         "Fuera del presupuesto vigente" if av else "Se retira"), tags=("neg",) if av else ())
        tv.bind("<Double-1>", self._toggle)
        self.v_pie.set((f"⚠ Solo coincide el {c['coincidencia'] * 100:.2f} % de las partidas: revisá bien antes de aplicar. "
                        if c["dudoso"] else "") +
                       f"Total actual {fmt(p.total_presupuesto())} → nuevo {fmt(self.an['total_importado'])}. "
                       "Se hará una copia de seguridad antes de aplicar.")
        self.b_sig.configure(text="Aplicar actualización", command=self.aplicar)

    def _toggle(self, ev):
        iid = self.tv_comp.identify_row(ev.y)
        if iid and iid.startswith("P"):
            k = iid[1:]
            self.aceptar[k] = not self.aceptar[k]
            vals = list(self.tv_comp.item(iid, "values"))
            vals[0] = "✓ Vincular (probable)" if self.aceptar[k] else "✗ Tratar como nueva"
            self.tv_comp.item(iid, values=vals)

    def aplicar(self):
        p = self.app.p
        try:
            import shutil
            carpeta = core.Proyecto.carpeta_respaldos(p.ruta)
            os.makedirs(carpeta, exist_ok=True)
            p.guardar()
            stem = os.path.splitext(os.path.basename(p.ruta))[0]
            shutil.copy2(p.ruta, os.path.join(carpeta, f"{stem}_antes de presupuesto V{p.version_presupuesto + 1}{core.EXT}"))
            v = core.aplicar_actualizacion(p, self.an, self.comp, self.aceptar, self.ruta)
            self.app.guardar()
        except Exception as e:
            ui.info(self, "No se pudo actualizar", str(e))
            return
        self.destroy()
        self.app.proyecto_cargado()
        ui.info(self.app, "Presupuesto actualizado", f"El proyecto ahora usa el presupuesto V{v}.")


class DialogoImportacion(Ventana):
    def __init__(self, app, imp):
        super().__init__(app, "Importar archivo recibido", 1040, 700)
        self.imp = imp
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        etiqueta(self, "Resumen de cambios", 22, "bold").grid(row=0, column=0, sticky="w", padx=28, pady=(20, 0))
        la = etiqueta(self, imp["archivo"] + (f"  ·  {imp['aviso']}" if imp["aviso"] else ""), 12, color="texto2",
                      wraplength=900, justify="left")
        la.grid(row=1, column=0, sticky="w", padx=28, pady=(0, 10))
        ui.ajustar_texto(la, self, 60, 200)
        cols = [("tipo", "Cambio", 150, "w"), ("fecha", "Fecha", 90, "center"), ("actividad", "Actividad", 330, "w"),
                ("ubicacion", "Ubicación", 150, "w"), ("valor", "Valor", 200, "w"), ("usuario", "Usuario", 170, "w")]
        marco, self.tv = ui.tabla(self, cols, arbol=False)
        marco.grid(row=2, column=0, sticky="nsew", padx=28)
        p = app.p
        self.usar = {}
        for l, r in imp["modificados"]:
            self.usar[l["id"]] = True
            it = p.item(r["item"])
            self.tv.insert("", "end", iid="M" + l["id"], values=(
                "✓ Usar el recibido", core.fecha_txt(r["fecha"]), p.etiqueta_item(it) if it else "", r["ubicacion"],
                f"{fmt(l['cantidad'])} → {fmt(r['cantidad'])}", r["mod_usuario"]), tags=("neg",))
        for r in imp["nuevos"]:
            it = p.item(r["item"])
            self.tv.insert("", "end", values=("Avance nuevo", core.fecha_txt(r["fecha"]), p.etiqueta_item(it) if it else "",
                                              r["ubicacion"], f"{fmt(r['cantidad'])} {it['unidad'] if it else ''}" +
                                              (f" · {r['obs']}" if r["obs"] else ""), r["usuario"]))
        for r, l, n in imp["contractual"]:
            it = p.item(r["item"])
            self.tv.insert("", "end", values=("Contractual", "", p.etiqueta_item(it) if it else "", n,
                                              f"{fmt(l)} → {fmt(r['cantidad'])}", ""))
        for tipo, d in imp["ubicaciones"]:
            self.tv.insert("", "end", values=("Ubicación nueva", "", "", d["nombre"], tipo, ""))
        self.tv.bind("<Double-1>", self._toggle)
        pie = ctk.CTkFrame(self, fg_color=C["tarjeta"], corner_radius=0)
        pie.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        n = len(imp["nuevos"])
        etiqueta(pie, f"{n} avances nuevos · {len(imp['modificados'])} registros modificados (doble clic para elegir) · "
                      f"{len(imp['contractual'])} contractuales · {len(imp['historial'])} filas de historial", 12,
                 color="texto2").pack(side="left", padx=28, pady=16)
        boton(pie, "Aplicar cambios", primario=True, ancho=160, command=self.aplicar).pack(side="right", padx=(8, 28), pady=16)
        boton(pie, "Cancelar", ancho=110, command=self.destroy).pack(side="right", pady=16)

    def _toggle(self, ev):
        iid = self.tv.identify_row(ev.y)
        if iid and iid.startswith("M"):
            k = iid[1:]
            self.usar[k] = not self.usar[k]
            vals = list(self.tv.item(iid, "values"))
            vals[0] = "✓ Usar el recibido" if self.usar[k] else "✗ Mantener el mío"
            self.tv.item(iid, values=vals)

    def aplicar(self):
        p = self.app.p
        try:
            p.guardar()
            import shutil
            carpeta = core.Proyecto.carpeta_respaldos(p.ruta)
            os.makedirs(carpeta, exist_ok=True)
            stem = os.path.splitext(os.path.basename(p.ruta))[0]
            shutil.copy2(p.ruta, os.path.join(carpeta, f"{stem}_antes de importar {os.path.splitext(self.imp['archivo'])[0]}{core.EXT}"))
            core.aplicar_importacion(p, self.imp, self.usar)
            self.app.guardar()
        except Exception as e:
            ui.info(self, "No se pudo importar", str(e))
            return
        self.destroy()
        self.app.proyecto_cargado()
        ui.info(self.app, "Importación aplicada", "Los cambios recibidos se incorporaron al proyecto.")


class DialogoSugerencias(Ventana):
    def __init__(self, app, sug, al_terminar):
        super().__init__(app, "Sugerir ubicaciones", 900, 600)
        self.sug, self.al_terminar = sug, al_terminar
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        etiqueta(self, "Partidas que mencionan una ubicación", 20, "bold").grid(row=0, column=0, sticky="w", padx=28, pady=(20, 8))
        cols = [("ok", "Asignar", 80, "center"), ("codigo", "Código", 110, "w"), ("descripcion", "Descripción", 440, "w"),
                ("ubicacion", "Ubicación propuesta", 180, "w")]
        marco, self.tv = ui.tabla(self, cols, arbol=False)
        marco.grid(row=1, column=0, sticky="nsew", padx=28)
        self.ok = {}
        for k, (it, nv, et) in enumerate(sug):
            self.ok[k] = True
            self.tv.insert("", "end", iid=str(k), values=("✓", it["codigo"], it["descripcion"], et))
        self.tv.bind("<Double-1>", self._toggle)
        pie = ctk.CTkFrame(self, fg_color=C["tarjeta"], corner_radius=0)
        pie.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        etiqueta(pie, "Doble clic para quitar una sugerencia. Revisá: textos como «B1» pueden ser nombres de equipos.", 12,
                 color="texto2").pack(side="left", padx=28, pady=16)
        boton(pie, "Asignar", primario=True, ancho=130, command=self.aplicar).pack(side="right", padx=(8, 28), pady=16)
        boton(pie, "Cancelar", ancho=110, command=self.destroy).pack(side="right", pady=16)

    def _toggle(self, ev):
        iid = self.tv.identify_row(ev.y)
        if iid:
            k = int(iid)
            self.ok[k] = not self.ok[k]
            vals = list(self.tv.item(iid, "values"))
            vals[0] = "✓" if self.ok[k] else "✗"
            self.tv.item(iid, values=vals)

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
        self.destroy()
        self.al_terminar()
        ui.info(self.app, "Ubicaciones asignadas", f"{n} partidas quedaron con ubicación fija.")


class DialogoUsuarios(Ventana):
    """Usuario actual; el administrador ve y administra todas las contraseñas."""

    def __init__(self, app):
        super().__init__(app, "Usuarios", 760, 560)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 10))
        admin = core.es_admin(app.usuario)
        if admin:
            self._img = ctk.CTkImage(ui.husky(128), size=(64, 64))
            ctk.CTkLabel(cab, text="", image=self._img).pack(side="left", padx=(0, 14))
        caja = ctk.CTkFrame(cab, fg_color="transparent")
        caja.pack(side="left")
        etiqueta(caja, app.usuario, 18, "bold").pack(anchor="w")
        etiqueta(caja, "Administrador · puede ver y cambiar todas las contraseñas" if admin else
                 ("Usuario con contraseña" if app.con_clave else "Usuario sin contraseña"), 12, color="texto2").pack(anchor="w")
        boton(cab, "Cambiar de usuario", ancho=160, command=self.cambiar_usuario).pack(side="right")
        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 20))
        self.cuerpo.grid_columnconfigure(0, weight=1)
        self.cuerpo.grid_rowconfigure(1, weight=1)
        self.ver = False
        self.armar()

    def _extra(self):
        return self.app.p.usuarios_proyecto() if self.app.p else None

    def armar(self):
        for w in self.cuerpo.winfo_children():
            w.destroy()
        app = self.app
        if core.es_admin(app.usuario):
            barra = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
            barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
            etiqueta(barra, "Usuarios con contraseña", 14, "bold").pack(side="left")
            boton(barra, "Ocultar contraseñas" if self.ver else "Mostrar contraseñas", ancho=170,
                  command=self._alternar).pack(side="right")
            boton(barra, "Quitar contraseña", ancho=150, command=self.quitar).pack(side="right", padx=8)
            boton(barra, "Cambiar contraseña", ancho=160, command=self.cambiar_otro).pack(side="right")
            cols = [("usuario", "Usuario", 260, "w"), ("clave", "Contraseña", 170, "w"), ("creado", "Creado", 150, "w")]
            marco, self.tv = ui.tabla(self.cuerpo, cols, arbol=False)
            marco.grid(row=1, column=0, sticky="nsew")
            regs = core.usuarios_registrados(self._extra())
            for u in sorted(regs):
                r = regs[u]
                c = core.ver_clave(app.llave, r.get("cifrada")) if self.ver else "••••••"
                if self.ver and not c:
                    c = "(no disponible)"
                self.tv.insert("", "end", iid=u, values=(u, c, r.get("creado", "")))
            if not regs:
                self.tv.insert("", "end", values=("Todavía no hay otros usuarios con contraseña.", "", ""))
        else:
            t = ui.Tarjeta(self.cuerpo)
            t.grid(row=0, column=0, sticky="ew")
            if app.con_clave:
                t.fila("Mi contraseña", boton(t, "Cambiar…", ancho=120, command=self.cambiar_mia),
                       "Necesitás tu contraseña actual.")
            else:
                t.fila("Proteger mi usuario", boton(t, "Crear contraseña…", ancho=160, command=self.crear_mia),
                       "Así nadie más puede entrar con tu nombre.")

    def _alternar(self):
        self.ver = not self.ver
        self.armar()

    def _sinc(self):
        if self.app.p:
            self.app.p.sincronizar_usuarios()
            self.app.guardar()

    def _sel(self):
        s = self.tv.selection()
        if not s or not self.tv.exists(s[0]) or s[0] not in core.usuarios_registrados(self._extra()):
            ui.info(self, "Usuarios", "Elegí un usuario de la lista.")
            return None
        return s[0]

    def cambiar_otro(self):
        u = self._sel()
        if not u:
            return
        r = ui.dialogo_form(self, "Cambiar contraseña", u, [("clave", "Nueva contraseña", True, "")],
                            ("Cancelar", "Guardar"),
                            validar=lambda v: "" if len(v["clave"]) >= 4 else "Mínimo 4 caracteres.")
        if r:
            core.cambiar_clave(u, r["clave"], self._extra())
            self._sinc()
            self.armar()

    def quitar(self):
        u = self._sel()
        if not u:
            return
        if ui.preguntar(self, "Quitar contraseña", f"{u} volverá a entrar solo con su nombre.", si="Quitar"):
            core.quitar_clave(u)
            self._sinc()
            self.armar()

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
        r = ui.dialogo_form(self, "Cambiar mi contraseña", u,
                            [("actual", "Contraseña actual", True, ""), ("nueva", "Nueva contraseña", True, ""),
                             ("nueva2", "Repetir nueva contraseña", True, "")], ("Cancelar", "Guardar"), validar=validar)
        if r:
            core.cambiar_clave(u, r["nueva"], self._extra())
            self._sinc()
            ui.info(self, "Contraseña", "Tu contraseña se cambió.")

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
        r = ui.dialogo_form(self, "Crear contraseña", u, [("clave", "Contraseña", True, ""),
                                                           ("clave2", "Repetir contraseña", True, "")],
                            ("Cancelar", "Guardar"), validar=validar)
        if r:
            self.app.con_clave = True
            self._sinc()
            self.armar()

    def cambiar_usuario(self):
        if self.app.p and not self.app.cerrar_proyecto():
            return
        self.destroy()
        self.app.usuario = None
        self.app.llave = None
        self.app.con_clave = False
        self.app.paginas = {}
        self.app.pagina = None
        self.app.mostrar_login()


class DialogoColumnas(Ventana):
    def __init__(self, app, visibles, al_aceptar):
        super().__init__(app, "Columnas", 420, 560)
        self.al_aceptar = al_aceptar
        etiqueta(self, "Columnas visibles", 18, "bold").pack(anchor="w", padx=24, pady=(20, 4))
        etiqueta(self, "Las que ocultes tampoco se exportan al Excel.", 12, color="texto2").pack(anchor="w", padx=24, pady=(0, 10))
        t = ui.Tarjeta(self)
        t.pack(fill="x", padx=24)
        self.vars = {}
        for k, n in xl.COLUMNAS_OPCIONALES:
            v = tk.BooleanVar(value=k in visibles)
            self.vars[k] = v
            t.fila(n, ui.Interruptor(t, v))
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=24, pady=16)
        boton(f, "Aceptar", primario=True, ancho=120, command=self.ok).pack(side="right")
        boton(f, "Cancelar", ancho=100, command=self.destroy).pack(side="right", padx=8)

    def ok(self):
        vis = {k for k, v in self.vars.items() if v.get()}
        self.destroy()
        self.al_aceptar(vis)


# =========================================================================
PAGINAS_MANUALES = ("proyecto", "presupuesto", "ubicaciones", "informes")
NOMBRE_MASTER = "Registro_Semanal"
NOMBRE_ACTUALIZACION = "actualizacion_semanal"


def _al_dia(metodo):
    """Despues de rearmar una pantalla manual, queda marcada como actualizada (con los datos de ahora)."""
    import functools

    @functools.wraps(metodo)
    def envuelto(self, *a, **kw):
        r = metodo(self, *a, **kw)
        if self.app.p is not None:
            self._rev_cargada = self.app.p.rev
            self._proy_cargado = self.app.p
        else:
            self._proy_cargado = None
        try:
            self.app.dibujar_lateral()
        except Exception:
            pass
        return r
    return envuelto


def _sin_rayas(metodo):
    """Envuelve el metodo que rearma el panel de la partida: se arma oculto y aparece completo."""
    import functools

    @functools.wraps(metodo)
    def envuelto(self, *a, **kw):
        panel = getattr(self, "panel", None)
        if panel is None:
            return metodo(self, *a, **kw)
        return ui.armar_oculto(panel, lambda: metodo(self, *a, **kw))
    return envuelto


for _cls in (PaginaProyecto, PaginaPresupuesto, PaginaUbicaciones):
    _cls.refrescar = _al_dia(_cls.refrescar)
PaginaInformes.generar = _al_dia(PaginaInformes.generar)

for _cls, _nombres in ((PaginaDatosFijos, ("mostrar",)), (PaginaRegistro, ("mostrar",))):
    for _n in _nombres:
        if hasattr(_cls, _n):
            setattr(_cls, _n, _sin_rayas(getattr(_cls, _n)))


# ------------------------------------------------------------------ registro de errores
RUTA_LOG = None


def registrar_error(titulo, texto):
    """Agrega el error al registro (%APPDATA%\\Ctrl-P\\errores.log); nunca deja archivos junto al proyecto."""
    try:
        import datetime as _dt
        with open(RUTA_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n===== {_dt.datetime.now():%Y-%m-%d %H:%M:%S} · Ctrl-P {VERSION} · {titulo}\n{texto}\n")
    except Exception:
        pass


def vigilante(app, segundos=8):
    """Si la ventana deja de responder mas de «segundos», anota en errores.log donde se quedo el programa
    (la linea exacta), aunque despues se cierre a la fuerza. Y cuando vuelve a responder, cuanto tardo."""
    import time
    import traceback
    estado = {"latido": time.monotonic(), "parado": False}
    hilo_principal = threading.main_thread().ident

    def latido():
        estado["latido"] = time.monotonic()
        try:
            app.after(500, latido)
        except Exception:
            pass

    def mirar():
        while True:
            time.sleep(1.0)
            espera = time.monotonic() - estado["latido"]
            if espera > segundos and not estado["parado"]:
                estado["parado"] = True
                try:
                    pila = "".join(traceback.format_stack(sys._current_frames()[hilo_principal]))
                except Exception as e:
                    pila = f"(no se pudo leer: {e})"
                registrar_error("No responde", f"La ventana lleva {espera:.0f} s sin responder. Página: "
                                f"{getattr(app, 'pagina', '?')}. Proyecto abierto: {bool(getattr(app, 'p', None))}.\n"
                                f"Dónde está el programa:\n{pila}")
            elif espera < 2 and estado["parado"]:
                estado["parado"] = False
                registrar_error("Volvió a responder", f"Página: {getattr(app, 'pagina', '?')}.")
    app.after(500, latido)
    threading.Thread(target=mirar, daemon=True, name="vigilante").start()


def autoprueba(app, ruta, log):
    """Prueba automatica (la usa GitHub antes de publicar una version): entra, abre el proyecto de prueba,
    recorre todas las paginas e Informes con sus combinaciones, exporta y se cierra. Si algo falla, lo
    escribe en «log» y el programa sale con codigo 1."""
    import traceback

    def fallo(texto):
        with open(log, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    app.report_callback_exception = lambda tp, val, tb: fallo("".join(traceback.format_exception(tp, val, tb)))
    ui.dialogo_texto = lambda *a, **k: 0
    ui.info = lambda *a, **k: None
    ui.preguntar = lambda *a, **k: False
    pasos = []

    def paso(f):
        pasos.append(f)
        return f

    @paso
    def entrar():
        app._act_revisado = True                      # sin buscar actualizaciones en la prueba
        app.entrar("PRUEBA - CI")

    @paso
    def abrir():
        app.abrir_proyecto(ruta)

    for clave in ("proyecto", "presupuesto", "ubicaciones", "datos", "registro", "planos", "apariencia"):
        paso(lambda c=clave: app.ir(c))

    @paso
    def registro():
        app.ir("registro")
        pg = app.paginas["registro"]
        pg.v_fecha.set("01/06/2026")
        pg.cambiar_fecha()
        it = [i for i in app.p.partidas() if i["codigo"] == "02.02"][0]
        pg.elegir(app.p.item(it["id"]))
        k = next(iter(pg.filas))
        pg.filas[k]["v"].set("5")
        app.refrescar_actual()
        pg.filas[k]["v"].set("")

    @paso
    def informes():
        app.ir("informes")
        pg = app.paginas["informes"]
        for modo in ("Período", "Estado al"):
            pg.v_modo.set(modo)
            pg._modo()
            pg.v_desde.set("01/06/2026")
            pg.v_hasta.set("30/06/2026")
            for det in ("Sumatoria", "+ Por semana"):
                for vista in ("Por partida", "Detallado por ubicación"):
                    for filtro in [t for _, t in core.FILTROS]:
                        for contr in (False, True):
                            pg.v_det.set(det)
                            pg.v_vista.set(vista)
                            pg.v_filtro.set(filtro)
                            pg.v_contr.set(contr)
                            pg.generar()

    @paso
    def barra_horizontal():
        # como en Informes: una semana cortada en dos, «+ Por semana», con avance y solo lo contractual;
        # se toca y arrastra la barra de desplazamiento horizontal (no debe quedar «No responde»)
        pg = app.paginas["informes"]
        pg.v_modo.set("Período")
        pg._modo()
        for det in ("+ Por semana", "+ Por día", "Sumatoria"):
            for filtro, contr in (("Con avance", True), ("Presupuesto completo", False)):
                pg.v_desde.set("04/06/2026")
                pg.v_hasta.set("10/06/2026")
                pg.v_det.set(det)
                pg.v_filtro.set(filtro)
                pg.v_contr.set(contr)
                pg.generar()
                app.update()
                barras = [w for w in pg.marco.winfo_children()
                          if isinstance(w, ctk.CTkScrollbar) and getattr(w, "_orientation", "") == "horizontal"]
                for b in barras:
                    c = b._canvas
                    w_, h_ = max(4, c.winfo_width()), max(4, c.winfo_height())
                    for x in (w_ // 2, 2, w_ - 2):
                        c.event_generate("<Button-1>", x=x, y=h_ // 2)
                        for k in range(8):
                            c.event_generate("<B1-Motion>", x=min(w_ - 1, x + k * 6), y=h_ // 2)
                        c.event_generate("<ButtonRelease-1>", x=x, y=h_ // 2)
                        app.update()

    @paso
    def exportar():
        import tempfile
        d = tempfile.mkdtemp()
        pg = app.paginas["informes"]
        for det in ("+ Por día", "Sumatoria"):
            pg.v_det.set(det)
            destino = os.path.join(d, f"inf_{len(os.listdir(d))}.xlsx")
            filedialog.asksaveasfilename = lambda *a, **k: destino
            pg.exportar()
            if not os.path.getsize(destino):
                raise RuntimeError("Excel vacío")
        import openpyxl
        for eleccion in (2, 1):                 # solo el corte / corte + memorias (columna ESTE PERÍODO)
            destino = os.path.join(d, f"corte_{eleccion}.xlsx")
            filedialog.asksaveasfilename = lambda *a, **k: destino
            ui.dialogo_texto = lambda *a, **k: eleccion
            pg.exportar_corte()
            ui.dialogo_texto = lambda *a, **k: 0
            wb_ = openpyxl.load_workbook(destino)
            if eleccion == 1:
                hm = [h for h in wb_.sheetnames if h.startswith("M.C ")]
                if not hm or "ESTE PERÍODO" not in [c.value for c in wb_[hm[0]][16]]:
                    raise RuntimeError(f"Corte sin memorias con ESTE PERÍODO: {wb_.sheetnames}")
        # memorias de calculo: solo memorias y informe + memorias
        import openpyxl
        for eleccion in (2, 1):
            destino = os.path.join(d, f"memorias_{eleccion}.xlsx")
            filedialog.asksaveasfilename = lambda *a, **k: destino
            ui.dialogo_texto = lambda *a, **k: eleccion
            pg.memorias()
            ui.dialogo_texto = lambda *a, **k: 0
            hojas = openpyxl.load_workbook(destino, read_only=True).sheetnames
            if not any(h.startswith("M.C ") for h in hojas):
                raise RuntimeError(f"Sin memorias de cálculo: {hojas}")

    @paso
    def salir():
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"AUTOPRUEBA OK ({len(pasos)} pasos)\n")
        app.al_cerrar()

    def correr(i=0):
        if i >= len(pasos):
            return
        try:
            pasos[i]()
        except Exception:
            fallo(f"AUTOPRUEBA FALLO en el paso {pasos[i].__name__}:\n" + traceback.format_exc())
            try:
                app.destroy()
            except Exception:
                pass
            return
        app.after(700, lambda: correr(i + 1))
    app.after(1500, correr)


def main():
    import multiprocessing
    multiprocessing.freeze_support()
    global RUTA_LOG
    import faulthandler
    import threading
    import traceback
    carpeta = core.carpeta_config()
    RUTA_LOG = os.path.join(carpeta, "errores.log")
    try:
        if os.path.getsize(RUTA_LOG) > 2_000_000:            # que no crezca sin limite
            os.replace(RUTA_LOG, RUTA_LOG + ".anterior")
    except OSError:
        pass
    marca = os.path.join(carpeta, "sesion_abierta")
    cierre_inesperado = os.path.exists(marca)
    flog = None
    try:
        flog = open(RUTA_LOG, "a", encoding="utf-8")
        flog.write(f"\n--- inicio {__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S} · Ctrl-P {VERSION} · "
                   f"{sys.platform} · Python {sys.version.split()[0]}\n")
        flog.flush()
        faulthandler.enable(flog, all_threads=True)          # cierres de golpe (errores internos de Windows/Tk)
    except Exception:
        pass
    sys.excepthook = lambda tp, val, tb: registrar_error("Error", "".join(traceback.format_exception(tp, val, tb)))
    threading.excepthook = lambda a: registrar_error(
        "Error en segundo plano", "".join(traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback)))
    try:
        with open(marca, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass
    act_.anotar_version_instalada(VERSION_INTERNA)
    archivo = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].lower().endswith(core.EXT) else None
    prueba = os.environ.get("CTRLP_AUTOPRUEBA")
    try:
        app = App(archivo)
        vigilante(app)
        if prueba:
            autoprueba(app, prueba, os.environ.get("CTRLP_AUTOPRUEBA_LOG") or os.path.join(carpeta, "autoprueba.log"))
        elif cierre_inesperado:
            registrar_error("Aviso", "La sesión anterior terminó sin cerrar el programa.")
            app.after(1500, app.avisar_cierre_inesperado)
        app.mainloop()
    except Exception:
        registrar_error("Error fatal", traceback.format_exc())
        raise
    finally:
        try:
            os.remove(marca)
        except OSError:
            pass
        try:
            import ctrlp_render
            ctrlp_render.cerrar()
        except Exception:
            pass


if __name__ == "__main__":
    main()
