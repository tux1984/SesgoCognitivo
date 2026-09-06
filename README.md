# Sesgo Cognitivo — Sistema de monitorización y mitigación de sesgo mediático

Trabajo de grado (Maestría en Inteligencia Artificial, Pontificia Universidad Javeriana). Autor:
Sebastian Eduardo Fanchi. Tutor: Andrés Darío Moreno Barbosa.

## El problema

Los medios digitales son hoy el canal informativo dominante en Colombia. Cuando el contenido que
consume un lector está sesgado —favorece sistemáticamente una postura, un actor o un encuadre— ese
sesgo interactúa con dos sesgos cognitivos propios del lector: el **sesgo de confirmación** (buscar y
valorar más la información que ya confirma lo que uno cree) y el **sesgo de anclaje** (dar peso
desproporcionado al primer dato recibido). El resultado es una exposición cada vez más unidireccional
que refuerza burbujas de filtro y cámaras de eco, en vez de una deliberación pública informada.

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
| 1 — Corpus | Recolección + segmentación de 500 oraciones reales (5 medios × 5 temas), esquema de anotación humana léxico/discursivo (9 categorías) | **500/500 recolectadas y verificadas, esquema de anotación listo** — pendiente la anotación humana (`src/sesgocognitivo/corpus/`) |
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
```

## Aviso de gobernanza de datos — El Tiempo

El aviso de copyright de El Tiempo prohíbe explícitamente el uso de su contenido para IA/ML, y el
tema sigue **pendiente de resolución legal con la universidad**. Se decidió, de forma deliberada,
incluir igualmente a El Tiempo en la recolección del corpus mientras se resuelve esa conversación —
es un riesgo aceptado a propósito y documentado aquí, no un descuido.

## Estado de la recolección: 500/500 ✅

Recolección real ejecutada (no simulada) contra los 5 medios, con extracción vía JSON-LD (incluyendo
el patrón `@graph` de schema.org) como fuente principal del cuerpo y la fecha, heurística de
contenedor principal como respaldo, deduplicación global por artículo, y un filtro de largo mínimo por
artículo que descarta contenido sospechosamente corto (paywall/teaser). El corpus fue auditado a fondo
tras la recolección inicial: sin duplicados, sin fechas faltantes, sin boilerplate/ruido publicitario,
y con la clasificación temática de cada artículo verificada individualmente (11 artículos mal
clasificados por coincidencia incidental de palabra clave fueron identificados y reemplazados). 41/41
tests dirigidos pasan.

**Redistribuciones de objetivo documentadas** (celdas del grid sin oferta suficiente de contenido
propio, resueltas moviendo el objetivo íntegro de opinión a noticia dura del mismo medio, preservando
siempre el total de 20 oraciones/celda):

- **Infobae Colombia** no tiene sección de opinión propia de Colombia (confirmado sobre 100 columnas
  de su feed de opinión: solo 3 mencionan Colombia, ninguna coincide con los 5 temas del corpus).
  Objetivo de opinión (6/tema) redistribuido íntegro a su propia noticia dura (14→20 por tema). Ver
  `medios.yaml` (`opinion_no_disponible`).
- **El Espectador / Seguridad y orden público**: su feed de opinión no tenía contenido sobre ese tema
  específico (6→20 en noticia dura).
- **El Tiempo / Relación con Estados Unidos**: no se encontró una columna de opinión propia sobre este
  tema en circulación (se probaron ~15 candidatas) (14→20 en noticia dura).

El esquema de anotación quedó definido como la **Tabla 1** de `esquemas_anotacion.xlsx` (esquema
completo: 5 categorías léxicas J1 + 4 discursivas J2, cada una con su span, más dirección/actor
objetivo/intensidad) — es el que implementa la hoja `Corpus - oraciones`, una fila por oración.

Detalle completo por celda: correr
`python -c "from sesgocognitivo.corpus.grid_tracker import GridState; import openpyxl; print(GridState.desde_workbook(openpyxl.load_workbook('data/corpus/grid_recoleccion_500_oraciones.xlsx')).resumen_texto())"`.

## Referencias

- `docs/propuesta/` — propuesta de trabajo de grado: motivación completa, estado del arte, pregunta de
  investigación, objetivos específicos y cronograma.
- `docs/metodologia/` — resúmenes de decisiones metodológicas tomadas con el tutor (documentos vivos,
  se actualizan sesión a sesión): distribución del corpus, validación de la segmentación, marco DART,
  retiro de la simulación de sesgos cognitivos.
- `docs/papers/` — fundamento teórico del esquema de anotación (Recasens et al. 2013; Rodrigo-Ginés et
  al. 2024; Alam et al. 2022).
