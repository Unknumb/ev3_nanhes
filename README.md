# 🧬 NHANES Longevity — Predictor de edad biológica y longevidad

> Tu cuerpo puede ser más joven o más viejo que tu edad real. Ingresa unos datos de
> salud y un modelo de ML estima tu **edad biológica** y tu **probabilidad de
> longevidad**, con una explicación de qué factores influyen.

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)
![Python](https://img.shields.io/badge/python-%E2%89%A53.10-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/web-Next.js-000000?logo=nextdotjs&logoColor=white)
![XGBoost](https://img.shields.io/badge/model-XGBoost-EB0A1E)

Proyecto **full-stack de ciencia de datos** que predice la longevidad humana a partir de
biomarcadores de la encuesta **NHANES (CDC)**. Cubre el ciclo completo: **ingesta → ETL →
entrenamiento → serving → API → dashboard**, con persistencia SQL y empaquetado en Docker.

---

## 📑 Tabla de contenidos
- [¿Qué hace?](#-qué-hace)
- [Arquitectura](#-arquitectura)
- [El modelo](#-el-modelo)
- [Estructura del repo](#-estructura-del-repo)
- [Stack](#-stack)
- [Inicio rápido](#-inicio-rápido)
- [Uso detallado](#-uso-detallado)
- [API REST](#-api-rest)
- [Pipelines (Kedro)](#-pipelines-kedro)
- [Tests y lint](#-tests-y-lint)
- [Datos y metodología](#-datos-y-metodología)
- [Equipo](#-equipo)
- [Documentación](#-documentación)
- [Aviso](#-aviso)

---

## 🎯 ¿Qué hace?

Dos modelos entrenados sobre el mismo dataset:
- **Clasificación** — `IS_LONGEVO` (1 si edad ≥ 70), con `XGBClassifier`.
- **Regresión** — `RIDAGEYR` (edad cronológica, interpretada como **edad biológica**), con `XGBRegressor`.

El usuario responde unas preguntas fáciles (peso, presión, si fuma, diabetes…) y opcionalmente
labs; el sistema devuelve su edad biológica estimada, su probabilidad de longevidad y una
**explicación SHAP** de qué factores empujan el resultado, todo en lenguaje simple.

---

## 🏗 Arquitectura

**Monorepo** donde el ETL (Kedro), el backend (`api/`) y el frontend (`web/`) comparten un único
contrato (`feature_schema.json`) y los modelos bendecidos (`data/09_serving/`).

```
   CDC (.xpt) ──► Kedro ETL ──► modelo .pkl ──► FastAPI ──► Next.js dashboard
                     │            (serving)        │  ▲
                     └──► Postgres ◄───────────────┘  └─ /predict /explain /metrics ...
```

| Capa | Tecnología | Rol |
|---|---|---|
| **Datos** | Archivos NHANES `.xpt` (SAS) del CDC | Materia prima, descargada en runtime |
| **ETL/ML** | Kedro + XGBoost | Descarga, limpieza, entrenamiento, serving |
| **API** | FastAPI | `/predict`, `/explain` (SHAP), `/metrics`, historial |
| **BD** | PostgreSQL | Historial de predicciones + agregados |
| **Web** | Next.js | Dashboard de 3 audiencias (operativa / técnica / ejecutiva) |

Diagramas completos en [`docs/arquitectura.md`](docs/arquitectura.md).

---

## 🤖 El modelo

El modelo de producción es el **combinado** (`nhanes_combined`): unifica los tres ciclos del equipo
en un único dataset (base **2017-2018** + longevos históricos **2015 → 2005**) y entrena **un**
clasificador + **un** regresor sobre **36 features**:

- **23 base** — demografía, antropometría, presión arterial, labs (colesterol, glucosa).
- **Panel PhenoAge** (Levine 2018) — 9 labs opcionales/imputados: HbA1c, HDL, albúmina, creatinina,
  fosfatasa alcalina, hemograma. Suben el modelo sin añadir fricción al formulario.
- **Cuestionario** — salud autopercibida, tabaquismo, diabetes, evento cardiovascular previo.

### Métricas (conjunto de test)

| Modelo | Métrica | Valor |
|---|---|---|
| Clasificación | Accuracy | **0.907** |
| | F1-score | **0.922** |
| Regresión (edad biológica) | MAE | **6.79 años** |
| | R² | **0.804** |

Entrenado sobre las **todas las edades de los 7 ciclos** (~42k adultos), con balanceo desacoplado
por modelo para no sesgar la edad biológica de personas jóvenes. Detalle en [`docs/modelo.md`](docs/modelo.md).

---

## 📂 Estructura del repo

```
ev3_nanhes/
├── src/ev3_nhanes/pipelines/   # ETL + entrenamiento (Kedro)
│   ├── nhanes_combined/         # 🏭 modelo de producción (todos los ciclos)
│   ├── nhanes_2013|2015|2017_2018/  # baselines por ciclo
│   ├── serving/                 # bendice el modelo a data/09_serving/
│   └── load_db/                 # carga el dataset procesado a Postgres
├── feature_schema.json          # contrato compartido back/front (36 features)
├── api/                         # Backend FastAPI (REST + SHAP + mailer)
├── web/                         # Frontend Next.js (React + Tailwind + Recharts)
├── conf/                        # catálogos y parámetros de Kedro
├── docs/                        # documentación del proyecto
├── tests/                       # pytest (pipelines + API)
├── notebooks/                   # EDA y prototipado (Álvaro, Nicolás)
├── docker-compose.yml           # api + web + postgres
└── Makefile                     # atajos (train, serve, up, test, lint)
```

---

## 🧰 Stack

- **ETL/ML:** Kedro 1.4, pandas, scikit-learn, XGBoost, SHAP
- **Backend:** FastAPI, Pydantic, SQLAlchemy 2.0, uvicorn
- **Frontend:** Next.js + React + Tailwind + Recharts
- **Datos:** PostgreSQL (Supabase en prod) · SQLite (dev)
- **Infra:** Docker, docker-compose · dependencias con [`uv`](https://docs.astral.sh/uv/)

---

## 🚀 Inicio rápido

### Requisitos
- Python ≥ 3.10 · [`uv`](https://docs.astral.sh/uv/) · Node ≥ 18 · (opcional) Docker
- **Acceso a internet** (el ETL descarga datos del CDC en runtime)

### Opción A — Docker (recomendado)
```bash
# 1) Entrenar el modelo (descarga del CDC + entrena, tarda unos minutos)
make train

# 2) Levantar api + web + postgres
make up           # = docker compose up --build -d
```
- Web: http://localhost:3000 · API: http://localhost:8000/docs · Postgres: `localhost:5432`

### Opción B — Local (sin Docker)
```bash
uv sync                                   # instala dependencias

kedro run --pipeline nhanes_combined      # entrena (descarga CDC)
kedro run --pipeline serving              # bendice a data/09_serving/

make serve                                # API en :8000  (uvicorn)
cd web && npm install && npm run dev      # web en :3000
```

---

## 🔧 Uso detallado

| Acción | Comando |
|---|---|
| Entrenar + bendecir | `make train` |
| Correr solo el ETL combinado | `kedro run --pipeline nhanes_combined` |
| Cargar dataset a Postgres | `kedro run --pipeline load_db` |
| API local | `make serve` |
| Web local | `cd web && npm run dev` |
| Levantar todo (Docker) | `make up` / bajar: `make down` / logs: `make logs` |
| Tests | `make test` |
| Lint | `make lint` |

> El front es **schema-driven**: el formulario y las validaciones se generan desde
> `feature_schema.json`, así que agregar/quitar features no requiere tocar el web.

---

## 🌐 API REST

Base: `http://localhost:8000` · Docs interactivas: `/docs`

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Estado (modelos y BD listos) |
| `GET` | `/schema` | Contrato de las 36 features (el front arma el form desde aquí) |
| `POST` | `/predict` | Longevidad + edad biológica + gap |
| `POST` | `/explain` | Contribuciones SHAP por feature |
| `GET` | `/feature-importance` | Importancia global del modelo |
| `GET` | `/metrics` | Reportes de entrenamiento (accuracy / MAE…) |
| `POST` | `/report` | Informe descargable / por correo |
| `GET` | `/history` | Historial de predicciones |
| `GET` | `/aggregates` | KPIs para la vista ejecutiva |

Referencia completa en [`docs/api.md`](docs/api.md).

---

## 🧩 Pipelines (Kedro)

Cada pipeline sigue 4 nodos (descarga → preprocesa → entrena clf → entrena reg). `kedro run` sin
argumentos corre todo (se autodescubren).

| Pipeline | Rol |
|---|---|
| `nhanes_combined` | **Producción**: une todos los ciclos y entrena el par clf+reg |
| `nhanes_2013` / `nhanes_2015` / `nhanes_2017_2018` | Baselines por ciclo (no servidos) |
| `serving` | Copia el modelo combinado a `data/09_serving/` + `metadata.json` |
| `load_db` | Escribe el dataset procesado en Postgres |

```bash
kedro run                              # todo
kedro run --pipeline nhanes_combined   # solo el de producción
kedro jupyter lab                      # notebooks con contexto Kedro
```

---

## ✅ Tests y lint

```bash
pytest                 # config y cobertura desde pyproject.toml
ruff check .           # lint (line-length 88)
ruff format .          # formato
```

CI (`.github/workflows`) corre `ruff check api tests` + `pytest` en cada push.

---

## 📊 Datos y metodología

- **Fuente:** NHANES (CDC) — archivos `.xpt` (SAS) descargados en runtime (no se commitean datos).
- **Data augmentation:** el ciclo base aporta todos los pacientes; los ciclos históricos aportan
  **solo longevos (≥70)** para balancear la clase minoritaria. `CICLO_ORIGEN` registra el origen.
- **Limpieza SAS:** el centinela `5.397605e-79` se convierte a `NaN` tras cada descarga.
- **Anti-fuga de datos:** `train_test_split` **antes** de transformar; la imputación/escalado/OHE
  vive dentro del `Pipeline` sklearn y se ajusta solo con el train de cada fold de
  `RandomizedSearchCV`. El pickle resultante es **autocontenido** (sin *training/serving skew*).
- `random_state=42` en todo el proyecto para reproducibilidad.

---

## 👥 Equipo

Cada integrante trabajó un ciclo NHANES; el modelo de producción los une a todos:

| Integrante | Ciclo NHANES |
|---|---|
| Nicolás | 2013-2014 |
| Álvaro | 2015-2016 |
| Juan | 2017-2018 |

---

## 📚 Documentación

| Documento | Contenido |
|---|---|
| [`docs/modelo.md`](docs/modelo.md) | Model card (métricas, features, metodología) |
| [`docs/arquitectura.md`](docs/arquitectura.md) | Diagramas y decisiones de diseño |
| [`docs/api.md`](docs/api.md) | Referencia de la API |
| [`docs/despliegue.md`](docs/despliegue.md) | Guía de despliegue |
| [`docs/manual_usuario.md`](docs/manual_usuario.md) | Manual de usuario |
| [`docs/informe_estudio_defensa.md`](docs/informe_estudio_defensa.md) | Informe de estudio / defensa |

---

## ⚠️ Aviso

Proyecto **académico/educativo**. **No es consejo médico ni diagnóstico.** La "edad biológica" es
una estimación poblacional a partir de biomarcadores NHANES (CDC), no una medición clínica.
