"""Rutas del proyecto, resueltas relativas a la raíz del repo (no al cwd)."""
from pathlib import Path

# src/sesgocognitivo/common/paths.py -> sube 3 niveles hasta la raíz del repo.
REPO_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = REPO_ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
MANUAL_URLS_DIR = CORPUS_DIR / "manual_urls"
LOGS_DIR = REPO_ROOT / "logs"

# Workbook único del corpus: 4 hojas (Grid de recoleccion, Resumen, Leyenda,
# Corpus - oraciones) con las 500 oraciones de los 5 dominios.
CORPUS_XLSX = CORPUS_DIR / "corpus_multidominio_500_oraciones.xlsx"

CORPUS_CONFIG_DIR = Path(__file__).resolve().parents[1] / "corpus" / "config"
TEMAS_YAML = CORPUS_CONFIG_DIR / "temas.yaml"
# No hay un medios.yaml por defecto: cada dominio tiene sus propios feeds
# (medios_economia.yaml, medios_salud.yaml, medios_medioambiente.yaml,
# medios_deportes.yaml) y el CLI exige elegir uno con --config-medios.
