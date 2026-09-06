"""Rutas del proyecto, resueltas relativas a la raíz del repo (no al cwd)."""
from pathlib import Path

# src/sesgocognitivo/common/paths.py -> sube 3 niveles hasta la raíz del repo.
REPO_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = REPO_ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
MANUAL_URLS_DIR = CORPUS_DIR / "manual_urls"
LOGS_DIR = REPO_ROOT / "logs"

GRID_XLSX = CORPUS_DIR / "grid_recoleccion_500_oraciones.xlsx"

CORPUS_CONFIG_DIR = Path(__file__).resolve().parents[1] / "corpus" / "config"
TEMAS_YAML = CORPUS_CONFIG_DIR / "temas.yaml"
MEDIOS_YAML = CORPUS_CONFIG_DIR / "medios.yaml"
