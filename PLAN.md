# PLAN — Full-stack NHANES Longevity (alineado a la pauta EV Parcial N°3)

Producto: solución **end-to-end** que predice longevidad desde biomarcadores NHANES.
El usuario ingresa datos y obtiene **(1)** probabilidad de ser longevo (`IS_LONGEVO`)
y **(2)** su **edad biológica estimada**, con explicabilidad SHAP. Sobre esa base se
monta un **dashboard analítico diferenciado por audiencia** (ejecutiva / técnica /
operativa).

> Este plan está mapeado 1:1 contra la **pauta de evaluación** (ver tabla de pesos
> abajo). Construimos hacia los indicadores que dan puntaje, no hacia un MVP genérico.

## Pauta → cómo la cubrimos (pesos reales)

### Dimensión Encargo (grupal)
| # | Indicador (peso) | Cómo lo cubrimos | Estado |
|---|---|---|---|
| 1 | **ETL ≥3 fuentes + validación esquemas + manejo errores (20%)** | 3 fuentes reales (ver abajo) + validación Pydantic/`feature_schema.json` + limpieza de centinelas SAS + manejo de errores en descarga | ⏳ falta BD + carga |
| 2 | **Documentación: arquitectura + APIs + instalación (20%)** | `/docs/` con diagrama de arquitectura, manual de usuario, guía de despliegue; Swagger auto en `/docs` de FastAPI | ⏳ falta `/docs/` + diagrama |
| 3 | **Dashboard interactivo por audiencia + negocio (25% — el más alto)** | **Streamlit** con 3 vistas (ejecutiva/técnica/operativa) + gráficos | ⏳ por construir |
| 4 | **Git profesional: PRs, conflictos, issues, code review (15%)** | PRs hacia `feature/fullstack-mvp`, issues, reviews; ya hay merge con conflictos resueltos (Juan) | 🔄 en curso |
| 5 | **Docker: compose + optimización + env vars (20%)** | `docker-compose.yml` (api + dashboard + Postgres), Dockerfiles, variables de entorno | ⏳ falta compose + db |

### Dimensión Presentación (individual)
| # | Indicador (peso) | Nota |
|---|---|---|
| 6 | Demo end-to-end en Docker (30%) | Sale del `docker-compose up` |
| 7 | Dashboards por audiencia + valor de negocio (30%) | Se cubre con el Streamlit del #3 |
| 8 | **Proceso colaborativo + metodología + mejoras (40% — el más alto)** | Cada uno debe poder explicar: flujo Git, tablero de gestión, lecciones aprendidas |

## Las 3 fuentes de datos (Indicador 1)
La pauta exige **al menos 3 fuentes distintas** (ej.: CSV/Excel, API REST, BD SQL/NoSQL):
1. **Archivos (extract):** los `.xpt` (SAS) de NHANES descargados de la CDC → se pueden
   materializar también como CSV en `data/`.
2. **API REST:** la propia **FastAPI** sirviendo predicciones; el dashboard la consume.
3. **Base de datos SQL (Postgres):** almacena el **dataset procesado** + el **historial
   de predicciones**. El dashboard ejecutivo lee de aquí los agregados (distribución de
   edad biológica, % longevos por cohorte). → cumple Indicador 1 **y** alimenta el #3.

> Postgres en `docker-compose` (refuerza también el Indicador 5 - orquestación).
> SQLite queda como fallback de desarrollo local.

## Dos hechos técnicos que guían el diseño
1. **Pickles autocontenidos.** El preprocesamiento (imputación, escalado, one-hot) vive
   dentro del `Pipeline` sklearn → la API pasa el dict crudo y llama `.predict()`.
2. **Campos opcionales → null → imputado.** El imputador está fiteado dentro del Pipeline,
   así que los campos no clínicos pueden ir vacíos. El form pide ~11 clínicos requeridos.

> ⚠️ `RIDAGEYR` (edad cronológica) **no** es input del modelo: es el target de regresión.
> El form la pide opcionalmente solo para mostrar el gap `edad_biologica - edad_cronologica`.

## Arquitectura (monorepo)
```
ev3_nanhes/
├── src/ev3_nhanes/pipelines/        # capa ETL (Kedro)
│   ├── nhanes_combined             # modelo de producción (todos los ciclos)  [HECHO]
│   ├── nhanes_2013 | nhanes_2015 | nhanes_2017_2018   # baselines por ciclo   [HECHO]
│   ├── serving/                     # bendice combinado -> data/09_serving/    [HECHO]
│   └── load_db/                     # carga dataset procesado -> Postgres      [HECHO]
├── feature_schema.json              # contrato compartido back/front          [HECHO]
├── api/                             # FastAPI: /predict /explain /schema /metrics [HECHO]
│   └── (+ historial de predicciones -> Postgres)                              [PENDIENTE]
├── dashboards/                      # Streamlit 3 audiencias                  [PENDIENTE]
├── docs/                            # diagrama arquitectura + manual + guía    [PENDIENTE]
├── docker-compose.yml               # api + dashboard + postgres              [PENDIENTE]
└── tests/                           # pytest                                  [HECHO api]
```
> Mapea a la estructura recomendada por la pauta (/etl→pipelines Kedro, /dashboards,
> /docs, /api, /docker→compose, /tests, /data). Lo documentamos en `/docs`.

## Dashboard Streamlit — 3 audiencias (Indicador 3, el más pesado)
- **Ejecutiva:** KPIs y valor de negocio — distribución de edad biológica, % longevos,
  agregados por cohorte (lee de Postgres). Lenguaje de negocio, sin jerga técnica.
- **Técnica:** métricas del modelo (accuracy/MAE desde `/metrics`), SHAP de `/explain`,
  importancia de features, matriz de confusión.
- **Operativa:** el predictor — form generado desde `GET /schema`, llama `/predict`,
  muestra gauge edad biológica vs cronológica + waterfall SHAP.

## Reparto
- **Álvaro → Backend:** API (hecho) + escribir **historial de predicciones a Postgres**;
  endpoint de agregados si el dashboard lo necesita; tests.
- **Juan → Dashboard (Streamlit):** las 3 vistas por audiencia; consume `/schema`,
  `/predict`, `/explain` y lee agregados de la BD. (Es el indicador de mayor puntaje.)
- **Nicolás → MLOps:** nodo Kedro `load_db` (dataset procesado → Postgres),
  `docker-compose.yml` (api + dashboard + postgres + env vars), Dockerfiles, CI (pytest+ruff),
  diagrama de arquitectura + guía de despliegue.

## Evidencia colaborativa (Indicadores 4 y 8)
- **PRs** hacia `feature/fullstack-mvp` (no a `main`), con **code review** cruzado.
- **Issues** por tarea + **tablero GitHub Projects** (para poder explicar metodología en el #8).
- Mantener historia de commits limpia; no reescribir `fullstack-mvp` (los demás parten de ahí).

## Milestones (~la semana que queda)
| Día | Entregable | Estado |
|---|---|---|
| 0 | contrato + serving + API + tests | ✅ hecho |
| 1 | entrenar 2015 real + bendecir; Postgres + nodo `load_db` | ⏳ |
| 1–2 | API escribe historial a BD; endpoint de agregados | ⏳ |
| 2–4 | Streamlit 3 audiencias consumiendo API + BD | ⏳ |
| 4 | `/docs`: diagrama arquitectura + manual + guía despliegue | ⏳ |
| 5 | `docker-compose` (api+dashboard+postgres) + demo end-to-end | ⏳ |

## Cómo arrancar (orden)
```bash
# 1) entrenar modelo de producción combinado (descarga CDC, lento)
kedro run --pipeline nhanes_combined
# 2) bendecirlo a ruta estable para la API
kedro run --pipeline serving
# 3) (próximo) cargar dataset procesado a Postgres
kedro run --pipeline load_db
# 4) levantar todo
docker-compose up        # api :8000, dashboard :8501, postgres :5432
```

## Deuda conocida
- **Modelo unificado + features clínicas (HECHO):** `nhanes_combined` une todos los ciclos
  (2005-2018) en un solo modelo de producción con **36 features** (23 base + panel PhenoAge de
  laboratorio + 4 de cuestionario). Entrenado y bendecido: F1 0.92 (clf), MAE 6.8 años / R² 0.80 (reg),
  con balanceo desacoplado por edad para no inflar la edad biológica de jóvenes.
- **PCR/inflamación (v2):** la hs-CRP solo existe 2015-2018 (hueco 2011-2014); para sumarla habría
  que restringir ciclos. Hoy se omite del panel PhenoAge a propósito.
- Plumbing de mortalidad del 2017 heredado del merge (muerto) — no afecta al serving combinado.
- Next.js queda **opcional / fuera del MVP evaluado**: la pauta nombra Plotly Dash/Streamlit
  y el dashboard graduado es el Streamlit. Si sobra tiempo, Next.js como front "producto".
