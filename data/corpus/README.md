# Datos del corpus

- `corpus_multidominio_500_oraciones.xlsx` — el corpus. Cuatro hojas:
  - `Corpus - oraciones` — las 500 oraciones, una por fila, de la fila 5 a la 504. Columnas
    A–I y `url_fuente` vienen dadas (gris, no se editan); J–AC son las que llena el anotador
    (amarillo): las 9 categorías con su span, `direccion` y `actor_objetivo`. La columna `aux`
    es una fórmula que alimenta el grid; nunca se escribe a mano ni por el pipeline.
  - `Grid de recoleccion` — tablero por medio × dominio. El % de avance mide la ANOTACIÓN:
    cuenta las oraciones que ya tienen `direccion` llena.
  - `Resumen` — totales por medio y por dominio, calculados desde el grid.
  - `Leyenda` — instrucciones de uso y ejemplos anotados.
  Estructura y reglas de escritura documentadas en `src/sesgocognitivo/corpus/excel_writer.py`.
- `esquemas_anotacion.xlsx` — referencia del esquema de anotación: Tabla 1 (completo, el que se
  usa: 9 categorías J1 léxico / J2 discursivo + dirección) y Tabla 2 (simplificado, derivable
  desde la Tabla 1 y conservado solo como alternativa documentada).
- `manual_urls/` — curación manual: una URL por línea (con su género), por medio y dominio, para
  las celdas que el descubrimiento automático de RSS no alcanzaba a llenar.

**No editar el .xlsx a mano mientras el pipeline esté corriendo** — puede pisar filas que el
script está a punto de escribir.
