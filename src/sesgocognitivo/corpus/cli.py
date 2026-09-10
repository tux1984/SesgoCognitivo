"""CLI del pipeline de recolección del corpus.

Ejemplos:
    python -m sesgocognitivo.corpus.cli --dry-run
    python -m sesgocognitivo.corpus.cli --medios infobae eltiempo
    python -m sesgocognitivo.corpus.cli --discover-only --medios elespectador lasillavacia semana
    python -m sesgocognitivo.corpus.cli --medios semana --manual-only
"""
from __future__ import annotations

import argparse
import dataclasses
import json
from datetime import datetime
from pathlib import Path

import openpyxl

from sesgocognitivo.common.logging_utils import setup_logging
from sesgocognitivo.common.paths import CORPUS_XLSX, LOGS_DIR, MANUAL_URLS_DIR, TEMAS_YAML
from sesgocognitivo.corpus import discovery
from sesgocognitivo.corpus.collector import recolectar_de_feed, recolectar_de_pagina, recolectar_manual
from sesgocognitivo.corpus.config_loader import load_medios, load_temas
from sesgocognitivo.corpus.excel_writer import escribir_filas, guardar_workbook_seguro
from sesgocognitivo.corpus.grid_tracker import GENERO_DURA, GENERO_OPINION, HOJA_CORPUS, HOJA_GRID, GridState
from sesgocognitivo.corpus.segmentation import get_segmenter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pipeline de recolección del corpus de 500 oraciones.")
    parser.add_argument("--medios", nargs="*", default=None, help="ids de medios a procesar (default: todos)")
    parser.add_argument("--dry-run", action="store_true", help="no escribe al Excel, solo reporta")
    parser.add_argument("--discover-only", action="store_true", help="solo descubre feeds, no recolecta")
    parser.add_argument("--manual-only", action="store_true", help="usa solo <manual-urls-dir>/<medio>.txt")
    parser.add_argument("--limite-por-feed", type=int, default=40)
    parser.add_argument("--forzar-spacy", action="store_true", help="fuerza el fallback spaCy (debug/pruebas)")
    parser.add_argument("--config-temas", type=Path, default=TEMAS_YAML, help="yaml de temas (default: los 5 dominios del corpus)")
    parser.add_argument(
        "--config-medios", type=Path, required=True,
        help="yaml de medios del dominio a recolectar (medios_economia.yaml, medios_salud.yaml, "
             "medios_medioambiente.yaml o medios_deportes.yaml)")
    parser.add_argument("--hoja-corpus", default=HOJA_CORPUS, help="hoja destino para las oraciones")
    parser.add_argument("--hoja-grid", default=HOJA_GRID, help="hoja destino para los objetivos del grid")
    parser.add_argument("--manual-urls-dir", type=Path, default=MANUAL_URLS_DIR, help="directorio de curación manual")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = setup_logging(f"corpus_run_{ts}.log")

    temas = load_temas(args.config_temas)
    medios = load_medios(args.config_medios)
    if args.medios:
        medios = [m for m in medios if m.id in args.medios]
    if not medios:
        logger.error("Ningún medio coincide con --medios %s", args.medios)
        return

    for m in medios:
        if m.aviso_legal:
            logger.warning("[%s] Aviso de gobernanza de datos: %s", m.id, m.aviso_legal)

    wb = openpyxl.load_workbook(CORPUS_XLSX, data_only=False)
    tracker = GridState.desde_workbook(wb, hoja_grid=args.hoja_grid, hoja_corpus=args.hoja_corpus)
    logger.info("Estado inicial del grid (medios seleccionados):\n%s", tracker.resumen_texto())

    if args.discover_only:
        reporte = {}
        for medio in medios:
            if not medio.descubrir:
                continue
            resultado = discovery.descubrir_feed(discovery.base_url_de(medio), medio.id)
            reporte[medio.id] = dataclasses.asdict(resultado)
            logger.info("[%s] descubrimiento: valido=%s metodo=%s feed=%s", medio.id, resultado.valido, resultado.metodo, resultado.feed_url)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        ruta_reporte = LOGS_DIR / f"discovery_report_{ts}.json"
        ruta_reporte.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Reporte de descubrimiento escrito en %s", ruta_reporte)
        return

    segmentar, backend = get_segmenter(forzar_spacy=args.forzar_spacy)
    logger.info("Backend de segmentación en uso en esta corrida: %s", backend.upper())

    todas_las_filas = []
    for medio in medios:
        feed_dura = medio.feeds.get("dura")
        feed_opinion = medio.feeds.get("opinion")
        mismo_feed = bool(feed_dura) and feed_dura == feed_opinion

        # La inferencia de género por artículo (ver classification.inferir_genero) se usa
        # SIEMPRE, no solo cuando dura==opinion: incluso un feed "dura" nominal (ej. el
        # feed genérico de Semana) puede traer alguna pieza de opinión mezclada, y forzar
        # el género de todo el feed la etiquetaría mal. El género pasado a
        # recolectar_de_feed es solo el valor por defecto para cuando no hay señal de
        # categoría/URL que diga lo contrario.
        if mismo_feed:
            # Un solo feed sirve ambos géneros: UNA sola pasada -- procesarlo dos veces
            # duplicaría cada artículo bajo ambos géneros.
            pasadas = [(GENERO_DURA, feed_dura, True)]
        else:
            pasadas = [(GENERO_OPINION, feed_opinion, True)]
            if not medio.solo_opinion:
                pasadas.insert(0, (GENERO_DURA, feed_dura, True))

        for genero, feed_configurado, inferir_por_entrada in pasadas:
            feed_url = None
            origen = "ninguno"

            if genero == GENERO_OPINION and medio.opinion_no_disponible:
                logger.warning(
                    "[%s/%s] marcado opinion_no_disponible=true (sin fuente de opinión propia "
                    "confirmada) -- se salta RSS/descubrimiento para evitar contenido fuera de "
                    "alcance; solo se intenta el fallback manual.",
                    medio.id, genero,
                )
                filas = recolectar_manual(medio, genero, temas, segmentar, tracker, manual_urls_dir=args.manual_urls_dir)
                todas_las_filas.extend(filas)
                continue

            if not args.manual_only and feed_configurado:
                ok, motivo, _ = discovery.validar_feed(feed_configurado)
                if ok:
                    feed_url, origen = feed_configurado, "configurado"
                else:
                    logger.warning("[%s/%s] feed configurado no validó (%s)", medio.id, genero, motivo)

            if feed_url is None and not args.manual_only and medio.descubrir:
                resultado = discovery.descubrir_feed(discovery.base_url_de(medio), medio.id)
                if resultado.valido:
                    feed_url, origen = resultado.feed_url, "descubierto"

            if feed_url:
                logger.info("[%s/%s] usando feed (%s): %s", medio.id, genero, origen, feed_url)
                filas = recolectar_de_feed(
                    feed_url, medio, genero, temas, segmentar, tracker,
                    limite=args.limite_por_feed, inferir_genero_por_entrada=inferir_por_entrada,
                )
                todas_las_filas.extend(filas)
            else:
                logger.warning("[%s/%s] sin feed válido, intentando fallback manual", medio.id, genero)
                filas = recolectar_manual(medio, genero, temas, segmentar, tracker, manual_urls_dir=args.manual_urls_dir)
                todas_las_filas.extend(filas)

        if not args.manual_only:
            # Si el medio es solo_opinion (ej. El Espectador, por riesgo de paywall en su
            # noticia dura), el género por defecto de sus feeds adicionales también debe
            # ser Opinión -- así, aunque inferir_genero no detecte el patrón de URL en
            # algún caso raro, nunca se cae de vuelta a Noticia dura para este medio.
            genero_por_defecto_extra = GENERO_OPINION if medio.solo_opinion else GENERO_DURA
            for feed_extra in medio.feeds_adicionales:
                ok, motivo, _ = discovery.validar_feed(feed_extra)
                if not ok:
                    logger.warning("[%s] feed adicional no validó (%s): %s", medio.id, motivo, feed_extra)
                    continue
                logger.info("[%s] usando feed adicional: %s", medio.id, feed_extra)
                filas = recolectar_de_feed(
                    feed_extra, medio, genero_por_defecto_extra, temas, segmentar, tracker,
                    limite=args.limite_por_feed, inferir_genero_por_entrada=True,
                )
                todas_las_filas.extend(filas)

            for pagina in medio.paginas_adicionales:
                logger.info("[%s] rastreando página: %s", medio.id, pagina.url)
                filas = recolectar_de_pagina(
                    pagina.url, pagina.incluir, medio, genero_por_defecto_extra, temas,
                    segmentar, tracker, patrones_excluir=pagina.excluir, limite=args.limite_por_feed,
                )
                todas_las_filas.extend(filas)

    logger.info("Total de oraciones recolectadas en esta corrida: %d", len(todas_las_filas))
    logger.info("Resumen de avance tras esta corrida:\n%s", tracker.resumen_texto())

    if args.dry_run:
        logger.info("--dry-run: no se escribió nada al Excel.")
        return

    if todas_las_filas:
        escritas = escribir_filas(wb, todas_las_filas, hoja_corpus=args.hoja_corpus)
        tracker.recomputar_columnas_fg(wb, hoja_grid=args.hoja_grid)
        guardar_workbook_seguro(wb, CORPUS_XLSX)
        logger.info("Escritas %d fila(s) nueva(s) en '%s'.", escritas, CORPUS_XLSX)
    else:
        logger.info("No hay filas nuevas para escribir en esta corrida.")


if __name__ == "__main__":
    main()
