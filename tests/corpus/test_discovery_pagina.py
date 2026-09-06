"""Regresión: el RSS de opinión de El Tiempo está dominado por caricaturas (10 items);
su página /opinion/ enlaza columnas de texto reales que el RSS nunca expone. Este test
verifica el filtrado de enlaces de página sin hacer ninguna llamada de red real."""
from sesgocognitivo.corpus.discovery import extraer_enlaces_de_pagina

HTML_PAGINA_OPINION = """
<html><body>
<a href="/opinion/columnistas/un-ministro-valiente-3582272">Un ministro valiente</a>
<a href="/opinion/editorial/el-costo-de-la-verdad-3583457">El costo de la verdad</a>
<a href="/opinion/cartas/las-fotomultas-3583474">Las fotomultas (carta)</a>
<a href="/opinion/caricaturas/son-buenisimos-3583782">Caricatura</a>
<a href="/opinion/editorial">Editorial (categoría, sin slug)</a>
<a href="/opinion/mas-opinion">Más opinión (nav)</a>
<a href="/politica/otra-noticia-cualquiera">Noticia no relacionada</a>
</body></html>
"""


def test_extraer_enlaces_de_pagina_filtra_categorias_vacias_y_excluidos(monkeypatch):
    import sesgocognitivo.corpus.discovery as discovery_mod

    class RespuestaFalsa:
        text = HTML_PAGINA_OPINION

        def raise_for_status(self):
            return None

    monkeypatch.setattr(discovery_mod.requests, "get", lambda *a, **k: RespuestaFalsa())

    enlaces = extraer_enlaces_de_pagina(
        "https://www.eltiempo.com/opinion",
        patrones_incluir=("/opinion/columnistas/", "/opinion/editorial/"),
        patrones_excluir=("/opinion/caricaturas/",),
    )

    assert any("un-ministro-valiente" in e for e in enlaces)
    assert any("el-costo-de-la-verdad" in e for e in enlaces)
    assert not any("cartas" in e for e in enlaces)
    assert not any("caricaturas" in e for e in enlaces)
    assert not any(e.endswith("/opinion/editorial") for e in enlaces)
    assert not any("mas-opinion" in e for e in enlaces)
    assert not any("otra-noticia-cualquiera" in e for e in enlaces)
