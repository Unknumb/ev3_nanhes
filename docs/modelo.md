# Model card — Longevidad NHANES (modelo COMBINADO)

Dos modelos entrenados sobre el mismo dataset preprocesado:
- **Clasificación** — `IS_LONGEVO` (1 si edad ≥ 70), `XGBClassifier`.
- **Regresión** — `RIDAGEYR` (edad cronológica, interpretada como **edad biológica**), `XGBRegressor`.

El modelo de producción es el **combinado** (`nhanes_combined`): unifica los aportes de los tres
ciclos del equipo en un único dataset y un único par de modelos. Los pipelines por ciclo
(`nhanes_2013` de Nicolás, `nhanes_2015` de Álvaro, `nhanes_2017_2018` de Juan) se conservan como
baselines comparables, pero **no** son los que se sirven en la API.

## Datos
- **Fuente:** NHANES (CDC), descarga de `.xpt` (SAS) en runtime.
- **Data augmentation:** el ciclo base **2017-2018** (Juan) aporta todos los pacientes; los ciclos
  históricos **2015-2016** (Álvaro), **2013-2014** (Nicolás), **2011, 2009, 2007, 2005** aportan
  **solo longevos (≥70)** para rescatar la clase minoritaria. `CICLO_ORIGEN` registra el origen de
  cada fila; cada ciclo se descarga una sola vez (sin solapes ni duplicados).
- **Split:** `train_test_split` 80/20, `random_state=42` (estratificado por `IS_LONGEVO` en
  clasificación).
- **36 features** (numéricas + categóricas NHANES), en tres bloques:
  - **23 base:** demografía, antropometría, presión arterial y labs originales (colesterol total, glucosa).
  - **Nivel B — panel PhenoAge** (Levine 2018), 9 labs **opcionales/imputados**: HbA1c, HDL, albúmina,
    creatinina, fosfatasa alcalina, leucocitos, % linfocitos, VCM, RDW. Suben el modelo sin añadir
    fricción (si el usuario no los tiene, se imputan).
  - **Nivel A — cuestionario**, 4 preguntas fáciles: salud autopercibida (`HSD010`), tabaquismo
    (`SMQ020`), diabetes (`DIQ010`) y evento cardiovascular previo (`MCQ_CVD`, derivada de `MCQ160B/C/E/F`).
  - Excluidas de features: `SEQN`, `RIDAGEYR`, `IS_LONGEVO`, `CICLO_ORIGEN`.
- **Imputación:** numéricas por **mediana** + `StandardScaler`; categóricas por moda + `OneHotEncoder`.
  (El combinado usa mediana en vez de KNN: con 7 ciclos y el panel de labs disperso, KNN O(n²) es inviable.)

## Métricas (modelo combinado · conjunto de test)

Dataset: 15.139 pacientes descargados → **11.741** adultos (≥18). Split train/test: **9.392 / 2.349**.

| Modelo | Métrica | **Combinado (A+B)** | Baseline 2015 |
|---|---|---|---|
| Clasificación | Accuracy | **0.907** | 0.871 |
| | F1-score | **0.922** | 0.870 |
| | Mejor F1 (CV train) | 0.917 | 0.870 |
| Regresión | MAE | **6.02 años** | 7.26 años |
| | R² | **0.812** | 0.747 |
| | Mejor MAE (CV train) | 6.11 años | 7.39 años |

**Lectura:** frente al baseline 2015, el modelo combinado (más ciclos + panel PhenoAge + cuestionario)
**mejora en ambas tareas**: el clasificador sube a F1 0.92 y la regresión baja el error de la edad
biológica a **~6 años** y explica el **81%** de la varianza (R² 0.75 → 0.81). En la importancia
global del regresor dominan justamente las features nuevas: evento cardiovascular previo (`MCQ_CVD`),
diabetes, HbA1c y tabaquismo — señal clínica real, no demográfica.

> Reproducible: `kedro run --pipeline nhanes_combined`. Los reportes quedan en
> `data/08_reporting/reporte_{clasificacion,regresion}_combined.txt`.

## Metodología (anti-fuga de datos)
- `train_test_split` **antes** de cualquier transformación.
- Preprocesamiento dentro de un `Pipeline` sklearn (`ColumnTransformer`):
  - numéricas: `SimpleImputer(median)` → `StandardScaler` (mediana, no KNN: el dataset combinado es
    grande y disperso por el panel de labs opcionales)
  - categóricas: `SimpleImputer(most_frequent)` → `OneHotEncoder(handle_unknown="ignore")`
  - se ajusta **solo con train** en cada fold de `RandomizedSearchCV` (30 iters, 5-fold).
- El `best_estimator_` es un **Pipeline autocontenido** → la API pasa el dict crudo
  y llama `.predict()` (sin preprocesamiento manual, sin *training/serving skew*).

### Mejores hiperparámetros (baseline 2015)
- **Clasificación:** `n_estimators=200`, `max_depth=3`, `learning_rate=0.2`,
  `subsample=1.0`, `colsample_bytree=0.9`, `min_child_weight=3`.
- **Regresión:** `n_estimators=300`, `max_depth=7`, `learning_rate=0.05`,
  `subsample=0.9`, `colsample_bytree=0.7`, `min_child_weight=5`.

Los del combinado quedan registrados en los reportes de `data/08_reporting/` tras reentrenar.

## Reentrenar
```bash
kedro run --pipeline nhanes_combined   # descarga CDC (todos los ciclos) + entrena el modelo único
kedro run --pipeline serving           # bendice los pickles a data/09_serving/
```
Genera los pickles bendecidos en `data/09_serving/` (ver [despliegue.md](despliegue.md)).
Reproducible con `random_state=42`.

## Limitaciones
- **Proyecto académico/educativo**: no es consejo médico ni diagnóstico.
- "Edad biológica" = edad cronológica **estimada** a partir de biomarcadores; es una
  aproximación poblacional, no una medición clínica.
- Entrenado sobre población NHANES (EE. UU.); puede no generalizar a otras poblaciones.
- El data augmentation con longevos históricos balancea la clase pero introduce
  pacientes de cohortes distintas (`CICLO_ORIGEN` lo documenta). El combinado acentúa esto al
  abarcar 7 ciclos (2005-2018).
- **Labs opcionales imputados:** el panel PhenoAge (Nivel B) sube el modelo, pero quien no aporta
  análisis recibe valores imputados por mediana → su predicción es menos personalizada (no errónea).
- **PCR (inflamación) excluida a propósito:** la PCR estándar se discontinuó tras 2009-2010 y la
  hs-CRP recién aparece en 2015; cubrirla dejaría huecos por ciclo (riesgo de proxy de cohorte), así
  que se omite del panel.
- `MCQ_CVD` (evento cardiovascular previo) domina la importancia: es señal real (la prevalencia de
  CVD sube con la edad), no fuga, ya que no se deriva de `RIDAGEYR`.
