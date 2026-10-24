"""
Ctrl-P - componentes visuales compartidos
=========================================
Paleta gris azulada (claro / oscuro), fuente Inter incluida, iconos y logo
dibujados, interruptores, contadores, tarjetas, tablas (Treeview) con estilo
y barra de titulo de Windows tenida.
"""

import base64
import io
import os
import sys
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
from PIL import Image, ImageDraw

# Paleta: (claro, oscuro)
C = {
    "lat_ini": ("#EEF2F7", "#272D36"), "lat_fin": ("#D6DFEA", "#1D2229"), "lat_sel": ("#C3CFDF", "#353F4C"),
    "fondo": ("#F6F8FB", "#1A1E24"), "tarjeta": ("#FFFFFF", "#232931"), "borde": ("#E2E7EE", "#313844"),
    "linea": ("#EDF0F4", "#2C323B"), "texto": ("#1E2730", "#E7EBF0"), "texto2": ("#5F6B7A", "#9AA6B4"),
    "acento": ("#4C6F9F", "#7096C8"), "acento_h": ("#3F5F8B", "#5E84B6"), "suave": ("#E7ECF3", "#2C333D"),
    "suave_h": ("#DCE3EC", "#353D48"), "campo": ("#F4F6F9", "#1D2228"), "campo_borde": ("#D3DBE5", "#3A4350"),
    "titulo0": ("#DCE3EC", "#2E3642"), "titulo": ("#EEF2F7", "#272E37"), "subtotal": ("#F4F6F9", "#252B33"),
    "rojo": ("#B42318", "#F97066"), "punto": ("#8A96A6", "#7D8896"), "sel": ("#D7E3F4", "#34465F"),
    "marca": ("#4C6F9F", "#7096C8"), "verde": ("#067647", "#47CD89"),
}
ICONOS = [  # clave, titulo, color, grupo
    ("proyecto", "Proyecto", "#3B82F6", 0),
    ("presupuesto", "Presupuesto", "#0EA5A4", 0),
    ("ubicaciones", "Ubicaciones", "#8B5CF6", 1),
    ("datos", "Datos fijos", "#F59E0B", 1),
    ("registro", "Registro de avance", "#10B981", 2),
    ("planos", "Planos", "#0EA5E9", 2),
    ("informes", "Informes de avance", "#EC4899", 2),
    ("apariencia", "Apariencia", "#64748B", 3),
]

FAM = "Segoe UI" if os.name == "nt" else "DejaVu Sans"


def recursos():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


NOMBRE_DOCS = "CTRL-P DOC"


def _documentos():
    """La carpeta Documentos real (aunque esté en OneDrive o movida)."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:   # CSIDL_PERSONAL
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def carpeta_docs():
    """Carpeta por defecto para guardar y exportar: «CTRL-P DOC» junto al .exe portable (se crea sola).
    Instalado (o si ahí no se puede escribir), usa Documentos\\CTRL-P DOC."""
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    instalado = getattr(sys, "frozen", False) and os.path.isfile(os.path.join(base, "unins000.exe"))
    raices = ([] if instalado else [base]) + [_documentos(), os.path.expanduser("~")]
    for raiz in raices:
        ruta = os.path.join(raiz, NOMBRE_DOCS)
        try:
            os.makedirs(ruta, exist_ok=True)
            prueba = os.path.join(ruta, ".ctrlp_prueba")
            with open(prueba, "w") as f:
                f.write("")
            os.remove(prueba)
            return ruta
        except OSError:
            continue
    return base


def registrar_fuentes():
    """Registra Inter (incluida en el programa) solo para este proceso."""
    global FAM
    carpeta = os.path.join(recursos(), "fuentes")
    archivos = [os.path.join(carpeta, f) for f in ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")]
    if not all(os.path.isfile(a) for a in archivos):
        return FAM
    if os.name == "nt":
        try:
            import ctypes
            ok = 0
            for a in archivos:
                ok += ctypes.windll.gdi32.AddFontResourceExW(a, 0x10, 0)
            if ok:
                FAM = "Inter"
        except Exception:
            pass
    else:
        try:
            dest = os.path.join(os.path.expanduser("~"), ".fonts")
            os.makedirs(dest, exist_ok=True)
            import shutil
            for a in archivos:
                d = os.path.join(dest, os.path.basename(a))
                if not os.path.exists(d):
                    shutil.copy(a, d)
            FAM = "Inter"
        except Exception:
            pass
    return FAM


def oscuro():
    return ctk.get_appearance_mode().lower() == "dark"


def col(k):
    return C[k][1 if oscuro() else 0]


def F(tam=13, peso="normal"):
    return ctk.CTkFont(family=FAM, size=tam, weight=peso)


def TF(tam=10, peso="normal"):
    """Fuente para widgets tk/ttk."""
    return (FAM, tam, "bold" if peso == "bold" else "normal")


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def foto_tk(pil):
    b = io.BytesIO()
    pil.save(b, "PNG")
    return tk.PhotoImage(data=base64.b64encode(b.getvalue()).decode("ascii"))


# =========================================================================
#  Numeros
# =========================================================================
def fmt(x, dec=2):
    if x is None:
        return "—"
    s = f"{x:,.{dec}f}"
    if s.startswith("-"):
        s = "−" + s[1:]
    if s in ("−0.00", "−0.000"):
        s = s[1:]
    return s


def fmt_pct(x, dec=2):
    if x is None:
        return "—"
    return f"{x * 100:,.{dec}f} %"


def txt_num(x):
    """Numero para un campo editable: 2 decimales, o los que tenga (hasta 6) para no perder precision."""
    if x is None:
        return ""
    t = f"{x:.6f}".rstrip("0")
    ent, _, dec = t.partition(".")
    return f"{ent}.{dec.ljust(2, '0')}"


def leer_num(texto):
    t = (texto or "").strip().replace(",", "")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return "error"


# =========================================================================
#  Dibujos: iconos y logo
# =========================================================================
def icono(clave, color, tam=28, escala=4):
    T = tam * escala
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = _hex(color)
    arriba = tuple(min(255, int(v + (255 - v) * 0.16)) for v in (r, g, b))
    for y in range(T):
        t = y / T
        d.line([(0, y), (T, y)], fill=tuple(int(arriba[i] * (1 - t) + (r, g, b)[i] * t) for i in range(3)) + (255,))
    m = Image.new("L", (T, T), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, T - 1, T - 1], radius=int(T * 0.25), fill=255)
    img.putalpha(m)
    d = ImageDraw.Draw(img)
    w = (255, 255, 255, 255)
    s = T / 24.0
    lw = max(2, int(2.0 * s))

    def L(pts, ancho=lw):
        d.line([(x * s, y * s) for x, y in pts], fill=w, width=ancho, joint="curve")

    if clave == "proyecto":
        d.rounded_rectangle([5 * s, 7 * s, 19 * s, 18 * s], radius=int(1.6 * s), outline=w, width=lw)
        L([(5, 9), (5, 6.5), (10, 6.5), (11.5, 8)])
    elif clave == "presupuesto":
        for yy in (8, 12, 16):
            L([(10, yy), (19, yy)])
            d.ellipse([5.5 * s, (yy - 1.1) * s, 7.7 * s, (yy + 1.1) * s], fill=w)
    elif clave == "ubicaciones":
        L([(6, 19), (6, 7), (12, 5), (18, 7), (18, 19)])
        L([(4.5, 19), (19.5, 19)])
        for x in (9, 14):
            for y in (10, 13.5):
                d.rectangle([x * s, y * s, (x + 1.6) * s, (y + 1.6) * s], fill=w)
    elif clave == "datos":
        for y, xc in ((7, 14), (12, 9), (17, 15)):
            L([(5, y), (19, y)], max(1, lw - 1))
            d.ellipse([(xc - 2) * s, (y - 2) * s, (xc + 2) * s, (y + 2) * s], fill=w)
    elif clave == "registro":
        d.rounded_rectangle([5 * s, 6.5 * s, 19 * s, 19 * s], radius=int(1.6 * s), outline=w, width=lw)
        L([(5, 10), (19, 10)])
        L([(9, 4.5), (9, 8)])
        L([(15, 4.5), (15, 8)])
        L([(12, 12), (12, 17)])
        L([(9.5, 14.5), (14.5, 14.5)])
    elif clave == "informes":
        L([(7, 18), (7, 12)])
        L([(12, 18), (12, 6)])
        L([(17, 18), (17, 10)])
    elif clave == "planos":
        d.rectangle([4.5 * s, 6 * s, 19.5 * s, 18 * s], outline=w, width=lw)
        L([(4.5, 12), (11, 12), (11, 18)], max(1, lw - 1))
        L([(11, 9), (15, 9)], max(1, lw - 1))
        L([(15, 6), (15, 12), (19.5, 12)], max(1, lw - 1))
    elif clave == "apariencia":
        d.ellipse([5 * s, 5 * s, 19 * s, 19 * s], outline=w, width=lw)
        d.pieslice([5 * s, 5 * s, 19 * s, 19 * s], 90, 270, fill=w)
    return img.resize((tam, tam), Image.LANCZOS)


def logo(tam=220, escala=6):
    """Logo de Ctrl-P: grua torre montando la viga del ultimo nivel de un edificio."""
    T = 64 * escala
    s = escala
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    m = Image.new("L", (T, T), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, T - 1, T - 1], radius=13 * s, fill=255)
    fondo = Image.new("RGBA", (T, T), _hex("#3B5A84") + (255,))
    img.paste(fondo, (0, 0), m)
    grid = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    for k in range(8, 64, 8):
        g.line([(0, k * s), (T, k * s)], fill=(255, 255, 255, 36), width=max(1, int(0.3 * s)))
        g.line([(k * s, 0), (k * s, T)], fill=(255, 255, 255, 36), width=max(1, int(0.3 * s)))
    img.alpha_composite(Image.composite(grid, Image.new("RGBA", (T, T)), m))
    d = ImageDraw.Draw(img)
    W = (255, 255, 255, 255)
    AM = _hex("#F5B13D") + (255,)
    AZ = _hex("#3B5A84") + (255,)

    def L(pts, ancho, colr=W):
        d.line([(x * s, y * s) for x, y in pts], fill=colr, width=max(1, int(ancho * s)), joint="curve")

    L([(11, 54), (11, 9)], 1.4)
    L([(15, 54), (15, 9)], 1.4)
    L([(11, 50), (15, 46), (11, 42), (15, 38), (11, 34), (15, 30), (11, 26), (15, 22), (11, 18), (15, 14), (11, 10)], 0.8)
    L([(5, 9), (58, 9)], 2)
    L([(13, 9), (13, 3.5)], 0.9)
    L([(13, 3.5), (57, 9)], 0.9)
    L([(13, 3.5), (5, 9)], 0.9)
    d.rounded_rectangle([5 * s, 9.5 * s, 11 * s, 14 * s], radius=int(0.8 * s), fill=W)
    L([(44, 10), (44, 18)], 0.9)
    d.rectangle([42.5 * s, 9 * s, 45.5 * s, 11 * s], fill=W)
    L([(38, 18), (50, 18)], 1.6, AM)
    L([(38, 21), (50, 21)], 1.6, AM)
    L([(44, 18), (44, 21)], 1.6, AM)
    d.rectangle([25 * s, 30 * s, 53 * s, 54 * s], fill=W)
    L([(25, 38), (53, 38)], 1.2, AZ)
    L([(25, 46), (53, 46)], 1.2, AZ)
    for y in (32.5, 40.5, 48.5):
        for x in (28, 36.75, 45.5):
            h = 5.5 if (y == 48.5 and x == 28) else 3.5
            d.rectangle([x * s, y * s, (x + 4.5) * s, (y + h) * s], fill=AZ)
    for x in (26, 39, 52):
        L([(x, 30), (x, 23)], 1.6)
    x = 25.0
    while x < 53:
        L([(x, 23), (min(x + 2, 53), 23)], 1.2)
        x += 3.6
    L([(4, 54), (60, 54)], 2)
    return img.resize((tam, tam), Image.LANCZOS)


def husky(tam=64, escala=8, fondo="#1E2A3A"):
    T = 100 * escala; s = escala
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, T - 1, T - 1], fill=fondo)
    def P(pts): return [(x * s, y * s) for x, y in pts]
    GR = (92, 104, 120, 255); OS = (52, 60, 72, 255); W = (240, 244, 248, 255); IN = (214, 160, 160, 255)
    # orejas
    d.polygon(P([(22, 44), (27, 12), (44, 30)]), fill=GR)
    d.polygon(P([(78, 44), (73, 12), (56, 30)]), fill=GR)
    d.polygon(P([(28, 36), (30, 20), (39, 30)]), fill=IN)
    d.polygon(P([(72, 36), (70, 20), (61, 30)]), fill=IN)
    # cabeza
    d.polygon(P([(18, 52), (24, 36), (36, 27), (50, 25), (64, 27), (76, 36), (82, 52), (78, 68),
                 (66, 82), (50, 88), (34, 82), (22, 68)]), fill=GR)
    # mascara blanca: frente (rombo), cejas, mejillas y hocico
    d.polygon(P([(50, 30), (55, 44), (50, 52), (45, 44)]), fill=W)
    d.polygon(P([(22, 60), (30, 52), (42, 54), (50, 58), (58, 54), (70, 52), (78, 60), (72, 74),
                 (62, 84), (50, 89), (38, 84), (28, 74)]), fill=W)
    d.polygon(P([(29, 45), (40, 40), (43, 44), (32, 48)]), fill=W)
    d.polygon(P([(71, 45), (60, 40), (57, 44), (68, 48)]), fill=W)
    # sombra oscura central del hocico
    d.polygon(P([(44, 52), (50, 50), (56, 52), (53, 60), (47, 60)]), fill=GR)
    # ojos azules
    for cx in (37, 63):
        d.polygon(P([(cx - 6, 51), (cx, 47), (cx + 6, 51), (cx, 54)]), fill=(25, 30, 38, 255))
        d.ellipse(P([(cx - 3, 48.5), (cx + 3, 53.5)]), fill=(120, 196, 240, 255))
        d.ellipse(P([(cx - 1.2, 50), (cx + 1.2, 52.5)]), fill=(20, 24, 30, 255))
    # nariz y boca
    d.polygon(P([(44, 64), (56, 64), (53, 69), (50, 70.5), (47, 69)]), fill=(28, 32, 40, 255))
    d.line(P([(50, 70.5), (50, 75)]), fill=(28, 32, 40, 255), width=int(1.6 * s))
    d.arc(P([(42, 69), (50, 77)]), 20, 160, fill=(28, 32, 40, 255), width=int(1.6 * s))
    d.arc(P([(50, 69), (58, 77)]), 20, 160, fill=(28, 32, 40, 255), width=int(1.6 * s))
    m = Image.new("L", (T, T), 0); ImageDraw.Draw(m).ellipse([0, 0, T - 1, T - 1], fill=255)
    out = Image.new("RGBA", (T, T), (0, 0, 0, 0)); out.paste(img, (0, 0), m)
    ImageDraw.Draw(out).ellipse([int(1.5 * s), int(1.5 * s), T - 1 - int(1.5 * s), T - 1 - int(1.5 * s)],
                                outline=(245, 177, 61, 255), width=int(3 * s))
    return out.resize((tam, tam), Image.LANCZOS)


def ojo(abierto, color="#5F6B7A", tam=20, escala=6):
    T = tam * escala
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = _hex(color) + (255,)
    s = T / 24.0
    lw = max(2, int(1.8 * s))
    d.arc([2 * s, 5 * s, 22 * s, 27 * s], 200, 340, fill=c, width=lw)
    d.arc([2 * s, -3 * s, 22 * s, 19 * s], 20, 160, fill=c, width=lw)
    d.ellipse([9 * s, 9 * s, 15 * s, 15 * s], outline=c, width=lw)
    if not abierto:
        d.line([(4 * s, 20 * s), (20 * s, 4 * s)], fill=c, width=lw)
    return img.resize((tam, tam), Image.LANCZOS)


def guardar_icono_ico(ruta):
    img = logo(256, 4)
    img.save(ruta, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def img_interruptor(encendido, osc, activo=True, w=44, h=24, escala=4):
    W, H = w * escala, h * escala
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    riel = _hex(C["acento"][1 if osc else 0]) if encendido else _hex("#3A4350" if osc else "#D3DBE5")
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=H // 2, fill=riel + (255 if activo else 110,))
    m = int(2.5 * escala)
    diam = H - 2 * m
    x0 = W - m - diam if encendido else m
    d.ellipse([x0, m + escala * 0.6, x0 + diam, m + diam + escala * 0.6], fill=(0, 0, 0, 45 if activo else 20))
    d.ellipse([x0, m, x0 + diam, m + diam], fill=(255, 255, 255, 255 if activo else 200))
    return img.resize((w, h), Image.LANCZOS)


def miniatura_tema(modo, ancho=96, alto=64, escala=3):
    W, H = ancho * escala, alto * escala
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    claro = ("#F6F8FB", "#FFFFFF", "#D6DFEA")
    osc = ("#1A1E24", "#232931", "#272D36")

    def ventana(dd, c, x0, x1):
        dd.rounded_rectangle([x0, 0, x1, H - 1], radius=15, fill=_hex(c[0]))
        dd.rectangle([x0 + 4, 22, x0 + (x1 - x0) * 0.32, H - 6], fill=_hex(c[2]))
        dd.rounded_rectangle([x0 + (x1 - x0) * 0.38, 40, x1 - 8, H - 10], radius=6, fill=_hex(c[1]))

    if modo == "Oscuro":
        ventana(d, osc, 0, W - 1)
    else:
        ventana(d, claro, 0, W - 1)
        if modo == "Automático":
            mitad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ventana(ImageDraw.Draw(mitad), osc, 0, W - 1)
            img.paste(mitad.crop((W // 2, 0, W, H)), (W // 2, 0), mitad.crop((W // 2, 0, W, H)))
    tinta = (120, 130, 145)
    xs = [W - 26 * escala, W - 17 * escala, W - 8 * escala]
    y0, y1 = 5 * escala, 9 * escala
    d.line([(xs[0], (y0 + y1) / 2), (xs[0] + 4 * escala, (y0 + y1) / 2)], fill=tinta, width=escala)
    d.rectangle([xs[1], y0, xs[1] + 4 * escala, y1], outline=tinta, width=escala)
    d.line([(xs[2], y0), (xs[2] + 4 * escala, y1)], fill=tinta, width=escala)
    d.line([(xs[2], y1), (xs[2] + 4 * escala, y0)], fill=tinta, width=escala)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=15, outline=(160, 170, 185), width=2)
    return img.resize((ancho, alto), Image.LANCZOS)


def tenir_barra_titulo(ventana, osc):
    if os.name != "nt":
        return
    try:
        import ctypes
        ventana.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(ventana.winfo_id())
        dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute
        v = ctypes.c_int(1 if osc else 0)
        for a in (20, 19):
            if dwm(hwnd, a, ctypes.byref(v), ctypes.sizeof(v)) == 0:
                break
        r, g, b = _hex(C["lat_ini"][1 if osc else 0])
        cap = ctypes.c_int(r | (g << 8) | (b << 16))
        dwm(hwnd, 35, ctypes.byref(cap), ctypes.sizeof(cap))
        r, g, b = _hex(C["texto"][1 if osc else 0])
        txt = ctypes.c_int(r | (g << 8) | (b << 16))
        dwm(hwnd, 36, ctypes.byref(txt), ctypes.sizeof(txt))
        esq = ctypes.c_int(2)
        dwm(hwnd, 33, ctypes.byref(esq), ctypes.sizeof(esq))
    except Exception:
        pass


def icono_ventana(ventana):
    try:
        ventana._ctrlp_icono = foto_tk(logo(64, 4))
        ventana.iconphoto(True, ventana._ctrlp_icono)
        ico = os.path.join(recursos(), "ctrlp.ico")
        if os.name == "nt" and os.path.isfile(ico):
            ventana.after(250, lambda: ventana.iconbitmap(ico))
    except Exception:
        pass


# =========================================================================
#  Widgets
# =========================================================================
_IMGS_SW = {}


def _imgs_sw():
    if not _IMGS_SW:
        for e in (True, False):
            for a in (True, False):
                _IMGS_SW[(e, a)] = ctk.CTkImage(light_image=img_interruptor(e, False, a),
                                                dark_image=img_interruptor(e, True, a), size=(44, 24))
    return _IMGS_SW


class Interruptor(ctk.CTkLabel):
    def __init__(self, master, var, comando=None):
        super().__init__(master, text="", width=44, height=24, cursor="hand2")
        self.var, self.activo, self.comando = var, True, comando
        self.bind("<Button-1>", self._clic)
        var.trace_add("write", lambda *_: self._pintar())
        self._pintar()

    def _clic(self, _=None):
        if self.activo:
            self.var.set(not self.var.get())
            if self.comando:
                self.comando()

    def _pintar(self):
        super().configure(image=_imgs_sw()[(bool(self.var.get()), self.activo)])

    def configure(self, **kw):
        if "state" in kw:
            self.activo = kw.pop("state") != "disabled"
            super().configure(cursor="hand2" if self.activo else "arrow")
            self._pintar()
        if kw:
            super().configure(**kw)


def boton(master, texto, primario=False, ancho=110, alto=34, **kw):
    if primario:
        return ctk.CTkButton(master, text=texto, width=ancho, height=alto, corner_radius=8, font=F(13, "bold"),
                             fg_color=C["acento"], hover_color=C["acento_h"], text_color="#FFFFFF",
                             text_color_disabled=("#C9D5E4", "#9FB2CC"), **kw)
    return ctk.CTkButton(master, text=texto, width=ancho, height=alto, corner_radius=8, font=F(13),
                         fg_color=C["suave"], hover_color=C["suave_h"], text_color=C["texto"],
                         text_color_disabled=C["texto2"], **kw)


def entrada(master, var=None, ancho=160, **kw):
    return ctk.CTkEntry(master, textvariable=var, width=ancho, height=32, corner_radius=8, font=F(13),
                        fg_color=C["campo"], border_color=C["campo_borde"], text_color=C["texto"], **kw)


def entrada_mayus(master, var, ancho=200, **kw):
    e = entrada(master, var, ancho, **kw)

    def subir(*_):
        v = var.get()
        if v != v.upper():
            pos = e.index(tk.INSERT)
            var.set(v.upper())
            e.icursor(pos)
    var.trace_add("write", subir)
    return e


def segmentado(master, valores, var, ancho=None, cmd=None):
    s = ctk.CTkSegmentedButton(master, values=valores, variable=var, font=F(12), height=30,
                               selected_color=C["tarjeta"], selected_hover_color=C["tarjeta"],
                               unselected_color=C["suave"], unselected_hover_color=C["suave_h"],
                               fg_color=C["suave"], text_color=C["texto"], corner_radius=8, command=cmd)
    if ancho:
        s.configure(width=ancho)
    return s


def menu(master, valores, var, ancho=200, cmd=None):
    return ctk.CTkOptionMenu(master, values=valores, variable=var, width=ancho, height=30, corner_radius=8,
                             font=F(12), dropdown_font=F(12), fg_color=C["suave"], button_color=C["suave_h"],
                             button_hover_color=C["borde"], text_color=C["texto"], dropdown_fg_color=C["tarjeta"],
                             dropdown_hover_color=C["suave"], dropdown_text_color=C["texto"], command=cmd,
                             dynamic_resizing=False)


def recortar(texto, fuente, ancho):
    """Recorta el texto con '…' para que quepa en 'ancho' pixeles."""
    import tkinter.font as tkf
    f = tkf.Font(family=fuente[0], size=fuente[1], weight="bold" if "bold" in fuente[2:] else "normal")
    if f.measure(texto) <= ancho:
        return texto
    while texto and f.measure(texto + "…") > ancho:
        texto = texto[:-1]
    return texto.rstrip() + "…"


def etiqueta(master, texto="", tam=13, peso="normal", color="texto", **kw):
    return ctk.CTkLabel(master, text=texto, font=F(tam, peso), text_color=C[color], anchor="w", **kw)


class Contador(ctk.CTkFrame):
    def __init__(self, master, var, minimo, maximo, paso=1, ancho=56, cmd=None):
        super().__init__(master, fg_color=C["suave"], corner_radius=8, height=32)
        self.var, self.minimo, self.maximo, self.paso, self.cmd = var, minimo, maximo, paso, cmd
        self.b1 = ctk.CTkButton(self, text="−", width=30, height=30, corner_radius=7, font=F(15),
                                fg_color="transparent", hover_color=C["suave_h"], text_color=C["texto"],
                                command=lambda: self.mover(-1))
        self.e = ctk.CTkEntry(self, textvariable=var, width=ancho, height=28, corner_radius=6, font=F(13, "bold"),
                              justify="center", fg_color=C["campo"], border_width=0, text_color=C["texto"])
        self.b2 = ctk.CTkButton(self, text="+", width=30, height=30, corner_radius=7, font=F(15),
                                fg_color="transparent", hover_color=C["suave_h"], text_color=C["texto"],
                                command=lambda: self.mover(1))
        self.b1.pack(side="left", padx=(1, 0), pady=1)
        self.e.pack(side="left", pady=1)
        self.b2.pack(side="left", padx=(0, 1), pady=1)
        self.e.bind("<FocusOut>", lambda _: self.mover(0))
        self.e.bind("<Return>", lambda _: self.mover(0))

    def mover(self, d):
        try:
            v = int(float(self.var.get() or self.minimo))
        except ValueError:
            v = self.minimo
        v = max(self.minimo, min(self.maximo, v + d * self.paso))
        self.var.set(str(v))
        if self.cmd:
            self.cmd()


_U32 = None


def _user32():
    """user32 con los tipos de argumento declarados (en Windows de 64 bits evita pasar mal los punteros)."""
    global _U32
    if _U32 is None:
        import ctypes
        from ctypes import wintypes
        u = ctypes.WinDLL("user32", use_last_error=True)
        u.SendMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        u.SendMessageW.restype = ctypes.c_ssize_t
        u.RedrawWindow.argtypes = (wintypes.HWND, ctypes.c_void_p, wintypes.HANDLE, wintypes.UINT)
        u.RedrawWindow.restype = wintypes.BOOL
        _U32 = u
    return _U32


class congelar:
    """Antes congelaba el dibujo de Windows (WM_SETREDRAW); se sacó porque podía cerrar el programa.
    Queda como bloque vacío para no tocar a quien lo usa."""

    def __init__(self, ventana):
        self.v = ventana

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def armar_oculto(widget, funcion):
    """Arma el contenido con el contenedor oculto y lo muestra completo de una vez (sin rayas, sin tocar Windows)."""
    info = None
    try:
        if widget.winfo_manager() == "grid" or hasattr(widget, "_parent_frame"):
            info = True
            widget.grid_remove()
    except tk.TclError:
        info = None
    try:
        return funcion()
    finally:
        if info:
            try:
                widget.update_idletasks()
                widget.grid()
            except tk.TclError:
                pass


class Desplazable(ctk.CTkScrollableFrame):
    """CTkScrollableFrame sin rayas al desplazar con muchos datos: junta los giros de la rueda en un solo movimiento
    por cuadro (~60 por segundo) y espera a que se termine de redibujar antes del siguiente."""

    PASO = 40      # px por muesca de la rueda

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._pendiente = 0
        self._job_rueda = None
        try:
            cv = self._parent_canvas
            self._scrollbar.configure(command=lambda *x: self._mover_barra(*x))
            cv.configure(yscrollincrement=1)
        except Exception:
            pass

    def _mover_barra(self, *x):
        cv = self._parent_canvas
        cv.yview(*x)
        cv.update_idletasks()

    def _mouse_wheel_all(self, event):
        try:
            if getattr(self, "_shift_pressed", False) or not self._check_if_valid_scroll(event.widget):
                return super()._mouse_wheel_all(event)
        except Exception:
            return super()._mouse_wheel_all(event)
        if sys.platform.startswith("win") or sys.platform == "darwin":
            d = event.delta if sys.platform == "darwin" else event.delta / 120
            pasos = -d
        else:
            pasos = -1 if getattr(event, "num", 5) == 4 else 1
        self._pendiente += pasos * self.PASO
        if self._job_rueda is None:
            self._job_rueda = self.after(16, self._aplicar_rueda)

    def _aplicar_rueda(self):
        self._job_rueda = None
        px, self._pendiente = int(round(self._pendiente)), 0
        try:
            cv = self._parent_canvas
            if px and cv.yview() != (0.0, 1.0):
                cv.yview_scroll(px, "units")
                cv.update_idletasks()
        except tk.TclError:
            pass


def desplegar(tv, abrir=True):
    """Abre (o cierra) todas las ramas del arbol. Cerrado: solo quedan a la vista las partidas principales."""
    pila = list(tv.get_children(""))
    while pila:
        i = pila.pop()
        hijos = tv.get_children(i)
        if hijos:
            tv.item(i, open=abrir)
            pila.extend(hijos)
    if not abrir:
        sel = [s for s in tv.selection() if tv.parent(s) == ""]
        tv.selection_set(sel)
        primeros = tv.get_children("")
        if primeros:
            tv.see(primeros[0])


def ajustar_texto(etq, ref, resta=0, minimo=120):
    """El texto de etq se acomoda (salta de linea) al ancho actual de ref, menos 'resta' px (o resta() px)."""
    def f(_=None):
        try:
            w = ref.winfo_width()
            if w <= 1 or not etq.winfo_exists():
                return
            r = resta() if callable(resta) else resta
            esc = ctk.ScalingTracker.get_widget_scaling(etq) if isinstance(etq, ctk.CTkBaseClass) else 1.0
            nuevo = max(minimo, int((w - r) / esc))
            if getattr(etq, "_wrap_actual", None) != nuevo:
                etq._wrap_actual = nuevo
                etq.configure(wraplength=nuevo)
        except tk.TclError:
            pass
    ref.bind("<Configure>", f, add="+")
    etq.bind("<Configure>", f, add="+")     # tambien cuando cambia el texto o se acomodan los vecinos
    etq.bind("<Map>", f, add="+")
    etq.after(50, f)
    etq.after(400, f)
    return etq


def flujo(contenedor, widgets, sep=6, sep_y=6):
    """Acomoda los widgets uno al lado del otro y pasa a la fila siguiente cuando no entran (como texto).
    Cada fila es un marco propio, asi las columnas de una fila no empujan a las de otra."""
    estado = {"firma": None, "filas": []}

    def ubicar(forzar=None):
        try:
            ancho = contenedor.winfo_width()
        except tk.TclError:
            return
        if ancho <= 1:
            return
        filas, x, fila = [], 0, []
        for w in widgets:
            rw = w.winfo_reqwidth()
            if fila and x + sep + rw > ancho:
                filas.append(fila)
                fila, x = [], 0
            fila.append(w)
            x += (sep if x else 0) + rw
        if fila:
            filas.append(fila)
        firma = tuple(len(f) for f in filas)
        if firma == estado["firma"] and forzar is not True:
            return
        estado["firma"] = firma
        for w in widgets:
            w.pack_forget()
        for fr in estado["filas"]:
            fr.destroy()
        estado["filas"] = []
        for r, f in enumerate(filas):
            fr = ctk.CTkFrame(contenedor, fg_color="transparent", height=1, corner_radius=0)
            fr.pack(side="top", anchor="w", pady=(0 if r == 0 else sep_y, 0))
            estado["filas"].append(fr)
            for c, w in enumerate(f):
                w.pack(in_=fr, side="left", padx=(0 if c == 0 else sep, 0))
                w.lift(fr)
    contenedor.bind("<Configure>", lambda e: ubicar(), add="+")
    contenedor.after(60, ubicar)
    return lambda: contenedor.after(30, lambda: ubicar(True))


class ScrollH(tk.Frame):
    """Contenedor con desplazamiento horizontal solo cuando el contenido no entra; si sobra espacio, lo estira.
    Poner el contenido en .interior."""

    def __init__(self, master, bg):
        super().__init__(master, bg=bg, highlightthickness=0, bd=0)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, height=1)
        self.canvas.pack(side="bottom", fill="x", expand=True)
        self.sb = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview, height=12,
                                   button_color=C["borde"][0] if isinstance(C["borde"], (list, tuple)) else C["borde"])
        self.canvas.configure(xscrollcommand=self.sb.set)
        self.interior = tk.Frame(self.canvas, bg=bg, highlightthickness=0, bd=0)
        self._win = self.canvas.create_window(0, 0, window=self.interior, anchor="nw")
        self._sb_visible = False
        self.interior.bind("<Configure>", lambda _: self._ajustar())
        self.canvas.bind("<Configure>", lambda _: self._ajustar())
        for w in (self.canvas, self.interior):
            w.bind("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(-1 if e.delta > 0 else 1, "units"), add="+")

    def _ajustar(self):
        req_w, req_h = self.interior.winfo_reqwidth(), self.interior.winfo_reqheight()
        cw = self.canvas.winfo_width()
        if cw <= 1:
            return
        self.canvas.itemconfigure(self._win, width=max(cw, req_w), height=req_h)
        if int(float(self.canvas.cget("height"))) != req_h:
            self.canvas.configure(height=req_h)
        self.canvas.configure(scrollregion=(0, 0, max(cw, req_w), req_h))
        hace_falta = req_w > cw + 1
        if hace_falta and not self._sb_visible:
            self.sb.pack(side="top", fill="x", pady=(0, 4))     # arriba de la tabla, siempre a la vista
            self._sb_visible = True
        elif not hace_falta and self._sb_visible:
            self.sb.pack_forget()
            self._sb_visible = False
            self.canvas.xview_moveto(0)


class Tarjeta(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=C["tarjeta"], corner_radius=12, border_width=1, border_color=C["borde"], **kw)
        self.grid_columnconfigure(1, weight=1)
        self._n = 0
        self._base = 0
        self.ancho_ayuda = 420

    def fila(self, texto, widget=None, ayuda=None):
        if self._n or self._base:
            ctk.CTkFrame(self, height=1, fg_color=C["linea"], corner_radius=0).grid(
                row=self._base + self._n * 2 - 1, column=0, columnspan=2, sticky="ew", padx=16)
        r = self._base + self._n * 2
        caja = ctk.CTkFrame(self, fg_color="transparent")
        caja.grid(row=r, column=0, sticky="w", padx=(18, 10), pady=11)
        etiqueta(caja, texto).pack(anchor="w")
        if ayuda:
            lb = ctk.CTkLabel(caja, text=ayuda, font=F(11), text_color=C["texto2"], anchor="w", justify="left",
                              wraplength=self.ancho_ayuda)
            lb.pack(anchor="w")
            ajustar_texto(lb, self, lambda w=widget: 70 + (w.winfo_reqwidth() if w is not None else 0), 160)
        if widget is not None:
            widget.grid(row=r, column=1, sticky="e", padx=(10, 16), pady=9)
        self._n += 1
        return caja


def estilo_tablas(raiz):
    """Estilo de ttk.Treeview acorde al tema."""
    st = ttk.Style(raiz)
    try:
        st.theme_use("clam")
    except Exception:
        pass
    st.configure("Ctrl.Treeview", background=col("tarjeta"), fieldbackground=col("tarjeta"),
                 foreground=col("texto"), rowheight=28, borderwidth=0, font=TF(10), indent=11)
    st.map("Ctrl.Treeview", background=[("selected", col("sel"))], foreground=[("selected", col("texto"))])
    st.configure("Ctrl.Treeview.Heading", background=col("subtotal"), foreground=col("texto2"),
                 font=TF(9, "bold"), relief="flat", borderwidth=0, padding=(6, 6))
    st.map("Ctrl.Treeview.Heading", background=[("active", col("suave"))])
    st.layout("Ctrl.Treeview", [("Ctrl.Treeview.treearea", {"sticky": "nswe"})])


def tabla(master, columnas, alturas=None, arbol=True):
    """columnas: lista de (clave, titulo, ancho, ancla). Devuelve (marco, treeview)."""
    marco = ctk.CTkFrame(master, fg_color=C["tarjeta"], corner_radius=12, border_width=1, border_color=C["borde"])
    marco.grid_columnconfigure(0, weight=1)
    marco.grid_rowconfigure(0, weight=1)
    tv = ttk.Treeview(marco, columns=[c[0] for c in columnas], style="Ctrl.Treeview",
                      show="tree headings" if arbol else "headings", selectmode="browse")
    for clave, titulo, ancho, ancla in columnas:
        tv.heading(clave, text=titulo, anchor=ancla)
        tv.column(clave, width=ancho, minwidth=40, anchor=ancla, stretch=(clave == "descripcion"))
    if arbol:
        tv.column("#0", width=64, minwidth=40, stretch=False)
    sb = ctk.CTkScrollbar(marco, command=tv.yview, button_color=C["suave_h"], button_hover_color=C["borde"])
    tv.configure(yscrollcommand=sb.set)
    sbx = ctk.CTkScrollbar(marco, command=tv.xview, orientation="horizontal", button_color=C["suave_h"],
                           button_hover_color=C["borde"])
    tv.configure(xscrollcommand=sbx.set)
    tv.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
    sb.grid(row=0, column=1, sticky="ns", padx=(2, 6), pady=8)
    sbx.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
    etiquetas_tabla(tv)
    return marco, tv


class ArbolFijo:
    """Tres Treeview que se ven como una sola tabla: columnas fijas a la izquierda, columnas que se desplazan
    en el medio (dias o semanas) y columnas fijas a la derecha. Imita lo que usa la pagina de Informes de un
    ttk.Treeview (insert, item, get_children, exists, parent, selection, see, tag_configure)."""

    def __init__(self, partes):
        self.partes = partes            # [(treeview, [claves])]
        self.tvs = [tv for tv, _ in partes]
        self.principal = self.tvs[0]
        self._sinc = False

    # --- lo que usa la pagina
    def insert(self, padre, pos, iid=None, values=(), **kw):
        vals = list(values)
        claves = [k for _, ks in self.partes for k in ks]
        mapa = dict(zip(claves, vals))
        iid = self.principal.insert(padre, pos, iid=iid, values=[mapa.get(k, "") for k in self.partes[0][1]], **kw)
        kw.pop("text", None)
        for tv, ks in self.partes[1:]:
            tv.insert(padre, pos, iid=iid, values=[mapa.get(k, "") for k in ks], **kw)
        return iid

    def exists(self, i):
        return self.principal.exists(i)

    def get_children(self, i=""):
        return self.principal.get_children(i)

    def parent(self, i):
        return self.principal.parent(i)

    def item(self, i, option=None, **kw):
        if kw:
            for tv in self.tvs:
                tv.item(i, **kw)
            return None
        return self.principal.item(i, option) if option else self.principal.item(i)

    def selection(self):
        return self.principal.selection()

    def selection_set(self, sel):
        for tv in self.tvs:
            tv.selection_set(sel)

    def see(self, i):
        for tv in self.tvs:
            tv.see(i)

    def tag_configure(self, *a, **kw):
        for tv in self.tvs:
            tv.tag_configure(*a, **kw)


def tabla_fija(master, izq, centro, der):
    """Tabla con columnas fijas a izquierda y derecha y el centro desplazable. Cada grupo: (clave, titulo, ancho, ancla).
    Devuelve (marco, ArbolFijo)."""
    marco = ctk.CTkFrame(master, fg_color=C["tarjeta"], corner_radius=12, border_width=1, border_color=C["borde"])
    marco.grid_rowconfigure(0, weight=1)
    partes, col = [], 0
    sb = ctk.CTkScrollbar(marco, button_color=C["suave_h"], button_hover_color=C["borde"])
    grupos = [("izq", izq), ("centro", centro), ("der", der)]
    vistas = {}
    for nombre, cols in grupos:
        if not cols:
            continue
        tv = ttk.Treeview(marco, columns=[c[0] for c in cols], style="Ctrl.Treeview",
                          show="tree headings" if nombre == "izq" else "headings", selectmode="browse")
        for clave, titulo, ancho, ancla in cols:
            tv.heading(clave, text=titulo, anchor=ancla)
            tv.column(clave, width=ancho, minwidth=40, anchor=ancla,
                      stretch=(nombre == "izq" and clave == "descripcion" and not centro))
        if nombre == "izq":
            tv.column("#0", width=40, minwidth=30, stretch=False)
        tv.grid(row=0, column=col, sticky="nsew", padx=((8 if col == 0 else 0), 0), pady=(8, 0))
        marco.grid_columnconfigure(col, weight=1 if (nombre == "centro" or (nombre == "izq" and not centro)) else 0)
        etiquetas_tabla(tv)
        vistas[nombre] = (tv, col)
        partes.append((tv, [c[0] for c in cols]))
        col += 1
    sb.grid(row=0, column=col, sticky="ns", padx=(2, 6), pady=8)
    arbol = ArbolFijo(partes)
    tvs = arbol.tvs

    # desplazamiento vertical comun
    def yview(*a):
        for tv in tvs:
            tv.yview(*a)
    sb.configure(command=yview)

    def al_mover(tv_origen):
        def f(a, b):
            sb.set(a, b)
            if arbol._sinc:
                return
            arbol._sinc = True
            try:
                for tv in tvs:
                    if tv is not tv_origen:
                        tv.yview_moveto(a)
            finally:
                arbol._sinc = False
        return f
    for tv in tvs:
        tv.configure(yscrollcommand=al_mover(tv))

    # abrir / cerrar ramas y seleccion iguales en las tres partes
    def sinc_rama(tv_origen, abrir):
        def f(_=None):
            i = tv_origen.focus()
            if i:
                for tv in tvs:
                    if tv is not tv_origen and tv.exists(i):
                        tv.item(i, open=abrir)
        return f
    tvs[0].bind("<<TreeviewOpen>>", sinc_rama(tvs[0], True), add="+")
    tvs[0].bind("<<TreeviewClose>>", sinc_rama(tvs[0], False), add="+")

    def sinc_sel(tv_origen):
        def f(_=None):
            if arbol._sinc:
                return
            arbol._sinc = True
            try:
                sel = tv_origen.selection()
                for tv in tvs:
                    if tv is not tv_origen:
                        tv.selection_set(sel)
            finally:
                arbol._sinc = False
        return f
    for tv in tvs:
        tv.bind("<<TreeviewSelect>>", sinc_sel(tv), add="+")

    # rueda del raton sobre cualquier parte: se mueven todas juntas
    def rueda(e):
        d = -1 if (getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4) else 1
        for tv in tvs:
            tv.yview_scroll(d * 3, "units")
        return "break"
    for tv in tvs:
        tv.bind("<MouseWheel>", rueda)
        tv.bind("<Button-4>", rueda)
        tv.bind("<Button-5>", rueda)

    # desplazamiento horizontal: solo el centro (o la izquierda si no hay centro)
    mov = vistas.get("centro", vistas.get("izq"))
    if mov:
        tvm, cm = mov
        estado = {"cabe": None, "ultimo": None}

        def mover_x(*a):
            # si todas las columnas ya se ven, no hay nada que desplazar (tocar la barra no hace nada)
            if estado["cabe"]:
                return
            tvm.xview(*a)

        sbx = ctk.CTkScrollbar(marco, command=mover_x, orientation="horizontal", button_color=C["suave_h"],
                               button_hover_color=C["borde"])

        def al_desplazar_x(a, b):
            a, b = float(a), float(b)
            if estado["ultimo"] == (a, b):
                return                                 # sin cambios: no se redibuja (evita idas y vueltas)
            estado["ultimo"] = (a, b)
            cabe = a <= 0.0 and b >= 1.0
            if cabe != estado["cabe"]:
                estado["cabe"] = cabe
                if cabe:
                    sbx.grid_remove()                  # la barra solo aparece cuando hay columnas que desplazar
                else:
                    sbx.grid(row=1, column=cm, sticky="ew", padx=(0 if cm else 8, 0), pady=(0, 6))
            if not cabe:
                sbx.set(a, b)
        tvm.configure(xscrollcommand=al_desplazar_x)
        sbx.grid(row=1, column=cm, sticky="ew", padx=(0 if cm else 8, 0), pady=(0, 6))
        tvm.bind("<Shift-MouseWheel>",
                 lambda e: ("break" if estado["cabe"] else (tvm.xview_scroll(-1 if e.delta > 0 else 1, "units"), "break")[1]))

    # la descripcion se agranda para llenar el espacio, o se achica (hasta 150) para dejar lugar al centro
    if centro and "izq" in vistas:
        tvi = vistas["izq"][0]
        fijo = sum(c[2] for c in izq if c[0] != "descripcion") + 40 + sum(c[2] for c in der) + 40
        total_centro = sum(c[2] for c in centro)

        def ajustar(e=None):
            w = marco.winfo_width()
            if w <= 1:
                return
            esc = ctk.ScalingTracker.get_widget_scaling(marco)
            libre = w / esc - fijo
            quiero = libre - total_centro if libre - total_centro >= 130 else libre - min(total_centro, 3 * 88)
            tvi.column("descripcion", width=int(max(130, min(520, quiero)) * esc))
        marco.bind("<Configure>", ajustar, add="+")
    return marco, arbol


def etiquetas_tabla(tv):
    tv.tag_configure("titulo0", background=col("titulo0"), font=TF(10, "bold"))
    tv.tag_configure("titulo", background=col("titulo"), font=TF(10, "bold"))
    tv.tag_configure("subtotal", background=col("subtotal"), font=TF(10, "bold"))
    tv.tag_configure("total", background=col("titulo0"), font=TF(10, "bold"))
    tv.tag_configure("neg", foreground=col("rojo"))
    tv.tag_configure("fuera", foreground=col("texto2"))
    tv.tag_configure("marca", foreground=col("texto2"))
    tv.tag_configure("negrita", font=TF(10, "bold"))
    tv.tag_configure("completa", foreground=col("verde"))


def dialogo_texto(raiz, titulo, mensaje, botones=("Aceptar",), primario=0):
    """Ventanita con el estilo del programa. Devuelve el indice del boton (o None)."""
    res = {"v": None}
    dlg = ctk.CTkToplevel(raiz, fg_color=C["tarjeta"])
    dlg.title(titulo)
    dlg.resizable(False, False)
    dlg.transient(raiz)
    etiqueta(dlg, titulo, 16, "bold").pack(anchor="w", padx=24, pady=(20, 6))
    ctk.CTkLabel(dlg, text=mensaje, font=F(13), text_color=C["texto"], justify="left", anchor="w",
                 wraplength=460).pack(anchor="w", padx=24)
    fila = ctk.CTkFrame(dlg, fg_color="transparent")
    fila.pack(fill="x", padx=24, pady=(18, 20))
    for k in reversed(range(len(botones))):
        boton(fila, botones[k], primario=(k == primario), ancho=max(100, 9 * len(botones[k])),
              command=lambda k=k: (res.update(v=k), dlg.destroy())).pack(side="right", padx=(8, 0))
    dlg.bind("<Escape>", lambda _: dlg.destroy())
    dlg.update_idletasks()
    x = raiz.winfo_rootx() + (raiz.winfo_width() - dlg.winfo_width()) // 2
    y = raiz.winfo_rooty() + (raiz.winfo_height() - dlg.winfo_height()) // 3
    dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    dlg.after(60, lambda: tenir_barra_titulo(dlg, oscuro()))
    icono_ventana(dlg)
    try:
        dlg.grab_set()
    except Exception:
        pass
    raiz.wait_window(dlg)
    return res["v"]


class CampoClave(ctk.CTkFrame):
    """Entrada de contrasena con boton para verla u ocultarla."""

    def __init__(self, master, var, ancho=300, alto=36, fuente=None, **kw):
        super().__init__(master, fg_color="transparent")
        self.var = var
        self.e = ctk.CTkEntry(self, textvariable=var, width=ancho - alto - 6, height=alto, corner_radius=8,
                              font=fuente or F(13), fg_color=C["campo"], border_color=C["campo_borde"],
                              text_color=C["texto"], show="•", **kw)
        self.e.pack(side="left")
        self._img = {k: ctk.CTkImage(light_image=ojo(k, "#5F6B7A"), dark_image=ojo(k, "#9AA6B4"), size=(20, 20))
                     for k in (True, False)}
        self.visible = False
        self.b = ctk.CTkButton(self, text="", image=self._img[True], width=alto, height=alto, corner_radius=8,
                               fg_color=C["suave"], hover_color=C["suave_h"], command=self.alternar)
        self.b.pack(side="left", padx=(6, 0))

    def alternar(self):
        self.visible = not self.visible
        self.e.configure(show="" if self.visible else "•")
        self.b.configure(image=self._img[not self.visible])

    def bind(self, *a, **k):
        return self.e.bind(*a, **k)

    def focus_set(self):
        self.e.focus_set()


def dialogo_form(raiz, titulo, mensaje, campos, botones=("Cancelar", "Aceptar"), primario=1, validar=None):
    """campos: [(clave, etiqueta, secreto, valor_inicial)]. Devuelve dict de valores o None.
    validar(valores) -> mensaje de error o "" (si hay error no se cierra)."""
    res = {"v": None}
    dlg = ctk.CTkToplevel(raiz, fg_color=C["tarjeta"])
    dlg.title(titulo)
    dlg.resizable(False, False)
    dlg.transient(raiz)
    etiqueta(dlg, titulo, 16, "bold").pack(anchor="w", padx=24, pady=(20, 6))
    if mensaje:
        ctk.CTkLabel(dlg, text=mensaje, font=F(12), text_color=C["texto2"], justify="left", anchor="w",
                     wraplength=380).pack(anchor="w", padx=24)
    vars_ = {}
    primero = None
    for clave, et, secreto, valor in campos:
        etiqueta(dlg, et, 12, "bold").pack(anchor="w", padx=24, pady=(12, 4))
        v = tk.StringVar(value=valor or "")
        vars_[clave] = v
        if secreto:
            w = CampoClave(dlg, v, 380)
        else:
            w = entrada(dlg, v, 380)
            w.configure(height=36)
        w.pack(anchor="w", padx=24)
        primero = primero or w
    v_err = tk.StringVar()
    ctk.CTkLabel(dlg, textvariable=v_err, font=F(12), text_color=C["rojo"], wraplength=380, justify="left").pack(
        anchor="w", padx=24, pady=(6, 0))

    def ok(k):
        vals = {c: v.get() for c, v in vars_.items()}
        if k == primario and validar:
            err = validar(vals)
            if err:
                v_err.set(err)
                return
        res["v"] = vals if k == primario else None
        dlg.destroy()

    fila = ctk.CTkFrame(dlg, fg_color="transparent")
    fila.pack(fill="x", padx=24, pady=(10, 20))
    for k in reversed(range(len(botones))):
        boton(fila, botones[k], primario=(k == primario), ancho=max(100, 9 * len(botones[k])),
              command=lambda k=k: ok(k)).pack(side="right", padx=(8, 0))
    dlg.bind("<Return>", lambda _: ok(primario))
    dlg.bind("<Escape>", lambda _: dlg.destroy())
    dlg.update_idletasks()
    x = raiz.winfo_rootx() + (raiz.winfo_width() - dlg.winfo_width()) // 2
    y = raiz.winfo_rooty() + (raiz.winfo_height() - dlg.winfo_height()) // 3
    dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    dlg.after(60, lambda: tenir_barra_titulo(dlg, oscuro()))
    icono_ventana(dlg)
    if primero is not None:
        dlg.after(120, primero.focus_set)
    try:
        dlg.grab_set()
    except Exception:
        pass
    raiz.wait_window(dlg)
    return res["v"]


def info(raiz, titulo, mensaje):
    dialogo_texto(raiz, titulo, mensaje)


def preguntar(raiz, titulo, mensaje, si="Sí", no="Cancelar"):
    return dialogo_texto(raiz, titulo, mensaje, (no, si), primario=1) == 1
