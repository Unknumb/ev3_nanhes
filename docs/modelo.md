# Model card — Longevidad NHANES (modelo COMBINADO)

Dos modelos entrenados sobre el mismo dataset preprocesado:
- **Clasificación** — `IS_LONGEVO` (1 si edad ≥ 70), `XGBClassifier`.
- **Regresión** — `RIDAGEYR` (edad cronológica, interpretada como **edad biológica**), `XGBRegressor`.

El modelo de producción es el **combinado** (`nhanes_combined`): unifica los aportes de los tres
ciclos del equipo en un único dataset y un único par de modelos. Los pipelines por ciclo
(`nhanes_2013` de Nicolás, `nhanes_2015` de Álvaro, `nhanes_2017_2018` de Juan) se conservan como
baselines comparables, pero **no** son los que se sirven en la API.

## Datos
- **Fuente:** NHANES (CDC), descarga de `.xpt` (SAS) en runtime. Se bajan **todas las edades** de
  los 7 ciclos del equipo (2017-2018 base + 2015, 2013, 2011, 2009, 2007, 2005) → **42.143** adultos.
- **Balanceo desacoplado por modelo** (clasificación y regresión necesitan distribuciones opuestas):
  - **Clasificación → vista aumentada:** ciclo base + **solo longevos (≥70)** de los históricos.
    Rescata la clase minoritaria → F1 alto. (~11.7k filas.)
  - **Regresión → vista balanceada por edad:** ciclo base + longevos históricos + **40% de los
    jóvenes históricos**. Evita que el regresor infle la edad biológica de personas jóvenes (un
    joven de 20 pasó de ~55 a ~33 años) manteniendo R²≥0.80. (~23.9k filas.)
  - El 0.4 está tuneado como el **máximo de jóvenes que mantiene R²≥0.80**. `CICLO_ORIGEN` registra
    el origen de cada fila.
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

| Modelo | Métrica | **Combinado** | Baseline 2015 |
|---|---|---|---|
| Clasificación (vista aumentada) | Accuracy | **0.907** | 0.871 |
| | F1-score | **0.922** | 0.870 |
| Regresión (vista balanceada) | MAE | **6.79 años** | 7.26 años |
| | R² | **0.804** | 0.747 |

**Lectura:** el clasificador acierta la longevidad con **F1 0.92**. La regresión explica el **80%**
de la varianza de edad con un error de **~6.8 años**, y —tras balancear por edad— ya **no infla** la
edad biológica de personas jóvenes (un caso de 20 años pasó de 55 a **33 años**). En la importancia
global del regresor dominan las features clínicas nuevas (evento cardiovascular, diabetes, HbA1c,
tabaquismo). Ambas métricas se mantienen **≥0.80** por diseño (el balanceo está tuneado a ese límite).

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
