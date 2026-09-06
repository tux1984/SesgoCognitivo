# Datos del corpus

- `grid_recoleccion_500_oraciones.xlsx` — grid de recolección (5 medios × 5 temas, 20 oraciones por
  celda) + hoja `Corpus - oraciones` donde vive el corpus real con su anotación. Estructura completa
  documentada en `src/sesgocognitivo/corpus/excel_writer.py`.
- `esquemas_anotacion.xlsx` — documento de referencia con dos propuestas de esquema de anotación:
  Tabla 1 (esquema completo, 9 categorías J1 léxico/J2 discursivo) y Tabla 2 (esquema simplificado,
  descartado). **La hoja `Corpus - oraciones` implementa la Tabla 1** — es el esquema con el que se
  anota en la práctica; Tabla 2 queda solo como referencia histórica en este archivo.
- `manual_urls/` — fallback de curación manual: una URL por línea, por medio, para cuando el
  descubrimiento automático de RSS/sitemap no encuentra un feed utilizable.

**No editar `grid_recoleccion_500_oraciones.xlsx` a mano mientras el pipeline de recolección esté
corriendo** — puede pisar filas que el script está a punto de escribir. La columna `aux` (AF) de
`Corpus - oraciones` es una fórmula auxiliar; nunca se escribe manualmente ni por el pipeline.
