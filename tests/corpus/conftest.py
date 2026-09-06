import pytest

from tests.corpus._fixture_builder import build_fixture_workbook


@pytest.fixture()
def fixture_wb_path(tmp_path):
    """Un .xlsx sintético (misma estructura relevante que el archivo real) en un tmp_path
    nuevo por test -- nunca se toca data/corpus/grid_recoleccion_500_oraciones.xlsx."""
    wb = build_fixture_workbook()
    ruta = tmp_path / "grid_recoleccion_mini.xlsx"
    wb.save(ruta)
    return ruta
