# Informe de estudio — Defensa individual EV Parcial N°3 (SCY1101)
## Proyecto: Predicción de longevidad y edad biológica con datos NHANES

> **Para qué sirve este documento.** Es tu guía para estudiar y poder **explicar el
> proyecto desde cero** en la defensa individual de 15 minutos: los notebooks de
> investigación, los pipelines de producción (Kedro) y los modelos (XGBoost).
> Está escrito para que entiendas el *porqué* de cada decisión, no solo el *qué*.
> Al final hay un guion minuto a minuto, un banco de preguntas del profesor y un glosario.

---

## 0. El "elevator pitch" (memorízalo)

> *"Construimos una solución **end-to-end** que estima la **longevidad** y la **edad
> biológica** de una persona a partir de sus biomarcadores de salud. Partimos de datos
> públicos de salud de EE. UU. (NHANES, del CDC), los procesamos con un pipeline ETL
> automatizado en **Kedro**, entrenamos dos modelos **XGBoost** —uno de clasificación y
> uno de regresión—, y los exponemos a través de una **API REST (FastAPI)** que alimenta
> un **dashboard diferenciado por audiencia** (ejecutiva, técnica y operativa). Todo está
> versionado en Git, persistido en una base de datos **SQL** y empaquetado en **Docker**."*

Si solo memorizas un párrafo, que sea ese. Cubre las 3 fuentes de datos, el ETL, los
modelos, la API, el dashboard, la base de datos y Docker —los seis ejes que evalúa la pauta.

---

## 1. Qué evalúa la pauta en la presentación individual (lo primero que debes saber)

La EV Parcial N°3 vale **40%** del ramo y se divide en:
- **Encargo (grupal) — 10%**: el producto en sí (indicadores 1–5).
- **Presentación (individual) — 30%**: tu defensa de 15 min (indicadores 6–8).

**Tú serás evaluado sobre estos 3 indicadores** (suman el 100% de la nota individual):

| # | Indicador | Peso | Qué debes demostrar |
|---|-----------|------|----------------------|
| **6** | Demuestra el funcionamiento completo del pipeline **end-to-end** | **30%** | Demo en vivo fluida + explicar arquitectura y decisiones técnicas. Nivel máximo = *"demo fluida, explicación detallada y respuestas sólidas"*. |
| **7** | Presenta **dashboards interactivos** por audiencia y **valor de negocio** | **30%** | Mostrar las vistas ejecutiva/técnica/operativa y explicar el valor para cada usuario. Nivel máximo = *"explica valor de negocio con ejemplos, evidencia comprensión de usuarios"*. |
| **8** | Explica el **proceso colaborativo**, herramientas y **metodología** | **40%** | Flujo Git, gestión del proyecto, **propуestas de mejora y análisis crítico**. Es el indicador **de mayor peso**. |

**Focos de observación de la pauta (cómo te miran):**
1. Claridad en la defensa del pipeline ETL y la arquitectura técnica.
2. Justificación de decisiones de diseño, herramientas y procesos.
3. Capacidad de **adaptar el discurso a distintas audiencias** (ejecutiva/técnica/operativa).
4. Argumentación sobre Git y despliegue en Docker.
5. **Reflexión crítica**: lecciones aprendidas y oportunidades de mejora.

**Conclusiones prácticas para preparar la defensa:**
- El indicador 8 (40%) **no es técnico**: es proceso, metodología y *autocrítica*. Llega con
  un relato claro del flujo Git (ramas, PRs, code review, resolución de conflictos) y con
  2–3 **mejoras concretas** que propondrías. Esto solo se gana hablando, no programando.
- El indicador 6 (30%) exige **demo en vivo**. Ten el `docker-compose up` probado de
  antemano y un plan B (capturas/video) por si falla la red o la descarga del CDC.
- El indicador 7 (30%) exige **adaptar el lenguaje**: a la audiencia ejecutiva NO le hablas
  de F1-score; le hablas de "% de personas longevas" y "edad biológica promedio".
- La pauta nombra **"Plotly Dash o Streamlit"** como ejemplo de dashboard. Ten claro qué
  herramienta presentas y por qué; si el dashboard graduado no es una de esas dos, prepara
  el argumento de por qué tu elección cumple igual la **diferenciación por audiencia**.

---

## 2. El problema y los datos (la base de todo)

**El problema de negocio.** ¿Se puede estimar cuán "viejo" está el cuerpo de una persona
—y si llegará a ser longeva— mirando solo sus biomarcadores (peso, presión, colesterol,
glucosa, etc.), sin saber su edad real? Esto tiene valor en salud preventiva, seguros y
bienestar: detectar a alguien cuya "edad biológica" es mayor que su edad real es una señal
de riesgo accionable.

**Los datos: NHANES.** Es la *National Health and Nutrition Examination Survey* del CDC
(EE. UU.). Publica, por ciclos de 2 años, tablas con exámenes médicos reales de miles de
personas. Los archivos vienen en formato **`.xpt` (SAS)** y se descargan directamente desde
`wwwn.cdc.gov`. **No** guardamos los datos en el repo: se descargan frescos en cada corrida
(reproducibilidad + no inflar el repo).

**Las dos variables objetivo (targets):**
- **`IS_LONGEVO`** (clasificación): 1 si la persona tiene **edad ≥ 70**, 0 si no. La
  creamos nosotros a partir de la edad.
- **`RIDAGEYR`** (regresión): la **edad cronológica** real en años. El modelo la predice a
  partir de los biomarcadores; ese valor predicho lo interpretamos como **"edad biológica"**.

**Idea clave de la "edad biológica":** si el modelo, mirando solo tus biomarcadores, te
estima 64 años cuando en realidad tienes 58, significa que *tu cuerpo se parece al de una
persona de 64* → tu edad biológica > tu edad cronológica. Esa diferencia la llamamos el
**`gap` = edad_biológica − edad_cronológica**.

**Las 36 features (variables de entrada)** son códigos NHANES originales, en tres bloques:
- **Base — Numéricas (19):** tamaño del hogar/familia e ingreso (`DMDHHSIZ`, `DMDFMSIZ`,
  `INDFMPIR`); medidas corporales (`BMXWT` peso, `BMXHT` estatura, `BMXBMI` IMC,
  `BMXWAIST` cintura, `BMXLEG`, `BMXARML`, `BMXARMC`); presión arterial y pulso
  (`BPXSY1/2/3` sistólica, `BPXDI1/2/3` diastólica, `BPXPLS` pulso); laboratorio
  (`LBXTC` colesterol total, `LBXGLU` glucosa).
- **Base — Categóricas (4):** `RIAGENDR` (sexo), `RIDRETH3` (etnia), `DMDEDUC2` (educación),
  `DMDMARTL` (estado civil).
- **Nivel B — panel PhenoAge (9 labs, opcionales/imputados):** `LBXGH` HbA1c, `LBDHDD` HDL,
  `LBXSAL` albúmina, `LBXSCR` creatinina, `LBXSAPSI` fosfatasa alcalina, `LBXWBCSI` leucocitos,
  `LBXLYPCT` % linfocitos, `LBXMCVSI` VCM, `LBXRDW` RDW. Alinean el modelo con el reloj de edad
  biológica validado de Levine (2018); suben las métricas sin añadir fricción al formulario.
- **Nivel A — cuestionario (4, fáciles):** `HSD010` (salud autopercibida), `SMQ020` (tabaquismo),
  `DIQ010` (diabetes), `MCQ_CVD` (evento cardiovascular previo, derivada de `MCQ160B/C/E/F`).
- **Excluidas de las features:** `SEQN` (id del paciente), `RIDAGEYR` (es target),
  `IS_LONGEVO` (es target), `CICLO_ORIGEN` (metadato de procedencia).

> ⚠️ **Punto que el profesor puede atacar:** `RIDAGEYR` (la edad) **NO es una feature** del
> modelo. Sería trampa ("fuga de datos") usar la edad para predecir la edad o la longevidad
> (que se define con la edad). El modelo solo ve biomarcadores.

---

## 3. PARTE A — Los notebooks (la fase de investigación)

Los notebooks (`notebooks/`, en español, autores Álvaro y Nicolás) son la **superficie de
prototipado**: ahí se exploró y se probó qué funcionaba. Después, lo que funcionó se
"productivizó" en `nodes.py` (los pipelines). **Hay dos series paralelas** (`_alvaro_2015`
y `_nicholas_2013`) porque cada integrante trabajó un ciclo NHANES distinto. Cada ciclo tiene
su pipeline (Nicolás 2013, Álvaro 2015, Juan 2017-2018), pero el modelo que se sirve en
producción es el **combinado** (`nhanes_combined`): unifica los tres aportes en un único dataset
(base 2017-2018 + longevos históricos 2015/2013/2011/2009/2007/2005) y entrena un solo par de
modelos sobre un contrato de 36 features (las 23 base + el panel PhenoAge de laboratorio + 4 de
cuestionario: salud autopercibida, tabaquismo, diabetes y evento cardiovascular previo).

Sigue siempre la misma narrativa numerada 01 → 05:

### Notebook 01 — EDA (Análisis Exploratorio de Datos)
**Objetivo:** entender los datos antes de modelar. Qué se hace y por qué:
- **Corrección del centinela SAS** (sección 2.1): el valor `5.397605e-79` es el código de
  "dato faltante" de SAS; si no lo conviertes a `NaN`, corrompe todas las estadísticas
  (medias, correlaciones). Es lo **primero** que se hace tras cargar.
- **Análisis de nulos** y **diccionario de variables** (qué significa cada código NHANES).
- **Distribución del target `RIDAGEYR`** y creación de `IS_LONGEVO`, observando el
  **desbalance de clases** (hay muchos menos longevos que no-longevos).
- **Comparación de biomarcadores longevos vs. no-longevos**, correlaciones, presión por
  grupo etario, pairplots.
- **Cómo explicarlo:** *"El EDA nos mostró dos cosas que definieron el resto del proyecto:
  (1) los datos venían con un centinela de SAS que había que limpiar, y (2) la clase
  'longevo' era minoritaria, lo que nos obligó a una estrategia de balanceo."*

### Notebook 02 — Preprocesamiento
**Objetivo:** dejar los datos listos para modelar. Pasos: selección de variables, filtrado
(solo adultos ≥18), creación de `IS_LONGEVO`, separación numéricas/categóricas,
**imputación** de nulos, **codificación** de categóricas (one-hot) y **escalado**
(`StandardScaler`).
- **Diferencia crítica con el pipeline de producción:** en el *notebook* el preprocesamiento
  se hace "a mano" sobre todo el dataset. En **producción esto cambió** para evitar **fuga
  de datos** (ver Parte B). Es importante que sepas explicar esta evolución: *"En el
  notebook exploramos el preprocesamiento de forma directa; al productivizar lo movimos
  dentro de un `Pipeline` de sklearn para que se ajuste solo con datos de entrenamiento."*

### Notebook 03 — Aprendizaje No Supervisado (PCA + K-Means)
**Objetivo:** descubrir **estructura oculta** en los datos sin usar el target.
- **PCA** (Análisis de Componentes Principales): reduce las ~23 dimensiones a 2–3
  componentes que concentran la mayor varianza, para poder **visualizar** y quitar ruido.
- **K-Means**: agrupa pacientes en *clusters*. El **número óptimo de grupos (K)** se elige
  con el **método del codo** y el **silhouette score**.
- **Resultado:** los centroides de cada cluster se interpretan como **"fenotipos de salud"**
  (perfiles de paciente). Es análisis exploratorio: **no entra al pipeline de producción**,
  pero demuestra dominio de aprendizaje *no supervisado* (parte del temario del ramo).
- **Cómo explicarlo:** *"El no supervisado no predice; agrupa. Lo usamos para validar que
  existen perfiles de salud diferenciables en la población, lo que respalda que un modelo
  supervisado pueda separar longevos de no longevos."*

### Notebook 04 — Clasificación (predecir `IS_LONGEVO`)
**Objetivo:** comparar modelos para predecir longevidad. Se prueban **Decision Tree**
(modelo base), **Random Forest** y **XGBoost**, y **gana XGBoost**.
- **Estrategia contra el desbalance:** `scale_pos_weight` (le da más peso a la clase
  minoritaria) + **data augmentation** (ver Parte B).
- **Threshold tuning:** se optimiza el umbral de decisión (no necesariamente 0.5) para
  maximizar el F1 según el balance entre falsos positivos y falsos negativos.
- Se evalúa con **classification report**, **matrices de confusión** e **importancia de
  variables**.

### Notebook 05 — Regresión (predecir la edad → "edad biológica")
**Objetivo:** predecir `RIDAGEYR` (edad) con **Random Forest Regressor** y **XGBoost
Regressor**; gana XGBoost.
- **Por qué el target NO se escala:** queremos predecir años reales e interpretables (un
  MAE de "7 años" tiene sentido; un MAE en unidades escaladas, no).
- Se evalúa con **MAE**, **R²**, gráfico de **edad real vs. predicha**, distribución del
  error e importancia de variables.
- **Conexión con el producto:** este modelo es el que produce la **"edad biológica"** que ve
  el usuario final en el dashboard.

> **Mensaje para la defensa:** los notebooks son el "laboratorio" (investigación
> reproducible, indicador de la pauta). Demuestran el **método científico de datos**:
> explorar → preprocesar → buscar estructura → clasificar → regresar.

---

## 4. PARTE B — Los pipelines (la fase de producción, con Kedro)

### 4.1 ¿Qué es Kedro y por qué lo usamos?
**Kedro** es un framework para estructurar proyectos de datos de forma **reproducible y
modular**. En vez de un notebook gigante, organizas el trabajo en:
- **Nodos**: funciones de Python puras (una entrada → una salida).
- **Pipelines**: nodos conectados en un grafo (DAG).
- **Catálogo de datos** (`conf/catalog*.yml`): declara dónde vive cada dataset (qué archivo,
  qué formato), separando los datos del código.

**Por qué Kedro y no solo notebooks:** los notebooks son geniales para explorar pero malos
para producción (orden de ejecución frágil, difícil de testear, difícil de versionar). Kedro
nos da **reproducibilidad** (`kedro run` corre todo igual siempre), **modularidad** y
**testeo** — exactamente lo que pide la pauta ("organización y reproducibilidad",
"automatización").

### 4.2 Los datos en capas (estructura `data/NN_*`)
Kedro recomienda numerar las capas de datos. Las nuestras:
`01_raw` → `02_intermediate` → `03_primary` → `04_feature` → `05_model_input` →
`06_models` → `07_model_output` → `08_reporting` → `09_serving`.
La capa **`09_serving`** contiene el modelo "bendecido" (el de producción) que consume la API.

### 4.3 El pipeline de producción `nhanes_combined` (4 nodos)
El modelo servido es el **combinado**. Su lógica vive en
`src/ev3_nhanes/pipelines/nhanes_combined/nodes.py` y comparte exactamente la misma estructura
**lineal de 4 nodos** que los pipelines por ciclo (Nicolás 2013, Álvaro 2015, Juan 2017-2018):

1. **`descargar_y_unir_combinado`** — sin inputs; **descarga los `.xpt` directamente del CDC** y
   los une. Une el ciclo base **2017-2018** (todos los pacientes) con los longevos (≥70) de los
   ciclos históricos **2015/2013/2011/2009/2007/2005**. Necesita internet. → `raw_nhanes_combined`.
2. **`preprocesar_datos_combinado`** — selecciona columnas, filtra adultos (≥18) y crea
   `IS_LONGEVO`. **Importante: ya NO imputa/escala/codifica aquí** (eso se movió al Pipeline
   de modelado para no filtrar información del test). → `preprocessed_nhanes_combined`.
3. **`entrenar_modelo_clasificacion`** — XGBoost + RandomizedSearchCV → pickle versionado.
4. **`entrenar_modelo_regresion`** — XGBoost + RandomizedSearchCV → pickle versionado.

`pipeline_registry.py` autodescubre los pipelines, así que `kedro run` (sin argumentos)
corre todo (los baselines por ciclo **y** el combinado). Los pipelines por ciclo se conservan
como referencia comparable, pero el que se bendice y sirve es el combinado.

### 4.4 Las 4 decisiones técnicas que DEBES saber explicar

Estas cuatro son las que el profesor preguntará. Domínalas.

**(a) Limpieza del centinela SAS (`5.397605e-79` → `NaN`).**
SAS marca los faltantes con ese número minúsculo. La función `_limpiar_missing_sas` lo
convierte a `NaN` **inmediatamente después de cada descarga**. Si no, corrompe medias,
escalados y correlaciones. *Decisión de robustez del ETL (indicador 1).*

**(b) Data augmentation para balancear la clase minoritaria.**
Los longevos (≥70) son pocos. Solución: el ciclo base aporta **TODOS los pacientes** (en el
modelo combinado, el **2017-2018**), pero los **ciclos históricos aportan SOLO los longevos
(≥70)** — en el combinado son seis: **2015, 2013, 2011, 2009, 2007 y 2005**. Así "rescatamos"
la clase minoritaria sin inflar la mayoritaria. La columna **`CICLO_ORIGEN`** registra de qué
ciclo vino cada fila (trazabilidad), y como cada ciclo se descarga una sola vez no hay duplicados.
- Detalle fino: al traer solo longevos se usa un **`left join`** (no `outer`) para no
  arrastrar pacientes jóvenes desde las tablas de laboratorio.
- *Cómo explicarlo:* *"En vez de inventar datos sintéticos (SMOTE), reutilizamos longevos
  reales de ciclos anteriores. Es data augmentation con datos auténticos."*

**(c) Anti-fuga de datos (data leakage) — la decisión estrella.**
La regla de oro: **el modelo nunca debe ver información del conjunto de test durante el
entrenamiento.** Por eso:
- El **`train_test_split` ocurre ANTES** de cualquier imputación/escalado.
- Todo el preprocesamiento (`KNNImputer`, `StandardScaler`, `OneHotEncoder`) vive **dentro
  de un `Pipeline` de sklearn** (`ColumnTransformer`), que se **ajusta solo con el train de
  cada *fold*** de la validación cruzada.
- Incluso `scale_pos_weight` se calcula **solo con el train**.
- *Por qué importa:* si imputas o escalas con todo el dataset (como en el notebook 02), el
  test "se entera" de la media/distribución global → métricas infladas y poco realistas.

**(d) Pickle autocontenido (sin *training/serving skew*).**
El modelo guardado (`best_estimator_`) es un **`Pipeline` completo**: preprocesamiento +
XGBoost en un solo objeto. Por eso la **API pasa el diccionario crudo** de biomarcadores y
llama `.predict()` — **no reimplementa el preprocesamiento**. Esto elimina el riesgo de que
el preprocesamiento en producción difiera del de entrenamiento (*training/serving skew*).
- Bonus: como el imputador está fiteado dentro del Pipeline, **los campos no clínicos
  pueden ir vacíos** → el formulario solo exige ~11 biomarcadores clínicos; el resto se
  imputa solo.

### 4.5 Las 3 fuentes de datos (requisito central del encargo)
La pauta exige **≥3 fuentes de naturaleza distinta**. Las nuestras:

| # | Fuente | Tipo | Rol |
|---|--------|------|-----|
| 1 | Archivos NHANES `.xpt` (SAS) del CDC | **Archivos remotos** | Materia prima del ETL/entrenamiento |
| 2 | API REST propia (FastAPI) | **Servicio REST** | El dashboard consume predicciones y explicabilidad |
| 3 | Base SQL (Postgres/Supabase; SQLite en dev) | **Base de datos** | Historial de predicciones + agregados para la vista ejecutiva |

> El pipeline **`load_db`** carga el dataset procesado a la base SQL; el pipeline **`serving`**
> copia el modelo combinado a la ruta estable `data/09_serving/` con su `metadata.json`.

---

## 5. PARTE C — Los modelos (XGBoost)

### 5.1 ¿Qué es XGBoost y por qué lo elegimos?
**XGBoost** = *Extreme Gradient Boosting*. Construye muchos **árboles de decisión** en
secuencia, donde **cada árbol corrige los errores del anterior** (*boosting*). Ganó sobre
Decision Tree y Random Forest porque:
- Maneja muy bien **datos tabulares** y relaciones no lineales.
- Es **robusto a outliers** y no le afecta la colinealidad (por eso NO usamos `drop_first`
  en el one-hot: los árboles no sufren multicolinealidad).
- Tiene regularización incorporada → menos overfitting.

### 5.2 Cómo se entrenan (igual para ambos)
1. `train_test_split` 80/20 (`random_state=42`; **estratificado por `IS_LONGEVO`** en
   clasificación para mantener la proporción de clases).
2. `Pipeline = [preprocesador, modelo XGBoost]`.
3. **`RandomizedSearchCV`** con **30 iteraciones** y **5-fold cross-validation**: prueba 30
   combinaciones aleatorias de hiperparámetros y se queda con la mejor según la métrica.
   - Clasificación: `scoring="f1"`, `StratifiedKFold(5)`.
   - Regresión: `scoring="neg_mean_absolute_error"`, `KFold(5)`.
4. El `best_estimator_` se evalúa **una sola vez** sobre el test intacto.

**Hiperparámetros buscados:** `n_estimators` (nº de árboles), `max_depth` (profundidad),
`learning_rate` (tasa de aprendizaje), `subsample`, `colsample_bytree`, `min_child_weight`.

### 5.3 Resultados (conjunto de test)
| Modelo | Métrica | Valor | Lectura en una frase |
|--------|---------|-------|----------------------|
| Clasificación | **Accuracy** | **0.871** | Acierta si es longevo ~87% de las veces. |
| Clasificación | **F1-score** | **0.870** | Equilibrio bueno entre precisión y recall (importante con clases desbalanceadas). |
| Regresión | **MAE** | **7.26 años** | Se equivoca en promedio ±7 años al estimar la edad biológica. |
| Regresión | **R²** | **0.747** | Explica ~75% de la variabilidad de la edad. |

Mejores hiperparámetros encontrados:
- **Clasificación:** `n_estimators=200, max_depth=3, learning_rate=0.2, subsample=1.0,
  colsample_bytree=0.9, min_child_weight=3`.
- **Regresión:** `n_estimators=300, max_depth=7, learning_rate=0.05, subsample=0.9,
  colsample_bytree=0.7, min_child_weight=5`.

> **Por qué la clasificación usa árboles poco profundos (`max_depth=3`) y la regresión más
> profundos (`max_depth=7`):** clasificar longevo/no-longevo es una frontera más simple;
> estimar la edad exacta es una tarea más fina que necesita más capacidad de modelo.

### 5.4 Explicabilidad: SHAP
Un modelo que solo dice "serás longevo" no genera confianza. **SHAP** (*SHapley Additive
exPlanations*) descompone **cada predicción** en cuánto empujó cada feature hacia el
resultado. El endpoint `/explain` devuelve, por ejemplo: *"glucosa alta (`LBXGLU`) empuja
+0.83 hacia longevo; IMC (`BMXBMI`) empuja −0.40 hacia no-longevo"*. En el dashboard se ve
como un **gráfico waterfall**. *Esto es clave para la audiencia técnica y para el "valor de
negocio" (decisiones explicables).*

### 5.5 Métricas, explicadas desde cero (para el glosario mental)
- **Accuracy:** % de aciertos totales. Engañosa con clases desbalanceadas (por eso miramos F1).
- **Precision:** de los que predije longevos, ¿cuántos lo eran?
- **Recall:** de los longevos reales, ¿a cuántos detecté?
- **F1-score:** media armónica de precision y recall (castiga el desbalance).
- **Matriz de confusión:** tabla de aciertos/errores (VP, VN, FP, FN).
- **MAE (Mean Absolute Error):** error promedio en las unidades del target (años).
- **R²:** proporción de la varianza explicada (1 = perfecto, 0 = no mejor que la media).

---

## 6. PARTE D — La arquitectura end-to-end (lo que muestras en la demo)

**Flujo completo:** `CDC (.xpt)` → **ETL Kedro** (descarga → limpia → preprocesa → entrena)
→ **modelo bendecido** (`data/09_serving`) → **API FastAPI** ↔ **Base SQL** → **Dashboard
por audiencia**. Todo orquestado con **docker-compose**.

**La API (FastAPI)** expone, entre otros:
- `GET /schema` — el contrato de las 36 features; el front arma el formulario desde aquí.
- `POST /predict` — devuelve `es_longevo`, `probabilidad`, `edad_biologica`, `gap`; persiste
  el registro en la BD (*best-effort*: si la BD cae, igual responde).
- `POST /explain` — contribuciones SHAP.
- `GET /metrics` — reportes de entrenamiento (accuracy / MAE).
- `GET /aggregates` — agregados del historial (para la vista ejecutiva).
- `GET /health` — liveness + estado de modelos y BD.
- Swagger automático en `/docs` (documentación de API siempre sincronizada — indicador 2).

**El dashboard, diferenciado por 3 audiencias** (esto es el indicador 7, 30%):
- **Ejecutiva:** KPIs de **negocio**, sin jerga. % de longevos, edad biológica promedio,
  gap promedio, distribución por cohorte (lee agregados de la BD). *"¿Cuánta gente de
  nuestra cartera está envejeciendo más rápido de lo normal?"*
- **Técnica:** métricas del modelo (accuracy/MAE desde `/metrics`), importancia de features,
  SHAP, matriz de confusión. Para data scientists.
- **Operativa:** el **predictor**: formulario → `/predict` → muestra edad biológica vs.
  cronológica (gauge) + waterfall SHAP. Para el usuario que ingresa un caso.

**Docker (indicador 5 del encargo, y parte de la demo del indicador 6):**
`docker-compose.yml` orquesta **api + dashboard + Postgres** con variables de entorno.
Demuestra orquestación y configuración externa.

---

## 7. Mapeo directo a tu nota individual — qué decir en cada indicador

### Indicador 6 (30%) — Demo end-to-end + arquitectura
**Qué hacer:** `docker-compose up`, luego en vivo: ingresar un caso en la vista operativa →
ver la predicción → mostrar el waterfall SHAP → mostrar que quedó guardado en el historial
→ abrir la vista ejecutiva y ver el agregado actualizado. Mientras tanto, narras el flujo
con el **diagrama de arquitectura**.
**Frase ganadora:** *"Lo que acaban de ver tocó las tres fuentes: el modelo entrenado desde
los archivos del CDC, servido por la API REST, y persistido en la base SQL que alimenta los
KPIs ejecutivos."*

### Indicador 7 (30%) — Dashboards por audiencia + valor de negocio
**Qué hacer:** mostrar las 3 vistas y **cambiar el lenguaje** en cada una. Explica
explícitamente *para quién* es cada vista y *qué decisión* habilita.
**Frase ganadora (ejecutiva):** *"Esta vista no menciona F1-score a propósito: a un gerente
le importa el % de su población en riesgo y la edad biológica promedio, no la métrica del
modelo."*

### Indicador 8 (40%, el más pesado) — Proceso colaborativo + metodología + mejoras
**Esto es lo que más decide tu nota y es 100% discurso.** Prepara:
- **Flujo Git:** trabajamos con ramas por feature, **Pull Requests** hacia una rama de
  integración (no a `main`), **code review** cruzado, **issues** por tarea y resolución de
  **conflictos de merge** reales. (Ten a mano el grafo de commits / la lista de PRs).
- **Reparto de roles:** backend (API + BD), dashboard (las 3 vistas), MLOps (pipelines +
  Docker + CI). Explica cómo coordinaron.
- **Metodología:** tablero de gestión (issues/Projects), milestones semanales.
- **Análisis crítico + mejoras (lo que da el 100%):** ver sección 9.

---

## 8. Guion de defensa — 15 minutos minuto a minuto

| Min | Bloque | Qué dices/haces |
|-----|--------|------------------|
| 0–1 | **Hook** | El elevator pitch (sección 0) + el problema de negocio (edad biológica). |
| 1–3 | **Datos y fuentes** | NHANES, las 3 fuentes, por qué `.xpt` del CDC, las 36 features. |
| 3–5 | **Notebooks → pipeline** | Cómo pasamos de investigación (notebooks 01–05) a producción (Kedro). El centinela SAS y el data augmentation. |
| 5–7 | **Modelos** | XGBoost clf + reg, anti-fuga de datos, métricas (87% / 7 años), SHAP. |
| 7–11 | **DEMO EN VIVO** | `docker-compose up` → predicción → SHAP → historial → vista ejecutiva. (Indicadores 6 y 7). |
| 11–13 | **Arquitectura + Docker** | Diagrama end-to-end, pickle autocontenido, compose con 3 servicios. |
| 13–15 | **Colaboración + mejoras** | Flujo Git, metodología, **2–3 mejoras concretas y autocrítica** (indicador 8, 40%). |

**Regla de oro de tiempos:** la demo y la colaboración valen 70% de tu nota; no gastes más
de 5 min en teoría de modelos.

---

## 9. Banco de preguntas del profesor (y cómo responder)

**"¿Por qué la edad no es una feature del modelo?"**
Porque `IS_LONGEVO` se define a partir de la edad y el target de regresión *es* la edad.
Usarla sería fuga de datos: el modelo "haría trampa". Solo ve biomarcadores.

**"¿Cómo evitan el data leakage?"**
`train_test_split` antes de transformar; todo el preprocesamiento dentro del `Pipeline`, que
se ajusta solo con el train de cada fold; `scale_pos_weight` calculado solo con el train.

**"Su accuracy es 87%, ¿no está inflado por el desbalance?"**
Por eso reportamos **F1 (0.870)**, no solo accuracy, y usamos `scale_pos_weight` +
estratificación + data augmentation. El F1 alto muestra que detectamos bien la clase
minoritaria, no solo la mayoritaria.

**"¿Por qué XGBoost y no una red neuronal / regresión logística?"**
Para datos **tabulares** medianos, los árboles con boosting suelen superar a las redes y son
más interpretables (SHAP). La regresión logística no captura las no-linealidades. Igual
comparamos contra Decision Tree y Random Forest como baselines.

**"¿Qué es el `5.397605e-79`?"**
El centinela de faltante de SAS. Lo convertimos a `NaN` apenas descargamos; si no, corrompe
todas las estadísticas.

**"Su 'edad biológica' ¿es un concepto médico real?"**
Es una **estimación poblacional**, no un diagnóstico clínico. Es la edad cronológica
*predicha* desde biomarcadores; el gap es una señal de riesgo, no un veredicto médico. (Lo
declaramos como limitación: proyecto académico, no consejo médico.)

**"¿Por qué un MAE de 7 años? ¿No es mucho?"**
Para estimar edad solo desde biomarcadores poblacionales es un error razonable; el R² de
0.75 indica que el modelo captura la mayor parte de la señal. Para el caso de uso (señal de
riesgo, no diagnóstico) es suficiente.

**"Si la base de datos se cae, ¿se cae el predictor?"**
No. La persistencia es **best-effort**: `/predict` responde igual; solo se pierde el registro
en el historial. Decisión de diseño para no acoplar la predicción a la BD.

**"¿Cómo garantizan reproducibilidad?"**
`random_state=42` en todo, `kedro run` determinista, dependencias congeladas con `uv.lock`,
y los datos se redescargan frescos del CDC.

**"¿Por qué Streamlit/Next.js para el dashboard y no otra cosa?"**
*(Ten lista la respuesta según lo que realmente presenten.)* Lo clave para la pauta es la
**diferenciación por audiencia** y el **valor de negocio**, que cubrimos con las 3 vistas.

---

## 10. Lecciones aprendidas y propuestas de mejora (munición para el indicador 8)

Tener esto listo es lo que separa un 80% de un 100% en el indicador de mayor peso.

**Lecciones aprendidas:**
- Mover el preprocesamiento del notebook al `Pipeline` de sklearn fue clave para eliminar la
  fuga de datos; aprendimos que "lo que funciona en el notebook" no es directamente
  productivo.
- El desbalance de clases dominó el diseño: sin data augmentation y `scale_pos_weight`, el
  modelo ignoraba a los longevos.
- Separar el contrato de features (`feature_schema.json`) como única fuente de verdad evitó
  desincronización entre back y front.

**Propuestas de mejora (di 2–3 con convicción):**
1. **Modelo unificado + features clínicas (ya hecho):** el modelo de producción es el **combinado**
   (`nhanes_combined`), que une los tres ciclos del equipo (2005-2018) en un solo dataset y un solo
   par de modelos, con **36 features**: las 23 base + el **panel PhenoAge** de laboratorio (Levine
   2018) + 4 de cuestionario (salud autopercibida, tabaquismo, diabetes, evento cardiovascular). Eso
   subió la regresión a R² 0.80 (MAE ~6.8 años) y la clasificación a F1 0.92, con un balanceo
   desacoplado por edad para no inflar la edad biológica de personas jóvenes. La siguiente
   mejora sería sumar PCR/inflamación restringiendo ciclos (hoy se omite por el hueco 2011-2014).
2. **MLOps real:** versionado de modelos y métricas con un *model registry* (MLflow),
   reentrenamiento programado y monitoreo de *drift*.
3. **Validación clínica / más features:** incorporar más biomarcadores (HbA1c, perfil
   lipídico completo) y validar la "edad biológica" contra literatura.
4. **Tests de extremo a extremo** del flujo API→BD→dashboard y CI que corra el pipeline con
   datos sintéticos (hoy depende de la descarga del CDC).
5. **Caché de descargas del CDC** para que la demo no dependa de la red en vivo.

---

## 11. Glosario exprés (para explicar "desde cero")

- **NHANES:** encuesta de salud del CDC (EE. UU.); fuente de los datos.
- **`.xpt`:** formato de archivo de SAS; así publica el CDC.
- **ETL:** Extract-Transform-Load (extraer, transformar, cargar) — el pipeline de datos.
- **Kedro:** framework para pipelines de datos reproducibles (nodos + catálogo).
- **Feature / target:** variable de entrada / variable a predecir.
- **Data augmentation:** aumentar datos de la clase minoritaria (aquí, longevos históricos).
- **Data leakage (fuga):** que el modelo "vea" información del test al entrenar → métricas falsas.
- **Pipeline (sklearn):** objeto que encadena preprocesamiento + modelo en uno solo.
- **`ColumnTransformer`:** aplica transformaciones distintas a columnas numéricas y categóricas.
- **Imputación:** rellenar valores faltantes (KNN para numéricas, moda para categóricas).
- **One-hot encoding:** convertir categorías en columnas binarias 0/1.
- **`StandardScaler`:** normaliza numéricas a media 0 y desviación 1.
- **Cross-validation (k-fold):** partir el train en k bloques para validar sin tocar el test.
- **`RandomizedSearchCV`:** busca hiperparámetros probando combinaciones al azar con CV.
- **XGBoost:** modelo de árboles con boosting; el ganador en ambos problemas.
- **SHAP:** método para explicar cada predicción feature por feature.
- **MAE / R² / F1 / Accuracy:** métricas (ver sección 5.5).
- **`scale_pos_weight`:** peso extra a la clase minoritaria en XGBoost.
- **FastAPI:** framework Python para construir la API REST.
- **Best-effort:** intento de guardar que no bloquea la respuesta si falla.
- **Training/serving skew:** que el preprocesamiento difiera entre entrenar y predecir (lo
  evitamos con el pickle autocontenido).
- **Docker / docker-compose:** empaquetado y orquestación de los servicios.

---

### Apéndice — Comandos para la demo
```bash
# 1) Entrenar el modelo de producción combinado (descarga del CDC, lento)
kedro run --pipeline nhanes_combined
# 2) Bendecirlo a la ruta estable que usa la API
kedro run --pipeline serving
# 3) Cargar el dataset procesado a la base SQL
kedro run --pipeline load_db
# 4) Levantar todo (api :8000, dashboard, postgres)
docker-compose up
# Verificar la API
curl http://localhost:8000/health
```
