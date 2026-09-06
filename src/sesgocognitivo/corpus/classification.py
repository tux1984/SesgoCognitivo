"""Clasificación de tema por coincidencia de palabras clave (heurística simple, documentada
como tal -- revisar/ajustar según lo que se vaya encontrando en el corpus real)."""
from __future__ import annotations

from urllib.parse import urlparse

from sesgocognitivo.corpus.config_loader import Tema

GENERO_DURA = "Noticia dura"
GENERO_OPINION = "Opinión-análisis"

# Señales de que una entrada es opinión/análisis en vez de noticia dura -- se usan solo
# cuando un medio no tiene feeds separados por género (ver `inferir_genero`).
_CATEGORIAS_OPINION = {"red de expertos", "opinión", "opinion", "columnistas", "editorial"}
_SEGMENTOS_URL_OPINION = ("/opinion/", "/columnistas/", "/editorial/", "/red-de-expertos/")


def clasificar_tema(texto: str, temas: list[Tema]) -> Tema | None:
    """Elige el tema con más OCURRENCIAS TOTALES de sus palabras clave en el texto -- no el
    primer tema (en orden de config) que matchee cualquier palabra.

    Dos hallazgos reales en las corridas contra El Tiempo motivan esto:
      1. "de la espriella" (keyword de 'Transición de gobierno') aparece en casi cualquier
         nota política porque es el presidente, absorbiendo artículos más específicos de
         otro tema con "primer match gana".
      2. Un artículo sobre embajadores y diplomacia con EE.UU. mencionaba de pasada "ayuda
         de emergencia enviada tras el sismo", empatando 4 keywords DISTINTAS con
         'Relación con Estados Unidos' (que también tenía 4 distintas) -- el desempate por
         orden de definición lo mandaba a 'terremoto', el tema equivocado. Contando
         OCURRENCIAS totales en vez de solo presencia, el tema realmente dominante del
         artículo (10 menciones de EE.UU./Washington/aranceles/Rubio vs. 4 del sismo) gana.

    Esto no toca las listas de keywords ya definidas en la metodología, solo cómo se
    puntúan.
    """
    contenido = texto.lower()
    mejor_tema: Tema | None = None
    mejor_conteo = 0
    for tema in temas:
        conteo = sum(contenido.count(k) for k in tema.keywords)
        if conteo > mejor_conteo:
            mejor_conteo = conteo
            mejor_tema = tema
    return mejor_tema


def inferir_genero(url: str, categoria: str | None, genero_por_defecto: str) -> str:
    """Solo se usa cuando un medio comparte un único feed para dura/opinión (ej. La Silla
    Vacía, Semana) -- ahí NO se puede simplemente forzar el mismo género a todas las
    entradas, o se termina recolectando el mismo artículo dos veces bajo géneros distintos
    (bug real encontrado en la primera corrida contra estos dos medios).
    """
    if categoria and categoria.strip().lower() in _CATEGORIAS_OPINION:
        return GENERO_OPINION
    ruta = urlparse(url).path.lower()
    if any(seg in ruta for seg in _SEGMENTOS_URL_OPINION):
        return GENERO_OPINION
    return genero_por_defecto
