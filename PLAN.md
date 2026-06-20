# PLAN — Full-stack NHANES Longevity

Producto: web donde el usuario ingresa biomarcadores y obtiene **(1)** probabilidad
de ser longevo (`IS_LONGEVO`) y **(2)** su **edad biológica estimada**, con
explicabilidad SHAP y las métricas del modelo.

## Decisiones cerradas
| Tema | Decisión |
|---|---|
| Modelo de producción v1 | **Ciclo 2015 (Álvaro)** — clasificación + regresión. Contrato de 23 features (reusable para 2013). El 2017 (Juan) queda como selector de ciclo en v2. |
| Frontend | **Next.js + React + Tailwind** |
| Deploy | **Local / Docker** por ahora (sin cloud) |
| Explicabilidad | **SHAP** dentro del MVP |
| Repos | **Monorepo** (este repo): Kedro + `api/` + `web/` comparten `feature_schema.json` y `data/09_serving/` |

## Dos hechos técnicos que guían el diseño
1. **Pickles autocontenidos.** El preprocesamiento (imputación, escalado, one-hot)
   vive dentro del `Pipeline` sklearn → la API pasa el dict crudo y llama
   `.predict()`. Cero preprocesamiento manual en el backend.
2. **Campos opcionales → null → imputado.** Como el imputador está fiteado dentro
   del Pipeline, los campos no clínicos (hogar, índice de pobreza, educación)
   pueden ir vacíos; el modelo los completa. El form pide ~15 clínicos requeridos.

> ⚠️ `RIDAGEYR` (edad cronológica) **no** es input del modelo: es el target de
> regresión. El form la pide opcionalmente solo para mostrar el gap
> `edad_biologica - edad_cronologica`.

## Arquitectura (monorepo)
```
ev3_nanhes/
├── src/ev3_nhanes/pipelines/
│   ├── nhanes_2013 | nhanes_2015 | nhanes_2017_2018   # training (existente)
│   └── serving/                # bendice el modelo 2015 -> data/09_serving/   [HECHO]
├── conf/base/catalog_serving.yml                       #                       [HECHO]
├── feature_schema.json         # contrato compartido back/front                [HECHO]
├── api/                        # FastAPI: /predict /explain /schema /metrics   [HECHO]
├── web/                        # Next.js + React + Tailwind                     [PENDIENTE]
└── docker-compose.yml          # levanta api + web                             [PENDIENTE]
```

## Reparto (en paralelo tras congelar el contrato)
- **Álvaro → Backend:** afinar `api/`, validación de rangos, manejo de errores, tests.
- **Juan → Frontend:** `web/` Next.js; renderiza el form desde `GET /schema`,
  muestra gauge edad biológica vs cronológica + waterfall SHAP de `/explain`.
- **Nicolás → MLOps:** pipeline `serving` (hecho), Dockerfiles, `docker-compose.yml`,
  CI (pytest + ruff). Más adelante: unificación de contrato para el selector de ciclo.

## Milestones (~1 semana)
| Día | Entregable | Estado |
|---|---|---|
| 0 | `feature_schema.json` + pipeline `serving` + esqueleto API | ✅ hecho |
| 1–2 | API `/predict` validada contra el modelo real bendecido | ⏳ falta entrenar 2015 |
| 2–4 | Frontend MVP consumiendo `/schema` + `/predict` | ⏳ |
| 4 | `/explain` SHAP integrado en el front | ⏳ (API lista) |
| 5 | `docker-compose` (api+web) + tests de integración | ⏳ |

## Cómo arrancar (orden)
```bash
# 1) entrenar el modelo de producción (descarga de la CDC, lento)
kedro run --pipeline nhanes_2015
# 2) bendecirlo a ruta estable para la API
kedro run --pipeline serving
# 3) levantar la API
pip install -r api/requirements.txt
uvicorn api.main:app --reload      # http://localhost:8000/docs
# 4) (próximo) crear web/ con Next.js apuntando a http://localhost:8000
```

## Pendiente / deuda conocida
- **`web/` (Next.js)** todavía no existe — siguiente milestone.
- **Selector de ciclo (v2):** 2017 usa otro contrato (DIQ010, SMQ020, promedios de
  presión, sin glucosa/colesterol). Requiere segundo sub-formulario o unificar y
  reentrenar.
- Deuda técnica del 2017 heredada del merge (plumbing de mortalidad muerto) — se
  dejó a propósito; no afecta al serving del 2015.
