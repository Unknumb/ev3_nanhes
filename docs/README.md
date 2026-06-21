# Documentación — EV3 NHANES Longevity

Solución **end-to-end** que predice longevidad y **edad biológica** a partir de
biomarcadores NHANES, con dashboard analítico, API REST, persistencia SQL y
despliegue en Docker.

## Índice
| Documento | Contenido |
|---|---|
| [Arquitectura](arquitectura.md) | Diagramas (componentes, ETL, secuencia, datos), 3 fuentes, decisiones de diseño |
| [API REST](api.md) | Referencia de endpoints, esquemas de request/response, ejemplos `curl` |
| [Manual de usuario](manual_usuario.md) | Cómo usar el dashboard (3 audiencias) e interpretar los resultados |
| [Guía de despliegue](despliegue.md) | Local, Docker, `docker-compose` + Supabase, entrenamiento de modelos |

## Mapa del repositorio
```
ev3_nanhes/
├── src/ev3_nhanes/pipelines/   # ETL + entrenamiento (Kedro)
│   ├── nhanes_2013|2015|2017_2018   # ciclos NHANES
│   ├── serving/                     # bendice el modelo de producción
│   └── load_db/                     # carga dataset procesado a SQL
├── feature_schema.json         # contrato compartido back/front (23 features)
├── api/                        # Backend FastAPI (REST)
├── dashboards/                 # Frontend Streamlit (3 audiencias)
├── docs/                       # esta documentación
├── tests/                      # pytest
├── data/                       # capas de datos Kedro (no versionado)
└── docker-compose.yml          # orquesta api + dashboard
```

> **Estado de implementación:** esta documentación describe la arquitectura
> objetivo. El avance real por componente se sigue en [`PLAN.md`](../PLAN.md).

## Resumen técnico
- **Modelos:** `XGBClassifier` (`IS_LONGEVO`, edad ≥ 70) + `XGBRegressor`
  (`RIDAGEYR`, interpretado como edad biológica). Ambos son `Pipeline` sklearn
  **autocontenidos** (preprocesamiento incluido) → la API pasa el dict crudo.
- **3 fuentes de datos:** archivos NHANES (CDC) · API REST (FastAPI) · base SQL
  (Supabase/Postgres). Ver [Arquitectura](arquitectura.md#las-3-fuentes-de-datos).
- **Reproducibilidad:** `random_state=42`, gestión con `uv`, pipelines Kedro versionados.
