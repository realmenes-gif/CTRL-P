"""
Ctrl-P - planos
===============
Carga de planos (PDF o imagen, con opcion de aplanar y comprimir como en PdFOL),
visor con zoom profundo, calibracion de escala, marcado de avance con estilos
(color, transparencia, grosor), formas (lineas, lineas libres, rectangulos,
circulos, poligonos, areas libres y puntos con distintas formas), notas,
colores por periodo y exportacion.
"""

import io
import math
import os
import tkinter as tk
from tkinter import colorchooser

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

import ctrlp_core as core
import ctrlp_render as render
import ctrlp_ui as ui
from concurrent.futures import ThreadPoolExecutor

NUCLEOS = render.NUCLEOS
_hilos = ThreadPoolExecutor(max_workers=NUCLEOS) if NUCLEOS > 1 else None


def en_paralelo(fn, partes):
    """Ejecuta fn sobre cada parte usando todos los nucleos (Pillow suelta el GIL en reduce/resize/composite)."""
    partes = list(partes)
    if _hilos is None or len(partes) < 2:
        return [fn(x) for x in partes]
    return list(_hilos.map(fn, partes))


def reducir(img):
    """img.reduce(2) repartido en franjas horizontales (una por nucleo) para planos grandes."""
    w, h = img.size
    if NUCLEOS < 2 or w * h < 4_000_000:
        return img.reduce(2)
    n = min(NUCLEOS, 16)
    cortes = [2 * round(h * k / n / 2) for k in range(n + 1)]
    cortes[-1] = h - (h % 2)
    franjas = en_paralelo(lambda k: img.crop((0, cortes[k], w - (w % 2), cortes[k + 1])).reduce(2), range(n))
    out = Image.new(img.mode, (w // 2, h // 2))
    for k, f in enumerate(franjas):
        out.paste(f, (0, cortes[k] // 2))
    return out
from ctrlp_ui import C, F, TF, boton, col, entrada, etiqueta, fmt

Image.MAX_IMAGE_PIXELS = None
LADO_MAX = 9000          # lado mayor de la imagen base (px)
ZOOM_MAX = 40.0
COLOR_PERIODO = "#16A34A"
COLOR_ANTERIOR = "#DC2626"
FORMAS_PUNTO = ["Círculo", "Cuadrado", "Triángulo", "Rombo", "Cruz", "Estrella"]
HERRAMIENTAS = [("Mover", "mover"), ("Editar", "editar"), ("Línea", "linea"), ("Línea libre", "linea_libre"), ("Rectángulo", "rect"),
                ("Círculo", "circulo"), ("Polígono", "area"), ("Área libre", "area_libre"), ("Punto", "punto"),
                ("Calibrar", "calibrar")]


# =========================================================================
#  Carga
# =========================================================================
def paginas_pdf(ruta):
    import pymupdf
    with pymupdf.open(ruta) as d:
        return d.page_count


def _matriz_para(page, dpi):
    import pymupdf
    z = dpi / 72.0
    w, h = page.rect.width * z, page.rect.height * z
    if max(w, h) > LADO_MAX:
        z *= LADO_MAX / max(w, h)
    return pymupdf.Matrix(z, z)


def _comprimir(img):
    """Imagen -> PNG con paleta (los planos son de pocos colores: queda liviano y nitido)."""
    img = img.convert("RGB")
    q = img.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    b = io.BytesIO()
    q.save(b, "PNG", optimize=True)
    return b.getvalue()


def importar_archivo(ruta, aplanar=True, dpi=200, pagina=0):
    """Devuelve (tipo, datos, ancho, alto). Con aplanar, el plano queda como imagen comprimida
    (mas liviano y rapido de mover); sin aplanar se guarda la pagina PDF original."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".pdf":
        import pymupdf
        with pymupdf.open(ruta) as d:
            if d.page_count == 0:
                raise core.ErrorCtrlP("El PDF no tiene páginas.")
            page = d[pagina]
            m = _matriz_para(page, dpi)
            if aplanar:
                img = render.renderizar(ruta, pagina, m.a, es_ruta=True)
                return "png", _comprimir(img), img.width, img.height
            nuevo = pymupdf.open()
            nuevo.insert_pdf(d, from_page=pagina, to_page=pagina)
            datos = nuevo.tobytes(garbage=4, deflate=True)
            nuevo.close()
            w = int(round(page.rect.width * m.a))
            h = int(round(page.rect.height * m.d))
            return f"pdf:{dpi}", datos, w, h
    try:
        img = Image.open(ruta)
        img.load()
    except Exception as e:
        raise core.ErrorCtrlP(f"No se pudo abrir la imagen:\n{e}")
    if max(img.size) > LADO_MAX:
        f = LADO_MAX / max(img.size)
        img = img.resize((int(img.width * f), int(img.height * f)), Image.LANCZOS)
    if aplanar:
        return "png", _comprimir(img), img.width, img.height
    b = io.BytesIO()
    img.convert("RGB").save(b, "PNG", optimize=True)
    return "png", b.getvalue(), img.width, img.height


def imagen_de(p, pid):
    pl = p.plano(pid, con_datos=True)
    if pl["tipo"].startswith("pdf"):
        import pymupdf
        datos = bytes(pl["datos"])
        with pymupdf.open(stream=datos, filetype="pdf") as d:
            z = pl["ancho"] / d[0].rect.width
        img = render.renderizar(datos, 0, z)
        if img.size != (pl["ancho"], pl["alto"]):
            img = img.resize((pl["ancho"], pl["alto"]))
        return img
    return Image.open(io.BytesIO(bytes(pl["datos"]))).convert("RGB")


# =========================================================================
#  Geometria
# =========================================================================
def largo_px(pts):
    return sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))


def area_px(pts):
    if len(pts) < 3:
        return 0.0
    s = 0.0
    for k in range(len(pts)):
        x1, y1 = pts[k]
        x2, y2 = pts[(k + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def area_neta_px(pts, huecos=()):
    """Area del contorno menos los vacios."""
    return max(area_px(pts) - sum(area_px(h) for h in (huecos or ())), 0.0)


def medida(tipo, pts, escala, huecos=()):
    """Medida real (m, m2 o unidades). None si el plano no esta calibrado. Las areas restan sus vacios."""
    if tipo == "punto":
        return 1.0
    if not escala:
        return None
    if tipo == "linea":
        return largo_px(pts) * escala
    return area_neta_px(pts, huecos) * escala * escala


def _dist_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.dist(p, a)
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def simplificar(pts, tol):
    """Reduce los puntos de un trazo libre (Douglas-Peucker)."""
    if len(pts) < 3:
        return list(pts)
    a, b = pts[0], pts[-1]
    dmax, idx = 0.0, 0
    for k in range(1, len(pts) - 1):
        d = _dist_seg(pts[k], a, b)
        if d > dmax:
            dmax, idx = d, k
    if dmax > tol:
        return simplificar(pts[:idx + 1], tol)[:-1] + simplificar(pts[idx:], tol)
    return [a, b]


def rectangulo(p0, p1):
    (x0, y0), (x1, y1) = p0, p1
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def elipse(p0, p1, n=72):
    (x0, y0), (x1, y1) = p0, p1
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0) / 2, abs(y1 - y0) / 2
    return [(round(cx + rx * math.cos(2 * math.pi * k / n), 2), round(cy + ry * math.sin(2 * math.pi * k / n), 2))
            for k in range(n)]


def ancla(m):
    pts = m["geom"]
    if not pts:
        return (0, 0)
    if m["tipo"] == "area":
        return (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))
    if m["tipo"] == "linea" and len(pts) >= 2:
        total = largo_px(pts) / 2
        acc = 0.0
        for k in range(len(pts) - 1):
            d = math.dist(pts[k], pts[k + 1])
            if acc + d >= total and d > 0:
                t = (total - acc) / d
                return (pts[k][0] + (pts[k + 1][0] - pts[k][0]) * t, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * t)
            acc += d
    return tuple(pts[0])


def dentro(p, pts):
    x, y = p
    res = False
    n = len(pts)
    for k in range(n):
        x1, y1 = pts[k]
        x2, y2 = pts[(k + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1:
            res = not res
    return res


def coinciden(a, b, tol):
    """Dos marcas se superponen (misma pared o zona)."""
    pa, pb = a["geom"], b["geom"]
    if not pa or not pb:
        return False
    if a["tipo"] == "punto" or b["tipo"] == "punto":
        return math.dist(pa[0], pb[0]) <= tol

    def cerca(p, pts, cerrado):
        segs = list(zip(pts, pts[1:] + ([pts[0]] if cerrado else [])))
        if not segs:
            return math.dist(p, pts[0]) <= tol
        return min(_dist_seg(p, s0, s1) for s0, s1 in segs) <= tol

    muestras = []
    for k in range(len(pa) - 1 if a["tipo"] == "linea" else len(pa)):
        p0, p1 = pa[k], pa[(k + 1) % len(pa)]
        for t in (0.25, 0.5, 0.75):
            muestras.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t))
    if not muestras:
        muestras = pa
    if len(muestras) > 60:
        muestras = muestras[::len(muestras) // 60]
    n = sum(1 for m in muestras if cerca(m, pb, b["tipo"] == "area"))
    return n >= max(1, 0.6 * len(muestras))


def texto_nota(p, m, cache_items, cache_hitos, ubicacion=None):
    it = cache_items.get(m["item"])
    partes = [ubicacion] if ubicacion else []
    if m["hito"]:
        partes.append(cache_hitos.get(m["hito"], "hito"))
    elif it:
        partes.append(it["codigo"])
    if m.get("equipo"):
        partes.append(p.nombre_equipo(m["equipo"]))
    if m["tramo"]:
        partes.append(p.nombre_tramo(m["tramo"]))
    if m["altura"]:
        partes.append(m["altura"])
    if it:
        partes.append(f"{fmt(m['cantidad'])} {it['unidad']}")
    partes.append(core.fecha_txt(m["fecha"])[:5])
    return " · ".join(partes)


# =========================================================================
#  Dibujo de marcas (sirve para pantalla y para exportar)
# =========================================================================
def _rgba(h, alpha_pct=100):
    h = (h or "#000000").lstrip("#")
    return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4)) + (int(max(0, min(100, alpha_pct)) * 2.55),)


def _forma_punto(d, x, y, forma, r, relleno, borde, ancho_borde):
    w = max(0, int(round(ancho_borde)))
    ol = borde if w else None
    if forma == "Cuadrado":
        d.rectangle([x - r, y - r, x + r, y + r], fill=relleno, outline=ol, width=w)
    elif forma == "Triángulo":
        d.polygon([(x, y - r), (x + r * 0.95, y + r * 0.8), (x - r * 0.95, y + r * 0.8)], fill=relleno, outline=ol, width=w)
    elif forma == "Rombo":
        d.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill=relleno, outline=ol, width=w)
    elif forma == "Cruz":
        g = max(2, int(r * 0.45))
        d.line([(x - r, y - r), (x + r, y + r)], fill=relleno, width=g)
        d.line([(x - r, y + r), (x + r, y - r)], fill=relleno, width=g)
    elif forma == "Estrella":
        pts = []
        for k in range(10):
            rr = r if k % 2 == 0 else r * 0.45
            a = -math.pi / 2 + k * math.pi / 5
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        d.polygon(pts, fill=relleno, outline=ol, width=w)
    else:
        d.ellipse([x - r, y - r, x + r, y + r], fill=relleno, outline=ol, width=w)


def dibujar_marcas(capa, marcas, a_pantalla, escala_z, estilos, seleccion=None):
    """Dibuja las marcas sobre una capa RGBA. a_pantalla(x, y) -> coordenadas en la capa;
    escala_z = pixeles de capa por pixel de plano (los grosores de linea estan en px de plano)."""
    d = ImageDraw.Draw(capa)
    for m in marcas:
        colr = m.get("color")
        if not colr:
            continue
        est = estilos.get(m["item"]) or core.Proyecto.ESTILO_BASE
        pts = [a_pantalla(x, y) for x, y in m["geom"]]
        sel = seleccion == m["id"]
        if m["tipo"] == "linea" and len(pts) >= 2:
            e = est["linea"]
            g = max(1, int(round(float(e.get("grosor", 6)) * escala_z)))
            if sel:
                d.line(pts, fill=(255, 255, 255, 230), width=g + 8, joint="curve")
            relleno = _rgba(colr, e.get("alpha", 85))
            d.line(pts, fill=relleno, width=g, joint="curve")
            if g >= 6:
                r = g / 2
                for x, y in (pts[0], pts[-1]):
                    d.ellipse([x - r, y - r, x + r, y + r], fill=relleno)
        elif m["tipo"] == "area" and len(pts) >= 3:
            e = est["area"]
            huecos = [[a_pantalla(x, y) for x, y in h] for h in (m.get("huecos") or []) if len(h) >= 3]
            if huecos:
                # relleno recortado: mascara con el contorno y los vacios en cero
                xs = [x for x, _ in pts]
                ys = [y for _, y in pts]
                bx0, by0 = max(0, int(min(xs)) - 2), max(0, int(min(ys)) - 2)
                bx1, by1 = min(capa.width, int(max(xs)) + 3), min(capa.height, int(max(ys)) + 3)
                if bx1 > bx0 and by1 > by0:
                    mask = Image.new("L", (bx1 - bx0, by1 - by0), 0)
                    dm = ImageDraw.Draw(mask)
                    dm.polygon([(x - bx0, y - by0) for x, y in pts], fill=255)
                    for h in huecos:
                        dm.polygon([(x - bx0, y - by0) for x, y in h], fill=0)
                    color = Image.new("RGBA", mask.size, _rgba(colr, e.get("alpha", 35)))
                    region = capa.crop((bx0, by0, bx1, by1))
                    capa.paste(Image.alpha_composite(region, Image.composite(color, Image.new("RGBA", mask.size,
                                                                                             (0, 0, 0, 0)), mask)),
                               (bx0, by0))
                    d = ImageDraw.Draw(capa)
            else:
                d.polygon(pts, fill=_rgba(colr, e.get("alpha", 35)))
            b = max(0, int(round(float(e.get("borde", 3)))))
            if b or sel:
                for anillo in [pts] + huecos:
                    d.line(anillo + [anillo[0]], fill=(255, 255, 255, 230) if sel else
                           _rgba(colr, e.get("alpha_borde", 90)), width=b + (4 if sel else 0), joint="curve")
        elif pts:
            e = est["punto"]
            r = max(2.0, float(e.get("tamano", 16)) / 2) + (4 if sel else 0)
            _forma_punto(d, pts[0][0], pts[0][1], e.get("forma", "Círculo"), r, _rgba(colr, e.get("alpha", 90)),
                         (255, 255, 255, 255), e.get("borde", 2))


# =========================================================================
#  Visor
# =========================================================================
class Visor(tk.Canvas):

    def __init__(self, master, al_terminar, al_seleccionar, al_estado, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=col("suave"), cursor="fleur", **kw)
        self.al_terminar, self.al_seleccionar, self.al_estado = al_terminar, al_seleccionar, al_estado
        self.piramide = []
        self.z, self.ox, self.oy = 1.0, 0.0, 0.0
        self.herr = "mover"
        self.pts = []
        self.marcas = []
        self.tramos = []
        self.estilos = {}
        self.notas = True
        self.iman = True           # puntos magneticos: esquinas y lineas del dibujo del plano
        self._gris = {}
        self.snap_tipo = None
        self.z_fit = 1.0
        self.escala = None
        self.unidad = "m"
        self.sel = None
        self.snap = None
        self.estilo_temp = None
        self._foto = None
        self._arr = None
        self._job = None
        self._arrastrando = False
        self._cursor_img = None
        self._clic_mover = None
        self._edit = None
        self.vacios = None        # {"ext": pts, "huecos": [...], "fin": fn(huecos o None), "herr_ant": ...}
        self.al_editar = None      # (mid, geom nueva) al soltar una marca movida o reformada
        self.al_borrar = None      # tecla Supr con una marca elegida
        self.al_doble = None       # doble clic sobre una marca con Editar: datos de la marca
        self.bind("<Configure>", lambda _: self.programar())
        self.bind("<ButtonPress-1>", self._p1)
        self.bind("<B1-Motion>", self._m1)
        self.bind("<ButtonRelease-1>", self._r1)
        self.bind("<Double-Button-1>", self._doble)
        for b in ("<ButtonPress-2>", "<ButtonPress-3>"):
            self.bind(b, self._inicio_arrastre)
        for b in ("<B2-Motion>", "<B3-Motion>"):
            self.bind(b, self._arrastre)
        self.bind("<Motion>", self._mov)
        self.bind("<MouseWheel>", self._rueda)
        self.bind("<Button-4>", lambda e: self._zoom(1.25, e.x, e.y))
        self.bind("<Button-5>", lambda e: self._zoom(0.8, e.x, e.y))
        self.bind("<Delete>", lambda _: self.al_borrar and self.sel and self.al_borrar())
        self.bind("<Escape>", lambda _: self.cancelar())
        self.bind("<Return>", lambda _: self.terminar())
        self.bind("<BackSpace>", lambda _: self.deshacer_punto())
        self.bind("<Enter>", lambda _: self.focus_set())

    # ---- imagen
    def cargar(self, img, escala, unidad="m"):
        self._gris = {}
        self.piramide = [img]
        while max(self.piramide[-1].size) > 1200:
            self.piramide.append(reducir(self.piramide[-1]))
        self.escala, self.unidad = escala, unidad or "m"
        self.pts = []
        self.sel = None
        self.after(30, self.ajustar)

    def limpiar(self):
        self.piramide = []
        self.marcas = []
        self.tramos = []
        self.delete("all")

    @property
    def tam(self):
        return self.piramide[0].size if self.piramide else (1, 1)

    def ajustar(self, intentos=20):
        if not self.piramide:
            return
        if (self.winfo_width() < 60 or self.winfo_height() < 60) and intentos > 0:
            self.after(100, lambda: self.ajustar(intentos - 1))
            return
        cw, ch = max(self.winfo_width(), 50), max(self.winfo_height(), 50)
        w, h = self.tam
        self.z = min(cw / w, ch / h) * 0.96
        self.z_fit = self.z
        self.ox = (w - cw / self.z) / 2
        self.oy = (h - ch / self.z) / 2
        self.dibujar()

    def a_pantalla(self, x, y):
        return ((x - self.ox) * self.z, (y - self.oy) * self.z)

    def a_imagen(self, sx, sy):
        return (self.ox + sx / self.z, self.oy + sy / self.z)

    def _zoom(self, f, sx, sy):
        if not self.piramide:
            return
        nz = max(0.01, min(self.z * f, ZOOM_MAX))
        x, y = self.a_imagen(sx, sy)
        self.z = nz
        self.ox = x - sx / nz
        self.oy = y - sy / nz
        self.programar(rapido=True)

    def zoom_centro(self, f):
        self._zoom(f, self.winfo_width() / 2, self.winfo_height() / 2)

    def _rueda(self, e):
        self._zoom(1.2 if e.delta > 0 else 1 / 1.2, e.x, e.y)

    def programar(self, rapido=False):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(10 if rapido else 40, self.dibujar)

    def _componer(self):
        """Fondo del plano + marcas con transparencia, en una sola imagen del tamano de la vista."""
        cw, ch = max(1, self.winfo_width()), max(1, self.winfo_height())
        fondo = Image.new("RGBA", (cw, ch), _rgba(col("suave")))
        if self.piramide:
            L = 0
            while L + 1 < len(self.piramide) and self.z * (2 ** (L + 1)) <= 1.0:
                L += 1
            f = 2 ** L
            img = self.piramide[L]
            x0, y0 = self.ox / f, self.oy / f
            x1, y1 = x0 + cw / (self.z * f), y0 + ch / (self.z * f)
            bx0, by0 = max(0.0, x0), max(0.0, y0)
            bx1, by1 = min(float(img.width), x1), min(float(img.height), y1)
            if bx1 > bx0 and by1 > by0:
                k = self.z * f                               # px de pantalla por px de este nivel
                sx, sy = round((bx0 - x0) * k), round((by0 - y0) * k)
                sw, sh = max(1, round((bx1 - bx0) * k)), max(1, round((by1 - by0) * k))
                metodo = Image.NEAREST if k > 2 else Image.BILINEAR
                n = min(NUCLEOS, 8) if sw * sh > 250_000 else 1
                cortes = [round(sh * i / n) for i in range(n + 1)]

                def franja(i):
                    a, b = cortes[i], cortes[i + 1]
                    caja = (bx0, by0 + a / k, bx1, min(by1, by0 + b / k))
                    return img.resize((sw, max(1, b - a)), metodo, box=caja)
                for i, parte in enumerate(en_paralelo(franja, range(n))):
                    fondo.paste(parte.convert("RGBA") if parte.mode != "RGBA" else parte, (sx, sy + cortes[i]))
        vis = [m for m in self.marcas if m.get("color")]
        if vis:
            capa = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            dibujar_marcas(capa, vis, self.a_pantalla, self.z, self.estilos, self.sel)
            fondo = Image.alpha_composite(fondo, capa)
        return fondo

    def dibujar(self):
        self._job = None
        self.configure(bg=col("suave"))
        self.delete("all")
        self._foto = ui.foto_tk(self._componer().convert("RGB"))
        self.create_image(0, 0, image=self._foto, anchor="nw", tags=("fondo",))
        self._dibujar_tramos()
        self._dibujar_notas()
        self._dibujar_temporal()
        self._dibujar_agarres()

    # ---- vacios de un area
    def iniciar_vacios(self, ext, huecos, fin):
        """Dibujar vacios dentro del area ext. fin(huecos) al terminar (Enter sin puntos o «Listo»); fin(None) si cancela."""
        self.vacios = {"ext": [tuple(q) for q in ext], "huecos": [list(map(tuple, h)) for h in huecos or []],
                       "fin": fin, "herr_ant": self.herr}
        self.herr = "vacio"
        self.pts = []
        self.configure(cursor="crosshair")
        self._dibujar_temporal()
        self._informar()

    def _cerrar_vacio(self):
        pts = self.pts
        self.pts = []
        v = self.vacios
        if not all(dentro(q, v["ext"]) for q in pts):
            self.al_estado("El vacío tiene que quedar dentro del área. Dibujalo de nuevo.")
            self._dibujar_temporal()
            return
        v["huecos"].append([(round(x, 2), round(y, 2)) for x, y in pts])
        self._dibujar_temporal()
        self._informar()

    def deshacer_vacio(self):
        if self.vacios and self.vacios["huecos"]:
            self.vacios["huecos"].pop()
            self._dibujar_temporal()
            self._informar()

    def terminar_vacios(self, ok=True):
        v, self.vacios = self.vacios, None
        if not v:
            return
        self.pts = []
        self.usar(v["herr_ant"] if v["herr_ant"] != "vacio" else "mover")
        v["fin"]([[list(q) for q in h] for h in v["huecos"]] if ok else None)

    # ---- edicion de trazos
    def _marca_sel(self):
        return next((m for m in self.marcas if m["id"] == self.sel and m.get("color")), None)

    def _agarres(self, m):
        """Vertices que se pueden arrastrar (los circulos y trazos libres muy densos solo se mueven enteros)."""
        if not m or m["tipo"] == "punto" or len(m["geom"]) > 60:
            return []
        return list(m["geom"])

    def _dibujar_agarres(self):
        self.delete("agarre")
        if self.herr != "editar":
            return
        m = self._marca_sel()
        if not m:
            return
        for x, y in self._agarres(m):
            sx, sy = self.a_pantalla(x, y)
            self.create_rectangle(sx - 5, sy - 5, sx + 5, sy + 5, fill="#FFFFFF", outline="#0EA5E9", width=2,
                                  tags=("agarre",))

    def _toca_marca(self, m, sx, sy):
        p = self.a_imagen(sx, sy)
        est = self.estilos.get(m["item"]) or core.Proyecto.ESTILO_BASE
        pts = m["geom"]
        if m["tipo"] == "linea" and len(pts) >= 2:
            tol = max(float(est["linea"].get("grosor", 6)) / 2, 8 / self.z)
            return min(_dist_seg(p, a, b) for a, b in zip(pts, pts[1:])) <= tol
        if m["tipo"] == "area" and len(pts) >= 3:
            return (dentro(p, pts) and not any(dentro(p, h) for h in m.get("huecos") or [])) or min(_dist_seg(p, a, b) for a, b in zip(pts, pts[1:] + pts[:1])) <= 8 / self.z
        if pts:
            return math.dist(p, pts[0]) <= max(float(est["punto"].get("tamano", 16)) / 2, 8) / self.z
        return False

    def _p1_editar(self, e):
        m = self._marca_sel()
        if m:
            for k, (x, y) in enumerate(self._agarres(m)):
                sx, sy = self.a_pantalla(x, y)
                if abs(sx - e.x) <= 7 and abs(sy - e.y) <= 7:
                    self._edit = self._nuevo_edit(m, k, e)
                    return
            if self._toca_marca(m, e.x, e.y):
                self._edit = self._nuevo_edit(m, None, e)
                return
        self._seleccionar(e.x, e.y)
        m = self._marca_sel()
        if m:
            self._edit = self._nuevo_edit(m, None, e)
        else:
            self._inicio_arrastre(e)

    def _nuevo_edit(self, m, k, e):
        return {"m": m, "k": k, "orig": [tuple(q) for q in m["geom"]], "ini": self.a_imagen(e.x, e.y),
                "orig_h": [[tuple(q) for q in h] for h in (m.get("huecos") or [])]}

    def _m1_editar(self, e):
        ed = self._edit
        if not ed:
            self._arrastre(e)
            return
        x, y = self.a_imagen(e.x, e.y)
        if ed["k"] is not None:
            p = self._imantar_editar(e.x, e.y, ed["m"]) or (x, y)
            g = list(ed["orig"])
            g[ed["k"]] = (round(p[0], 2), round(p[1], 2))
        else:
            dx, dy = x - ed["ini"][0], y - ed["ini"][1]
            g = [(round(a + dx, 2), round(b + dy, 2)) for a, b in ed["orig"]]
            if ed["orig_h"]:
                ed["m"]["huecos"] = [[(round(a + dx, 2), round(b + dy, 2)) for a, b in h] for h in ed["orig_h"]]
                ed["huecos_movidos"] = True
        ed["m"]["geom"] = g
        ed["movido"] = True
        self.programar(rapido=True)

    def _imantar_editar(self, sx, sy, propia):
        mejor, dmin = None, 11
        for m in self.marcas:
            if m is propia or not m.get("color") or len(m["geom"]) > 100:
                continue
            for x, y in m["geom"]:
                px, py = self.a_pantalla(x, y)
                d = math.hypot(px - sx, py - sy)
                if d < dmin:
                    mejor, dmin = (x, y), d
        return mejor

    def _r1_editar(self, e):
        ed, self._edit, self._arr = self._edit, None, None
        if not ed or not ed.get("movido"):
            return
        if self.al_editar:
            h = [[list(q) for q in hh] for hh in ed["m"]["huecos"]] if ed.get("huecos_movidos") else None
            ok = self.al_editar(ed["m"]["id"], [list(q) for q in ed["m"]["geom"]], h)
            if ok is False:
                ed["m"]["geom"] = ed["orig"]
                ed["m"]["huecos"] = ed["orig_h"]
                self.dibujar()

    # ---- marcas
    def poner_marcas(self, marcas, estilos, tramos=()):
        self.marcas = marcas
        self.estilos = estilos
        self.tramos = list(tramos)
        self.dibujar()

    def _dibujar_tramos(self):
        for t in self.tramos:
            pts = t.get("geom_pts") or []
            if len(pts) < 2:
                continue
            sp = [c for x, y in pts for c in self.a_pantalla(x, y)]
            self.create_line(*sp, fill="#8A96A6", width=2, dash=(6, 4), tags=("tramo",))
            ax, ay = self.a_pantalla(*pts[0])
            self.create_text(ax + 6, ay - 8, text=t["nombre"], anchor="w", fill="#5F6B7A", font=TF(8, "bold"))

    def _dibujar_notas(self):
        if not self.notas:
            return
        grupos = []
        for m in self.marcas:
            if not m.get("color") or not m.get("nota_txt"):
                continue
            ax, ay = self.a_pantalla(*ancla(m))
            for g in grupos:
                if g["item"] == m["item"] and math.dist((g["x"], g["y"]), (ax, ay)) < 18:
                    g["notas"].append(m)
                    break
            else:
                grupos.append({"x": ax, "y": ay, "item": m["item"], "notas": [m]})
        cw, ch = self.winfo_width(), self.winfo_height()
        # la nota es pequena con el plano completo y crece al acercar (tope 15 px)
        r = max(self.z / (self.z_fit or self.z), 1e-6)
        px = int(max(7, min(15, round(7 * r ** 0.5))))
        paso = px + 6
        borde = 1 if px < 10 else 2
        fuente = (ui.FAM, -px, "bold")
        for g in grupos:
            if not (-400 < g["x"] < cw + 50 and -50 < g["y"] < ch + 400):
                continue
            y = g["y"] - paso * 0.7 - paso * (len(g["notas"]) - 1)
            for m in g["notas"]:
                t = self.create_text(g["x"] + 4 + px * 0.4, y, text=m["nota_txt"], anchor="w", fill="#1E2730",
                                     font=fuente, tags=("nota", f"m:{m['id']}"))
                x0, y0, x1, y1 = self.bbox(t)
                r_ = self.create_rectangle(x0 - 3, y0 - 1, x1 + 3, y1 + 1, fill="#FFFFFF", outline=m["color"],
                                           width=borde, tags=("nota", f"m:{m['id']}"))
                self.tag_lower(r_, t)
                y += paso

    def _tipo(self):
        return {"linea": "linea", "linea_libre": "linea", "rect": "area", "circulo": "area", "area": "area", "vacio": "area",
                "area_libre": "area", "punto": "punto", "calibrar": "linea"}.get(self.herr, "")

    def _puntos_vista(self):
        """Puntos de la figura en construccion (incluye el cursor)."""
        if not self.pts:
            return []
        if self.herr == "rect" and self._cursor_img:
            return rectangulo(self.pts[0], self._cursor_img)
        if self.herr == "circulo" and self._cursor_img:
            return elipse(self.pts[0], self._cursor_img, 48)
        if self.herr in ("linea", "area", "area_libre", "vacio", "calibrar") and self._cursor_img:
            return list(self.pts) + [self._cursor_img]
        return list(self.pts)

    def _dibujar_temporal(self):
        self.delete("tmp")
        if self.vacios:
            v = self.vacios
            sp = [c for x, y in v["ext"] for c in self.a_pantalla(x, y)]
            self.create_polygon(*sp, fill="#0EA5E9", stipple="gray25", outline="#0EA5E9", width=2, tags=("tmp",))
            for h in v["huecos"]:
                hp = [c for x, y in h for c in self.a_pantalla(x, y)]
                self.create_polygon(*hp, fill="#FFFFFF", outline="#E11D48", width=2, dash=(6, 3), tags=("tmp",))
        if self.snap:
            x, y = self.a_pantalla(*self.snap)
            if self.snap_tipo == "linea":
                self.create_rectangle(x - 4, y - 4, x + 4, y + 4, outline="#F59E0B", width=2, tags=("tmp",))
            elif self.snap_tipo == "esquina":
                self.create_oval(x - 7, y - 7, x + 7, y + 7, outline="#F59E0B", width=2, tags=("tmp",))
                self.create_line(x - 10, y, x + 10, y, fill="#F59E0B", tags=("tmp",))
                self.create_line(x, y - 10, x, y + 10, fill="#F59E0B", tags=("tmp",))
            else:
                self.create_oval(x - 6, y - 6, x + 6, y + 6, outline="#0EA5E9", width=2, tags=("tmp",))
        pts = self._puntos_vista()
        if not pts:
            return
        sp = [c for x, y in pts for c in self.a_pantalla(x, y)]
        colr = "#0EA5E9" if self.herr != "calibrar" else "#F59E0B"
        tipo = self._tipo()
        if tipo == "area" and len(pts) >= 3:
            self.create_polygon(*sp, fill=colr, stipple="gray25", outline=colr, width=2, tags=("tmp",))
        elif len(sp) >= 4:
            g = 3
            if self.herr != "calibrar" and self.estilo_temp:
                g = max(2, min(600, int(float(self.estilo_temp["linea"].get("grosor", 6)) * self.z)))
            self.create_line(*sp, fill=colr, width=g, dash=(8, 4) if self.herr == "calibrar" else None, tags=("tmp",),
                             capstyle="round", joinstyle="round")
        if self.herr in ("linea", "area", "area_libre", "vacio", "calibrar") and len(self.pts) <= 200:
            for k in range(0, len(self.pts) * 2, 2):
                self.create_oval(sp[k] - 4, sp[k + 1] - 4, sp[k] + 4, sp[k + 1] + 4, fill="#FFFFFF", outline=colr,
                                 width=2, tags=("tmp",))

    # ---- herramientas
    def usar(self, herr):
        self.herr = herr
        self.pts = []
        self._arrastrando = False
        self.configure(cursor="fleur" if herr == "mover" else ("hand2" if herr == "editar" else
                                                               ("pencil" if "libre" in herr else "crosshair")))
        self._dibujar_temporal()
        self._dibujar_agarres()
        self._informar()

    def cancelar(self):
        if self.vacios and not self.pts:
            return self.terminar_vacios(False)
        self.pts = []
        self._arrastrando = False
        self._dibujar_temporal()
        self._informar()

    def deshacer_punto(self):
        if self.herr == "vacio" and not self.pts:
            return self.deshacer_vacio()
        if self.pts and self.herr in ("linea", "area", "area_libre", "vacio"):
            self.pts.pop()
            self._dibujar_temporal()
            self._informar()

    def _imantar(self, sx, sy):
        """Punto magnetico: vertice de otra marca o tramo, o esquina / linea del dibujo del plano."""
        self.snap_tipo = None
        if self.herr == "linea_libre" or not self.iman:
            return None
        mejor, dmin = None, 11
        for m in list(self.marcas) + [{"geom": t.get("geom_pts") or [], "color": "x"} for t in self.tramos]:
            if not m.get("color") or len(m["geom"]) > 100:
                continue
            for x, y in m["geom"]:
                px, py = self.a_pantalla(x, y)
                d = math.hypot(px - sx, py - sy)
                if d < dmin:
                    mejor, dmin = (x, y), d
        for x, y in self.pts:
            px, py = self.a_pantalla(x, y)
            d = math.hypot(px - sx, py - sy)
            if d < dmin:
                mejor, dmin = (x, y), d
        if mejor:
            self.snap_tipo = "vertice"
            return mejor
        r = self._iman_plano(sx, sy)
        if r:
            self.snap_tipo, mejor = r
        return mejor

    def _nivel_gris(self):
        """Nivel de la piramide con ~1 px por px de pantalla, en escala de grises (cacheado)."""
        L = 0
        while L + 1 < len(self.piramide) and self.z * (2 ** (L + 1)) <= 1.0:
            L += 1
        if L not in self._gris:
            g = self.piramide[L].convert("L")
            self._gris[L] = (g, g.load(), g.size)
        return L

    def _iman_plano(self, sx, sy, radio=10):
        """Busca cerca del cursor una esquina o cruce de lineas del plano (prioridad) o la linea mas cercana."""
        if not self.piramide:
            return None
        L = self._nivel_gris()
        g, px, (w, h) = self._gris[L]
        f = 2 ** L
        ix, iy = self.a_imagen(sx, sy)
        cx, cy = ix / f, iy / f
        esc = self.z * f                       # px de pantalla por px de este nivel
        r = max(2, int(radio / esc) + 1)
        x0, x1 = max(1, int(cx - r)), min(w - 2, int(cx + r))
        y0, y1 = max(1, int(cy - r)), min(h - 2, int(cy + r))
        if x1 <= x0 or y1 <= y0:
            return None
        UMBRAL = 120
        brazo = max(3, min(8, int(4 / max(esc, 0.25))))

        def oscuro(x, y):
            return 0 <= x < w and 0 <= y < h and px[x, y] < UMBRAL

        def tiene(x, y, dx, dy):
            return all(oscuro(x + dx * k, y + dy * k) for k in range(1, brazo + 1))

        def es_esquina(x, y):
            u, d, l, r_ = oscuro(x, y - 1), oscuro(x, y + 1), oscuro(x - 1, y), oscuro(x + 1, y)
            # esquina convexa (fin o quiebre de una linea, fina o gruesa)
            for (a1, a2, dx, dy) in ((u, l, 1, 1), (u, r_, -1, 1), (d, l, 1, -1), (d, r_, -1, -1)):
                if not a1 and not a2 and tiene(x, y, dx, 0) and tiene(x, y, 0, dy):
                    return True
            # esquina concava (rincon interior, o junto a un cruce en T de lineas finas)
            if u and d and l and r_:
                claros = [(dx, dy) for dx in (-1, 1) for dy in (-1, 1) if not oscuro(x + dx, y + dy)]
                if len(claros) == 1:
                    dx, dy = claros[0]
                    return tiene(x, y, dx, 0) and tiene(x, y, 0, dy)
            return False

        esquina, de = None, 1e18
        linea, dl = None, 1e18
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if px[x, y] >= UMBRAL:
                    continue
                d = (x - cx) ** 2 + (y - cy) ** 2
                if d > r * r:
                    continue
                if d < dl:
                    linea, dl = (x, y), d
                if d < de and es_esquina(x, y):
                    esquina, de = (x, y), d
        if esquina:
            return "esquina", ((esquina[0] + 0.5) * f, (esquina[1] + 0.5) * f)
        if linea:
            return "linea", ((linea[0] + 0.5) * f, (linea[1] + 0.5) * f)
        return None

    def _punto(self, e):
        p = self.snap or self.a_imagen(e.x, e.y)
        return (round(p[0], 2), round(p[1], 2))

    def _p1(self, e):
        self.focus_set()
        if not self.piramide:
            return
        if self.herr == "editar":
            return self._p1_editar(e)
        if self.herr == "mover":
            self._inicio_arrastre(e)
            self._clic_mover = (e.x, e.y)
            return
        p = self._punto(e)
        if self.herr == "punto":
            self.al_terminar("punto", [p])
            return
        if self.herr in ("linea_libre", "rect", "circulo"):
            self.pts = [p]
            self._cursor_img = p
            self._arrastrando = True
            return
        if self.herr in ("area", "area_libre", "vacio") and len(self.pts) >= 3:
            fx, fy = self.a_pantalla(*self.pts[0])
            if math.hypot(e.x - fx, e.y - fy) <= 9:      # clic en el primer punto: cierra el area
                self.terminar()
                return
        self.pts.append(p)
        if self.herr == "area_libre":
            self._libre_ini = (e.x, e.y)              # si arrastra, sigue a mano alzada
        if self.herr == "calibrar" and len(self.pts) == 2:
            pts = self.pts
            self.pts = []
            self._dibujar_temporal()
            self.al_terminar("calibrar", pts)
            return
        self._dibujar_temporal()
        self._informar()

    def _m1(self, e):
        if self.herr == "editar":
            return self._m1_editar(e)
        if self.herr == "mover":
            self._arrastre(e)
            return
        if self.herr == "area_libre" and getattr(self, "_libre_ini", None) and self.pts:
            ux, uy = self.a_pantalla(*self.pts[-1])
            if math.hypot(e.x - ux, e.y - uy) >= 3:
                q = self.a_imagen(e.x, e.y)
                self.pts.append((round(q[0], 2), round(q[1], 2)))
                self._cursor_img = q
                self._dibujar_temporal()
                self._informar()
            return
        if not self._arrastrando:
            return
        p = self._punto(e)
        if self.herr == "linea_libre":
            ux, uy = self.a_pantalla(*self.pts[-1])
            if math.hypot(e.x - ux, e.y - uy) >= 3:
                self.pts.append(p)
        self._cursor_img = p
        self._dibujar_temporal()
        self._informar()

    def _r1(self, e):
        if self.herr == "editar":
            return self._r1_editar(e)
        if self.herr == "mover":
            if self._clic_mover:
                x0, y0 = self._clic_mover
                self._clic_mover = None
                if abs(e.x - x0) < 4 and abs(e.y - y0) < 4:
                    self._seleccionar(e.x, e.y)
            return
        if self.herr == "area_libre":
            self._libre_ini = None
            return
        if not self._arrastrando:
            return
        self._arrastrando = False
        p = self._punto(e)
        p0 = self.pts[0] if self.pts else p
        if self.herr == "rect":
            pts, tipo = rectangulo(p0, p), "area"
        elif self.herr == "circulo":
            pts, tipo = elipse(p0, p), "area"
        else:
            pts = simplificar(self.pts + [p], 1.5 / self.z)
            tipo = "linea" if self.herr == "linea_libre" else "area"
        self.pts = []
        self._cursor_img = None
        self._dibujar_temporal()
        if (tipo == "linea" and largo_px(pts) * self.z > 4) or (tipo == "area" and area_px(pts) * self.z * self.z > 30):
            self.al_terminar(tipo, [(round(x, 2), round(y, 2)) for x, y in pts])

    def _doble(self, e):
        if self.herr == "editar" and self.sel and self.al_doble:
            self.after(10, self.al_doble)
            return
        if self.herr in ("linea", "area", "area_libre", "vacio"):
            if len(self.pts) >= 2 and math.dist(self.pts[-1], self.pts[-2]) < 1e-6:
                self.pts.pop()
            self.terminar()

    def terminar(self):
        if self.herr == "vacio":
            if len(self.pts) >= 3:
                self._cerrar_vacio()
            elif not self.pts:
                self.terminar_vacios(True)
            return
        if self.herr == "linea" and len(self.pts) >= 2:
            pts, self.pts = self.pts, []
            self._dibujar_temporal()
            self.al_terminar("linea", pts)
        elif self.herr in ("area", "area_libre") and len(self.pts) >= 3:
            pts, self.pts = self.pts, []
            self._dibujar_temporal()
            self.al_terminar("area", pts)

    def _seleccionar(self, sx, sy):
        for i in reversed(self.find_overlapping(sx - 3, sy - 3, sx + 3, sy + 3)):
            for t in self.gettags(i):
                if t.startswith("m:"):
                    return self._marcar_sel(t[2:])
        p = self.a_imagen(sx, sy)
        mejor = None
        for m in reversed(self.marcas):
            if not m.get("color"):
                continue
            est = self.estilos.get(m["item"]) or core.Proyecto.ESTILO_BASE
            pts = m["geom"]
            if m["tipo"] == "linea" and len(pts) >= 2:
                tol = max(float(est["linea"].get("grosor", 6)) / 2, 6 / self.z)
                if min(_dist_seg(p, a, b) for a, b in zip(pts, pts[1:])) <= tol:
                    mejor = m
                    break
            elif m["tipo"] == "area" and len(pts) >= 3:
                if dentro(p, pts) and not any(dentro(p, h) for h in m.get("huecos") or []):
                    mejor = m
                    break
            elif pts:
                r = max(float(est["punto"].get("tamano", 16)) / 2, 6) / self.z
                if math.dist(p, pts[0]) <= r:
                    mejor = m
                    break
        self._marcar_sel(mejor["id"] if mejor else None)

    def _marcar_sel(self, mid):
        if mid != self.sel:
            self.sel = mid
            self.dibujar()
        self.al_seleccionar(mid)

    def _inicio_arrastre(self, e):
        self._arr = (e.x, e.y, self.ox, self.oy)

    def _arrastre(self, e):
        if not self._arr:
            return
        x0, y0, ox, oy = self._arr
        self.ox = ox - (e.x - x0) / self.z
        self.oy = oy - (e.y - y0) / self.z
        self.programar(rapido=True)

    def _mov(self, e):
        if not self.piramide or self.herr in ("mover", "editar"):
            if self.snap:
                self.snap = None
                self._dibujar_temporal()
            return
        self.snap = self._imantar(e.x, e.y)
        if not self._arrastrando:
            self._cursor_img = self.snap or self.a_imagen(e.x, e.y)
        self._dibujar_temporal()
        self._informar()

    def _informar(self):
        h = self.herr
        if h == "mover":
            self.al_estado("Arrastrá para mover · rueda para acercar · clic en una marca para verla.")
            return
        if h == "editar":
            self.al_estado("Editar: clic en una marca y arrastrala para moverla · arrastrá los cuadritos para cambiar "
                           "la forma · doble clic para sus datos · Supr para borrarla.")
            return
        if h == "punto":
            self.al_estado("Clic para marcar una pieza (cuenta 1).")
            return
        if h == "vacio" and self.vacios:
            v = self.vacios
            neto = area_neta_px(v["ext"], v["huecos"])
            txt = f"{neto * self.escala ** 2:,.2f} {self.unidad}²" if self.escala else f"{neto:,.0f} px²"
            self.al_estado(f"Vacíos: {len(v['huecos'])} · área neta {txt} · dibujá cada vacío punto por punto dentro "
                           "del área (clic en el primer punto lo cierra) · Enter o «Listo» para terminar · Retroceso "
                           "quita el último vacío · Esc cancela.")
            return
        pts = self._puntos_vista()
        if h == "calibrar":
            if len(pts) == 2:
                self.al_estado(f"Distancia en el plano: {largo_px(pts):,.1f} px · clic en el segundo punto.")
            else:
                self.al_estado("Calibrar: clic en dos puntos de una medida conocida (por ejemplo una cota).")
            return
        if self._tipo() == "linea":
            v = largo_px(pts)
            txt = f"{v * self.escala:,.2f} {self.unidad}" if self.escala else f"{v:,.0f} px (plano sin calibrar)"
            extra = ("doble clic o Enter para terminar · Retroceso borra el último punto · Esc cancela"
                     if h == "linea" else "dibujá con el botón apretado")
        else:
            v = area_px(pts)
            txt = f"{v * self.escala ** 2:,.2f} {self.unidad}²" if self.escala else f"{v:,.0f} px² (sin calibrar)"
            extra = ("clic punto por punto (o arrastrá para un tramo a mano alzada) · clic en el primer punto, doble clic "
                     "o Enter para cerrar · Retroceso borra el último" if h == "area_libre" else
                     "doble clic o Enter para cerrar · Esc cancela" if h == "area" else "dibujá con el botón apretado")
            if self.iman and self.snap_tipo:
                extra = {"esquina": "imán: esquina", "linea": "imán: línea", "vertice": "imán: marca"}[self.snap_tipo] + \
                        " · " + extra
        self.al_estado(f"{txt} · {extra}.")


# =========================================================================
#  Dialogo de marca
# =========================================================================
class DialogoMarca(ctk.CTkToplevel):
    """Datos de una marca. Resultado en self.res (dict) o None.
    act: actividad elegida {item, nivel, equipo, tramo, hito, ref, pendiente, cantidad_reg, fecha}."""

    def __init__(self, app, p, plano, tipo, pts, act, marca=None, coincidentes=(), huecos=None, previo=None):
        super().__init__(app, fg_color=C["tarjeta"])
        self.app, self.p, self.plano, self.tipo, self.pts = app, p, plano, tipo, pts
        self.huecos = huecos or []
        self.act, self.marca = act, marca
        self.res = None
        self.item = p.item(act["item"])
        self.title("Marca en el plano" if not marca else "Editar marca")
        self.resizable(False, False)
        self.transient(app)
        ui.icono_ventana(self)
        self.med = medida(tipo, pts, plano["escala"], self.huecos) if not marca else marca["medida"]
        it = self.item
        u = it["unidad"]
        self.ref = act.get("ref") or ""
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=24, pady=(18, 0))
        etiqueta(cuerpo, "Editar marca" if marca else "Marcar en el plano", 16, "bold").pack(anchor="w")
        ctk.CTkLabel(cuerpo, text=f"{it['codigo']} {it['descripcion'][:90]}", font=F(12, "bold"), text_color=C["acento"],
                     wraplength=470, justify="left").pack(anchor="w")
        etiqueta(cuerpo, p.etiqueta_ubicacion(act["nivel"]) + "  ·  " + plano["nombre"], 12, color="texto2").pack(anchor="w")
        if coincidentes:
            ctk.CTkLabel(cuerpo, text="Coincide con marcas anteriores en el mismo lugar:\n" +
                         "\n".join(f"• {x}" for x in coincidentes[:5]) +
                         "\nLa nota se suma a las anteriores (mismo color en el plano).",
                         font=F(11), text_color=C["acento"], justify="left", wraplength=470).pack(anchor="w", pady=(8, 0))
        self.cajas = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
        self.cajas.pack(fill="x", pady=(8, 0))
        self._cajas()
        caja = ctk.CTkFrame(cuerpo, fg_color="transparent")
        caja.pack(fill="x", pady=(12, 0))
        self.v_modo = tk.StringVar()
        self.v_factor = tk.StringVar(value=f"{(marca['factor'] if marca else 1) or 1:g}")
        self.v_cant = tk.StringVar()
        self.v_fecha = tk.StringVar(value=core.fecha_txt(marca["fecha"] if marca else act.get("fecha") or core.hoy_iso()))
        radio = dict(font=F(12), text_color=C["texto"], fg_color=C["acento"], radiobutton_width=18, radiobutton_height=18,
                     command=self._calc)
        self.v_med_txt = tk.StringVar()
        if self.ref == core.ACUM and not marca:
            etiqueta(caja, f"Acumulado al {core.fecha_txt(act['fecha'])}: {fmt(act['cantidad_reg'])} {u}  ·  falta marcar "
                           f"{fmt(act['pendiente'])} {u}", 12, "bold").grid(row=0, column=0, columnspan=4, sticky="w")
            self.rb_med = ctk.CTkRadioButton(caja, text="Usar la medida del plano", variable=self.v_modo, value="medida",
                                             **radio)
            self.rb_med.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
            ctk.CTkRadioButton(caja, text="Ingresar la cantidad que representa", variable=self.v_modo, value="manual",
                               **radio).grid(row=5, column=0, sticky="w", pady=(8, 0))
            entrada(caja, self.v_cant, 110, justify="right").grid(row=5, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
            self.v_cant.set(f"{act['pendiente']:.2f}")
            self.v_modo.set("medida" if self.med is not None else "manual")
        elif self.ref and not marca:
            etiqueta(caja, f"Registro del {core.fecha_txt(act['fecha'])}: {fmt(act['cantidad_reg'])} {u}  ·  falta ubicar "
                           f"{fmt(act['pendiente'])} {u}", 12, "bold").grid(row=0, column=0, columnspan=4, sticky="w")
            ctk.CTkRadioButton(caja, text="Solo marcar (ubica la cantidad ya registrada)", variable=self.v_modo,
                               value="ubicar", **radio).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
            etiqueta(caja, "Cantidad que representa esta marca", 11, color="texto2").grid(row=2, column=0, sticky="w",
                                                                                        padx=(28, 0))
            entrada(caja, self.v_cant, 110, justify="right").grid(row=2, column=1, sticky="w", padx=(8, 0))
            self.v_cant.set(f"{act['pendiente']:.2f}")
            self.rb_med = ctk.CTkRadioButton(caja, text="Usar la medida del plano", variable=self.v_modo, value="medida",
                                             **radio)
            self.rb_med.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
            self.v_modo.set("ubicar")
        else:
            etiqueta(caja, "Fecha", 12, "bold").grid(row=0, column=0, sticky="w")
            ef = entrada(caja, self.v_fecha, 120, justify="center")
            ef.grid(row=1, column=0, sticky="w")
            if marca and marca.get("visual"):
                ef.configure(state="disabled")
            self.rb_med = ctk.CTkRadioButton(caja, text="Usar la medida del plano", variable=self.v_modo, value="medida",
                                             **radio)
            self.rb_med.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
            ctk.CTkRadioButton(caja, text="Ingresar la cantidad", variable=self.v_modo, value="manual", **radio).grid(
                row=5, column=0, sticky="w", pady=(8, 0))
            entrada(caja, self.v_cant, 110, justify="right").grid(row=5, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
            self.v_modo.set("medida" if self.med is not None else "manual")
            if marca:
                self.v_cant.set(f"{marca['cantidad']:.2f}")
                self.v_modo.set("medida" if (marca["medida"] is not None and abs(
                    (marca["medida"] or 0) * (marca["factor"] or 1) - marca["cantidad"]) < 1e-6) else "manual")
        fm = ctk.CTkFrame(caja, fg_color="transparent")
        fm.grid(row=4, column=0, columnspan=4, sticky="w", padx=(28, 0))
        etiqueta(fm, "", 12, textvariable=self.v_med_txt).pack(side="left")
        entrada(fm, self.v_factor, 64, justify="right").pack(side="left", padx=(6, 0))
        etiqueta(fm, "factor", 11, color="texto2").pack(side="left", padx=(4, 0))
        self.v_factor.trace_add("write", lambda *_: self._calc())
        if self.med is None:
            self.rb_med.configure(state="disabled")
        etiqueta(cuerpo, "Factor: multiplica la medida (ej. altura del muro para pasar de m a m², sección para m³).", 11,
                 color="texto2").pack(anchor="w", pady=(4, 0))
        f2 = ctk.CTkFrame(cuerpo, fg_color="transparent")
        f2.pack(fill="x", pady=(10, 0))
        etiqueta(f2, "Franja / altura (opcional)", 12, "bold").grid(row=0, column=0, sticky="w")
        etiqueta(f2, "Nota (opcional)", 12, "bold").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.v_altura = tk.StringVar(value=marca["altura"] if marca else "")
        self.v_nota = tk.StringVar(value=marca["nota"] if marca else "")
        entrada(f2, self.v_altura, 170, placeholder_text="ej. 0.00 a 1.20 m").grid(row=1, column=0, sticky="w")
        entrada(f2, self.v_nota, 290).grid(row=1, column=1, sticky="w", padx=(12, 0))
        self.v_err = tk.StringVar()
        ctk.CTkLabel(cuerpo, textvariable=self.v_err, font=F(12), text_color=C["rojo"], wraplength=470,
                     justify="left").pack(anchor="w", pady=(6, 0))
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=24, pady=(6, 20))
        boton(pie, "Guardar", primario=True, ancho=130, command=self.ok).pack(side="right")
        boton(pie, "Cancelar", ancho=110, command=self.destroy).pack(side="right", padx=8)
        if tipo == "area":
            n = len(self.huecos if not marca else (marca.get("huecos") or []))
            boton(pie, f"Vacíos ({n})…" if n else "Agregar vacíos…", ancho=150, command=self._vacios).pack(side="left")
        self.bind("<Escape>", lambda _: self.destroy())
        if previo:
            for k, var in (("factor", self.v_factor), ("altura", self.v_altura), ("nota", self.v_nota)):
                if previo.get(k) not in (None, ""):
                    var.set(previo[k])
        self._calc()
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + max(0, (app.winfo_height() - self.winfo_height()) // 4)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.after(60, lambda: ui.tenir_barra_titulo(self, ui.oscuro()))
        try:
            self.grab_set()
        except Exception:
            pass
        app.wait_window(self)

    def _cajas(self):
        p, it, act, m = self.p, self.item, self.act, self.marca
        nv = act["nivel"]
        self.hitos = p.hitos_de(it["id"])
        self.equipos = p.equipos_de(it["id"], nv)
        fijo = bool(self.ref) or bool(m and m.get("visual"))
        self.v_hito = tk.StringVar()
        self.v_equipo = tk.StringVar()
        self.v_tramo = tk.StringVar(value="(sin tramo)")
        self.v_tramo_nuevo = tk.StringVar()
        ini_h = (m or {}).get("hito") or act.get("hito") or ""
        ini_e = (m or {}).get("equipo") or act.get("equipo") or ""
        ini_t = (m or {}).get("tramo") or act.get("tramo") or ""
        self._ini = (ini_h, ini_e, ini_t)
        self.tramos = []
        if fijo:
            partes = [x for x in (("Equipo " + p.nombre_equipo(ini_e)) if ini_e else "",
                                  ("Tramo " + p.nombre_tramo(ini_t)) if ini_t else "",
                                  p.nombre_hito(ini_h) if ini_h else "") if x]
            if partes:
                etiqueta(self.cajas, " · ".join(partes), 12, "bold").grid(row=0, column=0, sticky="w")
            return
        col_ = 0
        if self.hitos:
            etiqueta(self.cajas, "Hito", 12, "bold").grid(row=0, column=col_, sticky="w")
            ops = [p.etiqueta_hito(h) for h in self.hitos]
            self.v_hito.set(next((ops[k] for k, h in enumerate(self.hitos) if h["id"] == ini_h), ops[0]))
            ui.menu(self.cajas, ops, self.v_hito, 200).grid(row=1, column=col_, sticky="nw", padx=(0, 10))
            col_ += 1
        if p.detalle_de(it["id"])["equipos"]:
            etiqueta(self.cajas, "Equipo", 12, "bold").grid(row=0, column=col_, sticky="w")
            self.v_equipo.set(next((e["nombre"] for e in self.equipos if e["id"] == ini_e), "(sin equipo)"))
            ui.menu(self.cajas, ["(sin equipo)"] + [e["nombre"] for e in self.equipos], self.v_equipo, 150,
                    cmd=lambda _: self._menu_tramos()).grid(row=1, column=col_, sticky="nw", padx=(0, 10))
            col_ += 1
        self.caja_tramo = ctk.CTkFrame(self.cajas, fg_color="transparent")
        self.caja_tramo.grid(row=0, column=col_, rowspan=3, sticky="nw")
        self._menu_tramos(ini_t)

    def _equipo_sel(self):
        return next((e["id"] for e in self.equipos if e["nombre"] == self.v_equipo.get()), "")

    def _menu_tramos(self, inicial=""):
        for w in self.caja_tramo.winfo_children():
            w.destroy()
        p, it = self.p, self.item
        self.tramos = (p.tramos_de(it["id"], self.act["nivel"], self._equipo_sel())
                       if p.detalle_de(it["id"])["tramos"] else [])
        if self.tipo == "punto" and not self.tramos:
            return
        ops = ["(sin tramo)"] + [t["nombre"] for t in self.tramos] + ["+ Nuevo tramo…"]
        self.v_tramo.set(next((t["nombre"] for t in self.tramos if t["id"] == inicial), "(sin tramo)"))
        etiqueta(self.caja_tramo, "Tramo", 12, "bold").pack(anchor="w")
        ui.menu(self.caja_tramo, ops, self.v_tramo, 170, cmd=lambda _: self._tramo_nuevo()).pack(anchor="w")
        self.e_tramo = entrada(self.caja_tramo, self.v_tramo_nuevo, 170, placeholder_text="Nombre del tramo nuevo")

    def _tramo_nuevo(self):
        if self.v_tramo.get().startswith("+"):
            self.e_tramo.pack(anchor="w", pady=(4, 0))
            self.e_tramo.focus_set()
        else:
            self.e_tramo.pack_forget()

    def _vacios(self):
        """Cierra el dialogo para dibujar los vacios en el plano; luego se vuelve a abrir con el area neta."""
        self.res = {"accion": "vacios", "previo": {"factor": self.v_factor.get(), "altura": self.v_altura.get(),
                                                    "nota": self.v_nota.get()}}
        self.destroy()

    def _calc(self):
        u = self.item["unidad"]
        f = ui.leer_num(self.v_factor.get())
        f = f if isinstance(f, float) else 1.0
        if self.med is None:
            self.v_med_txt.set("Calibrá el plano para medir   ×")
        elif self.tipo == "punto":
            self.v_med_txt.set(f"1 pieza  →  {fmt(f)} {u}   ×")
        else:
            un = (self.plano.get("unidad") or "m") + ("²" if self.tipo == "area" else "")
            vac = len(self.huecos) if not self.marca else len(self.marca.get("huecos") or [])
            self.v_med_txt.set(f"Medida {fmt(self.med)} {un}" + (f" (menos {vac} vacío{'s' if vac > 1 else ''})" if vac
                                                                 else "") + f"  →  {fmt(self.med * f)} {u}   ×")

    def ok(self):
        f = ui.leer_num(self.v_factor.get())
        if f in ("error",) or f is None or f <= 0:
            self.v_err.set("El factor debe ser un número mayor que cero.")
            return
        modo = self.v_modo.get()
        if modo == "medida" and self.med is None:
            self.v_err.set("El plano no está calibrado: calibralo o ingresá la cantidad.")
            return
        cant = self.med * f if modo == "medida" else ui.leer_num(self.v_cant.get())
        if cant in ("error", None) or cant <= 0:
            self.v_err.set("Escribí una cantidad mayor que cero.")
            return
        base = {"factor": f, "medida": self.med, "altura": self.v_altura.get().strip(), "nota": self.v_nota.get().strip()}
        if self.ref == core.ACUM and not self.marca:
            pend = self.act["pendiente"]
            if cant > pend + 0.005:
                r = ui.dialogo_texto(self, "Más que lo acumulado",
                                     f"Esta marca da {fmt(cant)} {self.item['unidad']} y del acumulado al "
                                     f"{core.fecha_txt(self.act['fecha'])} faltan marcar {fmt(pend)}.\n\nLa marca no crea "
                                     "avance: si se ejecutó más, registralo en Registro de avance.",
                                     ("Cancelar", f"Marcar {fmt(pend)}"), primario=1)
                if r != 1:
                    return
                cant = pend
            h, e, t = self._ini
            self.res = dict(base, modo="acumulado", cantidad=cant, fecha=self.act["fecha"], hito=h, equipo=e, tramo=t,
                            tramo_nuevo=None)
            self.destroy()
            return
        if self.ref and not self.marca:
            fecha = self.act["fecha"]
            h, e, t = self._ini
            res_modo = "ubicar"
            if modo == "medida":
                pend = self.act["pendiente"]
                if abs(cant - pend) > 0.005:
                    r = ui.dialogo_texto(self, "La medida no coincide",
                                         f"La medida del plano da {fmt(cant)} {self.item['unidad']} y en el registro "
                                         f"faltaban ubicar {fmt(pend)}.\n\n¿Reemplazar la cantidad manual por la medida del "
                                         f"plano, o conservar la manual?",
                                         ("Cancelar", "Conservar la manual", "Reemplazar"), primario=2)
                    if r == 2:
                        res_modo = "reemplazar"
                    elif r == 1:
                        cant = pend
                    else:
                        return
                else:
                    cant = pend
            elif cant > self.act["pendiente"] + 0.005:
                self.v_err.set(f"Esta marca no puede representar más de lo que falta ubicar ({fmt(self.act['pendiente'])}).")
                return
            self.res = dict(base, modo=res_modo, cantidad=cant, fecha=fecha, hito=h, equipo=e, tramo=t, tramo_nuevo=None)
            self.destroy()
            return
        if self.marca and self.marca.get("visual"):
            h, e, t = self._ini
            self.res = dict(base, modo="ubicar", cantidad=cant, fecha=self.marca["fecha"], hito=h, equipo=e, tramo=t,
                            tramo_nuevo=None)
            self.destroy()
            return
        try:
            fecha = core.txt_a_iso(self.v_fecha.get())
        except core.ErrorCtrlP as ex:
            self.v_err.set(str(ex))
            return
        hito = ""
        if self.hitos:
            k = [self.p.etiqueta_hito(x) for x in self.hitos].index(self.v_hito.get())
            hito = self.hitos[k]["id"]
        tramo, nuevo = "", None
        tn = self.v_tramo.get()
        if tn.startswith("+"):
            nuevo = core.mayus(self.v_tramo_nuevo.get())
            if not nuevo:
                self.v_err.set("Escribí el nombre del tramo nuevo.")
                return
        elif tn != "(sin tramo)":
            tramo = next(t["id"] for t in self.tramos if t["nombre"] == tn)
        self.res = dict(base, modo="avance", cantidad=cant, fecha=fecha, hito=hito, equipo=self._equipo_sel(),
                        tramo=tramo, tramo_nuevo=nuevo)
        self.destroy()


# =========================================================================
#  Estilo por actividad
# =========================================================================
class DialogoEstilo(ctk.CTkToplevel):
    def __init__(self, app, p, iid, c_per=None, c_ant=None):
        super().__init__(app, fg_color=C["tarjeta"])
        self.p, self.iid = p, iid
        self.res = None
        self.e = p.estilo_de(iid)
        it = p.item(iid)
        self.title("Estilo de la actividad")
        self.resizable(False, False)
        self.transient(app)
        ui.icono_ventana(self)
        c = ctk.CTkFrame(self, fg_color="transparent")
        c.pack(fill="both", expand=True, padx=24, pady=(18, 0))
        etiqueta(c, "Estilo de marcado", 16, "bold").pack(anchor="w")
        etiqueta(c, f"{it['codigo']} {it['descripcion'][:70]}", 12, color="texto2").pack(anchor="w")
        self.v = {}
        # dos columnas para que entre en pantallas bajas (laptops)
        cols = ctk.CTkFrame(c, fg_color="transparent")
        cols.pack(fill="x")
        izq = ctk.CTkFrame(cols, fg_color="transparent")
        der = ctk.CTkFrame(cols, fg_color="transparent")
        izq.grid(row=0, column=0, sticky="n", padx=(0, 6))
        der.grid(row=0, column=1, sticky="n", padx=(6, 0))
        donde = {"Líneas": izq, "Áreas": izq, "Puntos": der}

        def seccion(titulo):
            t = ui.Tarjeta(donde[titulo])
            t.pack(fill="x", pady=(10, 0))
            t.ancho_ayuda = 220
            etiqueta(t, titulo, 13, "bold").grid(row=0, column=0, sticky="w", padx=18, pady=(10, 0))
            t._base = 1
            return t

        def num(t, clave, sub, texto, ayuda=None):
            var = tk.StringVar(value=f"{self.e[sub][clave]:g}")
            self.v[(sub, clave)] = var
            t.fila(texto, entrada(t, var, 90, justify="right"), ayuda)

        def alpha(t, clave, sub, texto):
            var = tk.DoubleVar(value=float(self.e[sub][clave]))
            self.v[(sub, clave)] = var
            f = ctk.CTkFrame(t, fg_color="transparent")
            lbl = etiqueta(f, f"{var.get():.0f} %", 12)
            ctk.CTkSlider(f, from_=5, to=100, variable=var, width=140, button_color=C["acento"],
                          progress_color=C["acento"], command=lambda v, l=lbl: l.configure(text=f"{float(v):.0f} %")).pack(side="left")
            lbl.pack(side="left", padx=(8, 0))
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
        self.v_forma = tk.StringVar(value=self.e["punto"].get("forma", "Círculo"))
        t.fila("Forma", ui.menu(t, FORMAS_PUNTO, self.v_forma, 150))
        num(t, "tamano", "punto", "Tamaño (px en pantalla)")
        alpha(t, "alpha", "punto", "Opacidad")
        num(t, "borde", "punto", "Grosor del borde (px)")
        self.v_err = tk.StringVar()
        ctk.CTkLabel(c, textvariable=self.v_err, font=F(12), text_color=C["rojo"]).pack(anchor="w", pady=(6, 0))
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=24, pady=(4, 20))
        boton(pie, "Guardar", primario=True, ancho=130, command=self.ok).pack(side="right")
        boton(pie, "Cancelar", ancho=110, command=self.destroy).pack(side="right", padx=8)
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + max(0, (app.winfo_height() - self.winfo_height()) // 6)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.after(60, lambda: ui.tenir_barra_titulo(self, ui.oscuro()))
        try:
            self.grab_set()
        except Exception:
            pass
        app.wait_window(self)

    def ok(self):
        e = self.e
        for (sub, clave), var in self.v.items():
            if isinstance(var, tk.DoubleVar):
                e[sub][clave] = round(float(var.get()), 0)
                continue
            n = ui.leer_num(var.get())
            if not isinstance(n, float) or n < 0:
                self.v_err.set("Revisá los números: deben ser mayores o iguales a cero.")
                return
            e[sub][clave] = n
        e["punto"]["forma"] = self.v_forma.get()
        self.p.guardar_estilo(self.iid, e)
        self.res = e
        self.destroy()


# =========================================================================
#  Exportacion
# =========================================================================
def exportar_imagen(p, pid, marcas, estilos, ruta, titulo, subtitulo, leyenda, notas=True):
    """Plano con las marcas visibles a PNG o PDF. leyenda: [(color, texto)]."""
    img = imagen_de(p, pid)
    f = 1.0
    if max(img.size) > 7000:
        f = 7000 / max(img.size)
        img = img.resize((int(img.width * f), int(img.height * f)), Image.LANCZOS)
    img = img.convert("RGBA")
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dibujar_marcas(capa, marcas, lambda x, y: (x * f, y * f), f, estilos)
    d = ImageDraw.Draw(capa)
    base = max(img.size)
    try:
        fuente = ImageFont.truetype(os.path.join(ui.recursos(), "fuentes", "Inter-SemiBold.ttf"), max(14, int(base / 160)))
        fuente_t = ImageFont.truetype(os.path.join(ui.recursos(), "fuentes", "Inter-Bold.ttf"), max(22, int(base / 90)))
        fuente_n = ImageFont.truetype(os.path.join(ui.recursos(), "fuentes", "Inter-SemiBold.ttf"), max(9, int(base / 300)))
    except Exception:
        fuente = fuente_t = fuente_n = ImageFont.load_default()
    grupos = []
    for m in (marcas if notas else ()):
        if not m.get("color") or not m.get("nota_txt"):
            continue
        ax, ay = ancla(m)
        ax, ay = ax * f, ay * f
        for g in grupos:
            if g["item"] == m["item"] and math.dist((g["x"], g["y"]), (ax, ay)) < base / 80:
                g["notas"].append((m["nota_txt"], m["color"]))
                break
        else:
            grupos.append({"x": ax, "y": ay, "item": m["item"], "notas": [(m["nota_txt"], m["color"])]})
    alto_l = int(fuente_n.size * 1.6)
    pad = max(2, fuente_n.size // 4)
    for g in grupos:
        y = g["y"] - alto_l * len(g["notas"])
        for txt, colr in g["notas"]:
            x0, y0, x1, y1 = d.textbbox((g["x"] + pad * 2, y), txt, font=fuente_n)
            d.rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], fill=(255, 255, 255, 235), outline=_rgba(colr),
                        width=max(1, pad // 2))
            d.text((g["x"] + pad * 2, y), txt, font=fuente_n, fill=(30, 39, 48, 255))
            y += alto_l
    img = Image.alpha_composite(img, capa)
    franja = int(fuente_t.size * 3.6)
    out = Image.new("RGB", (img.width, img.height + franja), "white")
    out.paste(img.convert("RGB"), (0, franja))
    d = ImageDraw.Draw(out)
    d.text((30, 18), titulo, font=fuente_t, fill=(30, 39, 48))
    d.text((30, 18 + fuente_t.size + 12), subtitulo, font=fuente, fill=(95, 107, 122))
    x = out.width - 30
    for colr, txt in reversed(leyenda):
        w = d.textlength(txt, font=fuente)
        x -= w
        d.text((x, 28), txt, font=fuente, fill=(30, 39, 48))
        x -= fuente.size * 1.8
        d.rectangle([x, 28, x + fuente.size * 1.2, 28 + fuente.size * 1.2], fill=_rgba(colr)[:3])
        x -= 30
    if ruta.lower().endswith(".pdf"):
        out.save(ruta, "PDF", resolution=150.0)
    else:
        out.save(ruta, "PNG", optimize=True)
    return ruta


def elegir_color(raiz, inicial, titulo):
    r = colorchooser.askcolor(color=inicial, parent=raiz, title=titulo)
    return r[1] if r and r[1] else None
