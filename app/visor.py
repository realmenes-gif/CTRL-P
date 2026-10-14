"""
Ctrl-P Android - visor de planos tactil
=======================================
Mismo comportamiento que el visor de la computadora, pensado para el dedo:
- dos dedos: acercar/alejar y mover (con cualquier herramienta);
- un dedo: la herramienta elegida (mover, editar, linea, linea libre, rectangulo, circulo, poligono,
  area libre, punto, calibrar) y los vacios de un area;
- iman a esquinas y lineas del dibujo del plano y a vertices de otras marcas;
- notas pequenas con el plano completo y mas grandes al acercar (se pueden ocultar).
El plano y las marcas se componen con PIL (igual que en la computadora); mientras se mueve con los dedos
se desplaza la ultima imagen y al soltar se vuelve a dibujar nitida.
"""

import math
import os

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Mesh, Rectangle
from kivy.graphics.tesselator import Tesselator
from kivy.metrics import dp, sp
from kivy.uix.widget import Widget
from PIL import Image, ImageDraw, ImageFont

import ctrlp_core as core
import ui_k as ui
from planos_base import (LADO_VISTA, ZOOM_MAX, _dist_seg, _rgba, ancla, area_neta_px, area_px, dentro,
                         dibujar_marcas, elipse, largo_px, rectangulo, simplificar)

AZUL = (0.055, 0.647, 0.914, 1)
AMBAR = (0.96, 0.62, 0.04, 1)


def _fuente(px):
    try:
        return ImageFont.truetype(os.path.join(ui.recursos(), "fuentes", "Inter-Bold.ttf"), max(6, int(px)))
    except Exception:
        return ImageFont.load_default()


class Visor(Widget):
    def __init__(self, al_terminar=None, al_seleccionar=None, al_estado=None, solo_ver=False, **kw):
        super().__init__(**kw)
        self.al_terminar = al_terminar or (lambda *a: None)
        self.al_seleccionar = al_seleccionar or (lambda *a: None)
        self.al_estado = al_estado or (lambda *a: None)
        self.al_editar = None
        self.al_doble = None
        self.solo_ver = solo_ver
        self.piramide = []
        self.f0 = 1.0               # px del plano original por px de la imagen base del visor
        self.tam_orig = (1, 1)
        self.z, self.ox, self.oy = 1.0, 0.0, 0.0
        self.z_fit = 1.0
        self.herr = "mover"
        self.pts = []
        self.marcas, self.tramos, self.estilos = [], [], {}
        self.notas = True
        self.iman = True
        self._gris = {}
        self.snap, self.snap_tipo = None, None
        self.escala, self.unidad = None, "m"
        self.sel = None
        self.estilo_temp = None
        self.vacios = None
        self._cursor = None
        self._toques = {}
        self._gesto = None
        self._accion = None
        self._tex = None
        self._tex_vista = None
        with self.canvas:
            self._c_fondo = Color(*ui.rgba("suave"))
            self._r_fondo = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 1)
            self._r_img = Rectangle()
        self.bind(pos=self._mover_fondo, size=self._cambio_tam)

    # ---------------------------------------------------------------- imagen
    @property
    def tam(self):
        return self.tam_orig

    def cargar(self, img, escala, unidad="m", tam_original=None):
        """img: imagen del plano (puede venir reducida); tam_original: (ancho, alto) del plano en la base de datos."""
        self._gris = {}
        w0, h0 = tam_original or img.size
        if max(img.size) > LADO_VISTA:
            f = LADO_VISTA / max(img.size)
            img = img.resize((max(1, int(img.width * f)), max(1, int(img.height * f))), Image.BILINEAR)
        self.tam_orig = (w0, h0)
        self.f0 = w0 / img.width
        self.piramide = [img]
        while max(self.piramide[-1].size) > 1200:
            self.piramide.append(self.piramide[-1].reduce(2))
        self.escala, self.unidad = escala, unidad or "m"
        self.pts = []
        self.sel = None
        Clock.schedule_once(lambda *_: self.ajustar(), 0.05)

    def limpiar(self):
        self.piramide = []
        self.marcas, self.tramos = [], []
        self._tex = None
        self._r_img.texture = None
        self._r_img.size = (0, 0)
        self.canvas.after.clear()

    def ajustar(self):
        if not self.piramide or self.width < 20 or self.height < 20:
            return
        w, h = self.tam_orig
        self.z = min(self.width / w, self.height / h) * 0.96
        self.z_fit = self.z
        self.ox = (w - self.width / self.z) / 2
        self.oy = (h - self.height / self.z) / 2
        self.redibujar()

    def _mover_fondo(self, *_):
        self._r_fondo.pos, self._r_fondo.size = self.pos, self.size
        self._colocar_textura()
        self._dibujar_temporal()

    def _cambio_tam(self, *_):
        self._mover_fondo()
        if self.piramide:
            if self.z_fit and abs(self.z - self.z_fit) < 1e-9:
                Clock.schedule_once(lambda *_: self.ajustar(), 0)
            else:
                self.programar()

    # coordenadas: «pantalla» = px dentro del widget, con y hacia abajo (como en la computadora)
    def a_pantalla(self, x, y):
        return ((x - self.ox) * self.z, (y - self.oy) * self.z)

    def a_imagen(self, sx, sy):
        return (self.ox + sx / self.z, self.oy + sy / self.z)

    def _local(self, touch):
        return (touch.x - self.x, self.top - touch.y)

    def _kivy(self, sx, sy):
        return (self.x + sx, self.top - sy)

    def zoom(self, f, sx=None, sy=None):
        if not self.piramide:
            return
        sx = self.width / 2 if sx is None else sx
        sy = self.height / 2 if sy is None else sy
        nz = max(0.01, min(self.z * f, ZOOM_MAX))
        x, y = self.a_imagen(sx, sy)
        self.z = nz
        self.ox = x - sx / nz
        self.oy = y - sy / nz
        self._colocar_textura()
        self._dibujar_temporal()
        self.programar()

    def zoom_centro(self, f):
        self.zoom(f)

    # ---------------------------------------------------------------- dibujo
    def programar(self, demora=0.12):
        Clock.unschedule(self._redibujar_ev)
        Clock.schedule_once(self._redibujar_ev, demora)

    def _redibujar_ev(self, *_):
        self.redibujar()

    def redibujar(self):
        """Compone el plano y las marcas al tamano de la vista (igual que _componer en la computadora)."""
        Clock.unschedule(self._redibujar_ev)
        self._c_fondo.rgba = ui.rgba("suave")
        cw, ch = max(1, int(self.width)), max(1, int(self.height))
        if not self.piramide:
            self._r_img.size = (0, 0)
            self._dibujar_temporal()
            return
        fondo = Image.new("RGBA", (cw, ch), _rgba(ui.col("suave")))
        L = 0
        while L + 1 < len(self.piramide) and self.z * self.f0 * (2 ** (L + 1)) <= 1.0:
            L += 1
        f = self.f0 * (2 ** L)                          # px originales por px de este nivel
        img = self.piramide[L]
        x0, y0 = self.ox / f, self.oy / f
        x1, y1 = x0 + cw / (self.z * f), y0 + ch / (self.z * f)
        bx0, by0 = max(0.0, x0), max(0.0, y0)
        bx1, by1 = min(float(img.width), x1), min(float(img.height), y1)
        if bx1 > bx0 and by1 > by0:
            k = self.z * f
            sx, sy = round((bx0 - x0) * k), round((by0 - y0) * k)
            sw, sh = max(1, round((bx1 - bx0) * k)), max(1, round((by1 - by0) * k))
            metodo = Image.NEAREST if k > 2 else Image.BILINEAR
            parte = img.resize((sw, sh), metodo, box=(bx0, by0, bx1, by1))
            fondo.paste(parte.convert("RGBA"), (sx, sy))
        vis = [m for m in self.marcas if m.get("color")]
        capa = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        if vis:
            dibujar_marcas(capa, vis, self.a_pantalla, self.z, self.estilos, self.sel)
        self._tramos_pil(capa)
        if self.notas:
            self._notas_pil(capa)
        fondo = Image.alpha_composite(fondo, capa)
        self._tex = ui.textura(fondo)
        self._tex_vista = (self.z, self.ox, self.oy, cw, ch)
        self._colocar_textura()
        self._dibujar_temporal()

    def _colocar_textura(self):
        if self._tex is None or self._tex_vista is None:
            return
        z0, ox0, oy0, w0, h0 = self._tex_vista
        k = self.z / z0
        sx, sy = (ox0 - self.ox) * self.z, (oy0 - self.oy) * self.z
        self._r_img.texture = self._tex
        self._r_img.size = (w0 * k, h0 * k)
        self._r_img.pos = (self.x + sx, self.top - sy - h0 * k)

    def _tramos_pil(self, capa):
        if not self.tramos:
            return
        d = ImageDraw.Draw(capa)
        fuente = _fuente(dp(10))
        for t in self.tramos:
            pts = t.get("geom_pts") or []
            if len(pts) < 2:
                continue
            sp_ = [self.a_pantalla(x, y) for x, y in pts]
            for a, b in zip(sp_, sp_[1:]):        # linea punteada
                L = math.dist(a, b)
                n = max(1, int(L / dp(10)))
                for i in range(0, n, 2):
                    p0 = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
                    p1 = (a[0] + (b[0] - a[0]) * min(i + 1, n) / n, a[1] + (b[1] - a[1]) * min(i + 1, n) / n)
                    d.line([p0, p1], fill=(138, 150, 166, 255), width=max(2, int(dp(2))))
            d.text((sp_[0][0] + dp(6), sp_[0][1] - dp(14)), t["nombre"], fill=(95, 107, 122, 255), font=fuente)

    def _notas_pil(self, capa):
        grupos = []
        for m in self.marcas:
            if not m.get("color") or not m.get("nota_txt"):
                continue
            ax, ay = self.a_pantalla(*ancla(m))
            for g in grupos:
                if g["item"] == m["item"] and math.dist((g["x"], g["y"]), (ax, ay)) < dp(18):
                    g["notas"].append(m)
                    break
            else:
                grupos.append({"x": ax, "y": ay, "item": m["item"], "notas": [m]})
        if not grupos:
            return
        cw, ch = capa.size
        # pequena con el plano completo, mas grande al acercar (tope)
        r = max(self.z / (self.z_fit or self.z), 1e-6)
        px = max(7, min(15, round(7 * r ** 0.5))) * dp(1)
        fuente = _fuente(px)
        paso = px + dp(6)
        borde = 1 if px < dp(10) else 2
        d = ImageDraw.Draw(capa)
        for g in grupos:
            if not (-dp(400) < g["x"] < cw + dp(50) and -dp(50) < g["y"] < ch + dp(400)):
                continue
            y = g["y"] - paso * 0.7 - paso * (len(g["notas"]) - 1)
            for m in g["notas"]:
                x = g["x"] + 4 + px * 0.4
                bx0, by0, bx1, by1 = d.textbbox((x, y), m["nota_txt"], font=fuente, anchor="lm")
                d.rectangle([bx0 - 3, by0 - 2, bx1 + 3, by1 + 2], fill=(255, 255, 255, 255),
                            outline=_rgba(m["color"]), width=int(borde))
                d.text((x, y), m["nota_txt"], font=fuente, fill=(30, 39, 48, 255), anchor="lm")
                y += paso

    # ---------------------------------------------------------------- capa temporal (Kivy)
    def _puntos_vista(self):
        if not self.pts:
            return []
        if self.herr == "rect" and self._cursor:
            return rectangulo(self.pts[0], self._cursor)
        if self.herr == "circulo" and self._cursor:
            return elipse(self.pts[0], self._cursor, 48)
        if self.herr in ("linea", "area", "area_libre", "vacio", "calibrar") and self._cursor:
            return list(self.pts) + [self._cursor]
        return list(self.pts)

    def _poligono(self, pts_kivy, rgba):
        if len(pts_kivy) < 3:
            return
        try:
            tess = Tesselator()
            tess.add_contour([c for p in pts_kivy for c in p])
            if tess.tesselate():
                Color(*rgba)
                for vertices, indices in tess.meshes:
                    Mesh(vertices=vertices, indices=indices, mode="triangle_fan")
        except Exception:
            pass

    def _dibujar_temporal(self):
        cv = self.canvas.after
        cv.clear()
        with cv:
            if self.vacios:
                v = self.vacios
                ext = [self._kivy(*self.a_pantalla(x, y)) for x, y in v["ext"]]
                self._poligono(ext, (AZUL[0], AZUL[1], AZUL[2], 0.22))
                Color(*AZUL)
                Line(points=[c for p in ext for c in p], close=True, width=dp(1.4))
                for h in v["huecos"]:
                    hp = [self._kivy(*self.a_pantalla(x, y)) for x, y in h]
                    self._poligono(hp, (1, 1, 1, 0.85))
                    Color(0.88, 0.11, 0.28, 1)
                    Line(points=[c for p in hp for c in p], close=True, width=1, dash_length=6, dash_offset=3)
            if self.snap:
                x, y = self._kivy(*self.a_pantalla(*self.snap))
                Color(*(AMBAR if self.snap_tipo in ("linea", "esquina") else AZUL))
                r = dp(9)
                if self.snap_tipo == "linea":
                    Line(rectangle=(x - r / 2, y - r / 2, r, r), width=dp(1.4))
                else:
                    Line(circle=(x, y, r), width=dp(1.4))
                    if self.snap_tipo == "esquina":
                        Line(points=[x - r * 1.4, y, x + r * 1.4, y], width=1)
                        Line(points=[x, y - r * 1.4, x, y + r * 1.4], width=1)
            pts = self._puntos_vista()
            if pts:
                kp = [self._kivy(*self.a_pantalla(x, y)) for x, y in pts]
                col_ = AMBAR if self.herr == "calibrar" else AZUL
                tipo = self._tipo()
                if tipo == "area" and len(kp) >= 3:
                    self._poligono(kp, (col_[0], col_[1], col_[2], 0.25))
                    Color(*col_)
                    Line(points=[c for p in kp for c in p], close=True, width=dp(1.4))
                elif len(kp) >= 2:
                    g = dp(1.6)
                    if self.herr != "calibrar" and self.estilo_temp:
                        g = max(dp(1.2), min(300, float(self.estilo_temp["linea"].get("grosor", 6)) * self.z / 2))
                    Color(col_[0], col_[1], col_[2], 0.9)
                    if self.herr == "calibrar":
                        Line(points=[c for p in kp for c in p], width=1, dash_length=8, dash_offset=4)
                        Line(points=[c for p in kp for c in p], width=dp(1.2))
                    else:
                        Line(points=[c for p in kp for c in p], width=g, cap="round", joint="round")
                if self.herr in ("linea", "area", "area_libre", "vacio", "calibrar") and len(self.pts) <= 200:
                    for x, y in [self._kivy(*self.a_pantalla(a, b)) for a, b in self.pts]:
                        Color(1, 1, 1, 1)
                        Ellipse(pos=(x - dp(6), y - dp(6)), size=(dp(12), dp(12)))
                        Color(*col_)
                        Line(circle=(x, y, dp(6)), width=dp(1.4))
            if self.herr == "editar":
                m = self._marca_sel()
                for x, y in self._agarres(m):
                    kx, ky = self._kivy(*self.a_pantalla(x, y))
                    Color(1, 1, 1, 1)
                    Rectangle(pos=(kx - dp(8), ky - dp(8)), size=(dp(16), dp(16)))
                    Color(*AZUL)
                    Line(rectangle=(kx - dp(8), ky - dp(8), dp(16), dp(16)), width=dp(1.4))

    # ---------------------------------------------------------------- herramientas
    def _tipo(self):
        return {"linea": "linea", "linea_libre": "linea", "rect": "area", "circulo": "area", "area": "area",
                "vacio": "area", "area_libre": "area", "punto": "punto", "calibrar": "linea"}.get(self.herr, "")

    def usar(self, herr):
        self.herr = herr
        self.pts = []
        self._cursor = None
        self.snap = None
        self._dibujar_temporal()
        self._informar()

    def cancelar(self):
        if self.vacios and not self.pts:
            return self.terminar_vacios(False)
        self.pts = []
        self._cursor = None
        self._dibujar_temporal()
        self._informar()

    def deshacer_punto(self):
        if self.herr == "vacio" and not self.pts:
            return self.deshacer_vacio()
        if self.pts and self.herr in ("linea", "area", "area_libre", "vacio"):
            self.pts.pop()
            self._cursor = None
            self._dibujar_temporal()
            self._informar()

    def terminar(self):
        if self.herr == "vacio":
            if len(self.pts) >= 3:
                self._cerrar_vacio()
            elif not self.pts:
                self.terminar_vacios(True)
            return
        if self.herr == "linea" and len(self.pts) >= 2:
            pts, self.pts = self.pts, []
            self._cursor = None
            self._dibujar_temporal()
            self.al_terminar("linea", pts)
        elif self.herr in ("area", "area_libre") and len(self.pts) >= 3:
            pts, self.pts = self.pts, []
            self._cursor = None
            self._dibujar_temporal()
            self.al_terminar("area", pts)

    # ---- vacios
    def iniciar_vacios(self, ext, huecos, fin):
        self.vacios = {"ext": [tuple(q) for q in ext], "huecos": [list(map(tuple, h)) for h in huecos or []],
                       "fin": fin, "herr_ant": self.herr}
        self.herr = "vacio"
        self.pts = []
        self._dibujar_temporal()
        self._informar()

    def _cerrar_vacio(self):
        pts = self.pts
        self.pts = []
        self._cursor = None
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

    # ---- marcas y seleccion
    def poner_marcas(self, marcas, estilos, tramos=()):
        self.marcas = marcas
        self.estilos = estilos
        self.tramos = list(tramos)
        self.redibujar()

    def _marca_sel(self):
        return next((m for m in self.marcas if m["id"] == self.sel and m.get("color")), None)

    def _agarres(self, m):
        if not m or m["tipo"] == "punto" or len(m["geom"]) > 60:
            return []
        return list(m["geom"])

    def _toca_marca(self, m, sx, sy, tol_px=None):
        tol_px = tol_px or dp(14)
        p = self.a_imagen(sx, sy)
        est = self.estilos.get(m["item"]) or core.Proyecto.ESTILO_BASE
        pts = m["geom"]
        if m["tipo"] == "linea" and len(pts) >= 2:
            tol = max(float(est["linea"].get("grosor", 6)) / 2, tol_px / self.z)
            return min(_dist_seg(p, a, b) for a, b in zip(pts, pts[1:])) <= tol
        if m["tipo"] == "area" and len(pts) >= 3:
            return (dentro(p, pts) and not any(dentro(p, h) for h in m.get("huecos") or [])) or \
                min(_dist_seg(p, a, b) for a, b in zip(pts, pts[1:] + pts[:1])) <= tol_px / self.z
        if pts:
            return math.dist(p, pts[0]) <= max(float(est["punto"].get("tamano", 16)) / 2, tol_px) / self.z
        return False

    def _seleccionar(self, sx, sy):
        mejor = None
        for m in reversed(self.marcas):
            if m.get("color") and self._toca_marca(m, sx, sy):
                mejor = m
                break
        self._marcar_sel(mejor["id"] if mejor else None)

    def _marcar_sel(self, mid):
        if mid != self.sel:
            self.sel = mid
            self.redibujar()
        self.al_seleccionar(mid)

    # ---- iman
    def _imantar(self, sx, sy):
        self.snap_tipo = None
        if self.herr == "linea_libre" or not self.iman:
            return None
        radio = dp(16)
        mejor, dmin = None, radio
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
        r = self._iman_plano(sx, sy, radio)
        if r:
            self.snap_tipo, mejor = r
        return mejor

    def _nivel_gris(self):
        L = 0
        while L + 1 < len(self.piramide) and self.z * self.f0 * (2 ** (L + 1)) <= 1.0:
            L += 1
        if L not in self._gris:
            g = self.piramide[L].convert("L")
            self._gris[L] = (g, g.load(), g.size)
        return L

    def _iman_plano(self, sx, sy, radio):
        """Esquina o cruce de lineas del dibujo del plano (prioridad) o la linea mas cercana (como en la computadora)."""
        if not self.piramide:
            return None
        L = self._nivel_gris()
        g, px, (w, h) = self._gris[L]
        f = self.f0 * (2 ** L)
        ix, iy = self.a_imagen(sx, sy)
        cx, cy = ix / f, iy / f
        esc = self.z * f
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
            for (a1, a2, dx, dy) in ((u, l, 1, 1), (u, r_, -1, 1), (d, l, 1, -1), (d, r_, -1, -1)):
                if not a1 and not a2 and tiene(x, y, dx, 0) and tiene(x, y, 0, dy):
                    return True
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

    def _punto_en(self, sx, sy, con_iman=True):
        self.snap = self._imantar(sx, sy) if con_iman else None
        p = self.snap or self.a_imagen(sx, sy)
        return (round(p[0], 2), round(p[1], 2))

    # ---------------------------------------------------------------- toques
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if touch.is_mouse_scrolling:
            if self.piramide:
                sx, sy = self._local(touch)
                self.zoom(1.2 if touch.button == "scrolldown" else 1 / 1.2, sx, sy)
            return True
        touch.grab(self)
        self._toques[touch.uid] = touch
        if len(self._toques) >= 2:
            self._empezar_gesto()
            return True
        if not self.piramide:
            return True
        sx, sy = self._local(touch)
        self._accion = {"ini": (sx, sy), "movio": False, "tipo": None, "doble": touch.is_double_tap,
                        "vista": (self.ox, self.oy)}
        h = self.herr
        if self.solo_ver or h == "mover":
            self._accion["tipo"] = "pan"
        elif h == "editar":
            self._editar_down(sx, sy)
        elif h in ("linea_libre", "rect", "circulo"):
            self._accion["tipo"] = "trazo"
        elif h == "area_libre":
            self._accion["tipo"] = "libre_o_toque"
        else:
            self._accion["tipo"] = "toque"
            if h != "punto":
                self.snap = self._imantar(sx, sy)
                self._cursor = self.snap or self.a_imagen(sx, sy)
                self._dibujar_temporal()
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        if self._gesto is not None:
            self._mover_gesto()
            return True
        a = self._accion
        if not a:
            return True
        sx, sy = self._local(touch)
        if math.hypot(sx - a["ini"][0], sy - a["ini"][1]) > dp(8):
            a["movio"] = True
        t = a["tipo"]
        if t == "pan":
            ox0, oy0 = a["vista"]
            self.ox = ox0 - (sx - a["ini"][0]) / self.z
            self.oy = oy0 - (sy - a["ini"][1]) / self.z
            self._colocar_textura()
            self._dibujar_temporal()
        elif t == "editar":
            self._editar_move(sx, sy)
        elif t == "trazo":
            if not self.pts:
                if not a["movio"]:
                    return True
                self.pts = [self._punto_en(*a["ini"])]
            p = self._punto_en(sx, sy, con_iman=self.herr != "linea_libre")
            if self.herr == "linea_libre":
                ux, uy = self.a_pantalla(*self.pts[-1])
                if math.hypot(sx - ux, sy - uy) >= dp(3):
                    self.pts.append(p)
            self._cursor = p
            self._dibujar_temporal()
            self._informar()
        elif t == "libre_o_toque":
            if a["movio"]:
                if not a.get("libre"):
                    a["libre"] = True
                    self.pts.append(self._punto_en(*a["ini"]))
                ux, uy = self.a_pantalla(*self.pts[-1])
                if math.hypot(sx - ux, sy - uy) >= dp(3):
                    q = self.a_imagen(sx, sy)
                    self.pts.append((round(q[0], 2), round(q[1], 2)))
                    self._cursor = q
                    self._dibujar_temporal()
                    self._informar()
        elif t == "toque":
            if self.herr != "punto":
                self.snap = self._imantar(sx, sy)
                self._cursor = self.snap or self.a_imagen(sx, sy)
                self._dibujar_temporal()
                self._informar()
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        self._toques.pop(touch.uid, None)
        if self._gesto is not None:
            if not self._toques:
                self._gesto = None
                self.programar(0.05)
            else:
                self._empezar_gesto()
            return True
        a, self._accion = self._accion, None
        if not a:
            return True
        sx, sy = self._local(touch)
        t = a["tipo"]
        if t == "pan":
            if not a["movio"]:
                self._seleccionar(sx, sy)
            else:
                self.programar(0.05)
        elif t == "editar":
            self._editar_up(a)
        elif t == "trazo":
            self._fin_trazo(sx, sy)
        elif t == "libre_o_toque":
            if not a.get("libre"):
                self._toque(sx, sy, a["doble"])
        elif t == "toque":
            if a["movio"] and self.herr == "punto":
                return True
            self._toque(sx, sy, a["doble"])
        return True

    def _toque(self, sx, sy, doble):
        """Un toque de herramienta (agrega un punto, cierra un area o marca un punto)."""
        h = self.herr
        if h in ("linea", "area", "area_libre", "vacio") and doble and len(self.pts) >= 2:
            self.terminar()
            return
        p = self._punto_en(sx, sy, con_iman=h != "punto" or self.iman)
        self._cursor = None
        if h == "punto":
            self.snap = None
            self._dibujar_temporal()
            self.al_terminar("punto", [p])
            return
        if h in ("area", "area_libre", "vacio") and len(self.pts) >= 3:
            fx, fy = self.a_pantalla(*self.pts[0])
            if math.hypot(sx - fx, sy - fy) <= dp(18):
                self.terminar()
                return
        self.pts.append(p)
        if h == "calibrar" and len(self.pts) == 2:
            pts = self.pts
            self.pts = []
            self._dibujar_temporal()
            self.al_terminar("calibrar", pts)
            return
        self._dibujar_temporal()
        self._informar()

    def _fin_trazo(self, sx, sy):
        if not self.pts:
            return
        p = self._punto_en(sx, sy, con_iman=self.herr != "linea_libre")
        p0 = self.pts[0]
        if self.herr == "rect":
            pts, tipo = rectangulo(p0, p), "area"
        elif self.herr == "circulo":
            pts, tipo = elipse(p0, p), "area"
        else:
            pts = simplificar(self.pts + [p], 1.5 / self.z)
            tipo = "linea"
        self.pts = []
        self._cursor = None
        self.snap = None
        self._dibujar_temporal()
        if (tipo == "linea" and largo_px(pts) * self.z > 4) or (tipo == "area" and area_px(pts) * self.z * self.z > 30):
            self.al_terminar(tipo, [(round(x, 2), round(y, 2)) for x, y in pts])

    # ---- dos dedos
    def _empezar_gesto(self):
        ts = list(self._toques.values())[:2]
        if self._accion and self._accion.get("tipo") in ("trazo", "libre_o_toque") and self.herr != "area_libre":
            self.pts = []
        self._accion = None
        self._cursor = None
        if len(ts) < 2:
            self._gesto = None
            return
        (x1, y1), (x2, y2) = self._local(ts[0]), self._local(ts[1])
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        self._gesto = {"d": max(1.0, math.hypot(x2 - x1, y2 - y1)), "c": (cx, cy), "z": self.z,
                       "img": self.a_imagen(cx, cy)}

    def _mover_gesto(self):
        ts = list(self._toques.values())[:2]
        if len(ts) < 2 or not self.piramide:
            return
        g = self._gesto
        (x1, y1), (x2, y2) = self._local(ts[0]), self._local(ts[1])
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        d = max(1.0, math.hypot(x2 - x1, y2 - y1))
        nz = max(0.01, min(g["z"] * d / g["d"], ZOOM_MAX))
        ix, iy = g["img"]
        self.z = nz
        self.ox = ix - cx / nz
        self.oy = iy - cy / nz
        self._colocar_textura()
        self._dibujar_temporal()

    # ---- editar
    def _editar_down(self, sx, sy):
        a = self._accion
        a["tipo"] = "editar"
        m = self._marca_sel()
        if m:
            for k, (x, y) in enumerate(self._agarres(m)):
                px, py = self.a_pantalla(x, y)
                if abs(px - sx) <= dp(14) and abs(py - sy) <= dp(14):
                    a["ed"] = self._nuevo_edit(m, k, sx, sy)
                    return
            if self._toca_marca(m, sx, sy):
                a["ed"] = self._nuevo_edit(m, None, sx, sy)
                return
        a["ed"] = None

    def _nuevo_edit(self, m, k, sx, sy):
        return {"m": m, "k": k, "orig": [tuple(q) for q in m["geom"]], "ini": self.a_imagen(sx, sy),
                "orig_h": [[tuple(q) for q in h] for h in (m.get("huecos") or [])]}

    def _editar_move(self, sx, sy):
        a = self._accion
        ed = a.get("ed")
        if not ed:
            if a["movio"]:
                ox0, oy0 = a["vista"]
                self.ox = ox0 - (sx - a["ini"][0]) / self.z
                self.oy = oy0 - (sy - a["ini"][1]) / self.z
                self._colocar_textura()
                self._dibujar_temporal()
            return
        if not a["movio"]:
            return
        x, y = self.a_imagen(sx, sy)
        if ed["k"] is not None:
            p = self._imantar_editar(sx, sy, ed["m"]) or (x, y)
            g = list(ed["orig"])
            g[ed["k"]] = (round(p[0], 2), round(p[1], 2))
        else:
            dx, dy = x - ed["ini"][0], y - ed["ini"][1]
            g = [(round(q + dx, 2), round(r + dy, 2)) for q, r in ed["orig"]]
            if ed["orig_h"]:
                ed["m"]["huecos"] = [[(round(q + dx, 2), round(r + dy, 2)) for q, r in h] for h in ed["orig_h"]]
                ed["huecos_movidos"] = True
        ed["m"]["geom"] = g
        ed["movido"] = True
        self.programar(0.03)

    def _imantar_editar(self, sx, sy, propia):
        mejor, dmin = None, dp(16)
        for m in self.marcas:
            if m is propia or not m.get("color") or len(m["geom"]) > 100:
                continue
            for x, y in m["geom"]:
                px, py = self.a_pantalla(x, y)
                d = math.hypot(px - sx, py - sy)
                if d < dmin:
                    mejor, dmin = (x, y), d
        return mejor

    def _editar_up(self, a):
        ed = a.get("ed")
        if not a["movio"]:
            if a["doble"] and self.sel and self.al_doble:
                Clock.schedule_once(lambda *_: self.al_doble(), 0.05)
                return
            self._seleccionar(*a["ini"])
            self._dibujar_temporal()
            return
        if not ed:
            self.programar(0.05)
            return
        if ed.get("movido") and self.al_editar:
            h = [[list(q) for q in hh] for hh in ed["m"]["huecos"]] if ed.get("huecos_movidos") else None

            def deshacer():
                ed["m"]["geom"] = ed["orig"]
                ed["m"]["huecos"] = ed["orig_h"]
                self.redibujar()
            self.al_editar(ed["m"]["id"], [list(q) for q in ed["m"]["geom"]], h, deshacer)

    # ---------------------------------------------------------------- textos de ayuda
    def _informar(self):
        h = self.herr
        if h == "mover":
            self.al_estado("Un dedo mueve el plano · dos dedos acercan o alejan · tocá una marca para verla.")
            return
        if h == "editar":
            self.al_estado("Editar: tocá una marca y arrastrala para moverla · arrastrá los cuadritos para cambiar la "
                           "forma · doble toque para sus datos · «Borrar marca» para borrarla.")
            return
        if h == "punto":
            self.al_estado("Tocá para marcar una pieza (cuenta 1).")
            return
        if h == "vacio" and self.vacios:
            v = self.vacios
            neto = area_neta_px(v["ext"], v["huecos"])
            txt = f"{neto * self.escala ** 2:,.2f} {self.unidad}²" if self.escala else f"{neto:,.0f} px²"
            self.al_estado(f"Vacíos: {len(v['huecos'])} · área neta {txt} · dibujá cada vacío punto por punto dentro del "
                           "área (tocar el primer punto lo cierra) · «Listo» para terminar.")
            return
        pts = self._puntos_vista()
        if h == "calibrar":
            if len(pts) == 2:
                self.al_estado(f"Distancia en el plano: {largo_px(pts):,.1f} px · tocá el segundo punto.")
            else:
                self.al_estado("Calibrar: tocá dos puntos de una medida conocida (por ejemplo una cota).")
            return
        if self._tipo() == "linea":
            v = largo_px(pts)
            txt = f"{v * self.escala:,.2f} {self.unidad}" if self.escala else f"{v:,.0f} px (plano sin calibrar)"
            extra = ("tocá punto por punto · doble toque o «Terminar» para cerrar" if h == "linea"
                     else "dibujá arrastrando el dedo")
        else:
            v = area_px(pts)
            txt = f"{v * self.escala ** 2:,.2f} {self.unidad}²" if self.escala else f"{v:,.0f} px² (sin calibrar)"
            extra = ("tocá punto por punto (o arrastrá para un tramo a mano alzada) · tocar el primer punto, doble toque "
                     "o «Terminar» para cerrar" if h == "area_libre" else
                     "tocá punto por punto · tocar el primer punto o «Terminar» para cerrar" if h == "area" else
                     "dibujá arrastrando el dedo")
            if self.iman and self.snap_tipo:
                extra = {"esquina": "imán: esquina", "linea": "imán: línea", "vertice": "imán: marca"}[self.snap_tipo] + \
                        " · " + extra
        self.al_estado(f"{txt} · {extra}.")


# =========================================================================
#  Elegir color
# =========================================================================
PALETA = ["#16A34A", "#22C55E", "#0EA5E9", "#2563EB", "#4E79A7", "#7C3AED", "#DB2777", "#DC2626", "#EA580C", "#F59E0B",
          "#CA8A04", "#65A30D", "#0D9488", "#475569", "#1E2730", "#9CA3AF"]


def elegir_color(inicial, titulo, al_elegir):
    from kivy.uix.gridlayout import GridLayout
    d = ui.Dialogo(titulo, ancho=520)
    g = GridLayout(cols=8, spacing=dp(8), size_hint_y=None)
    g.bind(minimum_height=g.setter("height"))
    e = ui.Campo(inicial or "", pista="#RRGGBB")
    for c in PALETA:
        b = ui.Boton("", alto=48)
        b._c_normal = ui.rgba(c)
        b._c_toque = ui.rgba(c, 0.8)
        b._estado()
        b.bind(on_release=lambda w, c=c: setattr(e, "text", c))
        g.add_widget(b)
    d.cuerpo.add_widget(g)
    d.cuerpo.add_widget(ui.Etiqueta("Color (código)", 13, True))
    d.cuerpo.add_widget(e)

    def fin(k):
        if k == 0:
            d.dismiss()
            return
        t = e.text.strip()
        if not t.startswith("#"):
            t = "#" + t
        try:
            ui.rgba(t)
            if len(t) != 7:
                raise ValueError
        except Exception:
            ui.aviso("Elegí un color de la paleta o escribí uno como #16A34A.")
            return
        d.dismiss()
        al_elegir(t.upper())
    d.botones(["Cancelar", "Usar color"], 1, fin)
    d.open()
