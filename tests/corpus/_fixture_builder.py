"""Construye un workbook sintético que replica la ESTRUCTURA relevante del grid real
(hojas, fila de header en 4, filas 5-7 de ejemplo, datos desde fila 8, dropdowns de
medio/tema/género y del esquema completo de anotación de 9 categorías) sin usar el
archivo real como fuente. Los tests SIEMPRE corren contra esto.
"""
from __future__ import annotations

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

MEDIOS = ["Infobae Colombia", "El Tiempo", "El Espectador", "La Silla Vacía", "Semana"]
TEMAS = [
    "Transición de gobierno y relación con la oposición",
    "Respuesta a la emergencia del terremoto",
    "Relación con Estados Unidos",
    "Reformas sociales en disputa (pensional/tributaria)",
    "Seguridad y orden público",
]
GENEROS = ["Noticia dura", "Opinión-análisis"]

# Las 9 categorías del esquema completo (J1 léxico + J2 discursivo), cada una con su
# columna booleana seguida de su columna de span -- ver esquemas_anotacion.xlsx "Tabla 1".
CATEGORIAS_BOOL_SPAN = [
    "verbo_factivo", "verbo_asertivo", "palabra_subjetiva", "hedge", "etiqueta_valorativa",
    "sensacionalismo", "mind_reading", "falta_atribucion", "opinion_como_hecho",
]


def build_fixture_workbook() -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    ws_grid = wb.create_sheet("Grid de recoleccion")
    ws_grid["A4"], ws_grid["B4"] = "Medio", "Tema"
    ws_grid["C4"], ws_grid["D4"] = "Objetivo dura", "Objetivo opinión"
    fila = 5
    objetivos_dura = {"Infobae Colombia": 14, "El Tiempo": 14, "El Espectador": 6, "La Silla Vacía": 8, "Semana": 10}
    for medio in MEDIOS:
        for tema in TEMAS:
            ws_grid.cell(row=fila, column=1, value=medio)
            ws_grid.cell(row=fila, column=2, value=tema)
            ws_grid.cell(row=fila, column=3, value=objetivos_dura[medio])
            ws_grid.cell(row=fila, column=4, value=20 - objetivos_dura[medio])
            fila += 1
    dv_estado = DataValidation(type="list", formula1='"Pendiente,En progreso,Completo"')
    ws_grid.add_data_validation(dv_estado)
    dv_estado.add(f"J5:J{fila - 1}")

    wb.create_sheet("Resumen")
    wb.create_sheet("Leyenda")

    ws = wb.create_sheet("Corpus - oraciones")
    headers = [
        "articulo_id", "oracion_id", "medio", "tema", "género\n(dura/opinión)",
        "fecha_\npublicación", "oracion_texto", "oracion_anterior", "oracion_siguiente",
    ]
    for categoria in CATEGORIAS_BOOL_SPAN:
        headers.append(categoria)
        headers.append(f"{categoria}_span")
    headers += [
        "direccion", "actor_objetivo", "intensidad_lexica", "camuflaje_epistemico",
        "aux: primera\nfila de la\noración (no editar)",
    ]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=4, column=i, value=h)
    assert len(headers) == 32  # A..AF (COLUMNA_AUX); AG (url_fuente) lo agrega escribir_filas
    ws.merge_cells("A1:AF1")
    ws.merge_cells("A2:AF2")
    ws["A1"] = "Grid de recolección — 500 oraciones"
    ws["A2"] = "Celdas amarillas = editables."

    # Filas de ejemplo protegidas (5-7), imitando el archivo real.
    ws["A5"], ws["B5"] = "ART_0231", "ART_0231_S07"
    ws["C5"], ws["D5"], ws["E5"] = "El Tiempo", TEMAS[0], "Noticia dura"
    ws["G5"] = "Oración de ejemplo con hallazgo léxico y discursivo."
    ws["AF5"] = "=IF(COUNTIF($B$5:B5,B5)=1,1,0)"

    ws["A6"], ws["B6"] = "ART_0198", "ART_0198_S02"
    ws["C6"], ws["D6"], ws["E6"] = "El Espectador", TEMAS[3], "Opinión-análisis"
    ws["G6"] = "Oración de ejemplo con hallazgo solo discursivo."
    ws["AF6"] = "=IF(COUNTIF($B$5:B6,B6)=1,1,0)"

    ws["A7"], ws["B7"] = "ART_0245", "ART_0245_S03"
    ws["C7"], ws["D7"], ws["E7"] = "El Tiempo", TEMAS[0], "Noticia dura"
    ws["G7"] = "Oración de ejemplo neutral."
    ws["AF7"] = "=IF(COUNTIF($B$5:B7,B7)=1,1,0)"

    for fila in range(8, 20 + 1):
        ws.cell(row=fila, column=32, value=f"=IF(COUNTIF($B$5:B{fila},B{fila})=1,1,0)")

    dv_medio = DataValidation(type="list", formula1=f'"{",".join(MEDIOS)}"')
    dv_tema = DataValidation(type="list", formula1=f'"{",".join(TEMAS)}"')
    dv_genero = DataValidation(type="list", formula1=f'"{",".join(GENEROS)}"')
    ws.add_data_validation(dv_medio); dv_medio.add("C5:C20")
    ws.add_data_validation(dv_tema); dv_tema.add("D5:D20")
    ws.add_data_validation(dv_genero); dv_genero.add("E5:E20")

    dv_bool = DataValidation(type="list", formula1='"TRUE,FALSE"')
    ws.add_data_validation(dv_bool)
    for i, _categoria in enumerate(CATEGORIAS_BOOL_SPAN):
        col_bool = 10 + i * 2  # J, L, N, P, R, T, V, X, Z
        dv_bool.add(f"{openpyxl.utils.get_column_letter(col_bool)}5:{openpyxl.utils.get_column_letter(col_bool)}20")

    dv_direccion = DataValidation(type="list", formula1='"favorece,perjudica,neutral"')
    ws.add_data_validation(dv_direccion)
    dv_direccion.add("AB5:AB20")

    dv_intensidad = DataValidation(type="whole", operator="between", formula1="1", formula2="5")
    ws.add_data_validation(dv_intensidad)
    dv_intensidad.add("AD5:AD20")
    dv_intensidad.add("AE5:AE20")

    return wb
