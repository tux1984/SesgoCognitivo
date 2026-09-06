"""Descubrimiento automático de feeds RSS/sitemap para medios sin URL de feed confirmada.

Orden de intento (se detiene en el primer candidato que valide):
  1. Patrones comunes de CMS (WordPress `/feed/`, Arc XP `/arc/outboundfeeds/...`).
  2. `<link rel="alternate" type="application/rss+xml">` en el <head> del home.
  3. Lo mismo, pero sobre páginas de sección (/opinion/, /politica/, /noticias/) -- necesario
     porque varios medios solo exponen su feed específico ahí, no en el home.

La validación de un candidato no se limita a que el XML parsee: se extrae el cuerpo real de
una muestra de artículos (mismo código de extracción que usa la recolección real, para no
tener una implementación separada que pueda divergir) y se exige una mediana de caracteres
razonable, para descartar teasers/paywalls sin depender de substrings genéricos como
"premium" o "suscríbete" (que aparecen igual en menús/pies de página de artículos completos
y producen falsos positivos).

El paso de sitemap (`/sitemap.xml`, `/news-sitemap.xml`) queda documentado pero no
implementado: ninguno de los 5 medios del corpus lo necesitó en las pruebas en vivo que
sustentan `medios.yaml`. Si un medio futuro lo requiere, agregar aquí un paso adicional que
parsee el sitemap/urlset y filtre por `<lastmod>` + palabras clave de path.
"""
from __future__ import annotations

import dataclasses
import logging
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from sesgocognitivo.corpus.extraction import HEADERS, extraer_cuerpo

logger = logging.getLogger("sesgocognitivo")

PATRONES_CMS = [
    "feed/",
    "rss/",
    "rss.xml",
    "arc/outboundfeeds/rss/",
    "arc/outboundfeeds/discover/?outputType=xml",
]
SECCIONES_A_PROBAR = ["opinion/", "politica/", "noticias/"]
MIN_MEDIANA_CUERPO = 1200  # chars; ver docstring del módulo


@dataclasses.dataclass
class ResultadoDescubrimiento:
    medio_id: str
    feed_url: str | None
    metodo: str
    entradas_muestra: list[str]
    valido: bool
    motivo: str


def base_url_de(medio) -> str:
    return medio.home


def _extraer_links_rss(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for link in soup.find_all("link", rel="alternate"):
        tipo = link.get("type", "") or ""
        if "rss" in tipo or "atom" in tipo or "xml" in tipo:
            href = link.get("href")
            if href:
                links.append(urljoin(base_url, href))
    return links


def validar_feed(feed_url: str) -> tuple[bool, str, list[str]]:
    try:
        feed = feedparser.parse(feed_url, request_headers=HEADERS)
    except Exception as e:
        return False, f"error al parsear: {e}", []

    if not feed.entries or len(feed.entries) < 3:
        return False, f"menos de 3 entradas ({len(feed.entries) if feed.entries else 0})", []

    muestra = feed.entries[:5]
    largos: list[int] = []
    titulos: list[str] = []
    for entry in muestra:
        link = entry.get("link")
        if not link:
            continue
        try:
            cuerpo = extraer_cuerpo(link)
        except Exception:
            continue
        largos.append(len(cuerpo))
        titulos.append(entry.get("title", ""))

    if not largos:
        return False, "no se pudo extraer cuerpo de ninguna entrada de muestra", []

    largos.sort()
    mediana = largos[len(largos) // 2]
    if mediana < MIN_MEDIANA_CUERPO:
        return (
            False,
            f"cuerpo mediano muy corto ({mediana} chars, mínimo {MIN_MEDIANA_CUERPO}) "
            "-- posible teaser/paywall",
            titulos,
        )
    return True, f"ok, mediana {mediana} chars sobre {len(largos)} muestras", titulos


def extraer_enlaces_de_pagina(
    url_pagina: str,
    patrones_incluir: tuple[str, ...],
    patrones_excluir: tuple[str, ...] = (),
) -> list[str]:
    """Extrae URLs de artículo de una página de sección/listado (no un feed RSS) -- para
    medios cuyo RSS de una categoría es demasiado angosto o está dominado por contenido no
    relevante (ej. el RSS de opinión de El Tiempo trae mayormente caricaturas de 10 items,
    mientras que su página /opinion/ enlaza 70+ columnas reales de texto).

    Cada patrón de `patrones_incluir` debe terminar en "/"; se exige que quede al menos un
    carácter después del patrón (el slug del artículo) -- así "/opinion/editorial/" (bare,
    sin nada después) o "/opinion/cartas" (sin el "/" final, no matchea) quedan afuera, sin
    necesitar una lista de exclusión para cada caso de enlace de navegación.
    """
    r = requests.get(url_pagina, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    enlaces: set[str] = set()
    for a in soup.find_all("a", href=True):
        href_abs = urljoin(url_pagina, a["href"])
        if any(p in href_abs for p in patrones_excluir):
            continue
        for patron in patrones_incluir:
            idx = href_abs.find(patron)
            if idx == -1:
                continue
            resto = href_abs[idx + len(patron):].strip("/")
            if resto:
                enlaces.add(href_abs)
            break
    return sorted(enlaces)


def descubrir_feed(base_url: str, medio_id: str) -> ResultadoDescubrimiento:
    intentos: list[tuple[str, str, bool, str]] = []

    for patron in PATRONES_CMS:
        candidato = urljoin(base_url, patron)
        ok, motivo, titulos = validar_feed(candidato)
        intentos.append((candidato, "patron_cms", ok, motivo))
        if ok:
            return ResultadoDescubrimiento(medio_id, candidato, "patron_cms", titulos, True, motivo)

    try:
        r = requests.get(base_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        for candidato in _extraer_links_rss(r.text, base_url):
            ok, motivo, titulos = validar_feed(candidato)
            intentos.append((candidato, "link_home", ok, motivo))
            if ok:
                return ResultadoDescubrimiento(medio_id, candidato, "link_home", titulos, True, motivo)
    except Exception as e:
        intentos.append((base_url, "link_home", False, str(e)))

    for seccion in SECCIONES_A_PROBAR:
        seccion_url = urljoin(base_url, seccion)
        try:
            r = requests.get(seccion_url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
            intentos.append((seccion_url, "link_seccion", False, str(e)))
            continue
        for candidato in _extraer_links_rss(r.text, seccion_url):
            ok, motivo, titulos = validar_feed(candidato)
            intentos.append((candidato, "link_seccion", ok, motivo))
            if ok:
                return ResultadoDescubrimiento(medio_id, candidato, "link_seccion", titulos, True, motivo)

    logger.warning("No se pudo descubrir un feed válido para %s. Intentos: %s", medio_id, intentos)
    return ResultadoDescubrimiento(
        medio_id, None, "ninguno", [], False, f"{len(intentos)} intentos fallidos: {intentos}"
    )
