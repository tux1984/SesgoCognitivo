"""Tests dirigidos del segmentador. No se prueba la descarga real de sat-12l-sm aquí (~1.1GB,
demasiado lento/costoso para un test unitario) -- eso se valida en la corrida real de
'calentamiento' documentada en el README. Aquí solo se verifica el contrato de la función y
que el fallback forzado a spaCy funcione y quede marcado como tal.
"""
from sesgocognitivo.corpus.segmentation import get_segmenter


def test_forzar_spacy_devuelve_backend_spacy():
    segmentar, backend = get_segmenter(forzar_spacy=True)
    assert backend == "spacy"
    oraciones = segmentar("Hola. Esta es una prueba simple.")
    assert isinstance(oraciones, list)
    assert len(oraciones) >= 1


def test_segmentador_devuelve_lista_de_strings_no_vacias():
    segmentar, _ = get_segmenter(forzar_spacy=True)
    oraciones = segmentar("Primera oración.   Segunda oración con espacios raros.  ")
    assert all(isinstance(o, str) and o for o in oraciones)
