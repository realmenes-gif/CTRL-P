"""Arma un proyecto de prueba (datos inventados) para la prueba automatica antes de publicar una version.
Uso: python prueba/crear_prueba.py <carpeta destino>   ->  <carpeta>/Registro_Semanal.ctrlp"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import openpyxl  # noqa: E402

import ctrlp_core as core  # noqa: E402

destino = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
os.makedirs(destino, exist_ok=True)
xlsx = os.path.join(destino, "presupuesto_prueba.xlsx")
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Presupuesto"
ws.append(["OBRA DE PRUEBA"])
ws.append([])
ws.append(["ITEM", "DESCRIPCION", "UNIDAD", "CANTIDAD", "PRECIO UNITARIO", "TOTAL"])
filas = [("01", "OBRAS PRELIMINARES", None, None, None, None),
         ("01.01", "LIMPIEZA DEL TERRENO", "M2", 1000, 2.5, 2500),
         ("01.02", "TRAZO Y NIVELACION", "M2", 800, 1.25, 1000),
         ("02", "ESTRUCTURA", None, None, None, None),
         ("02.01", "CONCRETO EN ZAPATAS", "M3", 120, 150, 18000),
         ("02.02", "MURO DE BLOQUE", "M2", 300, 40, 12000)]
for f in filas:
    ws.append(list(f))
ws.append([None, "TOTAL", None, None, None, 33500])
wb.save(xlsx)

_, datos = core.leer_excel(xlsx)
mapa, ini = core.detectar_columnas(datos)
an = core.analizar_presupuesto(datos, mapa, ini, xlsx)
ruta = os.path.join(destino, "Registro_Semanal" + core.EXT)
if os.path.exists(ruta):
    os.remove(ruta)
p = core.Proyecto.crear(ruta, "PRUEBA - CI", an, {"nombre": "OBRA DE PRUEBA", "contratista": "", "propietario": "",
                                                  "moneda": "US$"})
b1 = p.crear_edificio("B1", ["NIVEL 1", "NIVEL 2"])
ext = p.crear_edificio("SECTOR I", [], es_area=True, tramos=["TRAMO 1", "TRAMO 2"])
nv = {u["etiqueta"]: u["nivel"] for u in p.ubicaciones()}
muro = [i for i in p.partidas() if i["codigo"] == "02.02"][0]["id"]
limp = [i for i in p.partidas() if i["codigo"] == "01.01"][0]["id"]
p.set_contractual(muro, nv["B1 NIVEL 1"], 200)
p.set_contractual(muro, nv["B1 NIVEL 2"], 100)
p.guardar_avance(muro, nv["B1 NIVEL 1"], "2026-06-01", 120, "")
p.guardar_avance(muro, nv["B1 NIVEL 2"], "2026-06-08", 110, "pasa del contractual")
p.guardar_avance(limp, nv["SECTOR I TRAMO 1"], "2026-06-02", 1000, "")
p.guardar()
p.cerrar()
print(ruta)
