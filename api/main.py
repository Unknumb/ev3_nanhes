from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import model_registry as registry
from .schema import PredictRequest, PredictResponse, validate_features

app = FastAPI(
    title="NHANES Longevity API",
    version="0.1.0",
    description="Predice longevidad (IS_LONGEVO) y edad biologica desde biomarcadores NHANES.",
)

_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8501",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "models_ready": registry.models_ready(),
    }

@app.get("/schema")
def schema() -> dict:
    return registry.load_schema()

def _require_models() -> None:
    if not registry.models_ready():
        raise HTTPException(
            status_code=503,
            detail="Modelos no disponibles. Corre: kedro run --pipeline serving",
        )

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    _require_models()
    errores = validate_features(req.features)
    if errores:
        raise HTTPException(status_code=422, detail=errores)
    return PredictResponse(**registry.predict(req.features, req.edad_cronologica))

@app.post("/explain")
def explain(req: PredictRequest) -> dict:
    _require_models()
    errores = validate_features(req.features)
    if errores:
        raise HTTPException(status_code=422, detail=errores)
    try:
        return registry.explain(req.features)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

@app.get("/metrics")
def metrics() -> dict:
    reportes_dir = Path(registry._ROOT) / "data" / "08_reporting"
    out: dict[str, str] = {}
    for nombre in (
        "reporte_clasificacion_2015.txt",
        "reporte_regresion_2015.txt",
    ):
        ruta = reportes_dir / nombre
        out[nombre] = ruta.read_text(encoding="utf-8") if ruta.exists() else "(no disponible)"
    return out