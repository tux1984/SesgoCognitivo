"""Segmentador de oraciones: sat-12l-sm (wtpsplit) es el backend PRIMARIO del proyecto,
validado en `docs/metodologia/` como el único método sin errores frente a abreviaturas de
título/mes y comillas de cita en el español periodístico colombiano. spaCy es un fallback
documentado, usado solo si SaT no está disponible en el entorno — y el fallback queda
registrado en el log con nivel WARNING (no un print silencioso) para poder auditar después
qué filas del corpus se segmentaron con el backend de menor calidad.
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger("sesgocognitivo")

SAT_MODEL = "sat-12l-sm"
SPACY_MODEL = "es_core_news_sm"

Segmentador = Callable[[str], list[str]]


def get_segmenter(forzar_spacy: bool = False) -> tuple[Segmentador, str]:
    """Devuelve (segmentador, backend) donde backend in {"sat", "spacy"}.

    `forzar_spacy=True` solo debe usarse en pruebas o depuración explícita; el uso normal
    del pipeline siempre debe intentar SaT primero.
    """
    if not forzar_spacy:
        try:
            from wtpsplit import SaT

            sat = SaT(SAT_MODEL)
            logger.info("Segmentador PRIMARIO cargado: SaT %s", SAT_MODEL)

            def segmentar(texto: str) -> list[str]:
                return [s.strip() for s in sat.split(texto) if s.strip()]

            return segmentar, "sat"
        except Exception:
            logger.warning(
                "No se pudo cargar el segmentador primario SaT (%s); cayendo a spaCy (%s) "
                "como FALLBACK. Esto degrada la segmentación en abreviaturas de mes y "
                "desplazamiento de comillas en citas (ver docs/metodologia/ sección 2). "
                "Cualquier oración escrita con este backend queda marcada en el log de corrida.",
                SAT_MODEL,
                SPACY_MODEL,
                exc_info=True,
            )

    import spacy

    nlp = spacy.load(SPACY_MODEL)
    logger.warning("Segmentador de FALLBACK en uso: spaCy %s", SPACY_MODEL)

    def segmentar(texto: str) -> list[str]:
        return [s.text.strip() for s in nlp(texto).sents if s.text.strip()]

    return segmentar, "spacy"
