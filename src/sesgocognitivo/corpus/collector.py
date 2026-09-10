"""Orquestación: RSS/manual -> extracción -> clasificación -> segmentación -> tracker -> filas."""
from __future__ import annotations

import dataclasses
import logging
import time

import feedparser

from sesgocognitivo.common.paths import MANUAL_URLS_DIR
from sesgocognitivo.corpus.classification import clasificar_tema, inferir_genero
from sesgocognitivo.corpus.config_loader import MedioConfig, Tema
from sesgocognitivo.corpus.discovery import extraer_enlaces_de_pagina
from sesgocognitivo.corpus.extraction import HEADERS, es_texto_ruido, extraer_cuerpo, extraer_fecha_publicacion
from sesgocognitivo.corpus.grid_tracker import GridState

logger = logging.getLogger("sesgocognitivo")

MAX_ORACIONES_DURA = 12  # tope original: noticia dura suele repetir la misma info en cola

# Umbral mínimo de caracteres extraídos por ARTÍCULO (no por feed -- eso ya lo valida
# discovery.validar_feed sobre una muestra). Hallazgo real revisando El Espectador: de 8
# artículos de una categoría ya validada, 6 bajaron completos (2200-5900 chars) y 2
# volvieron vacíos/truncados (0 y 549 chars) -- presumiblemente los que sí están tras el
# paywall "Premium". El umbral es un poco más laxo que el de validación de feed (1200)
# porque acá se aplica a CADA artículo individual, y noticias breves legítimas pueden ser
# más cortas que el promedio de una muestra.
MIN_CUERPO_ARTICULO = 800


@dataclasses.dataclass
class FilaOracion:
    articulo_id: str
    oracion_id: str
    medio: str
    tema: str
    genero: str
    fecha_publicacion: str
    oracion_texto: str
    oracion_anterior: str
    oracion_siguiente: str
    url_fuente: str


def procesar_articulo(
    url: str,
    medio: MedioConfig,
    genero: str,
    temas: list[Tema],
    segmentar,
    tracker: GridState,
    fecha: str | None = None,
) -> list[FilaOracion]:
    aid = tracker.obtener_o_asignar_articulo_id(url)
    if tracker.articulo_ya_procesado(medio.nombre, aid):
        # Mismo articulo_id ya recolectado en una corrida anterior (u otro feed de esta
        # misma corrida) bajo cualquier tema/género -- evita, por ejemplo, que un artículo
        # cross-listado en dos categorías del mismo CMS (ej. "opinion" y "judicial" en El
        # Espectador) termine duplicado con un género distinto cada vez.
        return []

    texto = extraer_cuerpo(url)
    if len(texto) < MIN_CUERPO_ARTICULO:
        logger.warning(
            "Descartado por cuerpo sospechosamente corto (%d chars < %d, posible paywall/teaser): %s",
            len(texto), MIN_CUERPO_ARTICULO, url,
        )
        return []

    tema = clasificar_tema(texto, temas)
    if tema is None:
        return []

    if tracker.esta_llena(medio.nombre, tema.nombre, genero):
        return []

    if not fecha:
        # RSS ya trae `published` gratis (pasado como `fecha` por el llamador); esto solo
        # se activa para recolectar_de_pagina/recolectar_manual, que no tienen esa metadata.
        try:
            fecha = extraer_fecha_publicacion(url)
        except Exception:
            fecha = ""

    oraciones = segmentar(texto)

    # Hallazgos de la auditoría 2026-09-05 sobre el corpus real: (1) boilerplate como el
    # disclaimer fijo de La Silla Vacía o una leyenda "Fuente: X." de un gráfico vienen
    # dentro del articleBody de JSON-LD tal cual, sin marca HTML que los distinga -- el
    # filtro de ruido de extraction.py nunca se les aplicaba porque solo corría sobre la
    # ruta de respaldo <p>. (2) Un artículo de El Tiempo trajo la misma oración repetida
    # dos veces SEGUIDAS tras la segmentación (artefacto de la fuente, no del segmentador
    # en sí) -- se descartan repeticiones consecutivas idénticas.
    oraciones = [o for o in oraciones if not es_texto_ruido(o)]
    oraciones = [o for i, o in enumerate(oraciones) if i == 0 or o != oraciones[i - 1]]

    if genero == "Noticia dura":
        oraciones = oraciones[:MAX_ORACIONES_DURA]

    restante = tracker.restante(medio.nombre, tema.nombre, genero)
    if restante <= 0:
        return []
    oraciones = oraciones[:restante]
    if not oraciones:
        return []

    filas: list[FilaOracion] = []
    for i, oracion in enumerate(oraciones):
        filas.append(
            FilaOracion(
                articulo_id=aid,
                oracion_id=f"{aid}_S{i + 1:02d}",
                medio=medio.nombre,
                tema=tema.nombre,
                genero=genero,
                fecha_publicacion=fecha or "",
                oracion_texto=oracion,
                oracion_anterior=oraciones[i - 1] if i > 0 else "",
                oracion_siguiente=oraciones[i + 1] if i < len(oraciones) - 1 else "",
                url_fuente=url,
            )
        )

    tracker.registrar(medio.nombre, tema.nombre, genero, [f.oracion_id for f in filas], aid)
    return filas


def recolectar_de_feed(
    feed_url: str,
    medio: MedioConfig,
    genero_por_defecto: str,
    temas: list[Tema],
    segmentar,
    tracker: GridState,
    limite: int = 40,
    sleep_s: float = 1.0,
    inferir_genero_por_entrada: bool = False,
) -> list[FilaOracion]:
    """`inferir_genero_por_entrada=True` se usa cuando un medio comparte el MISMO feed para
    dura/opinión (ej. La Silla Vacía, Semana): ahí no se puede forzar `genero_por_defecto`
    a todas las entradas sin terminar recolectando el mismo artículo dos veces bajo géneros
    distintos (bug real de la primera corrida contra estos medios) -- en su lugar, el género
    se infiere por artículo (categoría del feed o segmento de URL, ver `classification.py`).
    """
    feed = feedparser.parse(feed_url, request_headers=HEADERS)
    filas_totales: list[FilaOracion] = []
    if not feed.entries:
        logger.warning("Feed sin entradas: %s (%s)", feed_url, medio.id)
        return filas_totales

    for entry in feed.entries[:limite]:
        link = entry.get("link")
        if not link:
            continue
        if inferir_genero_por_entrada:
            categoria = entry.get("category") or (entry.get("tags", [{}])[0].get("term") if entry.get("tags") else None)
            genero = inferir_genero(link, categoria, genero_por_defecto)
        else:
            genero = genero_por_defecto
        try:
            filas = procesar_articulo(
                link,
                medio,
                genero,
                temas,
                segmentar,
                tracker,
                fecha=entry.get("published", ""),
            )
            if filas:
                filas_totales.extend(filas)
                logger.info(
                    "+ [%s/%s] %s -> %d oración(es) (tema: %s)",
                    medio.nombre,
                    genero,
                    entry.get("title", "")[:70],
                    len(filas),
                    filas[0].tema,
                )
            time.sleep(sleep_s)
        except Exception as e:
            logger.warning("Error procesando %s: %s", link, e)

    return filas_totales


def recolectar_manual(
    medio: MedioConfig,
    genero: str,
    temas: list[Tema],
    segmentar,
    tracker: GridState,
    manual_urls_dir=MANUAL_URLS_DIR,
) -> list[FilaOracion]:
    """`manual_urls_dir` permite apuntar a un directorio paralelo (ej. curación manual de
    un dominio nuevo) sin tocar `data/corpus/manual_urls/` del corpus principal."""
    if not medio.manual_fallback:
        return []
    ruta = manual_urls_dir / f"{medio.manual_fallback}.txt"
    if not ruta.exists():
        logger.warning("No existe archivo de curación manual: %s", ruta)
        return []

    filas_totales: list[FilaOracion] = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = linea.split(",")
        url = partes[0].strip()
        genero_linea = partes[1].strip() if len(partes) > 1 else genero
        try:
            filas = procesar_articulo(url, medio, genero_linea, temas, segmentar, tracker)
            if filas:
                filas_totales.extend(filas)
                logger.info("+ [manual %s/%s] %s -> %d oración(es)", medio.nombre, genero_linea, url, len(filas))
        except Exception as e:
            logger.warning("Error procesando URL manual %s: %s", url, e)

    return filas_totales


def recolectar_de_pagina(
    url_pagina: str,
    patrones_incluir: tuple[str, ...],
    medio: MedioConfig,
    genero_por_defecto: str,
    temas: list[Tema],
    segmentar,
    tracker: GridState,
    patrones_excluir: tuple[str, ...] = (),
    limite: int = 60,
    sleep_s: float = 1.0,
) -> list[FilaOracion]:
    """Recolecta desde una página de sección/listado en vez de un feed RSS -- útil cuando
    el RSS de una categoría es demasiado angosto o está dominado por contenido no relevante
    (ej. el RSS de opinión de El Tiempo trae mayormente caricaturas; su página /opinion/
    enlaza 70+ columnas de texto reales que el RSS nunca expone). El género se infiere por
    artículo igual que en un feed, ya que la página puede mezclar columnistas/editorial.
    """
    try:
        enlaces = extraer_enlaces_de_pagina(url_pagina, patrones_incluir, patrones_excluir)
    except Exception as e:
        logger.warning("Error obteniendo enlaces de %s: %s", url_pagina, e)
        return []

    filas_totales: list[FilaOracion] = []
    for link in enlaces[:limite]:
        genero = inferir_genero(link, None, genero_por_defecto)
        try:
            filas = procesar_articulo(link, medio, genero, temas, segmentar, tracker)
            if filas:
                filas_totales.extend(filas)
                logger.info("+ [pagina %s/%s] %s -> %d oración(es) (tema: %s)", medio.nombre, genero, link[-70:], len(filas), filas[0].tema)
            time.sleep(sleep_s)
        except Exception as e:
            logger.warning("Error procesando %s: %s", link, e)

    return filas_totales
