import openpyxl

from sesgocognitivo.corpus.grid_tracker import GENERO_DURA, GENERO_OPINION, GridState


def test_lee_objetivos_y_conteos_iniciales(fixture_wb_path):
    wb = openpyxl.load_workbook(fixture_wb_path)
    tracker = GridState.desde_workbook(wb)

    medio, tema = "El Tiempo", "Transición de gobierno y relación con la oposición"
    assert tracker.objetivo(medio, tema, GENERO_DURA) == 14
    # Las filas 5-7 son el ejemplo protegido (ART_0231/ART_0245) y NO deben contarse -- a
    # diferencia de la fórmula SUMIFS real de la hoja Grid, que sí las cuenta por accidente
    # (de ahí que el archivo real muestre H10=2). El tracker solo mira filas >= 8.
    assert tracker.n_oraciones(medio, tema, GENERO_DURA) == 0
    assert not tracker.esta_llena(medio, tema, GENERO_DURA)
    assert tracker.restante(medio, tema, GENERO_DURA) == 14


def test_celda_sin_datos_previos_no_esta_llena(fixture_wb_path):
    wb = openpyxl.load_workbook(fixture_wb_path)
    tracker = GridState.desde_workbook(wb)
    medio, tema = "Semana", "Seguridad y orden público"
    assert tracker.n_oraciones(medio, tema, GENERO_OPINION) == 0
    assert tracker.restante(medio, tema, GENERO_OPINION) == 10
    assert not tracker.esta_llena(medio, tema, GENERO_OPINION)


def test_registrar_actualiza_conteo_en_memoria(fixture_wb_path):
    wb = openpyxl.load_workbook(fixture_wb_path)
    tracker = GridState.desde_workbook(wb)
    medio, tema = "Semana", "Seguridad y orden público"

    tracker.registrar(medio, tema, GENERO_OPINION, [f"X_S{i:02d}" for i in range(1, 11)], "X")
    assert tracker.n_oraciones(medio, tema, GENERO_OPINION) == 10
    assert tracker.esta_llena(medio, tema, GENERO_OPINION)
    assert tracker.restante(medio, tema, GENERO_OPINION) == 0


def test_resumen_texto_no_revienta(fixture_wb_path):
    wb = openpyxl.load_workbook(fixture_wb_path)
    tracker = GridState.desde_workbook(wb)
    texto = tracker.resumen_texto()
    assert "TOTAL:" in texto


def test_articulo_ya_procesado_es_independiente_de_tema_y_genero(fixture_wb_path):
    """Regresión: un artículo cross-listado en dos categorías del mismo medio (ej. El
    Espectador en "opinion" y "judicial" a la vez) no debe poder recolectarse dos veces con
    un género distinto cada vez -- la dedup por (medio,tema,genero) sola no lo detecta."""
    wb = openpyxl.load_workbook(fixture_wb_path)
    tracker = GridState.desde_workbook(wb)
    medio, tema = "Semana", "Seguridad y orden público"

    assert not tracker.articulo_ya_procesado(medio, "ART_X")
    tracker.registrar(medio, tema, GENERO_DURA, ["ART_X_S01", "ART_X_S02"], "ART_X")
    assert tracker.articulo_ya_procesado(medio, "ART_X")
    # Mismo articulo_id, pero consultado para un género/tema distinto: sigue marcado.
    assert tracker.articulo_ya_procesado(medio, "ART_X")
    # Un medio distinto con el mismo articulo_id no debe verse afectado.
    assert not tracker.articulo_ya_procesado("El Tiempo", "ART_X")


def test_asigna_ids_cortos_secuenciales_por_url(fixture_wb_path):
    """Regresión de usabilidad 2026-09-07: articulo_id/oracion_id eran la URL completa,
    impracticable de referenciar. Ahora se asignan ids cortos (ART_001, ART_002...) -- la
    URL real sigue viviendo aparte en la columna url_fuente, así que no se pierde nada."""
    wb = openpyxl.load_workbook(fixture_wb_path)
    tracker = GridState.desde_workbook(wb)

    id1 = tracker.obtener_o_asignar_articulo_id("https://example.test/nota-a")
    id2 = tracker.obtener_o_asignar_articulo_id("https://example.test/nota-b")
    assert id1 == "ART_001"
    assert id2 == "ART_002"
    # La misma URL consultada de nuevo devuelve el mismo id, no uno nuevo.
    assert tracker.obtener_o_asignar_articulo_id("https://example.test/nota-a") == id1


def test_numeracion_continua_desde_ids_ya_presentes_en_la_hoja(fixture_wb_path):
    """Si la hoja ya trae ART_005 de una corrida anterior, la siguiente URL nueva debe
    recibir ART_006, no reiniciar ni colisionar."""
    from sesgocognitivo.corpus.excel_writer import COLUMNA_URL

    wb = openpyxl.load_workbook(fixture_wb_path)
    ws = wb["Corpus - oraciones"]
    ws["A8"] = "ART_005"
    ws["B8"] = "ART_005_S01"
    ws["C8"] = "Semana"
    ws["D8"] = "Seguridad y orden público"
    ws["E8"] = "Noticia dura"
    ws[f"{COLUMNA_URL}8"] = "https://example.test/ya-existente"

    tracker = GridState.desde_workbook(wb)
    assert tracker.obtener_o_asignar_articulo_id("https://example.test/ya-existente") == "ART_005"
    assert tracker.obtener_o_asignar_articulo_id("https://example.test/nota-nueva") == "ART_006"
