"""Carga de configuración de temas y medios desde YAML (en vez de dicts hardcodeados)."""
from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

from sesgocognitivo.common.paths import MEDIOS_YAML, TEMAS_YAML


@dataclasses.dataclass(frozen=True)
class Tema:
    id: str
    nombre: str
    keywords: list[str]


@dataclasses.dataclass(frozen=True)
class PaginaAdicional:
    """Página de sección/listado a rastrear en busca de enlaces a artículos (no un feed
    RSS) -- ver discovery.extraer_enlaces_de_pagina y collector.recolectar_de_pagina."""
    url: str
    incluir: tuple[str, ...]
    excluir: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class MedioConfig:
    id: str
    nombre: str
    home: str
    descubrir: bool
    feeds: dict[str, str]  # {"dura": url, "opinion": url}
    manual_fallback: str | None = None
    aviso_legal: str | None = None
    solo_opinion: bool = False
    # True cuando se confirmó que el medio NO tiene una fuente de opinión propia del país
    # (ej. Infobae Colombia usa autores/feed compartidos con otros países de habla
    # hispana) -- evita que el pipeline caiga a auto-descubrimiento y termine reusando por
    # error el feed de noticia dura bajo la etiqueta de opinión, o recolectando contenido
    # fuera de alcance geográfico.
    opinion_no_disponible: bool = False
    # Feeds temáticos/de sección adicionales (ej. tags de WordPress, secciones de un CMS)
    # que amplían cobertura por tema más allá del feed principal dura/opinión. El género
    # de cada entrada se infiere por artículo (ver classification.inferir_genero), no se
    # asume dura por defecto para todo el feed.
    feeds_adicionales: list[str] = dataclasses.field(default_factory=list)
    # Páginas de sección a rastrear (no RSS) cuando el feed de una categoría es demasiado
    # angosto o está dominado por contenido irrelevante (ver PaginaAdicional).
    paginas_adicionales: list[PaginaAdicional] = dataclasses.field(default_factory=list)


def load_temas(ruta: Path = TEMAS_YAML) -> list[Tema]:
    data = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    return [Tema(id=t["id"], nombre=t["nombre"], keywords=list(t["keywords"])) for t in data["temas"]]


def load_medios(ruta: Path = MEDIOS_YAML) -> list[MedioConfig]:
    data = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    medios = []
    for m in data["medios"]:
        medios.append(
            MedioConfig(
                id=m["id"],
                nombre=m["nombre"],
                home=m["home"],
                descubrir=m.get("descubrir", False),
                feeds=dict(m.get("feeds", {})),
                manual_fallback=m.get("manual_fallback"),
                aviso_legal=(m.get("aviso_legal") or "").strip() or None,
                solo_opinion=m.get("solo_opinion", False),
                opinion_no_disponible=m.get("opinion_no_disponible", False),
                feeds_adicionales=list(m.get("feeds_adicionales", [])),
                paginas_adicionales=[
                    PaginaAdicional(
                        url=p["url"],
                        incluir=tuple(p["incluir"]),
                        excluir=tuple(p.get("excluir", [])),
                    )
                    for p in m.get("paginas_adicionales", [])
                ],
            )
        )
    return medios
