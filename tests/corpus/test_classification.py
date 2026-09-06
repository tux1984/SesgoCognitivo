import openpyxl

from sesgocognitivo.corpus.classification import clasificar_tema, inferir_genero
from sesgocognitivo.corpus.config_loader import load_medios, load_temas
from sesgocognitivo.corpus.excel_writer import leer_valores_permitidos


def test_temas_yaml_nombres_coinciden_con_dropdown_real(fixture_wb_path):
    """Si alguien edita temas.yaml (o el Excel) y los nombres divergen, esto falla en vez
    de corromper silenciosamente filas del corpus real."""
    wb = openpyxl.load_workbook(fixture_wb_path)
    ws = wb["Corpus - oraciones"]
    nombres_dropdown = set(leer_valores_permitidos(ws, "D"))
    nombres_yaml = {t.nombre for t in load_temas()}
    assert nombres_dropdown == nombres_yaml


def test_medios_yaml_nombres_coinciden_con_dropdown_real(fixture_wb_path):
    wb = openpyxl.load_workbook(fixture_wb_path)
    ws = wb["Corpus - oraciones"]
    nombres_dropdown = set(leer_valores_permitidos(ws, "C"))
    nombres_yaml = {m.nombre for m in load_medios()}
    assert nombres_dropdown == nombres_yaml


def test_clasificar_tema_por_keyword():
    temas = load_temas()
    tema = clasificar_tema("El presidente habló de la reforma pensional en el congreso.", temas)
    assert tema is not None
    assert tema.id == "reformas_sociales"


def test_clasificar_tema_sin_coincidencia_devuelve_none():
    temas = load_temas()
    assert clasificar_tema("Receta de arroz con pollo para el domingo.", temas) is None


def test_clasificar_tema_no_lo_absorbe_la_mencion_generica_del_presidente():
    """Regresión: 'de la espriella' (keyword de Transición) aparece en casi cualquier nota
    política porque es el presidente. Un texto con más coincidencias específicas de otro
    tema debe ganarle, no perder por estar Transición primero en la lista de config."""
    temas = load_temas()
    texto = (
        "El presidente De la Espriella se reunió con funcionarios de Estados Unidos en "
        "Washington para discutir aranceles con el enviado de Trump."
    )
    tema = clasificar_tema(texto, temas)
    assert tema is not None
    assert tema.id == "relacion_eeuu"


def test_clasificar_tema_ocurrencias_totales_desempatan_coincidencias_distintas_empatadas():
    """Regresión: un artículo sobre embajadores/diplomacia con EE.UU. mencionaba de pasada
    'ayuda de emergencia enviada tras el sismo', empatando 4 keywords DISTINTAS con
    'terremoto' y 4 con 'relacion_eeuu'. Contando ocurrencias TOTALES (no solo presencia),
    el tema realmente dominante (EE.UU./Washington, mencionado muchas veces) debe ganar."""
    temas = load_temas()
    texto = (
        "Los embajadores designados ante Estados Unidos y Naciones Unidas se preparan. "
        "Washington y Nueva York serán los escenarios centrales de la agenda con Estados "
        "Unidos. El enviado de Rubio y las conversaciones sobre aranceles con Washington "
        "marcarán el rumbo. También se mencionó la ayuda de emergencia enviada tras el "
        "sismo, parte de la reconstrucción por el terremoto, como un punto secundario de "
        "la agenda de Estados Unidos."
    )
    tema = clasificar_tema(texto, temas)
    assert tema is not None
    assert tema.id == "relacion_eeuu"


def test_clasificar_tema_no_matchea_seguridad_alimentaria_como_seguridad_publica():
    """Regresión: 'seguridad' a secas se quitó de las keywords del tema porque matcheaba
    'seguridad alimentaria' en un artículo de biodiversidad sin relación con orden público."""
    temas = load_temas()
    texto = (
        "El estudio identificó especies de peces migratorios de las que depende la "
        "seguridad alimentaria de las comunidades locales en la Amazonía."
    )
    assert clasificar_tema(texto, temas) is None


def test_inferir_genero_por_categoria_red_de_expertos():
    """Regresión: La Silla Vacía comparte un único feed para dura/opinión; su categoría
    'Red de Expertos' debe mapear a Opinión-análisis, no quedarse en el género por defecto."""
    genero = inferir_genero(
        "https://lasillavacia.com/red-de-expertos/red-rural/algo",
        categoria="Red de Expertos",
        genero_por_defecto="Noticia dura",
    )
    assert genero == "Opinión-análisis"


def test_inferir_genero_por_categoria_en_vivo_es_dura():
    genero = inferir_genero(
        "https://lasillavacia.com/en-vivo/algo-que-paso",
        categoria="En Vivo",
        genero_por_defecto="Noticia dura",
    )
    assert genero == "Noticia dura"


def test_inferir_genero_por_url_cuando_no_hay_categoria():
    genero = inferir_genero(
        "https://www.semana.com/opinion/columnista/articulo/titulo",
        categoria=None,
        genero_por_defecto="Noticia dura",
    )
    assert genero == "Opinión-análisis"
