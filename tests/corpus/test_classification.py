import openpyxl

from sesgocognitivo.corpus.classification import clasificar_tema, inferir_genero
from sesgocognitivo.corpus.config_loader import load_medios, load_temas
from sesgocognitivo.corpus.excel_writer import leer_valores_permitidos
from sesgocognitivo.common.paths import CORPUS_CONFIG_DIR as CONFIG_DIR


def test_temas_yaml_nombres_coinciden_con_dropdown_real(fixture_wb_path):
    """Si alguien edita temas.yaml (o el Excel) y los nombres divergen, esto falla en vez
    de corromper silenciosamente filas del corpus real."""
    wb = openpyxl.load_workbook(fixture_wb_path)
    ws = wb["Corpus - oraciones"]
    nombres_dropdown = set(leer_valores_permitidos(ws, "D"))
    nombres_yaml = {t.nombre for t in load_temas()}
    assert nombres_dropdown == nombres_yaml


def test_medios_yaml_nombres_coinciden_con_dropdown_real(fixture_wb_path):
    """Cada dominio tiene su propio yaml de medios; todos deben usar exactamente los
    mismos nombres del dropdown (Deportes es la excepción: no incluye La Silla Vacía,
    que no tiene cobertura deportiva, así que es un subconjunto)."""
    wb = openpyxl.load_workbook(fixture_wb_path)
    ws = wb["Corpus - oraciones"]
    nombres_dropdown = set(leer_valores_permitidos(ws, "C"))
    for archivo in sorted(CONFIG_DIR.glob("medios_*.yaml")):
        nombres_yaml = {m.nombre for m in load_medios(archivo)}
        assert nombres_yaml <= nombres_dropdown, f"{archivo.name} tiene medios fuera del dropdown"
    assert {m.nombre for m in load_medios(CONFIG_DIR / "medios_salud.yaml")} == nombres_dropdown


def test_clasificar_tema_por_keyword():
    temas = load_temas()
    tema = clasificar_tema(
        "Los sindicatos y el Gobierno discuten el aumento del salario mínimo y la reforma laboral.",
        temas,
    )
    assert tema is not None
    assert tema.id == "economia"


def test_clasificar_tema_sin_coincidencia_devuelve_none():
    temas = load_temas()
    assert clasificar_tema("Receta de arroz con pollo para el domingo.", temas) is None


def test_clasificar_tema_no_lo_absorbe_una_mencion_de_paso_de_otro_dominio():
    """Regresión: una nota de salud que menciona de paso al ministro de Ambiente no debe
    irse a medio_ambiente solo porque esa keyword aparezca. Gana el dominio con más
    ocurrencias, no el que quede primero en la lista de config."""
    temas = load_temas()
    texto = (
        "La crisis de las EPS volvió a escalar: la reforma a la salud sigue trabada y el "
        "Gobierno insiste en liquidar las EPS intervenidas. Varias EPS acumulan deudas y "
        "la crisis de las EPS golpea a los pacientes. En la misma sesión habló el ministro "
        "de ambiente sobre un tema distinto."
    )
    tema = clasificar_tema(texto, temas)
    assert tema is not None
    assert tema.id == "salud"


def test_clasificar_tema_ocurrencias_totales_desempatan_coincidencias_distintas_empatadas():
    """Regresión: contar keywords DISTINTAS (presencia) deja empates que se resuelven por
    orden de config, mandando el artículo al tema equivocado. Contando ocurrencias TOTALES
    gana el dominio realmente dominante del texto."""
    temas = load_temas()
    texto = (
        "El fracking volvió al debate: el ministro de ambiente defendió el fracking con "
        "pilotos regulados y la deforestación sigue creciendo. El fracking cerca del "
        "páramo de santurbán preocupa a las comunidades. En un párrafo aparte se citó la "
        "reforma laboral y a los sindicatos como contexto económico del anuncio."
    )
    tema = clasificar_tema(texto, temas)
    assert tema is not None
    assert tema.id == "medio_ambiente"


def test_clasificar_tema_no_matchea_texto_sin_relacion_con_ningun_dominio():
    """Regresión: keywords demasiado genéricas ('seguridad', 'salario mínimo' a secas)
    matcheaban textos de otro tema. Un texto sin relación real debe devolver None."""
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
