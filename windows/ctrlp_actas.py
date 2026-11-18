"""
Ctrl-P - Actas (formularios de liberación / registros de calidad)
================================================================
Con el formato Excel que se carga para una actividad (Informes › Generar actas), saca un acta por
edificio, nivel y tipo, todas en un libro (una hoja por acta).

El formato se lee por sus rótulos, no por celdas fijas: «FECHA», «REGISTRO», «ACTIVIDAD», «UBICACIÓN»,
la tabla «DETALLE DE LEVANTAMIENTO…» (título, fila de encabezados, filas de datos y la fila de total) y
«OBSERVACIONES». El resto del formato (logos, lista de verificación, croquis, firmas) queda igual.

Cuentas de cada hito (cantidades reales, en la unidad de la partida):
  anterior        = todo lo registrado hasta el corte (sin pasar lo contractual)
  este período    = lo registrado después del corte y hasta el fin del período
  con enmienda    = este período × % de enmienda, sin pasar lo que le falta al hito para lo contractual
                    (con «Suministro cobrado hasta»: el % es el complemento de lo cobrado en cada hito, 61 % → 39 %)
  a cobrar        = con enmienda × % del hito (equivalente)
  pendiente       = contractual − anterior − con enmienda
Total a cobrar = suma de lo equivalente; su % es sobre lo contractual del tipo en ese edificio y nivel.
"""

import copy
import io
import unicodedata

import openpyxl
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Side
from openpyxl.worksheet.cell_range import CellRange
from openpyxl.worksheet.properties import PageSetupProperties
import datetime as dt


CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)
DER = Alignment(horizontal="right", vertical="center")
IZQ = Alignment(horizontal="left", vertical="center")
CAB = ["ÍTEM", "PARTIDA", "DESCRIPCIÓN (HITO)", "UBICACIÓN", "CANT. CONTRACTUAL ({u})", "% DEL HITO",
       "ACUM. ANTERIOR ({u})", "% ANTERIOR", "CANT. ESTE PERÍODO ({u})", "% ENMIENDA",
       "PERÍODO CON ENMIENDA ({u}, tope contractual)", "EQUIVALENTE A COBRAR ({u} × % hito)",
       "CANT. PENDIENTE ({u})", "% PENDIENTE"]
ANCHOS = [None, None, 70, None, 14, 10, 14, 11, 14, 12, 17, 17, 14, 12]     # None = como en el formato
PCT = {5, 7, 9, 13}


class ErrorActa(Exception):
    pass


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(t.replace(":", " ").split())


# ------------------------------------------------------------------ lectura del formato
def _celdas(ws):
    for fila in ws.iter_rows():
        for c in fila:
            if isinstance(c.value, str) and c.value.strip():
                yield c


def _rango_de(ws, celda):
    for m in ws.merged_cells.ranges:
        if m.min_row <= celda.row <= m.max_row and m.min_col <= celda.column <= m.max_col:
            return m
    return CellRange(min_col=celda.column, min_row=celda.row, max_col=celda.column, max_row=celda.row)


def _valor_a_la_derecha(ws, celda):
    """La celda donde va el dato de un rótulo: la primera a su derecha, saltando las celdas combinadas del rótulo."""
    m = _rango_de(ws, celda)
    return ws.cell(m.min_row, m.max_col + 1)


def leer_formato(ws):
    pos = {}
    for c in _celdas(ws):
        n = _norm(c.value)
        if n.startswith("FECHA") and "fecha" not in pos:
            pos["fecha"] = _valor_a_la_derecha(ws, c)
        elif n.startswith("REGISTRO") and "registro" not in pos:
            pos["registro"] = _valor_a_la_derecha(ws, c)
        elif n.startswith("ACTIVIDAD") and "actividad" not in pos:
            pos["actividad"] = _valor_a_la_derecha(ws, c)
        elif n.startswith("UBICACION") and "ubicacion" not in pos and c.row < 40:
            pos["ubicacion"] = _valor_a_la_derecha(ws, c)
        elif n.startswith("DETALLE DE LEVANTAMIENTO") and "detalle" not in pos:
            pos["detalle"] = c
    if "detalle" not in pos:
        raise ErrorActa("El formato no tiene la tabla «DETALLE DE LEVANTAMIENTO DE OBRA EJECUTADA». "
                        "Revisá que el título esté escrito así en el Excel.")
    t = pos["detalle"]
    m = _rango_de(ws, t)
    pos["col0"], pos["fila_titulo"], pos["fila_cab"] = m.min_col, t.row, t.row + 1
    # la fila de total: la primera debajo del encabezado que dice «TOTAL»
    tot = None
    for r in range(t.row + 2, min(ws.max_row, t.row + 80) + 1):
        if any(_norm(ws.cell(r, c).value).find("TOTAL") >= 0 for c in range(1, ws.max_column + 1)):
            tot = r
            break
    if tot is None:
        raise ErrorActa("En la tabla de detalle del formato no se encontró la fila de total («CANTIDAD TOTAL…»).")
    pos["fila_total"] = tot
    pos["filas_datos"] = tot - (t.row + 2)
    return pos


# ------------------------------------------------------------------ datos de Ctrl-P
def _sumas(p, iid, nivel, cond, args, factor=False):
    """Cantidades por hito. Con factor, lo registrado después del suministro vale × el complemento de lo cobrado
    como suministro en ese hito (ver Proyecto.factores_suministro): es lo que ya cuenta como cobrado."""
    fx, fa = p._sql_factor() if factor else ("1.0", [])
    q = (f"SELECT COALESCE(hito,''), SUM(cantidad * {fx}) FROM avances WHERE item=? AND nivel=? AND " + cond +
         " GROUP BY 1")
    return {h: s or 0.0 for h, s in p.con.execute(q, tuple(fa) + (iid, nivel) + tuple(args))}


def tipos_de(p, iid):
    """Tipos de la partida (MURO, TABIQUERÍA…), o [None] si sus hitos no tienen tipos (o no tiene hitos)."""
    ts = []
    for h in p.hitos_de(iid):
        t = h.get("tipo") or None
        if t not in ts:
            ts.append(t)
    return ts or [None]


def datos_acta(p, it, nivel, tipo, corte, hasta, enmienda):
    iid = it["id"]
    if tipo:
        cont = p.cant_tipos_de(iid).get((nivel, tipo)) or 0.0
    else:
        cont = p.contractual_de(iid).get(nivel) or 0.0
    ant = _sumas(p, iid, nivel, "fecha <= ?", (corte,), factor=True)   # suministro + instalado × complemento
    fs = p.suministros().get(iid)
    facs = p.factores_suministro() if fs and corte >= fs else {}
    per = _sumas(p, iid, nivel, "fecha > ? AND fecha <= ?", (corte, hasta))
    hs = [h for h in p.hitos_de(iid) if (h.get("tipo") or None) == tipo] or \
        [{"id": "", "nombre": it["descripcion"], "pct": 100.0}]
    filas = []
    for h in hs:
        a = min(ant.get(h["id"], 0.0), cont) if cont else ant.get(h["id"], 0.0)
        q = per.get(h["id"], 0.0)
        # con suministro cobrado: el complemento de lo cobrado en el hito (61 % → × 39 %); si no, la enmienda
        fac = facs.get((iid, nivel, h["id"]), (None, 1.0))[1] if facs else enmienda
        con_enm = q * fac
        if cont:
            con_enm = min(con_enm, max(0.0, cont - a))
        f = h["pct"] / 100.0
        filas.append({"hito": h["nombre"], "pct": f, "ant": a, "per": q, "enm": con_enm, "fac": fac, "cob": con_enm * f,
                      "pend_cant": max(0.0, cont - a - con_enm) if cont else 0.0,
                      "pend": max(0.0, 1 - (a + con_enm) / cont) if cont else 0.0})
    return cont, filas


def actas_posibles(p, items, corte, hasta):
    """[(item, nivel, tipo)] con algo registrado en el período, en el orden de ubicaciones y tipos."""
    res = []
    orden = [u["nivel"] for u in p.ubicaciones()]
    for iid in items:
        it = p.item(iid)
        if not it:
            continue
        con = {(r[0], r[1] or "") for r in p.con.execute(
            "SELECT nivel, hito FROM avances WHERE item=? AND fecha > ? AND fecha <= ? AND cantidad<>0 "
            "GROUP BY nivel, hito", (iid, corte, hasta))}
        tipo_de = {h["id"]: (h.get("tipo") or None) for h in p.hitos_de(iid)}
        hay = {(n, tipo_de.get(h)) for n, h in con}
        for n in orden:
            for t in tipos_de(p, iid):
                if (n, t) in hay:
                    res.append((it, n, t))
    return res


# ------------------------------------------------------------------ armado de cada hoja
def _area(pa):
    """«'HOJA'!$B$2:$O$108» (o una lista de eso) -> CellRange B2:O108, sin el nombre de la hoja."""
    if not pa:
        return None
    if isinstance(pa, (list, tuple)):
        pa = pa[0]
    try:
        return CellRange(str(pa).split(",")[0].split("!")[-1].replace("$", "").replace("'", ""))
    except Exception:
        return None


def _insertar_filas(ws, antes_de, n, modelo):
    if n <= 0:
        return
    alturas = {r: ws.row_dimensions[r].height for r in range(antes_de, ws.max_row + 1)}
    merges = [CellRange(str(m)) for m in ws.merged_cells.ranges]
    for m in list(ws.merged_cells.ranges):
        ws.merged_cells.remove(m)
    ws.insert_rows(antes_de, n)
    for r, h in alturas.items():
        ws.row_dimensions[r + n].height = h
    for m in merges:
        if m.min_row >= antes_de:
            m.shift(row_shift=n)
        ws.merged_cells.add(m)
    for k in range(n):
        r = antes_de + k
        ws.row_dimensions[r].height = ws.row_dimensions[modelo].height
        for c in range(1, ws.max_column + 1):
            ws.cell(r, c)._style = copy.copy(ws.cell(modelo, c)._style)
    for im in ws._images:
        if im.anchor._from.row >= antes_de - 1:
            im.anchor._from.row += n
    rng = _area(ws.print_area)
    if rng:
        rng.expand(down=n)
        ws.print_area = rng.coord
    for b in ws.row_breaks.brk:
        if b.id >= antes_de:
            b.id += n


def armar_hoja(ws, pos, it, ubic, tipo, cont, filas, registro, fecha, enmienda, nota):
    unidad = it["unidad"] or ""
    c0 = pos["col0"]
    ncols = len(CAB)
    extra = max(0, len(filas) - pos["filas_datos"])
    _insertar_filas(ws, pos["fila_total"], extra, pos["fila_total"] - 1)
    fc, f1 = pos["fila_cab"], pos["fila_cab"] + 1
    tot = pos["fila_total"] + extra
    # título a todo el ancho de la tabla
    for m in list(ws.merged_cells.ranges):
        if m.min_row == pos["fila_titulo"] and m.min_col <= c0 <= m.max_col:
            ws.unmerge_cells(str(m))
    for c in range(c0, c0 + ncols):
        ws.cell(pos["fila_titulo"], c)._style = copy.copy(ws.cell(pos["fila_titulo"], c0)._style)
    ws.merge_cells(start_row=pos["fila_titulo"], start_column=c0, end_row=pos["fila_titulo"],
                   end_column=c0 + ncols - 1)
    # la tabla, sin celdas combinadas y con el estilo de una celda de datos del formato
    for m in list(ws.merged_cells.ranges):
        if fc <= m.min_row <= tot:
            ws.unmerge_cells(str(m))
    est_cab = copy.copy(ws.cell(fc, c0 + 8)._style)
    est_dato = copy.copy(ws.cell(f1, c0 + 8)._style)
    est_tot = copy.copy(ws.cell(tot, c0 + 8)._style)
    for r in range(fc, tot + 1):
        for c in range(c0, c0 + ncols):
            cel = ws.cell(r, c)
            cel._style = copy.copy(est_cab if r == fc else est_tot if r == tot else est_dato)
            cel.value = None
    ws.row_dimensions[fc].height = 52
    # anchos: la descripción y la ubicación suman lo mismo que en el formato (logos y lista de verificación quietos)
    L = openpyxl.utils.get_column_letter
    cd, ce = L(c0 + 2), L(c0 + 3)
    d0, e0 = ws.column_dimensions[cd].width or 13, ws.column_dimensions[ce].width or 13
    for k, w in enumerate(ANCHOS):
        if w:
            ws.column_dimensions[L(c0 + k)].width = w
    ws.column_dimensions[ce].width = max(12, round(d0 + e0 - ws.column_dimensions[cd].width, 2))
    corr = (ws.column_dimensions[cd].width - d0) * 7 * 9525
    for im in ws._images:
        if im.anchor._from.col == c0 + 2 and im.anchor._from.row < 6:   # (columna 0-based: la de la ubicación)
            im.anchor._from.colOff = max(0, int(im.anchor._from.colOff - corr))
    for k, t in enumerate(CAB):
        cel = ws.cell(fc, c0 + k)
        cel.value = t.format(u=unidad)
        cel.alignment = CENTRO
    # encabezado del acta
    if "fecha" in pos:
        ws[pos["fecha"].coordinate] = fecha
        ws[pos["fecha"].coordinate].number_format = "dd/mm/yyyy"
        ws[pos["fecha"].coordinate].alignment = IZQ
    if "registro" in pos:
        ws[pos["registro"].coordinate] = registro
    if "actividad" in pos:
        base = str(ws[pos["actividad"].coordinate].value or "").strip() or it["descripcion"]
        ws[pos["actividad"].coordinate] = f"{base} · {tipo}" if tipo else base
    if "ubicacion" in pos:
        ws[pos["ubicacion"].coordinate] = ubic
    # filas
    L_ = lambda k: openpyxl.utils.get_column_letter(c0 + k)       # letra de la columna k de la tabla
    F, G, H, I, J, K, Lc, M, N, O = (L_(k) for k in range(4, 14))
    for k, f in enumerate(filas):
        r = f1 + k
        # datos de Ctrl-P como valores; las cuentas como fórmulas (se pueden revisar y ajustar en Excel)
        vals = [k + 1, it["codigo"], f["hito"], ubic, round(cont, 2), f["pct"], round(f["ant"], 2),
                f"=IF({F}{r}>0,{H}{r}/{F}{r},0)", round(f["per"], 2), round(f.get("fac", enmienda), 6),
                f"=IF({F}{r}>0,ROUND(MIN({J}{r}*{K}{r},MAX(0,{F}{r}-{H}{r})),2),ROUND({J}{r}*{K}{r},2))",
                f"=ROUND({Lc}{r}*{G}{r},2)", f"=IF({F}{r}>0,MAX(0,{F}{r}-{H}{r}-{Lc}{r}),0)",
                f"=IF({F}{r}>0,MAX(0,1-({H}{r}+{Lc}{r})/{F}{r}),0)"]
        for c, v in enumerate(vals):
            cel = ws.cell(r, c0 + c)
            cel.value = v
            if c <= 3:
                cel.alignment = CENTRO
                cel.number_format = "0" if c == 0 else "@"
            else:
                cel.alignment = DER
                cel.number_format = "0.00%" if c in PCT else "#,##0.00"
    total = round(sum(round(f["cob"], 2) for f in filas), 2)
    ws.merge_cells(start_row=tot, start_column=c0, end_row=tot, end_column=c0 + 10)
    ws.cell(tot, c0).value = f"TOTAL A COBRAR ({unidad} equivalentes)"
    ws.cell(tot, c0).alignment = CENTRO
    ct = ws.cell(tot, c0 + 11)
    ct.value, ct.number_format, ct.alignment = f"=SUM({M}{f1}:{M}{tot - 1})", "#,##0.00", DER
    ws.cell(tot, c0 + 13).value = None          # sin % abajo: quedaba bajo «% pendiente» y confundía
    # nota en Observaciones
    if nota:
        for r in range(tot + 1, tot + 8):
            for c in range(1, ws.max_column + 1):
                cel = ws.cell(r, c)
                if _norm(cel.value) == "OBSERVACIONES":
                    fb = cel.font
                    cel.value = CellRichText(TextBlock(InlineFont(rFont=fb.name, sz=fb.sz, b=True), "OBSERVACIONES\n"),
                                             TextBlock(InlineFont(rFont=fb.name, sz=fb.sz), nota))
                    cel.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                    break
            else:
                continue
            break
    # borde parejo en toda la tabla (título, encabezados, filas y total)
    fino = Side(style="thin", color="000000")
    b = Border(left=fino, right=fino, top=fino, bottom=fino)
    for r in range(pos["fila_titulo"], tot + 1):
        for c in range(c0, c0 + ncols):
            ws.cell(r, c).border = b
    _centrar_firmas(ws, c0, c0 + ncols - 1, pos["fila_titulo"])
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    return total


def _px_col(ws, c):
    w = ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width
    return int((w if w else 8.43) * 7 + 5)


def _centrar_firmas(ws, c_ini, c_fin, fila_desde):
    """Las imágenes anchas de firmas (las que van debajo de la tabla de verificación y de la de detalle) quedan
    centradas en el ancho del formato."""
    EMU = 9525
    ancho_total = sum(_px_col(ws, c) for c in range(c_ini, c_fin + 1))
    for im in ws._images:
        a = im.anchor
        ext = getattr(a, "ext", None)
        if ext is None or not getattr(ext, "width", None):
            continue
        w_px, h_px = ext.width / EMU, ext.height / EMU
        if w_px < ancho_total * 0.5 or a._from.row < 10:        # solo las firmas (anchas y no del encabezado)
            continue
        if w_px > ancho_total * 0.96:                           # que no se salga del ancho de la tabla
            f = ancho_total * 0.96 / w_px
            w_px, h_px = w_px * f, h_px * f
        im.width, im.height = w_px, h_px                        # mismo tamaño para Excel y para otros visores
        ext.width, ext.height = int(w_px * EMU), int(h_px * EMU)
        izq = max(0, (ancho_total - w_px) / 2)
        c, x = c_ini, 0
        while c <= c_fin and x + _px_col(ws, c) <= izq:
            x += _px_col(ws, c)
            c += 1
        a._from.col = c - 1                                    # 0-based
        a._from.colOff = int((izq - x) * EMU)


def _imagenes(hoja):
    """Los logos del formato, leídos una sola vez (openpyxl cierra el archivo de la imagen al leerla)."""
    res = []
    for im in hoja._images:
        try:
            res.append((im, im._data()))
        except Exception:
            pass
    return res


def _copiar_imagenes(imagenes, destino):
    for im, datos in imagenes:
        n = XLImage(io.BytesIO(datos))
        ext = getattr(im.anchor, "ext", None)
        if ext is not None and getattr(ext, "width", None):     # el tamaño con que se ve en el formato
            n.width, n.height = ext.width / 9525, ext.height / 9525
        else:
            n.width, n.height = im.width, im.height
        n.anchor = copy.deepcopy(im.anchor)
        destino.add_image(n)


def _nombre_hoja(base, usados):
    base = "".join(ch for ch in base if ch not in '[]:*?/\\')[:31] or "ACTA"
    n, k = base, 2
    while n in usados:
        sfx = f" ({k})"
        n, k = base[:31 - len(sfx)] + sfx, k + 1
    usados.add(n)
    return n


def generar(p, formato, actas, corte, hasta, fecha_acta, primer_num, enmienda, ruta, progreso=None):
    """actas: [(item, nivel, tipo)]. Devuelve [(registro, ubicación, tipo, total)] y el último número usado."""
    datos = p.formato_acta_datos(formato["id"])
    if not datos:
        raise ErrorActa("Este formato no tiene archivo. Cargalo de nuevo.")
    wb = openpyxl.load_workbook(io.BytesIO(datos))
    plantilla = wb.worksheets[0]
    leer_formato(plantilla)                              # avisa si al formato le falta algo
    imagenes = _imagenes(plantilla)
    pa = plantilla.print_area
    titulos = plantilla.print_title_rows
    usados = {plantilla.title}
    if isinstance(fecha_acta, str):
        fecha_acta = dt.date.fromisoformat(fecha_acta)
    prefijo = formato.get("prefijo") or ""
    nota = (formato.get("nota") or "").strip()
    etiquetas = {u["nivel"]: u["etiqueta"] for u in p.ubicaciones()}
    hechas = []
    num = primer_num
    for k, (it, nivel, tipo) in enumerate(actas):
        if progreso:
            progreso(k / max(1, len(actas)), f"Acta {k + 1} de {len(actas)}")
        ws = wb.copy_worksheet(plantilla)
        _copiar_imagenes(imagenes, ws)
        ws.page_setup = copy.copy(plantilla.page_setup)
        ws.page_margins = copy.copy(plantilla.page_margins)
        ws.print_options = copy.copy(plantilla.print_options)
        if _area(pa):
            ws.print_area = _area(pa).coord
        if titulos:
            ws.print_title_rows = str(titulos).split("!")[-1].replace("$", "")
        for b in plantilla.row_breaks.brk:
            ws.row_breaks.append(copy.copy(b))
        ws.sheet_view.showGridLines = plantilla.sheet_view.showGridLines
        ubic = etiquetas.get(nivel, nivel)
        registro = f"{prefijo}{num:03d}"
        cont, filas = datos_acta(p, it, nivel, tipo, corte, hasta, enmienda)
        pos = leer_formato(ws)
        total = armar_hoja(ws, pos, it, ubic, tipo, cont, filas, registro, fecha_acta, enmienda, nota)
        corto = (tipo or it["codigo"])[:3]
        ws.title = _nombre_hoja(f"{registro} {ubic} {corto}", usados)
        hechas.append((registro, ubic, tipo or it["codigo"], total))
        num += 1
    wb.remove(plantilla)
    wb.calculation.fullCalcOnLoad = True          # Excel calcula las fórmulas al abrir
    if not wb.worksheets:
        raise ErrorActa("No hay actas para generar.")
    wb.active = 0
    wb.save(ruta)
    return hechas, num - 1
