"""Regresión del bug real encontrado en la primera corrida contra Infobae/El Tiempo: la
heurística ingenua de <p> devolvía bylines, "PUBLICIDAD" y -- en El Tiempo -- puro chrome de
cookies/cuenta de usuario en vez del cuerpo del artículo. Usa HTML sintético (sin red)."""
from sesgocognitivo.corpus.extraction import (
    _articlebody_desde_jsonld,
    es_texto_ruido,
    _fecha_desde_jsonld,
    extraer_cuerpo,
    extraer_fecha_publicacion,
)
from bs4 import BeautifulSoup

HTML_CON_JSONLD = """
<html><head>
<script type="application/ld+json">
{"@type": "NewsArticle", "datePublished": "2026-08-29T23:15:00-05:00", "articleBody": "Primer párrafo real del artículo con suficiente longitud de texto para pasar el umbral mínimo establecido en la extracción. Segundo párrafo, también real, continuando la nota periodística de prueba con más detalle para asegurar longitud suficiente."}
</script>
</head><body>
<article><p>Por Fulano de Tal</p><p>PUBLICIDAD</p></article>
</body></html>
"""

HTML_CON_GRAPH = """
<html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "BreadcrumbList", "itemListElement": []},
  {"@type": "NewsArticle", "datePublished": "2026-08-15T10:00:00-05:00", "articleBody": "Primer párrafo real del artículo envuelto en la propiedad @graph, con longitud de texto suficiente para superar el umbral mínimo establecido en la extracción de cuerpo. Segundo párrafo también real, continuando la nota periodística de prueba con más detalle para asegurar longitud total suficiente."}
]}
</script>
</head><body>
<article><p>Por Fulano de Tal</p></article>
</body></html>
"""

HTML_SOLO_P_CON_RUIDO = """
<html><body>
<div class="chrome"><p>PUBLICIDAD</p><p>Por Fulano de Tal</p></div>
<div class="cuerpo">
<p>Este es el primer párrafo real de la noticia, con contenido periodístico genuino y largo.</p>
<p>Este es el segundo párrafo real, continuando con más detalles sustanciales de la nota.</p>
<p>Un tercer párrafo real que aporta contexto adicional relevante para el lector interesado.</p>
</div>
<div class="cookies"><p>Utilizamos cookies propias y de terceros para mejorar su experiencia de navegación.</p></div>
</body></html>
"""


def test_jsonld_tiene_prioridad_sobre_p():
    soup = BeautifulSoup(HTML_CON_JSONLD, "html.parser")
    cuerpo = _articlebody_desde_jsonld(soup)
    assert cuerpo is not None
    assert "Primer párrafo real" in cuerpo
    assert "PUBLICIDAD" not in cuerpo
    assert "Por Fulano" not in cuerpo


def test_jsonld_desempaqueta_graph():
    """Regresión de auditoría 2026-09-05: 2 filas reales de La Silla Vacía (plantilla "Red
    de Expertos") quedaron sin fecha_publicacion porque su JSON-LD envuelve los items en
    `{"@graph": [...]}` en vez de exponerlos como lista plana u objeto único -- ninguna de
    las dos formas que _items_jsonld manejaba antes. El cuerpo casi no se notó porque cayó
    al fallback de <p> por pura coincidencia; la fecha simplemente se perdía en silencio."""
    soup = BeautifulSoup(HTML_CON_GRAPH, "html.parser")
    cuerpo = _articlebody_desde_jsonld(soup)
    assert cuerpo is not None
    assert "Primer párrafo real" in cuerpo
    assert _fecha_desde_jsonld(soup) == "2026-08-15T10:00:00-05:00"


def test_fecha_desde_jsonld():
    """Regresión de auditoría 2026-09-05: 32 filas del corpus real (recolectadas vía
    recolectar_de_pagina/recolectar_manual, que no tienen metadata de feed) quedaron sin
    fecha_publicacion porque nadie extraía datePublished del JSON-LD -- misma fuente que
    ya se usa para el cuerpo del artículo."""
    soup = BeautifulSoup(HTML_CON_JSONLD, "html.parser")
    assert _fecha_desde_jsonld(soup) == "2026-08-29T23:15:00-05:00"


def test_extraer_fecha_publicacion_via_red(monkeypatch):
    import sesgocognitivo.corpus.extraction as extraction_mod

    class RespuestaFalsa:
        text = HTML_CON_JSONLD

        def raise_for_status(self):
            return None

    monkeypatch.setattr(extraction_mod.requests, "get", lambda *a, **k: RespuestaFalsa())
    assert extraer_fecha_publicacion("https://ejemplo.test/nota") == "2026-08-29T23:15:00-05:00"


def test_filtro_de_ruido_descarta_byline_y_publicidad():
    assert es_texto_ruido("Por Fulano de Tal")
    assert es_texto_ruido("PUBLICIDAD")
    # Regresión de auditoría 2026-09-05: columna de "Red de Expertos" de La Silla Vacía
    # con esta atribución de columnista invitado como primera "oración" segmentada --
    # distinta de "Por Fulano" (patrón ya cubierto), casi se cuela como la fila 500ª del
    # corpus real en vez del primer enunciado real de la columna.
    assert es_texto_ruido("Esta columna fue escrita por el columnista invitado Enrique Sanz Posse.")
    assert es_texto_ruido("Fuente: Dow Jones.")
    assert es_texto_ruido(
        "Este es un espacio de debate que no compromete la opinión de La Silla Vacía ni de sus aliados."
    )
    assert es_texto_ruido("Utilizamos cookies propias y de terceros.")
    assert not es_texto_ruido("Este es un párrafo real de contenido periodístico genuino.")


def test_fallback_de_parrafos_elige_el_contenedor_principal(monkeypatch):
    import sesgocognitivo.corpus.extraction as extraction_mod

    class RespuestaFalsa:
        text = HTML_SOLO_P_CON_RUIDO

        def raise_for_status(self):
            return None

    monkeypatch.setattr(extraction_mod.requests, "get", lambda *a, **k: RespuestaFalsa())

    cuerpo = extraer_cuerpo("https://ejemplo.test/nota")
    assert "primer párrafo real" in cuerpo
    assert "segundo párrafo real" in cuerpo
    assert "PUBLICIDAD" not in cuerpo
    assert "Por Fulano" not in cuerpo
    assert "cookies" not in cuerpo.lower()
