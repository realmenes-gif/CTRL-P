"""
Ctrl-P Android - Datos fijos
============================
Cantidad contractual por ubicacion, ubicacion fija, y "mas detalles" de la actividad:
desglose por equipos, tramos y pago por hitos (con tipos, cada uno con sus hitos y su cantidad por nivel).
Mismas reglas que en la computadora (las valida ctrlp_core).
"""

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget

import ctrlp_core as core
import ui_k as ui
from paginas import Pagina
from tabla import ArbolPartidas
from ui_k import (Boton, Campo, Casilla, Columna, Desplazable, Espacio, Etiqueta, Fila, Menu, Segmentado, Tarjeta,
                  fmt, leer_num, rgba, txt_num)

SIN_EQ = "(sin equipo)"


class PaginaDatosFijos(Pagina):
    clave = "datos"
    titulo = "Datos fijos"
    subtitulo = ("Cantidad contractual de cada actividad por ubicación. Es opcional: donde no se asigne, el avance se "
                 "mide contra el total de la partida.")

    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.cab_der.add_widget(Boton("◀ Partidas", ancho=120, al_tocar=self._alternar_arbol))
        self.seg = Segmentado(["Carga inicial", "Editar datos fijos"], "Carga inicial", ancho=330,
                              al_cambiar=lambda _: self.mostrar())
        self.cab_der.add_widget(self.seg)
        caja = BoxLayout(orientation="horizontal", spacing=dp(16))
        self.arbol = ArbolPartidas(app, self.elegir, "Estado", size_hint_x=None, width=dp(340))
        caja.add_widget(self.arbol)
        self.col = Columna(espacio=12)
        self.desp = Desplazable(self.col)
        caja.add_widget(self.desp)
        self.caja = caja
        self.cuerpo.add_widget(caja)
        b = self.barra_inferior()
        self.l_estado = Etiqueta("", 13, color="texto2")
        b.add_widget(self.l_estado)
        b.add_widget(Boton("Sugerir ubicaciones…", ancho=210, al_tocar=self.sugerir))
        b.add_widget(Boton("Guardar", primario=True, ancho=140, al_tocar=self.guardar))
        self.it = None
        self._limpiar_estado()
        self.arbol_visible = True
        self._ver_todas = False
        self._visibles = None

    def _limpiar_estado(self):
        self.vars, self.vars_tipo = {}, {}
        self.hitos_ed, self.tramos_ed, self.equipos_ed = [], {}, {}
        self.hitos_orig, self.tramos_orig, self.equipos_orig = [], {}, {}

    def _alternar_arbol(self):
        self.arbol_visible = not self.arbol_visible
        if self.arbol_visible:
            self.caja.add_widget(self.arbol, index=len(self.caja.children))
        else:
            self.caja.remove_widget(self.arbol)
        self.cab_der.children[-1].text = "◀ Partidas" if self.arbol_visible else "▶ Partidas"

    @property
    def editar(self):
        return self.seg.valor == "Editar datos fijos"

    def al_cambiar_proyecto(self):
        self.it = None
        self.arbol.marcas = {}
        self._limpiar_estado()

    def refrescar(self):
        if not self.p:
            return
        self._marcas()
        self.arbol.cargar()
        if self.it:
            self.arbol.ver(self.it["id"])
        self.mostrar()

    def _marcas(self):
        cont = self.p.todo_contractual()
        desc = {it["id"] for it, _ in self.p.descuadres()}
        self.arbol.marcas = {}
        for it in self.p.partidas():
            if it["id"] in desc:
                self.arbol.marcas[it["id"]] = "●"
            elif it["id"] in cont:
                self.arbol.marcas[it["id"]] = "✓"

    def elegir(self, it):
        def seguir():
            self.it = it
            self._ver_todas = False
            self.mostrar()
            if self.arbol_visible and self.desp.width < dp(700):
                self._alternar_arbol()
        self.antes_de_salir(seguir)

    def antes_de_salir(self, seguir, al_cancelar=None):
        if self.it and self._cambios():
            def r(k):
                if k == 2:
                    if self.guardar():
                        seguir()
                elif k == 1:
                    self._limpiar_estado()
                    seguir()
                elif al_cancelar:
                    al_cancelar()
            ui.opciones("Cambios sin guardar", "Hay datos fijos sin guardar en esta partida.",
                        ["Cancelar", "Descartar", "Guardar"], r, primario=2)
            return
        seguir()

    def guardar_pendiente(self):
        if self.it and self._cambios():
            return self.guardar()
        return True

    def _cambios(self):
        if self._hitos_cambiados() or self._lista_cambiada(self.tramos_ed, self.tramos_orig, True) or \
                self._lista_cambiada(self.equipos_ed, self.equipos_orig):
            return True
        for txt, orig in [(x[0], x[1]) for x in self.vars.values()] + [(x[0], x[1]) for x in self.vars_tipo.values()]:
            n = leer_num(txt)
            if n == "error":
                return True
            if (n is None) != (orig is None) or (n is not None and abs(n - orig) > 1e-9):
                return True
        fija_txt = getattr(self, "m_fija", None) and self.m_fija.valor
        if fija_txt is not None and self.it:
            nueva = next((u["nivel"] for u in self.p.ubicaciones() if u["etiqueta"] == fija_txt), None)
            if nueva != self.p.ubic_fija_de(self.it["id"]):
                return True
        return False

    def _alternar_todas(self, si):
        """Partida repartida completa: ver solo las ubicaciones asignadas o todas (lo escrito se conserva)."""
        def seguir():
            self._ver_todas = si
            self._redibujar()
        if not si:
            self.antes_de_salir(seguir)
        else:
            seguir()

    # ---------------------------------------------------------------- armado
    def _redibujar(self):
        y = self.desp.scroll_y
        self.mostrar(conservar=True)
        Clock.schedule_once(lambda *_: setattr(self.desp, "scroll_y", y), 0)

    def mostrar(self, conservar=False):
        self.col.clear_widgets()
        if not conservar:
            self._limpiar_estado()
        if not self.p:
            return
        if not self.p.edificios():
            self.col.add_widget(Etiqueta("Primero creá las ubicaciones (edificios y áreas).", 15, color="texto2"))
            return
        if not self.it:
            self.col.add_widget(Etiqueta("Elegí una partida en la lista de la izquierda.", 15, color="texto2"))
            self.l_estado.text = f"{len(self.p.descuadres())} actividades con contractual descuadrado"
            return
        p = self.p
        it = p.item(self.it["id"])
        self.it = it
        bloqueado = p.solo_agregar
        cont = p.contractual_de(it["id"])
        fija = p.ubic_fija_de(it["id"])
        asign = sum(cont.values())
        t = Tarjeta(relleno=16, espacio=6)
        f1 = Fila(alto=30)
        f1.add_widget(Etiqueta(f"{it['codigo']} · {it['unidad']} · {p.get_meta('moneda', 'US$')} {fmt(it['pu'])}", 13,
                               True, color="acento"))
        t.add_widget(f1)
        t.add_widget(Etiqueta(it["descripcion"], 14, True))
        dif = (it["cantidad"] or 0) - asign
        f2 = Fila(alto=50, espacio=20)
        for txt, val, punto in (("Cantidad de la partida", it["cantidad"], False), ("Asignado", asign, False),
                                ("Sin asignar", dif, bool(cont) and abs(dif) > 0.005)):
            c = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(190))
            c.add_widget(Etiqueta(txt, 11, color="texto2"))
            c.add_widget(Etiqueta(("● " if punto else "") + fmt(val), 17, True))
            f2.add_widget(c)
        f2.add_widget(Widget())
        t.add_widget(f2)
        opciones = ["Ninguna (por ubicación)"] + [u["etiqueta"] for u in p.ubicaciones()]
        self.m_fija = Menu(opciones, p.etiqueta_ubicacion(fija) if fija else opciones[0], ancho=300)
        self.m_fija.disabled = bloqueado or (not self.editar and bool(fija))
        t.fila("Ubicación fija", self.m_fija,
               "Para presupuestos que ya vienen separados: la partida pertenece a una sola ubicación.")
        self.col.add_widget(t)
        # partida repartida completa: solo las ubicaciones con cantidad asignada (menos scroll)
        filtro = None if fija else p.ubicaciones_registro(it["id"])
        self._visibles = None if self._ver_todas else filtro
        if fija:
            self.col.add_widget(Etiqueta(f"Esta partida pertenece solo a {p.etiqueta_ubicacion(fija)}; su contractual es "
                                         "la cantidad de la partida.", 13, color="texto2"))
        self._mas_detalles(it, bloqueado, fija)
        if not fija:
            if filtro is not None:
                fv = Fila(alto=44)
                if self._visibles is not None:
                    ocultas = sum(1 for e in p.edificios() for n in p.niveles_de(e["id"]) if n["id"] not in self._visibles)
                    fv.add_widget(Etiqueta(f"La cantidad ya está repartida completa: solo se ven las ubicaciones "
                                           f"asignadas ({ocultas} ocultas).", 12, color="texto2"))
                    fv.add_widget(Boton("Mostrar todas", ancho=150, alto=36, tam=13,
                                        al_tocar=lambda: self._alternar_todas(True)))
                else:
                    fv.add_widget(Etiqueta("Mostrando todas las ubicaciones.", 12, color="texto2"))
                    fv.add_widget(Boton("Solo las asignadas", ancho=170, alto=36, tam=13,
                                        al_tocar=lambda: self._alternar_todas(False)))
                self.col.add_widget(fv)
            self._contractuales(it, cont, bloqueado)
        if bloqueado:
            self.l_estado.text = "Archivo de «Solo agregar avance»: los datos fijos no se pueden modificar."
        elif not self.editar:
            self.l_estado.text = "Carga inicial: las cantidades ya guardadas solo se modifican en «Editar datos fijos»."
        else:
            self.l_estado.text = "Editar datos fijos: cada cambio queda en el historial."

    # ---------------------------------------------------------------- contractual por ubicacion
    def _contractuales(self, it, cont, bloqueado):
        tipos = [(tp, hs[0]["id"]) for tp, hs in self.p.tipos_hito(it["id"]) if tp]
        cant_t = self.p.cant_tipos_de(it["id"]) if tipos else {}
        grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        n_ed = 0
        for e in self.p.edificios():
            niv = [n for n in self.p.niveles_de(e["id"]) if self._visibles is None or n["id"] in self._visibles]
            if not niv:
                continue
            n_ed += 1
            tt = Tarjeta(relleno=14, espacio=6)
            s = sum(cont.get(n["id"], 0) for n in niv if n["id"] in cont)
            hay = any(n["id"] in cont for n in niv)
            cab = Fila(alto=34)
            cab.add_widget(Etiqueta(e["nombre"], 16, True))
            cab.add_widget(Etiqueta(fmt(s) if hay else "Sin asignar", 15, True, color="texto" if hay else "texto2",
                                    alinear="right"))
            tt.add_widget(cab)
            for n in niv:
                orig = cont.get(n["id"])
                if n["id"] not in self.vars:
                    self.vars[n["id"]] = [txt_num(orig), orig]
                st = self.vars[n["id"]]
                f = Fila(alto=46)
                f.add_widget(Etiqueta("Área sin nivel" if e["es_area"] else n["nombre"], 14, bool(tipos)))
                en = Campo(st[0], pista="Sin asignar", ancho=150, alinear="right", numerico=True)
                en.bind(text=lambda w, t, st=st: st.__setitem__(0, t))
                fijo_n = bloqueado or (not self.editar and orig is not None)
                en.disabled = fijo_n
                f.add_widget(en)
                tt.add_widget(f)
                if tipos:
                    campos_t = []
                    for tp, hid0 in tipos:
                        o_t = cant_t.get((n["id"], tp))
                        k = (n["id"], hid0)
                        if k not in self.vars_tipo:
                            self.vars_tipo[k] = [txt_num(o_t), o_t, tp]
                        stt = self.vars_tipo[k]
                        ft = Fila(alto=42)
                        ft.add_widget(Espacio(1, ancho=18))
                        ft.add_widget(Etiqueta(tp, 13, color="texto2"))
                        et = Campo(stt[0], pista="Sin asignar", ancho=130, alinear="right", numerico=True, alto=40)
                        et.disabled = bloqueado or (not self.editar and o_t is not None)
                        et.bind(text=lambda w, t, stt=stt: stt.__setitem__(0, t))
                        campos_t.append(et)
                        ft.add_widget(et)
                        tt.add_widget(ft)

                    def sumar(*_, en=en, campos_t=campos_t, fijo_n=fijo_n):
                        nums = [leer_num(x.text) for x in campos_t]
                        if any(isinstance(x, float) for x in nums):
                            tot = sum(x for x in nums if isinstance(x, float))
                            en.text = txt_num(round(tot, 6))
                            en.disabled = True
                        else:
                            en.disabled = fijo_n
                    for x in campos_t:
                        x.bind(text=sumar)
                    sumar()
            grid.add_widget(tt)
        if n_ed % 2:
            grid.add_widget(Widget(size_hint_y=None, height=0))
        self.col.add_widget(grid)

    # ---------------------------------------------------------------- mas detalles
    def _mas_detalles(self, it, bloqueado, fija):
        det = self.p.detalle_de(it["id"])
        t = Tarjeta(relleno=16, espacio=6)
        t.add_widget(Etiqueta("Más detalles de la actividad", 15, True))
        for txt, clave, ayuda, cmd in (
                ("Desglose por equipos", "equipos", "La cantidad de cada ubicación se reparte entre equipos (ej. UMA-01: "
                 "100 ML de ductos). Cada equipo con cantidad asignada tiene su propio tope de cobro.", self._toggle_equipos),
                ("Por tramos", "tramos", "Tuberías, excavaciones, muros… El avance se puede llevar por tramo (también se "
                 "dibujan en los planos). Donde no haya tramos, se pone solo la cantidad.", self._toggle_tramos),
                ("Pago por hitos", "hitos", "La actividad se reconoce por etapas con su porcentaje (ej. estructura 50 %, "
                 "primer forro 17 %…). El avance se ingresa por hito. Con tipos (ej. tres tipos de tabique), cada tipo "
                 "tiene sus hitos.", self._toggle_hitos)):
            cb = Casilla(txt, bool(det[clave]), al_cambiar=cmd)
            cb.disabled = bloqueado
            t.add_widget(cb)
            fa = Fila(alto=1)
            fa.add_widget(Espacio(1, ancho=34))
            la = Etiqueta(ayuda, 12, color="texto2")
            fa.add_widget(la)
            la.bind(height=lambda w, h, fa=fa: setattr(fa, "height", h))
            t.add_widget(fa)
        self.col.add_widget(t)
        if det["hitos"]:
            self._editor_hitos(it, bloqueado, det)
        if det["equipos"]:
            self._editor_lista(it, bloqueado, fija, "equipos")
        if det["tramos"]:
            self._editor_lista(it, bloqueado, fija, "tramos")

    def _toggle(self, fn, nombre, si):
        try:
            fn(self.it["id"], si)
        except core.ErrorCtrlP as e:
            ui.info(nombre, str(e))
            self._redibujar()
            return
        self.app.guardar()
        self._redibujar()

    def _toggle_equipos(self, si):
        self._toggle(self.p.activar_equipos, "Desglose por equipos", si)

    def _toggle_tramos(self, si):
        self._toggle(self.p.activar_tramos, "Por tramos", si)

    def _toggle_hitos(self, si):
        self._toggle(self.p.activar_hitos, "Pago por hitos", si)

    # ---------------------------------------------------------------- hitos (con tipos)
    def _editor_hitos(self, it, bloqueado, det):
        t = Tarjeta(relleno=16, espacio=6)
        cab = Fila(alto=40)
        cab.add_widget(Etiqueta("Hitos de pago", 15, True))
        self.l_suma = Etiqueta("", 13, True, color="texto2", alinear="right")
        cab.add_widget(self.l_suma)
        bloq = Casilla("Bloquear porcentajes", bool(det["hitos_bloq"]), al_cambiar=self._toggle_bloqueo, negrita=False)
        bloq.size_hint_x = None
        bloq.width = dp(230)
        bloq.disabled = bloqueado
        cab.add_widget(bloq)
        t.add_widget(cab)
        self.hitos_orig = [(h["id"], h["nombre"], h["pct"], h.get("tipo") or "") for h in self.p.hitos_de(it["id"])]
        if not self.hitos_ed:
            for tp, hs in self.p.tipos_hito(it["id"]):
                self.hitos_ed.append([tp, [[h["id"], h["nombre"], f"{h['pct']:g}"] for h in hs]])
            if not self.hitos_ed:
                self.hitos_ed = [["", [[None, "", ""]]]]
        con_tipos = len(self.hitos_ed) > 1 or bool(self.hitos_ed[0][0].strip())
        fijo = bloqueado or det["hitos_bloq"]
        self.l_sumas_g = []
        for g, grupo in enumerate(self.hitos_ed):
            if con_tipos:
                ft = Fila(alto=46)
                ft.add_widget(Etiqueta("Tipo", 14, True, ancho_fijo=50))
                et = Campo(grupo[0], pista="Nombre del tipo (ej. TABIQUE 1 CARA)", mayus=True, ancho=300)
                et.bind(text=lambda w, tx, grupo=grupo: grupo.__setitem__(0, tx))
                et.disabled = fijo
                ft.add_widget(et)
                bt = Boton("Quitar tipo", ancho=120, al_tocar=lambda g=g: self._quitar_tipo(g))
                bt.disabled = fijo
                ft.add_widget(bt)
                ls = Etiqueta("", 13, True, color="texto2")
                self.l_sumas_g.append(ls)
                ft.add_widget(ls)
                t.add_widget(ft)
            else:
                self.l_sumas_g.append(None)
            ind = 24 if con_tipos else 0
            fh = Fila(alto=22)
            fh.add_widget(Espacio(1, ancho=ind))
            fh.add_widget(Etiqueta("Hito", 12, color="texto2", ancho_fijo=320))
            fh.add_widget(Etiqueta("% reconocido", 12, color="texto2"))
            t.add_widget(fh)
            for k, h in enumerate(grupo[1]):
                fr = Fila(alto=46)
                fr.add_widget(Espacio(1, ancho=ind))
                en = Campo(h[1], pista="Nombre del hito", ancho=310)
                en.bind(text=lambda w, tx, h=h: h.__setitem__(1, tx))
                ep = Campo(h[2], ancho=100, alinear="right", numerico=True)
                ep.bind(text=lambda w, tx, h=h: (h.__setitem__(2, tx), self._sumar_hitos()))
                fr.add_widget(en)
                fr.add_widget(ep)
                fr.add_widget(Etiqueta("%", 14, color="texto2", ancho_fijo=20))
                bx = Boton("×", ancho=44, al_tocar=lambda g=g, k=k: self._quitar_hito(g, k))
                fr.add_widget(bx)
                fr.add_widget(Widget())
                for w in (en, ep, bx):
                    w.disabled = fijo
                t.add_widget(fr)
            if con_tipos:
                fb = Fila(alto=44)
                fb.add_widget(Espacio(1, ancho=ind))
                b = Boton("+ Agregar hito a este tipo", ancho=250, al_tocar=lambda g=g: self._agregar_hito(g))
                b.disabled = fijo
                fb.add_widget(b)
                fb.add_widget(Widget())
                t.add_widget(fb)
        pie = Fila(alto=46)
        if not con_tipos:
            b = Boton("+ Agregar hito", ancho=160, al_tocar=lambda: self._agregar_hito(0))
            b.disabled = fijo
            pie.add_widget(b)
        b = Boton("+ Agregar tipo", ancho=160, al_tocar=self._agregar_tipo)
        b.disabled = fijo
        pie.add_widget(b)
        pie.add_widget(Widget())
        t.add_widget(pie)
        t.add_widget(Etiqueta(
            "Cada tipo tiene sus hitos y debe sumar 100 %. En cada ubicación, avance equivalente = Σ de todos los tipos "
            "(cantidad de cada hito × su %). Se guarda con «Guardar»." if con_tipos else
            "Avance equivalente = Σ (cantidad de cada hito × su %). Con «+ Agregar tipo» se separa por tipos (ej. tres "
            "tipos de tabique), cada uno con sus hitos. Se guarda con «Guardar».", 12, color="texto2"))
        self.col.add_widget(t)
        self._sumar_hitos()

    def _sumar_hitos(self):
        con_tipos = len(self.hitos_ed) > 1 or bool(self.hitos_ed[0][0].strip())
        todos = True
        txt0 = ""
        for g, grupo in enumerate(self.hitos_ed):
            tot = 0.0
            for h in grupo[1]:
                n = leer_num(h[2])
                if isinstance(n, float):
                    tot += n
            ok = abs(tot - 100) < 0.005
            todos = todos and ok
            txt = f"Suma {tot:,.2f} %" + ("  ✓" if ok else "  · debe ser 100 %")
            if g < len(self.l_sumas_g) and self.l_sumas_g[g] is not None:
                self.l_sumas_g[g].text = txt
            if g == 0:
                txt0 = txt
        self.l_suma.text = (f"{len(self.hitos_ed)} tipos" + ("  ✓" if todos else "  · cada tipo debe sumar 100 %")
                            if con_tipos else txt0)

    def _agregar_hito(self, g):
        self.hitos_ed[g][1].append([None, "", ""])
        self._redibujar()

    def _agregar_tipo(self):
        self.hitos_ed.append(["", [[None, "", ""]]])
        self._redibujar()

    def _quitar_tipo(self, g):
        self.hitos_ed.pop(g)
        if not self.hitos_ed:
            self.hitos_ed = [["", [[None, "", ""]]]]
        self._redibujar()

    def _quitar_hito(self, g, k):
        self.hitos_ed[g][1].pop(k)
        if not self.hitos_ed[g][1]:
            self.hitos_ed[g][1].append([None, "", ""])
        self._redibujar()

    def _toggle_bloqueo(self, si):
        def hacer():
            self.p.bloquear_hitos(self.it["id"], si)
            self.app.guardar()
            self.mostrar()
        if not si:
            def r(ok):
                if ok:
                    hacer()
                else:
                    self._redibujar()
            ui.preguntar("Desbloquear porcentajes",
                         "Si cambiás los porcentajes de los hitos, cambia el avance equivalente de todo lo ya "
                         "registrado en esta partida, incluso de períodos ya estimados.\n\n¿Desbloquear?", r,
                         si="Desbloquear")
            return
        if self._hitos_cambiados():
            ui.info("Bloquear porcentajes", "Primero guardá los cambios de los hitos.")
            self._redibujar()
            return
        hacer()

    def _lista_hitos(self):
        res = []
        for tp, hitos in self.hitos_ed:
            for hid, n, pc in hitos:
                v = leer_num(pc)
                if v == "error":
                    raise core.ErrorCtrlP(f"Porcentaje no válido: «{pc}».")
                if n.strip() or v:
                    res.append((hid, n.strip(), v, tp.strip()))
        return res

    def _hitos_cambiados(self):
        if not self.hitos_ed or not self.it or not self.p.detalle_de(self.it["id"])["hitos"]:
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

    # ---------------------------------------------------------------- equipos y tramos
    def _editor_lista(self, it, bloqueado, fija, tipo):
        es_eq = tipo == "equipos"
        con_eq = bool(self.p.detalle_de(it["id"])["equipos"])
        t = Tarjeta(relleno=16, espacio=6)
        t.add_widget(Etiqueta("Equipos" if es_eq else "Tramos", 15, True))
        t.add_widget(Etiqueta(
            "Equipos de referencia para el cobro de esta partida (ej. UMA-01, FC-01). Si asignás cantidad, es su tope; "
            "si no, toma lo disponible del nivel." if es_eq else
            "Se crean aquí o al marcar en los planos. Si asignás cantidad, es su tope; si no, toma lo disponible.",
            12, color="texto2"))
        orig = {}
        for x in (self.p.equipos_de(it["id"]) if es_eq else self.p.tramos_de(it["id"])):
            orig.setdefault(x["nivel"], []).append(x)
        nombres_eq = {e["id"]: e["nombre"] for e in self.p.equipos_de(it["id"])}
        if es_eq:
            self.equipos_orig = orig
            if not self.equipos_ed:
                self.equipos_ed = {nv: [[x["id"], x["nombre"], txt_num(x["contractual"])] for x in l]
                                   for nv, l in orig.items()}
            datos = self.equipos_ed
        else:
            self.tramos_orig = orig
            if not self.tramos_ed:
                self.tramos_ed = {nv: [[x["id"], x["nombre"], txt_num(x["contractual"]),
                                        nombres_eq.get(x["equipo"], SIN_EQ)] for x in l] for nv, l in orig.items()}
            datos = self.tramos_ed
        cont = self.p.contractual_de(it["id"])
        palabra = "equipos" if es_eq else "tramos"
        for u in self.p.ubicaciones():
            if fija and u["nivel"] != fija:
                continue
            nv = u["nivel"]
            filas = datos.get(nv, [])
            if self._visibles is not None and nv not in self._visibles and not filas:
                continue
            f = Fila(alto=44)
            f.add_widget(Etiqueta(u["etiqueta"], 14, True, ancho_fijo=200))
            suma = sum(x for x in (leer_num(fl[2]) for fl in filas) if isinstance(x, float))
            info = f"{len(filas)} {palabra}" if filas else f"sin {palabra}"
            if suma:
                info += f" · suman {fmt(suma)}"
                if nv in cont:
                    info += f" de {fmt(cont[nv])} contractual"
                    if es_eq and abs(suma - cont[nv]) > 0.005:
                        info += "  ●"
            f.add_widget(Etiqueta(info, 12, color="texto2"))
            b = Boton("+ Equipo" if es_eq else "+ Tramo", ancho=110, al_tocar=lambda nv=nv: self._agregar_fila(tipo, nv))
            b.disabled = bloqueado
            f.add_widget(b)
            t.add_widget(f)
            ops_eq = ([SIN_EQ] + [fl[1].strip().upper() for fl in self.equipos_ed.get(nv, []) if fl[1].strip()]
                      if con_eq and not es_eq else None)
            for k, fl in enumerate(filas):
                ff = Fila(alto=46)
                ff.add_widget(Espacio(1, ancho=18))
                en = Campo(fl[1], pista="Nombre", mayus=True, ancho=230)
                en.bind(text=lambda w, tx, fl=fl: fl.__setitem__(1, tx))
                ec = Campo(fl[2], ancho=120, alinear="right", numerico=True)
                ec.bind(text=lambda w, tx, fl=fl: fl.__setitem__(2, tx))
                ff.add_widget(en)
                ff.add_widget(ec)
                ws = [en, ec]
                if ops_eq is not None:
                    if fl[3] not in ops_eq:
                        fl[3] = SIN_EQ
                    m = Menu(ops_eq, fl[3], ancho=170, al_cambiar=lambda v, fl=fl: fl.__setitem__(3, v))
                    ff.add_widget(m)
                    ws.append(m)
                extra = ""
                if not es_eq and fl[0]:
                    tr = self.p.tramo(fl[0])
                    extra = " · dibujado en plano" if tr and tr["geom"] else ""
                ff.add_widget(Etiqueta(it["unidad"] + extra, 12, color="texto2"))
                bx = Boton("×", ancho=44, al_tocar=lambda nv=nv, k=k: self._quitar_fila(tipo, nv, k))
                ff.add_widget(bx)
                ws.append(bx)
                if bloqueado:
                    for w in ws:
                        w.disabled = True
                t.add_widget(ff)
        self.col.add_widget(t)

    def _agregar_fila(self, tipo, nv):
        if tipo == "equipos":
            self.equipos_ed.setdefault(nv, []).append([None, "", ""])
        else:
            self.tramos_ed.setdefault(nv, []).append([None, "", "", SIN_EQ])
        self._redibujar()

    def _quitar_fila(self, tipo, nv, k):
        datos = self.equipos_ed if tipo == "equipos" else self.tramos_ed
        xid = datos[nv][k][0]
        if xid:
            nombre = self.p.nombre_equipo(xid) if tipo == "equipos" else self.p.nombre_tramo(xid)

            def r(si):
                if not si:
                    return
                try:
                    if tipo == "equipos":
                        self.p.eliminar_equipo(xid)
                    else:
                        self.p.eliminar_tramo(xid)
                except core.ErrorCtrlP as e:
                    ui.info("Eliminar", str(e))
                    return
                self.app.guardar()
                datos[nv].pop(k)
                self._redibujar()
            ui.preguntar("Eliminar", f"¿Eliminar {'el equipo' if tipo == 'equipos' else 'el tramo'} {nombre}?", r,
                         si="Eliminar")
            return
        datos[nv].pop(k)
        self._redibujar()

    def _lista_cambiada(self, datos, orig_por_nv, con_equipo=False):
        if not self.it:
            return False
        orig = {x["id"]: x for l in (orig_por_nv or {}).values() for x in l}
        nombres_eq = {e["id"]: e["nombre"] for e in self.p.equipos_de(self.it["id"])} if con_equipo else {}
        for nv, filas in (datos or {}).items():
            for fl in filas:
                xid, n, c = fl[0], fl[1], leer_num(fl[2])
                if xid is None:
                    if n.strip() or c is not None:
                        return True
                    continue
                o = orig.get(xid)
                if not o or core.mayus(n) != o["nombre"] or c == "error" or \
                        (c is None) != (o["contractual"] is None) or (c is not None and abs(c - o["contractual"]) > 1e-9):
                    return True
                if con_equipo and len(fl) > 3 and fl[3] != nombres_eq.get(o.get("equipo"), SIN_EQ):
                    return True
        return False

    # ---------------------------------------------------------------- guardar
    def _guardar_detalles(self):
        n = 0
        iid = self.it["id"]
        det = self.p.detalle_de(iid)
        if det["hitos"] and self.hitos_ed and self._hitos_cambiados():
            if self.p.guardar_hitos(iid, self._lista_hitos()):
                n += 1
        if det["equipos"] and self.equipos_ed:
            for nv, filas in self.equipos_ed.items():
                for eid, nombre, ctxt in filas:
                    c = leer_num(ctxt)
                    if c == "error":
                        raise core.ErrorCtrlP(f"Cantidad de equipo no válida: «{ctxt}».")
                    if eid is None:
                        if nombre.strip():
                            self.p.crear_equipo(iid, nv, nombre, c)
                            n += 1
                        elif c is not None:
                            raise core.ErrorCtrlP("Hay un equipo con cantidad pero sin nombre.")
                    else:
                        o = self.p.equipo(eid)
                        if core.mayus(nombre) != o["nombre"] or (c is None) != (o["contractual"] is None) or \
                                (c is not None and abs(c - o["contractual"]) > 1e-9):
                            self.p.editar_equipo(eid, nombre, c)
                            n += 1
        if det["tramos"] and self.tramos_ed:
            for nv, filas in self.tramos_ed.items():
                ids_eq = {e["nombre"]: e["id"] for e in self.p.equipos_de(iid, nv)}
                for fl in filas:
                    tid, nombre, ctxt = fl[0], fl[1], fl[2]
                    eq = ids_eq.get(fl[3], "") if len(fl) > 3 else ""
                    c = leer_num(ctxt)
                    if c == "error":
                        raise core.ErrorCtrlP(f"Cantidad de tramo no válida: «{ctxt}».")
                    if tid is None:
                        if nombre.strip():
                            self.p.crear_tramo(iid, nv, nombre, c, equipo=eq)
                            n += 1
                        elif c is not None:
                            raise core.ErrorCtrlP("Hay un tramo con cantidad pero sin nombre.")
                    else:
                        o = self.p.tramo(tid)
                        if core.mayus(nombre) != o["nombre"] or (c is None) != (o["contractual"] is None) or \
                                (c is not None and abs(c - o["contractual"]) > 1e-9) or eq != (o["equipo"] or ""):
                            self.p.editar_tramo(tid, nombre, c, equipo=eq)
                            n += 1
        return n

    def guardar(self):
        if not self.p or not self.it or self.p.solo_agregar:
            return True
        n_cambios = 0
        try:
            fija_txt = self.m_fija.valor
            nueva = next((u["nivel"] for u in self.p.ubicaciones() if u["etiqueta"] == fija_txt), None)
            if nueva != self.p.ubic_fija_de(self.it["id"]):
                self.p.set_ubic_fija(self.it["id"], nueva)
                n_cambios += 1
            n_cambios += self._guardar_detalles()
            tipo_de = {h["id"]: h.get("tipo") or "" for h in self.p.hitos_de(self.it["id"])}
            for (nv, hid0), (txt, _, _) in self.vars_tipo.items():
                tp = tipo_de.get(hid0)
                if not tp:
                    continue
                n = leer_num(txt)
                if n == "error":
                    raise core.ErrorCtrlP(f"Cantidad no válida: «{txt}».")
                if self.p.set_cant_tipo(self.it["id"], nv, tp, n):
                    n_cambios += 1
            for nv, (txt, orig) in ({} if self.p.ubic_fija_de(self.it["id"]) else self.vars).items():
                n = leer_num(txt)
                if n == "error":
                    raise core.ErrorCtrlP(f"Cantidad no válida: «{txt}».")
                if self.p.set_contractual(self.it["id"], nv, n):
                    n_cambios += 1
        except core.ErrorCtrlP as e:
            ui.info("Datos fijos", str(e))
            return False
        if n_cambios:
            self.app.guardar()
            ui.aviso("Datos fijos guardados")
        self._marcas()
        self.arbol.poner_marca(self.it["id"], self.arbol.marcas.get(self.it["id"], ""))
        self._limpiar_estado()
        self.mostrar()
        self.app.lateral.dibujar()
        return True

    def sugerir(self):
        if not self.p or self.p.solo_agregar:
            return
        sug = self.p.sugerir_ubicaciones()
        if not sug:
            ui.info("Sugerir ubicaciones", "No se encontraron partidas cuya descripción mencione una ubicación.\n\n"
                    "Esta opción sirve para presupuestos que ya vienen separados por edificio y nivel.")
            return
        import dialogos
        dialogos.DialogoSugerencias(self.app, sug, self.refrescar).open()
