# Model card — Longevidad NHANES (ciclo 2015)

Dos modelos entrenados sobre el mismo dataset preprocesado:
- **Clasificación** — `IS_LONGEVO` (1 si edad ≥ 70), `XGBClassifier`.
- **Regresión** — `RIDAGEYR` (edad cronológica, interpretada como **edad biológica**), `XGBRegressor`.

## Datos
- **Fuente:** NHANES (CDC), descarga de `.xpt` (SAS) en runtime.
- **Data augmentation:** el ciclo base **2015-2016** aporta todos los pacientes; los
  ciclos históricos **2013, 2011, 2009, 2007** aportan **solo longevos (≥70)** para
  rescatar la clase minoritaria. `CICLO_ORIGEN` registra el origen de cada fila.
- **Volumen:** 14.022 pacientes descargados → **10.043** tras filtrar adultos (≥18).
- **Split:** `train_test_split` 80/20, `random_state=42` (estratificado por
  `IS_LONGEVO` en clasificación). Train/test: **8.034 / 2.009**.
- **23 features** (numéricas + categóricas NHANES). Excluidas de features:
  `SEQN`, `RIDAGEYR`, `IS_LONGEVO`, `CICLO_ORIGEN`.

## Métricas (conjunto de test)
| Modelo | Métrica | Valor |
|---|---|---|
| Clasificación | Accuracy | **0.871** |
| | F1-score | **0.870** |
| | Mejor F1 (CV train) | 0.870 |
| Regresión | MAE | **7.26 años** |
| | R² | **0.747** |
| | Mejor MAE (CV train) | 7.39 años |

**Lectura:** el clasificador acierta la longevidad ~87% de las veces; la regresión
estima la edad biológica con error promedio de ~7 años y explica el 75% de la varianza.

## Metodología (anti-fuga de datos)
- `train_test_split` **antes** de cualquier transformación.
- Preprocesamiento dentro de un `Pipeline` sklearn (`ColumnTransformer`):
  - numéricas: `KNNImputer(5)` → `StandardScaler`
  - categóricas: `SimpleImputer(most_frequent)` → `OneHotEncoder(handle_unknown="ignore")`
  - se ajusta **solo con train** en cada fold de `RandomizedSearchCV` (30 iters, 5-fold).
- El `best_estimator_` es un **Pipeline autocontenido** → la API pasa el dict crudo
  y llama `.predict()` (sin preprocesamiento manual, sin *training/serving skew*).

### Mejores hiperparámetros
- **Clasificación:** `n_estimators=200`, `max_depth=3`, `learning_rate=0.2`,
  `subsample=1.0`, `colsample_bytree=0.9`, `min_child_weight=3`.
- **Regresión:** `n_estimators=300`, `max_depth=7`, `learning_rate=0.05`,
  `subsample=0.9`, `colsample_bytree=0.7`, `min_child_weight=5`.

## Reentrenar
```bash
make train     # kedro run --pipeline nhanes_2015 + serving
```
Genera los pickles bendecidos en `data/09_serving/` (ver [despliegue.md](despliegue.md)).
Reproducible con `random_state=42`.

## Limitaciones
- **Proyecto académico/educativo**: no es consejo médico ni diagnóstico.
- "Edad biológica" = edad cronológica **estimada** a partir de biomarcadores; es una
  aproximación poblacional, no una medición clínica.
- Entrenado sobre población NHANES (EE. UU.); puede no generalizar a otras poblaciones.
- El data augmentation con longevos históricos balancea la clase pero introduce
  pacientes de cohortes distintas (`CICLO_ORIGEN` lo documenta).
