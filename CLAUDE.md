# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [Kedro](https://kedro.org) 1.4.0 ML project that predicts human longevity from NHANES health
biomarkers. The Python package is `ev3_nhanes` (note: the repo directory is misspelled `ev3_nanhes`).
Code comments, notebooks, and print statements are in Spanish.

Two models are trained from the same preprocessed dataset:
- **Classification** — `IS_LONGEVO` (1 if age ≥ 70), via `XGBClassifier`.
- **Regression** — `RIDAGEYR` (chronological age, interpreted as "biological age"), via `XGBRegressor`.

## Commands

```bash
# Run the full pipeline (download → preprocess → train both models)
kedro run

# Run only one pipeline or node
kedro run --pipeline nhanes_2015
kedro run --nodes nodo_descarga_nhanes_2015   # node names are in pipeline.py

# Tests (config + coverage flags come from pyproject.toml)
pytest
pytest tests/test_run.py::TestKedroRun::test_kedro_run_no_pipeline   # single test

# Lint / format (ruff config in pyproject.toml, line-length 88)
ruff check .
ruff format .

# Notebooks with Kedro context (provides `context`, `session`, `catalog`, `pipelines`)
kedro jupyter lab
```

Dependencies are managed with **uv** (`uv.lock` present); use `uv sync` or `uv run <cmd>`.

> **Dependency gotcha:** `nodes.py` imports `scikit-learn` and `xgboost`, but neither is declared in
> `pyproject.toml` or `requirements.txt` (they're only present in `.venv`). If you touch dependencies
> or set up a fresh environment, add them — `kedro run` fails without them.

## Architecture

**Pipeline flow** (`src/ev3_nhanes/pipelines/nhanes_2015/`): a single linear pipeline of 4 nodes
wired in `pipeline.py`, with all logic in `nodes.py`:

1. `descargar_y_unir_2015` — no inputs; **downloads `.xpt` (SAS) files directly from the CDC**
   (`wwwn.cdc.gov`) at runtime. Internet access is required to run the pipeline. Output → `raw_nhanes_2015`.
2. `preprocesar_datos_2015` — imputation (KNN for numeric, most-frequent for categorical),
   one-hot encoding, `StandardScaler`, and creation of the `IS_LONGEVO` target. → `preprocessed_nhanes_2015`.
3. `entrenar_modelo_clasificacion` / `entrenar_modelo_regresion` — each runs `RandomizedSearchCV`
   (30 iters, 5-fold CV) over an XGBoost model. → versioned pickle models.

`pipeline_registry.py` auto-discovers pipelines via `find_pipelines()` and sets `__default__` to
their sum, so `kedro run` with no args runs everything.

**Key domain logic in `nodes.py`** (read these before changing preprocessing):
- **Data augmentation for class balance:** the base cycle (2015-2016) contributes *all* patients,
  but four historical cycles (2013, 2011, 2009, 2007) contribute *only* patients aged ≥ 70
  (`solo_longevos=True`), to rescue the minority longevity class. `CICLO_ORIGEN` records each row's source cycle.
- **SAS sentinel cleaning:** the value `5.397605e-79` is SAS's "missing" marker and is converted to
  `NaN` in `_limpiar_missing_sas` immediately after every download. Preserve this — it corrupts stats otherwise.
- Historical cycles use a `left` join (vs `outer` for the base cycle) to avoid pulling in young patients from lab tables.
- Feature/target columns are referenced by raw NHANES codes (e.g. `RIDAGEYR`, `BMXBMI`, `LBXGLU`).
  Columns excluded from features: `SEQN`, `RIDAGEYR`, `IS_LONGEVO`, `CICLO_ORIGEN`.

**Config** (`conf/`): the active dataset definitions live in `conf/base/catalog_2015.yml`
(`conf/base/catalog.yml` is empty); Kedro's default `catalog*` glob picks both up. Environments are
`base` and `local` (`settings.py`). Outputs land in the numbered `data/NN_*` layer directories; raw
NHANES data is **not** committed (downloaded fresh each run).

**Notebooks** (`notebooks/`, Spanish, by Álvaro): exploratory companions that mirror the pipeline
stages — `01` EDA, `02` preprocessing, `03` unsupervised (PCA + K-Means), `04` classification,
`05` regression. They are the research/prototyping surface; `nodes.py` is the productionized version.

## Conventions

- New pipelines go under `src/ev3_nhanes/pipelines/<name>/` with `nodes.py` + `pipeline.py`; they're
  auto-registered. Mirror tests under `tests/pipelines/<name>/`.
- `random_state=42` is used throughout for reproducibility.
- Avoid committing data or anything in `conf/local/` (per `.gitignore` and the README).
