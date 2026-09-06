"""Control de avance por celda (medio, tema, género) del grid de recolección.

La hoja 'Grid de recoleccion' cuenta oraciones por medio+tema (SUMIFS sobre la columna aux de
'Corpus - oraciones', ver excel_writer.COLUMNA_AUX), pero NO separa por género -- no hay forma de saber desde la propia
hoja si el sub-objetivo de opinión de un medio ya se llenó. Este tracker lee
'Corpus - oraciones' directamente para tener esa granularidad y decidir cuándo dejar de
recolectar para una celda específica.
"""
from __future__ import annotations

import dataclasses
import logging

from sesgocognitivo.corpus.classification import GENERO_DURA, GENERO_OPINION

logger = logging.getLogger("sesgocognitivo")

HOJA_GRID = "Grid de recoleccion"
HOJA_CORPUS = "Corpus - oraciones"

GRID_FILA_INICIO = 5
GRID_FILA_FIN = 29

CORPUS_FILA_INICIO = 8  # filas 5-7 son ejemplo protegido, nunca se cuentan aquí
CORPUS_FILA_FIN = 557

__all__ = [
    "GENERO_DURA", "GENERO_OPINION", "GridState", "ObjetivoCelda",
    "HOJA_GRID", "HOJA_CORPUS", "GRID_FILA_INICIO", "GRID_FILA_FIN",
    "CORPUS_FILA_INICIO", "CORPUS_FILA_FIN",
]


@dataclasses.dataclass(frozen=True)
class ObjetivoCelda:
    medio: str
    tema: str
    objetivo_dura: int
    objetivo_opinion: int


@dataclasses.dataclass
class GridState:
    objetivos: dict[tuple[str, str], ObjetivoCelda]
    _oraciones_vistas: dict[tuple[str, str, str], set] = dataclasses.field(default_factory=dict)
    _articulos_vistos: dict[tuple[str, str, str], set] = dataclasses.field(default_factory=dict)
    # Independiente de tema/género: un mismo articulo_id puede aparecer en más de una
    # categoría/feed del mismo medio (ej. un artículo de El Espectador cross-listado en
    # "opinion" y "judicial" a la vez) y terminar clasificado con un género distinto en
    # cada corrida -- la dedup por (medio,tema,genero) no lo detecta porque son claves
    # distintas. Este set global por medio evita reprocesar el mismo artículo dos veces
    # sin importar bajo qué género/tema haya entrado la primera vez.
    _articulos_procesados_por_medio: dict[str, set] = dataclasses.field(default_factory=dict)

    @classmethod
    def desde_workbook(cls, wb) -> "GridState":
        ws_grid = wb[HOJA_GRID]
        objetivos: dict[tuple[str, str], ObjetivoCelda] = {}
        for fila in range(GRID_FILA_INICIO, GRID_FILA_FIN + 1):
            medio = ws_grid.cell(row=fila, column=1).value
            tema = ws_grid.cell(row=fila, column=2).value
            if not (medio and tema):
                continue
            obj_dura = ws_grid.cell(row=fila, column=3).value or 0
            obj_opinion = ws_grid.cell(row=fila, column=4).value or 0
            objetivos[(medio, tema)] = ObjetivoCelda(medio, tema, int(obj_dura), int(obj_opinion))

        estado = cls(objetivos=objetivos)

        ws_corpus = wb[HOJA_CORPUS]
        for fila in range(CORPUS_FILA_INICIO, CORPUS_FILA_FIN + 1):
            articulo_id = ws_corpus.cell(row=fila, column=1).value
            oracion_id = ws_corpus.cell(row=fila, column=2).value
            medio = ws_corpus.cell(row=fila, column=3).value
            tema = ws_corpus.cell(row=fila, column=4).value
            genero = ws_corpus.cell(row=fila, column=5).value
            if not (medio and tema and genero and oracion_id):
                continue
            estado._registrar_visto(medio, tema, genero, oracion_id, articulo_id)

        return estado

    def _registrar_visto(self, medio: str, tema: str, genero: str, oracion_id: str, articulo_id: str | None) -> None:
        clave = (medio, tema, genero)
        self._oraciones_vistas.setdefault(clave, set()).add(oracion_id)
        if articulo_id:
            self._articulos_vistos.setdefault(clave, set()).add(articulo_id)
            self._articulos_procesados_por_medio.setdefault(medio, set()).add(articulo_id)

    def articulo_ya_procesado(self, medio: str, articulo_id: str) -> bool:
        return articulo_id in self._articulos_procesados_por_medio.get(medio, set())

    def n_oraciones(self, medio: str, tema: str, genero: str) -> int:
        return len(self._oraciones_vistas.get((medio, tema, genero), set()))

    def n_articulos(self, medio: str, tema: str, genero: str) -> int:
        return len(self._articulos_vistos.get((medio, tema, genero), set()))

    def objetivo(self, medio: str, tema: str, genero: str) -> int:
        celda = self.objetivos.get((medio, tema))
        if not celda:
            return 0
        return celda.objetivo_dura if genero == GENERO_DURA else celda.objetivo_opinion

    def restante(self, medio: str, tema: str, genero: str) -> int:
        return max(0, self.objetivo(medio, tema, genero) - self.n_oraciones(medio, tema, genero))

    def esta_llena(self, medio: str, tema: str, genero: str) -> bool:
        return self.restante(medio, tema, genero) <= 0

    def registrar(self, medio: str, tema: str, genero: str, oracion_ids: list[str], articulo_id: str | None) -> None:
        clave = (medio, tema, genero)
        self._oraciones_vistas.setdefault(clave, set()).update(oracion_ids)
        if articulo_id:
            self._articulos_vistos.setdefault(clave, set()).add(articulo_id)
            self._articulos_procesados_por_medio.setdefault(medio, set()).add(articulo_id)

    def resumen_texto(self) -> str:
        lineas = []
        total_actual = 0
        total_objetivo = 0
        for (medio, tema), celda in self.objetivos.items():
            for genero, objetivo in ((GENERO_DURA, celda.objetivo_dura), (GENERO_OPINION, celda.objetivo_opinion)):
                actual = self.n_oraciones(medio, tema, genero)
                total_actual += actual
                total_objetivo += objetivo
                pct = actual / objetivo if objetivo else 0.0
                if objetivo == 0:
                    # Celda deliberadamente vacía (ver opinion_no_disponible / redistribución
                    # de objetivos en medios.yaml) -- no es trabajo pendiente, es 0/0 a propósito.
                    sugerido = "N/A (sin objetivo)"
                elif actual >= objetivo:
                    sugerido = "Completo"
                elif actual > 0:
                    sugerido = "En progreso"
                else:
                    sugerido = "Pendiente"
                lineas.append(f"  {medio} / {tema} / {genero}: {actual}/{objetivo} ({pct:.0%}) -> sugerido: {sugerido}")
        lineas.append(f"TOTAL: {total_actual}/{total_objetivo}")
        return "\n".join(lineas)

    def recomputar_columnas_fg(self, wb) -> None:
        """Recalcula (no incrementa) F/G 'artículos recolectados' desde cero cada corrida,
        para que rerunear el pipeline sea idempotente y no duplique conteos."""
        ws_grid = wb[HOJA_GRID]
        for fila in range(GRID_FILA_INICIO, GRID_FILA_FIN + 1):
            medio = ws_grid.cell(row=fila, column=1).value
            tema = ws_grid.cell(row=fila, column=2).value
            if not (medio and tema):
                continue
            n_dura = self.n_articulos(medio, tema, GENERO_DURA)
            n_opinion = self.n_articulos(medio, tema, GENERO_OPINION)
            ws_grid.cell(row=fila, column=6, value=n_dura)  # F
            ws_grid.cell(row=fila, column=7, value=n_opinion)  # G
