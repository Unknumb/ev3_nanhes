# API — NHANES Longevity (serving v1)

Sirve el modelo de producción (**COMBINADO**: todos los ciclos del equipo,
2005-2018): clasificación `IS_LONGEVO` + regresión de **edad biológica**. Los
pickles son Pipelines sklearn autocontenidos, así que la API solo arma el
DataFrame crudo y predice. El contrato es de 36 features (23 base + panel
PhenoAge de laboratorio opcional + 4 de cuestionario).

## 1. Generar el modelo bendecido (una vez)
```bash
# entrena el modelo combinado (descarga CDC) y bendice a data/09_serving/
kedro run --pipeline nhanes_combined
kedro run --pipeline serving
```
Esto crea `data/09_serving/model_clasificacion_2015.pkl`,
`model_regresion_2015.pkl` y `metadata.json`.

## 2. Correr la API (local, desde la raíz del repo)
```bash
pip install -r api/requirements.txt
uvicorn api.main:app --reload
# docs interactivas: http://localhost:8000/docs
```

> **En un servidor (EC2/producción)** hay que escuchar en todas las interfaces y
> permitir el origen público del frontend, o las llamadas se cuelgan / las bloquea CORS:
> ```bash
> export CORS_ORIGINS="http://<IP_o_dominio_del_front>"
> uvicorn api.main:app --host 0.0.0.0 --port 8000
> ```
> Detalles (Security Group, Elastic IP, dominio, HTTPS) en [docs/despliegue.md](../docs/despliegue.md).

## 3. Docker
```bash
docker build -f api/Dockerfile -t ev3-api .
docker run -v "$PWD/data:/app/data" -p 8000:8000 ev3-api
```

## Endpoints
| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/health` | liveness + `models_ready` + `db_ready` |
| GET | `/schema` | `feature_schema.json` (el front renderiza el form desde aquí) |
| POST | `/predict` | `es_longevo`, `probabilidad`, `edad_biologica`, `gap` (persiste en BD) |
| POST | `/explain` | contribuciones SHAP por feature |
| GET | `/metrics` | reportes de entrenamiento (accuracy / MAE) |
| GET | `/aggregates` | agregados del historial (totales, % longevos, distribución edad biológica) para el dashboard ejecutivo |

## Base de datos (3ª fuente)
Cada `/predict` se guarda en una BD SQL. Se configura con la variable de entorno
`DATABASE_URL`:

```bash
# Postgres gestionado (Supabase) — lo provee Nicolás
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"

# Fallback de desarrollo local (por defecto, sin infra): SQLite
# DATABASE_URL no seteada -> sqlite:///data/predictions.db
```
La escritura es **best-effort**: si la BD está caída, `/predict` igual responde
(solo se pierde el registro en el historial). Las tablas se crean solas al arrancar.

### Ejemplo `/predict`
```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{
  "edad_cronologica": 64,
  "features": {
    "RIAGENDR": 1, "RIDRETH3": 3,
    "BMXWT": 82, "BMXHT": 175, "BMXBMI": 26.8, "BMXWAIST": 98,
    "BPXSY1": 128, "BPXDI1": 80, "BPXPLS": 72,
    "LBXTC": 190, "LBXGLU": 99
  }
}'
```
Los campos `required:false` del schema pueden omitirse: el imputador del
Pipeline los completa.
