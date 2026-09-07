"""Regresión: se encontró revisando El Espectador que algunos artículos de una categoría
ya validada (paywall "Premium" aplicado a solo una parte del contenido, no a la sección
entera) devuelven un cuerpo vacío o muy corto. procesar_articulo debe descartarlos antes de
clasificar/segmentar, no producir oraciones parciales de una nota truncada."""
from sesgocognitivo.corpus.classification import GENERO_DURA, GENERO_OPINION
from sesgocognitivo.corpus.collector import MIN_CUERPO_ARTICULO, procesar_articulo
from sesgocognitivo.corpus.config_loader import MedioConfig, load_temas
from sesgocognitivo.corpus.grid_tracker import GridState, ObjetivoCelda


def _medio_falso():
    return MedioConfig(
        id="falso", nombre="Infobae Colombia", home="https://example.test/",
        descubrir=False, feeds={},
    )


def _tracker_vacio():
    return GridState(objetivos={
        ("Infobae Colombia", "Seguridad y orden público"): ObjetivoCelda(
            "Infobae Colombia", "Seguridad y orden público", 14, 6
        )
    })


def test_procesar_articulo_descarta_cuerpo_corto(monkeypatch):
    import sesgocognitivo.corpus.collector as collector_mod

    texto_corto = "Nota breve." * 5  # muy por debajo de MIN_CUERPO_ARTICULO
    assert len(texto_corto) < MIN_CUERPO_ARTICULO
    monkeypatch.setattr(collector_mod, "extraer_cuerpo", lambda url, timeout=15: texto_corto)

    filas = procesar_articulo(
        "https://example.test/nota-truncada", _medio_falso(), GENERO_DURA, [], lambda t: [t], _tracker_vacio()
    )
    assert filas == []


def test_procesar_articulo_no_reprocesa_articulo_ya_visto(monkeypatch):
    """Regresión: un articulo_id ya registrado bajo CUALQUIER (tema,genero) no debe
    volver a extraerse/segmentarse, ni siquiera bajo un género distinto."""
    import sesgocognitivo.corpus.collector as collector_mod

    llamadas = []
    monkeypatch.setattr(
        collector_mod, "extraer_cuerpo",
        lambda url, timeout=15: (llamadas.append(url) or "x" * (MIN_CUERPO_ARTICULO + 10)),
    )

    tracker = _tracker_vacio()
    url = "https://example.test/ART_Y"
    aid = tracker.obtener_o_asignar_articulo_id(url)
    tracker.registrar("Infobae Colombia", "Seguridad y orden público", GENERO_DURA, [f"{aid}_S01"], aid)

    filas = procesar_articulo(url, _medio_falso(), GENERO_OPINION, [], lambda t: [t], tracker)
    assert filas == []
    assert llamadas == []  # ni siquiera se llegó a extraer el cuerpo


def test_procesar_articulo_completa_fecha_con_jsonld_si_no_llega_del_llamador(monkeypatch):
    """Regresión: recolectar_de_pagina/recolectar_manual no tienen metadata de feed y
    pasaban fecha=None -- procesar_articulo debe rellenarla con extraer_fecha_publicacion
    en vez de dejar la columna F vacía."""
    import sesgocognitivo.corpus.collector as collector_mod
    from sesgocognitivo.corpus.config_loader import load_temas

    texto_largo = "El Gobierno anunció un nuevo estatuto antiterrorista contra grupos armados. " * 15
    monkeypatch.setattr(collector_mod, "extraer_cuerpo", lambda url, timeout=15: texto_largo)
    monkeypatch.setattr(collector_mod, "extraer_fecha_publicacion", lambda url, timeout=15: "2026-08-01T00:00:00-05:00")

    filas = procesar_articulo(
        "https://example.test/nota-sin-fecha", _medio_falso(), GENERO_DURA, load_temas(),
        lambda t: [t], _tracker_vacio(),
        fecha=None,
    )
    assert len(filas) == 1
    assert filas[0].fecha_publicacion == "2026-08-01T00:00:00-05:00"


def test_procesar_articulo_no_pisa_fecha_ya_provista_por_el_feed(monkeypatch):
    """El caso común (RSS) ya trae `published` -- no debe llamar a extraer_fecha_publicacion."""
    import sesgocognitivo.corpus.collector as collector_mod
    from sesgocognitivo.corpus.config_loader import load_temas

    texto_largo = "El Gobierno anunció un nuevo estatuto antiterrorista contra grupos armados. " * 15
    monkeypatch.setattr(collector_mod, "extraer_cuerpo", lambda url, timeout=15: texto_largo)

    def _no_deberia_llamarse(url, timeout=15):
        raise AssertionError("no debería llamarse cuando ya hay fecha del feed")

    monkeypatch.setattr(collector_mod, "extraer_fecha_publicacion", _no_deberia_llamarse)

    filas = procesar_articulo(
        "https://example.test/nota-con-fecha", _medio_falso(), GENERO_DURA, load_temas(),
        lambda t: [t], _tracker_vacio(),
        fecha="2026-07-01T00:00:00-05:00",
    )
    assert filas[0].fecha_publicacion == "2026-07-01T00:00:00-05:00"


def test_procesar_articulo_filtra_boilerplate_entre_oraciones_reales(monkeypatch):
    """Regresión de auditoría 2026-09-05: el disclaimer fijo de La Silla Vacía
    ("Este es un espacio de debate que no compromete...") apareció como primera oración en
    las 5 columnas de opinión recolectadas de ese medio -- viene dentro del articleBody de
    JSON-LD sin marca que lo distinga, así que el filtro debe aplicarse a nivel de oración
    ya segmentada, no solo a nivel de párrafo <p> (que nunca corre para JSON-LD)."""
    import sesgocognitivo.corpus.collector as collector_mod
    from sesgocognitivo.corpus.config_loader import load_temas

    oraciones_falsas = [
        "Este es un espacio de debate que no compromete la opinión de La Silla Vacía ni de sus aliados.",
        "El Gobierno anunció un nuevo estatuto antiterrorista contra los grupos armados del país.",
        "La medida busca frenar el avance de estructuras criminales en varias regiones.",
    ]
    # clasificar_tema opera sobre el texto CRUDO extraído, no sobre `oraciones_falsas` --
    # debe contener las keywords del tema para que procesar_articulo llegue al filtro que
    # este test quiere probar (si no, "tema is None" corta la función antes de segmentar).
    monkeypatch.setattr(
        collector_mod, "extraer_cuerpo",
        lambda url, timeout=15: "estatuto antiterrorista grupos armados. " * 20,
    )

    def segmentar_falso(_texto):
        return oraciones_falsas

    filas = procesar_articulo(
        "https://example.test/columna-opinion", _medio_falso(), GENERO_OPINION, load_temas(),
        segmentar_falso, _tracker_vacio(),
    )
    textos = [f.oracion_texto for f in filas]
    assert not any("espacio de debate" in t for t in textos)
    assert any("estatuto antiterrorista" in t for t in textos)
    # El disclaimer filtrado no debe quedar colgado como "oracion_anterior" de la primera fila real
    assert filas[0].oracion_anterior == ""


def test_procesar_articulo_descarta_oracion_repetida_consecutiva(monkeypatch):
    """Regresión: un artículo de El Tiempo trajo la misma oración repetida dos veces
    seguidas tras la segmentación (artefacto de la fuente) -- eso duplicaba contenido
    idéntico dentro de un mismo artículo, distinto del bug de oracion_id repetido entre
    corridas separadas (ver test_grid_tracker / test_excel_writer)."""
    import sesgocognitivo.corpus.collector as collector_mod
    from sesgocognitivo.corpus.config_loader import load_temas

    repetida = "El movimiento de Reddington se produce después de que ayer pidiera al juez la retirada de un miembro del jurado."
    oraciones_falsas = [
        "El juez declaró la nulidad del juicio tras no llegar a un veredicto unánime.",
        repetida,
        repetida,
        "El caso continuará con un nuevo jurado en las próximas semanas.",
    ]
    monkeypatch.setattr(
        collector_mod, "extraer_cuerpo",
        lambda url, timeout=15: "estatuto antiterrorista grupos armados. " * 20,
    )

    filas = procesar_articulo(
        "https://example.test/nota-judicial", _medio_falso(), GENERO_DURA, load_temas(),
        lambda _t: oraciones_falsas, _tracker_vacio(),
    )
    textos = [f.oracion_texto for f in filas]
    assert textos.count(repetida) == 1


def test_procesar_articulo_acepta_cuerpo_normal(monkeypatch):
    import sesgocognitivo.corpus.collector as collector_mod

    texto_largo = (
        "El Gobierno anunció un nuevo estatuto antiterrorista contra grupos armados. " * 15
    )
    assert len(texto_largo) >= MIN_CUERPO_ARTICULO
    monkeypatch.setattr(collector_mod, "extraer_cuerpo", lambda url, timeout=15: texto_largo)

    filas = procesar_articulo(
        "https://example.test/nota-completa", _medio_falso(), GENERO_DURA, load_temas(),
        lambda t: [t], _tracker_vacio(),
    )
    assert len(filas) == 1
    assert filas[0].tema == "Seguridad y orden público"
