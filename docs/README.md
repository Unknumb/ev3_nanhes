# Documentación — EV3 NHANES Longevity

Solución **end-to-end** que predice longevidad y **edad biológica** a partir de
biomarcadores NHANES, con dashboard analítico, API REST, persistencia SQL y
despliegue en Docker.

## Índice
| Documento | Contenido |
|---|---|
| [Arquitectura](arquitectura.md) | Diagramas (componentes, ETL, secuencia, datos), 3 fuentes, decisiones de diseño |
| [Model card](modelo.md) | Datos, métricas reales, metodología anti-fuga, hiperparámetros, limitaciones |
| [API REST](api.md) | Referencia de endpoints, esquemas de request/response, ejemplos `curl` |
| [Manual de usuario](manual_usuario.md) | Cómo usar el dashboard (3 audiencias) e interpretar los resultados |
| [Guía de despliegue](despliegue.md) | Local, Docker, `docker-compose`, `make train`, entrenamiento de modelos |

## Mapa del repositorio
```
ev3_nanhes/
├── src/ev3_nhanes/pipelines/   # ETL + entrenamiento (Kedro)
│   ├── nhanes_2013|2015|2017_2018   # ciclos NHANES
│   ├── serving/                     # bendice el modelo de producción
│   └── load_db/                     # carga dataset procesado a SQL
├── feature_schema.json         # contrato compartido back/front (23 features)
├── api/                        # Backend FastAPI (REST)
├── web/                        # Frontend Next.js (3 audiencias)
├── docs/                       # esta documentación
├── tests/                      # pytest
├── data/                       # capas de datos Kedro (no versionado)
├── Makefile                    # train / serve / up / down / test / lint
└── docker-compose.yml          # orquesta postgres + api (+ web pendiente)
```

> **Estado:** MVP integrado en `feature/fullstack-mvp` (backend + capa SQL + modelo
> real + infra + docs + frontend). Avance fino por componente en [`PLAN.md`](../PLAN.md).

## Resumen técnico
- **Modelos:** `XGBClassifier` (`IS_LONGEVO`, edad ≥ 70, **accuracy 0.87**) +
  `XGBRegressor` (`RIDAGEYR` como edad biológica, **MAE 7.26 años**). Ambos son
  `Pipeline` sklearn **autocontenidos** → la API pasa el dict crudo. Ver [modelo.md](modelo.md).
- **3 fuentes de datos:** archivos NHANES (CDC) · API REST (FastAPI) · base SQL
  (Postgres local / Supabase). Ver [Arquitectura](arquitectura.md#las-3-fuentes-de-datos).
- **Reproducibilidad:** `random_state=42`, gestión con `uv`, pipelines Kedro versionados.
