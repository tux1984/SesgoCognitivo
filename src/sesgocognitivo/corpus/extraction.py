"""Extracción del cuerpo de un artículo.

Se descubrió en la corrida real contra Infobae/El Tiempo que la heurística ingenua de
concatenar todos los <p> del documento recoge basura: bylines ("Por Fulano"), marcadores
"PUBLICIDAD", y -- en el caso de El Tiempo -- el <article> real de la página solo contiene
metadatos de UI (compartir/guardar/timestamps), no el cuerpo de la noticia en absoluto (el
cuerpo real ni siquiera está en un <p> del HTML estático).

Estrategia, en orden:
  1. JSON-LD (`<script type="application/ld+json">`, propiedad `articleBody` de un item
     @type que contenga "Article"/"NewsArticle"/"BlogPosting" etc.) -- confirmado en vivo
     que Infobae y El Tiempo publican el cuerpo COMPLETO ahí para SEO, incluso cuando el
     HTML visible está fragmentado/renderizado por JS. Es la fuente más confiable cuando
     existe.
  2. Si no hay JSON-LD con cuerpo suficiente: <p> dentro de <article>, o si no, el grupo de
     <p> con mayor cantidad de texto acumulado bajo un mismo padre directo (el cuerpo real
     casi siempre concentra muchos párrafos largos en un solo contenedor; el ruido de sitio
     -- menú, cookies, widgets -- queda disperso en contenedores chicos).
  3. En cualquier caso, se aplica un filtro de párrafos de ruido conocido (bylines,
     "PUBLICIDAD", avisos de cookies/suscripción, chrome de cuenta de usuario) como red de
     seguridad final.

Revisar manualmente muestras nuevas por medio a medida que se agreguen -- esta heurística
se validó en vivo solo contra Infobae y El Tiempo.
"""
from __future__ import annotations

import json
import re

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (investigacion academica - corpus de tesis)"}

MIN_ARTICLEBODY_CHARS = 200
MIN_CONTENEDOR_CHARS = 200

_PATRONES_RUIDO = [
    re.compile(r"^por\s+[a-záéíóúñ .]{3,40}$", re.IGNORECASE),  # "Por Luciano Niño"
    re.compile(r"^esta columna fue escrita por", re.IGNORECASE),  # atribución de columnista invitado (La Silla Vacía "Red de Expertos")
    re.compile(r"^publicidad$", re.IGNORECASE),
    re.compile(r"cookies?", re.IGNORECASE),
    re.compile(r"si contin[uú]a navegando", re.IGNORECASE),
    re.compile(r"^(mi cuenta|empleos|temas del d[ií]a|compartir|guardar|reportar|noticia)$", re.IGNORECASE),
    re.compile(r"^desde \$", re.IGNORECASE),
    re.compile(r"^(bienvenid[oa]|hola)\b.*(cuenta|correo|verific)", re.IGNORECASE),
    re.compile(r"^conoce y personaliza tu perfil", re.IGNORECASE),
    re.compile(r"^suscr[ií]bete", re.IGNORECASE),
    re.compile(r"^copyright\s*©", re.IGNORECASE),
    re.compile(r"^ingrese o reg[ií]strese", re.IGNORECASE),
    # Hallazgos de la auditoría 2026-09-05 sobre el corpus real de 500 oraciones:
    re.compile(r"^fuente:\s*.+$", re.IGNORECASE),  # "Fuente: Dow Jones." -- leyenda de gráfico, no oración
    re.compile(r"espacio de debate que no compromete la opini[oó]n", re.IGNORECASE),  # disclaimer fijo de La Silla Vacía en TODAS sus columnas de opinión
]


def es_texto_ruido(texto: str) -> bool:
    """Aplica tanto a párrafos (ruta de respaldo <p>) como a ORACIONES ya segmentadas (ruta
    JSON-LD, ver `collector.procesar_articulo`) -- el articleBody de JSON-LD no pasa por
    ningún filtro antes de esta auditoría, y boilerplate como el disclaimer de La Silla
    Vacía o una leyenda "Fuente: X." de un gráfico vienen incluidos ahí tal cual, sin marca
    HTML que los distinga del resto del cuerpo."""
    limpio = texto.strip()
    if not limpio:
        return True
    if len(limpio) < 15 and (limpio.isupper() or limpio.istitle()):
        return True
    return any(p.search(limpio) for p in _PATRONES_RUIDO)


def _limpiar_texto_html(fragmento: str) -> str:
    """El articleBody de JSON-LD puede traer entidades HTML (&nbsp;) o tags sueltos;
    parsearlo como HTML normaliza ambas cosas de una vez."""
    return BeautifulSoup(fragmento, "html.parser").get_text(" ", strip=True)


def _items_jsonld(soup: BeautifulSoup) -> list[dict]:
    """Hallazgo de auditoría 2026-09-05: La Silla Vacía (plantilla "Red de Expertos") no
    publica una lista plana de objetos JSON-LD ni un único objeto -- envuelve todo en
    `{"@context": ..., "@graph": [...]}` (patrón estándar de schema.org para agrupar
    NewsArticle + BreadcrumbList + WebPage bajo un mismo script). Sin desempaquetar
    `@graph`, tanto `articleBody` como `datePublished` se perdían en silencio para esas
    2 URLs -- el cuerpo terminaba cayendo al fallback de <p> (funcionaba por suerte) pero
    la fecha simplemente quedaba en "" sin ningún error visible."""
    items: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
        for bloque in data if isinstance(data, list) else [data]:
            if not isinstance(bloque, dict):
                continue
            grafo = bloque.get("@graph")
            if isinstance(grafo, list):
                items.extend(item for item in grafo if isinstance(item, dict))
            else:
                items.append(bloque)
    return items


def _articlebody_desde_jsonld(soup: BeautifulSoup) -> str | None:
    # No se filtra por @type: en la práctica basta con exigir un articleBody sustancial
    # (>= MIN_ARTICLEBODY_CHARS) -- @type varía entre medios (NewsArticle,
    # ReportageNewsArticle, OpinionNewsArticle...) y mantener una lista exhaustiva no
    # aporta nada que el umbral de largo no filtre ya.
    for item in _items_jsonld(soup):
        cuerpo = item.get("articleBody")
        if cuerpo:
            texto = _limpiar_texto_html(cuerpo)
            if len(texto) >= MIN_ARTICLEBODY_CHARS:
                return texto
    return None


def _fecha_desde_jsonld(soup: BeautifulSoup) -> str:
    for item in _items_jsonld(soup):
        fecha = item.get("datePublished")
        if fecha:
            return str(fecha)
    return ""


def _parrafos_de_contenedor_principal(soup: BeautifulSoup) -> list:
    article = soup.find("article")
    if article:
        parrafos = article.find_all("p")
        if sum(len(p.get_text(strip=True)) for p in parrafos) >= MIN_CONTENEDOR_CHARS:
            return parrafos

    todos = soup.find_all("p")
    if not todos:
        return []
    grupos: dict[int, list] = {}
    for p in todos:
        grupos.setdefault(id(p.parent), []).append(p)

    mejor = max(grupos.values(), key=lambda ps: sum(len(p.get_text(strip=True)) for p in ps))
    total_mejor = sum(len(p.get_text(strip=True)) for p in mejor)
    return mejor if total_mejor >= MIN_CONTENEDOR_CHARS else todos


def extraer_cuerpo(url: str, timeout: int = 15) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    cuerpo_ld = _articlebody_desde_jsonld(soup)
    if cuerpo_ld:
        return cuerpo_ld

    parrafos = _parrafos_de_contenedor_principal(soup)
    textos = [p.get_text(" ", strip=True) for p in parrafos]
    textos = [t for t in textos if not es_texto_ruido(t)]
    return " ".join(textos)


def extraer_fecha_publicacion(url: str, timeout: int = 15) -> str:
    """Fecha de publicación desde JSON-LD (`datePublished`) -- fallback para fuentes que no
    traen fecha por su cuenta: recolectar_de_pagina (rastrea páginas de sección, no hay
    metadata de feed) y recolectar_manual (URLs curadas a mano). Las entradas de RSS/feed ya
    traen `published` gratis y no necesitan esto. Devuelve "" si no se encuentra."""
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    return _fecha_desde_jsonld(soup)
