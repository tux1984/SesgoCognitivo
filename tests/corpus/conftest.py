import pytest

from tests.corpus._fixture_builder import build_fixture_workbook


@pytest.fixture()
def fixture_wb_path(tmp_path):
    """Un .xlsx sintético (misma estructura relevante que el archivo real) en un tmp_path
    nuevo por test -- nunca se toca data/corpus/corpus_multidominio_500_oraciones.xlsx."""
    wb = build_fixture_workbook()
    ruta = tmp_path / "corpus_mini.xlsx"
    wb.save(ruta)
    return ruta
