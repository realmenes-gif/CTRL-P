"""
Ctrl-P Android - planos (parte sin pantalla)
============================================
Carga de planos (PDF o imagen), geometria, notas, dibujo de marcas y exportacion: lo mismo que
ctrlp_planos.py de la computadora. En la tablet los PDF se dibujan con el lector propio de Android
(PdfRenderer); en la PC de prueba, con pymupdf si esta instalado.
"""

import io
import math
import os
import tempfile

from PIL import Image, ImageDraw, ImageFont

import ctrlp_core as core
from dibujos import fmt

Image.MAX_IMAGE_PIXELS = None
LADO_MAX = 9000          # lado mayor de la imagen base al cargar (igual que en la computadora)
LADO_VISTA = 6000        # en la tablet el visor trabaja con a lo sumo este lado (ahorra memoria; las medidas no cambian)
ZOOM_MAX = 40.0
COLOR_PERIODO = "#16A34A"
COLOR_ANTERIOR = "#DC2626"
FORMAS_PUNTO = ["Círculo", "Cuadrado", "Triángulo", "Rombo", "Cruz", "Estrella"]
HERRAMIENTAS = [("Mover", "mover"), ("Editar", "editar"), ("Línea", "linea"), ("Línea libre", "linea_libre"),
                ("Rectángulo", "rect"), ("Círculo", "circulo"), ("Polígono", "area"), ("Área libre", "area_libre"),
                ("Punto", "punto"), ("Calibrar", "calibrar")]


def recursos():
    return os.path.dirname(os.path.abspath(__file__))


def _android():
    try:
        from kivy.utils import platform
        return platform == "android"
    except Exception:
        return False


# =========================================================================
#  PDF: Android (PdfRenderer) o pymupdf
# =========================================================================
class _PdfAndroid:
    """Abre un PDF con android.graphics.pdf.PdfRenderer y dibuja paginas (por franjas, sin agotar la memoria)."""

    def __init__(self, ruta):
        from jnius import autoclass
        File = autoclass("java.io.File")
        PFD = autoclass("android.os.ParcelFileDescriptor")
        self.Renderer = autoclass("android.graphics.pdf.PdfRenderer")
        self.Page = autoclass("android.graphics.pdf.PdfRenderer$Page")
        self.Bitmap = autoclass("android.graphics.Bitmap")
        self.Config = autoclass("android.graphics.Bitmap$Config")
        self.Matrix = autoclass("android.graphics.Matrix")
        self.ByteBuffer = autoclass("java.nio.ByteBuffer")
        self.Color = autoclass("android.graphics.Color")
        self.fd = PFD.open(File(ruta), PFD.MODE_READ_ONLY)
        self.r = self.Renderer(self.fd)

    @property
    def paginas(self):
        return self.r.getPageCount()

    def tam(self, k):
        pg = self.r.openPage(k)
        try:
            return pg.getWidth(), pg.getHeight()        # en puntos (1/72")
        finally:
            pg.close()

    def dibujar(self, k, ancho, alto):
        """Pagina k a una imagen PIL RGB de ancho x alto, en franjas de 1024 filas."""
        out = Image.new("RGB", (ancho, alto), "white")
        pg = self.r.openPage(k)
        try:
            pw, ph = pg.getWidth(), pg.getHeight()
            sx, sy = ancho / pw, alto / ph
            paso = 1024
            for y0 in range(0, alto, paso):
                h = min(paso, alto - y0)
                bmp = self.Bitmap.createBitmap(ancho, h, self.Config.ARGB_8888)
                bmp.eraseColor(self.Color.WHITE)
                m = self.Matrix()
                m.setScale(sx, sy)
                m.postTranslate(0, -y0)
                pg.render(bmp, None, m, self.Page.RENDER_MODE_FOR_DISPLAY)
                buf = self.ByteBuffer.allocate(ancho * h * 4)
                bmp.copyPixelsToBuffer(buf)
                datos = bytes(buf.array())
                bmp.recycle()
                franja = Image.frombuffer("RGBA", (ancho, h), datos, "raw", "RGBA", 0, 1).convert("RGB")
                out.paste(franja, (0, y0))
        finally:
            pg.close()
        return out

    def cerrar(self):
        try:
            self.r.close()
            self.fd.close()
        except Exception:
            pass


def _abrir_pdf(ruta):
    if _android():
        return _PdfAndroid(ruta)
    return None


def paginas_pdf(ruta):
    d = _abrir_pdf(ruta)
    if d is not None:
        try:
            return d.paginas
        finally:
            d.cerrar()
    import pymupdf
    with pymupdf.open(ruta) as doc:
        return doc.page_count


def _pdf_a_imagen(ruta, pagina, dpi):
    """Pagina de un PDF a imagen PIL, con el lado mayor limitado a LADO_MAX."""
    d = _abrir_pdf(ruta)
    if d is not None:
        try:
            if d.paginas == 0:
                raise core.ErrorCtrlP("El PDF no tiene páginas.")
            pw, ph = d.tam(pagina)
            z = dpi / 72.0
            if max(pw, ph) * z > LADO_MAX:
                z = LADO_MAX / max(pw, ph)
            return d.dibujar(pagina, int(round(pw * z)), int(round(ph * z)))
        finally:
            d.cerrar()
    import pymupdf
    with pymupdf.open(ruta) as doc:
        if doc.page_count == 0:
            raise core.ErrorCtrlP("El PDF no tiene páginas.")
        page = doc[pagina]
        z = dpi / 72.0
        if max(page.rect.width, page.rect.height) * z > LADO_MAX:
            z = LADO_MAX / max(page.rect.width, page.rect.height)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _comprimir(img):
    """Imagen -> PNG con paleta (los planos son de pocos colores: queda liviano y nitido)."""
    img = img.convert("RGB")
    q = img.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    b = io.BytesIO()
    q.save(b, "PNG", optimize=True)
    return b.getvalue()


def importar_archivo(ruta, aplanar=True, dpi=200, pagina=0):
    """Devuelve (tipo, datos, ancho, alto). En la tablet el plano siempre queda aplanado (imagen comprimida),
    que es lo que abre y se mueve rapido; el archivo .ctrlp es el mismo que en la computadora."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".pdf":
        img = _pdf_a_imagen(ruta, pagina, dpi)
        return "png", _comprimir(img), img.width, img.height
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


def imagen_de(p, pid, lado_max=None):
    """Imagen del plano en su tamano original (o reducida a lado_max; ver factor_de)."""
    pl = p.plano(pid, con_datos=True)
    if pl["tipo"].startswith("pdf"):
        datos = bytes(pl["datos"])
        ancho, alto = pl["ancho"], pl["alto"]
        f = 1.0
        if lado_max and max(ancho, alto) > lado_max:
            f = lado_max / max(ancho, alto)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            tmp.write(datos)
            tmp.close()
            d = _abrir_pdf(tmp.name)
            if d is not None:
                try:
                    return d.dibujar(0, max(1, int(ancho * f)), max(1, int(alto * f)))
                finally:
                    d.cerrar()
            import pymupdf
            with pymupdf.open(tmp.name) as doc:
                page = doc[0]
                z = ancho * f / page.rect.width
                pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                tam = (max(1, int(ancho * f)), max(1, int(alto * f)))
                return img if img.size == tam else img.resize(tam)
        finally:
            try:
                os.remove(tmp.name)
            except OSError:
                pass
    img = Image.open(io.BytesIO(bytes(pl["datos"])))
    if lado_max and max(img.size) > lado_max:
        img.draft("RGB", (lado_max, lado_max))
        f = lado_max / max(img.size)
        img = img.convert("RGB").resize((max(1, int(img.width * f)), max(1, int(img.height * f))), Image.BILINEAR)
        return img
    return img.convert("RGB")


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
        fuente = ImageFont.truetype(os.path.join(recursos(), "fuentes", "Inter-SemiBold.ttf"), max(14, int(base / 160)))
        fuente_t = ImageFont.truetype(os.path.join(recursos(), "fuentes", "Inter-Bold.ttf"), max(22, int(base / 90)))
        fuente_n = ImageFont.truetype(os.path.join(recursos(), "fuentes", "Inter-SemiBold.ttf"), max(9, int(base / 300)))
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
