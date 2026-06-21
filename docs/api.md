# API REST — Referencia

Backend FastAPI que sirve el modelo de producción (ciclo **2015**): clasificación
`IS_LONGEVO` + regresión de **edad biológica**, con explicabilidad SHAP y
persistencia del historial.

- **Base URL (local):** `http://localhost:8000`
- **Docs interactivas (OpenAPI/Swagger):** `http://localhost:8000/docs`
- **Esquema OpenAPI:** `http://localhost:8000/openapi.json`

> La documentación interactiva se genera automáticamente desde el código (FastAPI),
> por lo que siempre está sincronizada con la implementación.

## Endpoints
| Método | Ruta | Descripción | Códigos |
|---|---|---|---|
| GET | `/health` | Liveness + estado de modelos y base de datos | 200 |
| GET | `/schema` | Contrato de features (el front arma el formulario) | 200 |
| POST | `/predict` | Predice longevidad + edad biológica (persiste en BD) | 200, 422, 503 |
| POST | `/explain` | Contribuciones SHAP por feature | 200, 422, 501 |
| GET | `/metrics` | Reportes de entrenamiento (accuracy / MAE) | 200 |
| GET | `/aggregates` | Agregados del historial para la vista ejecutiva | 200, 503 |

---

### `GET /health`
```json
{ "status": "ok", "models_ready": true, "db_ready": true }
```
- `models_ready`: hay modelos bendecidos en `data/09_serving/`.
- `db_ready`: la base SQL acepta conexiones.

### `GET /schema`
Devuelve `feature_schema.json`: lista de 23 features con `code`, `label`, `type`
(`numeric`/`categorical`), `required`, `min`/`max`/`unit` u `options`. El dashboard
renderiza el formulario directamente desde aquí.

### `POST /predict`
**Request**
```json
{
  "edad_cronologica": 64,
  "features": {
    "RIAGENDR": 1, "RIDRETH3": 3,
    "BMXWT": 82, "BMXHT": 175, "BMXBMI": 26.8, "BMXWAIST": 98,
    "BPXSY1": 128, "BPXDI1": 80, "BPXPLS": 72,
    "LBXTC": 190, "LBXGLU": 99
  }
}
```
- `features`: mapa `código NHANES → valor`. Los campos `required:false` del schema
  pueden omitirse o ir en `null`: el imputador del Pipeline los completa.
- `edad_cronologica` es **opcional** y **no** es feature del modelo; solo sirve para
  calcular el `gap`.

**Response 200**
```json
{
  "es_longevo": false,
  "probabilidad": 0.2731,
  "edad_biologica": 58.4,
  "edad_cronologica": 64,
  "gap": -5.6
}
```
- `gap = edad_biologica − edad_cronologica` (o `null` si no se envió edad).

**Errores**
- `422`: validación fallida (feature desconocida, requerido ausente, fuera de
  rango o categoría inválida). El cuerpo trae `detail` con la lista de errores.
- `503`: modelos no disponibles (correr `kedro run --pipeline serving`).

**Ejemplo `curl`**
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"edad_cronologica":64,"features":{"RIAGENDR":1,"RIDRETH3":3,"BMXWT":82,"BMXHT":175,"BMXBMI":26.8,"BMXWAIST":98,"BPXSY1":128,"BPXDI1":80,"BPXPLS":72,"LBXTC":190,"LBXGLU":99}}'
```

### `POST /explain`
Mismo `request` que `/predict`. Devuelve las contribuciones SHAP agregadas al
feature NHANES original (reagrupa las columnas one-hot).
```json
{
  "base_value": -0.51,
  "contribuciones": [
    { "feature": "LBXGLU", "shap": 0.83, "empuja": "longevo" },
    { "feature": "BMXBMI", "shap": -0.40, "empuja": "no_longevo" }
  ]
}
```
- `501` si `shap` no está instalado.

### `GET /metrics`
Devuelve el texto de los reportes de entrenamiento:
```json
{
  "reporte_clasificacion_2015.txt": "accuracy ...",
  "reporte_regresion_2015.txt": "MAE ..."
}
```

### `GET /aggregates`
Agregados calculados sobre el historial de predicciones (para la vista ejecutiva):
```json
{
  "total_predicciones": 128,
  "pct_longevos": 41.4,
  "edad_biologica_promedio": 62.7,
  "gap_promedio": -2.1,
  "edad_biologica_distribucion": [
    { "min": 30.2, "max": 36.1, "count": 5 }
  ],
  "ultimas": [
    { "created_at": "2026-06-20T18:03:00+00:00", "es_longevo": false,
      "probabilidad": 0.27, "edad_biologica": 58.4, "gap": -5.6 }
  ]
}
```
- `503` si la base SQL no está disponible.
