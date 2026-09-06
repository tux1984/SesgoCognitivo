"""Configuración de logging compartida por todos los bloques del proyecto."""
import logging
import sys

from sesgocognitivo.common.paths import LOGS_DIR


def setup_logging(nombre_log: str, nivel=logging.INFO) -> logging.Logger:
    """Logger que escribe a consola (stderr) y a un archivo en logs/<nombre_log>.

    Los fallbacks de segmentador (SaT -> spaCy) y otras decisiones silenciosas del
    pipeline original se vuelven WARNING visibles aquí, no un print() que se pierde.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sesgocognitivo")
    logger.setLevel(nivel)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    consola = logging.StreamHandler(sys.stderr)
    consola.setFormatter(fmt)
    logger.addHandler(consola)

    archivo = logging.FileHandler(LOGS_DIR / nombre_log, encoding="utf-8")
    archivo.setFormatter(fmt)
    logger.addHandler(archivo)

    return logger
