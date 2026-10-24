"""Ctrl-P Android - paleta, numeros y dibujos (iconos, logo, husky) compartidos con la version de escritorio."""

import io
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
    "marca": ("#4C6F9F", "#7096C8"), "verde": ("#067647", "#47CD89"), "naranja": ("#EA580C", "#FB923C"),
}
ICONOS = [  # clave, titulo, color, grupo
    ("proyecto", "Proyecto", "#3B82F6", 0),
    ("presupuesto", "Presupuesto", "#0EA5A4", 0),
    ("ubicaciones", "Ubicaciones", "#8B5CF6", 1),
    ("datos", "Datos fijos", "#F59E0B", 1),
    ("registro", "Registro de avance", "#10B981", 2),
    ("planos", "Planos", "#0EA5E9", 2),
    ("informes", "Informes de avance", "#EC4899", 2),
    ("enlinea", "En línea", "#2563EB", 3),
    ("apariencia", "Apariencia", "#64748B", 3),
]

NOMBRE_DOCS = "CTRL-P DOC"


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


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
    elif clave == "enlinea":          # nube con flechas de subir y bajar
        d.ellipse([4 * s, 9.5 * s, 11 * s, 16.5 * s], fill=w)
        d.ellipse([8 * s, 6 * s, 16.5 * s, 14.5 * s], fill=w)
        d.ellipse([13 * s, 9 * s, 20 * s, 16 * s], fill=w)
        d.rectangle([7.5 * s, 12 * s, 16.5 * s, 16.5 * s], fill=w)
        az = _hex(color) + (255,)
        lw2 = max(1, int(1.4 * s))
        d.line([(10.2 * s, 15.5 * s), (10.2 * s, 10.5 * s)], fill=az, width=lw2)
        d.polygon([(8.4 * s, 12 * s), (12 * s, 12 * s), (10.2 * s, 9.6 * s)], fill=az)
        d.line([(13.8 * s, 10 * s), (13.8 * s, 15 * s)], fill=az, width=lw2)
        d.polygon([(12 * s, 13.5 * s), (15.6 * s, 13.5 * s), (13.8 * s, 15.9 * s)], fill=az)
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


def a_png(pil):
    b = io.BytesIO()
    pil.save(b, "PNG")
    return b.getvalue()
