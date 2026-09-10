# Sesgo Cognitivo — Sistema de monitorización y mitigación de sesgo mediático

Trabajo de grado (Maestría en Inteligencia Artificial, Pontificia Universidad Javeriana). Autor:
Sebastian Eduardo Fanchi. Tutor: Andrés Darío Moreno Barbosa.

## El problema

Los medios digitales son hoy el canal informativo dominante en Colombia. El sesgo mediático —cuando la
cobertura favorece sistemáticamente una postura, un actor o un encuadre, muchas veces por elección
léxica del periodista— es lo que este proyecto caracteriza y aborda directamente. La motivación
original viene de la literatura sobre sesgos cognitivos del lector (confirmación, anclaje): un consumo
mediático sesgado y unidireccional los refuerza y favorece burbujas de filtro, esa literatura sigue
siendo el fundamento teórico del proyecto — ver [Nota sobre el pivote de alcance](#nota-sobre-el-pivote-de-alcance).

La literatura internacional sobre detección automática de sesgo mediático mediante procesamiento de
lenguaje natural (PLN) es amplia, pero está construida casi por completo sobre inglés y medios
estadounidenses. Para el ecosistema mediático colombiano e hispanohablante en general, los recursos
—corpus anotados, clasificadores, pipelines— prácticamente no existen. Esta tesis busca cerrar
parcialmente esa brecha.

## La solución propuesta

Una prueba de concepto (POC) que integra tres piezas, apoyándose en componentes ya existentes
(modelos preentrenados, embeddings, LLM) en vez de entrenar nada desde cero:

1. **Detección de sesgo léxico/discursivo** sobre un corpus real de noticias colombianas, anotado a
   mano siguiendo un esquema con fundamento en la literatura (Recasens et al. 2013; Rodrigo-Ginés et
   al. 2024) — ver [Bloque 1](#bloques-del-sistema).
2. **Recomendación con diversidad garantizada**, no solo relevancia: un selector que aplica
   restricciones normativas explícitas (balance de posturas, inclusión de voces minoritarias) usando
   el marco **DART** (Vrijenhoek et al. 2021), en vez de optimizar por engagement — que es, por
   diseño, el mecanismo que produce burbujas de filtro.
3. **Explicaciones en lenguaje natural vía LLM** que le dicen al lector no solo *qué* se le está
   recomendando sino *por qué* es sesgado el artículo original y *qué mecanismo discursivo concreto*
   se detectó — atendiendo el hallazgo de que la sola exposición a perspectivas diversas, sin
   explicación, no cambia la percepción de sesgo del lector (Spinde et al. 2020).

El detalle completo de la motivación, el estado del arte y los objetivos específicos está en
`docs/propuesta/Propuesta_TdG_SebastianFanchi_2026-1.pdf` (la propuesta formal presentada al comité).

## Nota sobre el pivote de alcance

La propuesta original contemplaba además simular un histórico de lectura de un usuario ficticio
("Nestor") para medir directamente si una explicación reduce su sesgo de confirmación/anclaje. Esa
simulación y la detección directa de sesgos cognitivos se **retiraron del alcance del POC** (decisión
documentada en `docs/metodologia/resumen_sesion_2_dart_sin_sesgos_cognitivos.pdf`): habría exigido
programar de antemano la reacción del usuario simulado, un diseño circular que no demuestra nada.

El sistema se sostiene ahora sobre dos pilares que no dependen de esa simulación:

- **Literatura ya existente**: la sola exposición a perspectivas diversas no cambia significativamente
  la percepción de sesgo del lector (Spinde et al.), lo que motiva el componente de explicación como
  algo más que un añadido — es el argumento central de por qué la explicabilidad importa.
- **La distinción léxico/discursivo del propio esquema de anotación**: un mecanismo léxico (J1) es uno
  que el lector típicamente sí puede notar por sí mismo (una palabra cargada); uno discursivo (J2) es
  uno que normalmente no percibe sin ayuda (una opinión presentada con estructura de hecho, una
  atribución de intención sin fuente). Esa asimetría —no una etiqueta nueva— es el criterio que usa el
  Bloque 4 para decidir qué mecanismo explicar primero cuando una oración tiene más de un hallazgo: lo
  discursivo tiene, en principio, mayor potencial de generar una reconsideración crítica genuina que lo
  léxico, que el lector ya intuía.

El resultado cuantitativo comparativo de la tesis pasa a ser las métricas DART (línea base ingenua vs.
recomendador propuesto) — medibles con aritmética simple sobre el corpus ya anotado— en vez de un
cambio de creencia simulado.

## Bloques del sistema

| Bloque | Contenido | Estado |
|---|---|---|
| 1 — Corpus | Recolección + segmentación de 500 oraciones reales (5 medios × 5 dominios), esquema de anotación humana léxico/discursivo (9 categorías) | **500/500 recolectadas y auditadas, esquema de anotación listo** — pendiente la anotación humana (`src/sesgocognitivo/corpus/`) |
| 2 — Detección | Inventario y evaluación de modelos preentrenados de detección de sesgo en español | Placeholder (`src/sesgocognitivo/deteccion/`) |
| 3 — Recomendación | Selector con restricción de diversidad (métricas DART: Representación, Activación, Voces alternativas, Fragmentación) vs. baseline por relevancia | Placeholder (`src/sesgocognitivo/recomendador/`) |
| 4 — Explicabilidad | Explicaciones en lenguaje natural vía LLM, priorizando mecanismos discursivos sobre léxicos | Placeholder (`src/sesgocognitivo/explicaciones/`) |
| 5 — Evaluación | Métricas técnicas del sistema integrado + prueba piloto con usuarios (condicional) | Placeholder (`src/sesgocognitivo/evaluacion/`) |

## Estructura del repo

```
data/corpus/            # el .xlsx de trabajo (grid de recolección + corpus anotado) y sus insumos
docs/
  propuesta/             # propuesta formal de trabajo de grado (motivación, estado del arte, objetivos)
  metodologia/           # resúmenes de decisiones tomadas con el tutor (documentos vivos)
  papers/                # papers de referencia citados en el esquema de anotación
src/sesgocognitivo/
  corpus/                # Bloque 1: recolección, segmentación, clasificación y escritura al Excel
  deteccion/             # Bloque 2 (placeholder)
  recomendador/          # Bloque 3 (placeholder)
  explicaciones/         # Bloque 4 (placeholder)
  evaluacion/            # Bloque 5 (placeholder)
  common/                # utilidades compartidas entre bloques (paths, logging)
tests/                   # tests dirigidos, siempre contra fixtures sintéticos (nunca el xlsx real)
logs/                    # reportes de descubrimiento de fuentes y progreso de recolección (gitignored)
```

Cada bloque vive en su propio subpaquete bajo `src/sesgocognitivo/` con sus propias dependencias
declaradas como *extra* en `pyproject.toml` (`pip install -e ".[corpus]"`, `".[deteccion]"`, etc.), de
forma que instalar uno no arrastra las dependencias de los demás mientras siguen sin construirse.

## Instalación (Bloque 1 — recolección)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[corpus]"
python -m spacy download es_core_news_sm
```

El segmentador primario (`sat-12l-sm`, vía `wtpsplit`) descarga un modelo de ~1.1GB desde Hugging
Face la primera vez que se usa — puede tardar varios minutos. spaCy es un *fallback* documentado,
usado solo si SaT no está disponible en el entorno (ver `src/sesgocognitivo/corpus/segmentation.py`).

## Uso

```bash
python -m sesgocognitivo.corpus.cli --help

# La recolección es por dominio: cada uno tiene sus propios feeds.
python -m sesgocognitivo.corpus.cli \
  --config-medios src/sesgocognitivo/corpus/config/medios_salud.yaml \
  --manual-only --dry-run
```

`--dry-run` reporta el avance sin escribir al Excel. Es el paso obligatorio antes de
cualquier corrida real: atrapa clasificaciones erróneas y ruido nuevo antes de que lleguen
al corpus.

## Aviso de gobernanza de datos — El Tiempo

El aviso de copyright de El Tiempo prohíbe explícitamente el uso de su contenido para IA/ML, y el
tema sigue **pendiente de resolución legal con la universidad**. Se decidió, de forma deliberada,
incluir igualmente a El Tiempo en la recolección del corpus mientras se resuelve esa conversación —
es un riesgo aceptado a propósito y documentado aquí, no un descuido.

## Estado de la recolección: 500/500 ✅

El corpus vive en **`data/corpus/corpus_multidominio_500_oraciones.xlsx`**: 500 oraciones de
89 artículos, repartidas en 5 dominios de 100 oraciones cada uno — Política, Economía y
negocios, Salud, Medio ambiente y Deportes — sobre los mismos 5 medios. Cada dominio cubre un
debate genuinamente polarizante (reforma laboral y salario mínimo, crisis de las EPS, fracking
y páramo de Santurbán, Selección Colombia y arbitraje), para no evaluar la herramienta solo
sobre contenido político.

Recolección real ejecutada (no simulada), con extracción vía JSON-LD (incluyendo el patrón
`@graph` de schema.org) como fuente principal del cuerpo y la fecha, heurística de contenedor
principal como respaldo, deduplicación global por artículo, y un filtro de largo mínimo que
descarta contenido sospechosamente corto (paywall/teaser).

El corpus fue auditado oración por oración: sin duplicados de id ni de texto, sin fechas
faltantes, sin boilerplate ni artefactos de maquetación (pies de foto, subtítulos de sección,
teasers de enlace interno), y con la clasificación temática de cada artículo verificada contra
el contexto real de sus palabras clave, no solo contra el conteo.

**Redistribuciones de objetivo documentadas** (celdas sin oferta suficiente de contenido
propio, resueltas moviendo el objetivo a otro género o medio y dejando la nota en el grid):

- **Infobae Colombia** no tiene sección de opinión propia de Colombia: se confirmó que su feed
  de opinión es el global, dominado por autores argentinos. Su cuota va 100% a noticia dura
  (`opinion_no_disponible` en los `medios_*.yaml`).
- **La Silla Vacía / Deportes**: sin cobertura deportiva activa en la ventana del corpus; su
  cuota se redistribuyó entre los otros cuatro medios.
- **Semana / Deportes (opinión)**: no tiene columnistas de opinión deportiva; esa cuota pasó a
  El Tiempo y El Espectador.

El esquema de anotación es la **Tabla 1** de `esquemas_anotacion.xlsx`: 5 categorías léxicas J1
+ 4 discursivas J2, cada una con su span, más `direccion` y `actor_objetivo` (lista cerrada de
9 roles). Lo implementa la hoja `Corpus - oraciones`, una fila por oración.

Detalle por celda:
`python -c "from sesgocognitivo.corpus.grid_tracker import GridState; import openpyxl; from sesgocognitivo.common.paths import CORPUS_XLSX; print(GridState.desde_workbook(openpyxl.load_workbook(CORPUS_XLSX)).resumen_texto())"`.

## Referencias

- `docs/propuesta/` — propuesta de trabajo de grado: motivación completa, estado del arte, pregunta de
  investigación, objetivos específicos y cronograma.
- `docs/metodologia/` — resúmenes de decisiones metodológicas tomadas con el tutor (documentos vivos,
  se actualizan sesión a sesión): distribución del corpus, validación de la segmentación, marco DART,
  retiro de la simulación de sesgos cognitivos.
- `docs/papers/` — fundamento teórico del esquema de anotación (Recasens et al. 2013; Rodrigo-Ginés et
  al. 2024; Alam et al. 2022).
