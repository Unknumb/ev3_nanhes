"""Tests de la API de serving.

Construyen un modelo SINTETICO (mismo Pipeline sklearn que produce el pipeline
2015) en un directorio temporal, para que la suite corra en CI sin necesidad de
entrenar el modelo real (descarga de la CDC + RandomizedSearchCV).
"""

from __future__ import annotations

import os
import pickle
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="ev3_serving_test_"))
os.environ["MODEL_DIR"] = str(_TMP_DIR)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR / 'test_predictions.db'}"

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.pipeline import Pipeline as SkPipeline
from xgboost import XGBClassifier, XGBRegressor

from api import db
from api.main import app
from ev3_nhanes.pipelines.nhanes_2015 import nodes as n2015

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("xgboost")
pytest.importorskip("sqlalchemy")

VALID_FEATURES = {
    "RIAGENDR": 1,
    "RIDRETH3": 3,
    "BMXWT": 82,
    "BMXHT": 175,
    "BMXBMI": 26.8,
    "BMXWAIST": 98,
    "BPXSY1": 128,
    "BPXDI1": 80,
    "BPXPLS": 72,
    "LBXTC": 190,
    "LBXGLU": 99,
}

_CAT_OPCIONES = {
    "RIAGENDR": [1, 2],
    "RIDRETH3": [1, 2, 3, 4, 6, 7],
    "DMDEDUC2": [1, 2, 3, 4, 5],
    "DMDMARTL": [1, 2, 3, 4, 5, 6],
}


def _build_synthetic_models(dest: Path) -> None:
    """Entrena modelos diminutos con el preprocesador real y los persiste."""
    rng = np.random.default_rng(42)
    codes = n2015._COLS_NUMERICAS + n2015._COLS_CATEGORICAS
    n = 200
    data: dict = {c: rng.uniform(20, 150, n) for c in n2015._COLS_NUMERICAS}
    for c in n2015._COLS_CATEGORICAS:
        data[c] = rng.choice(_CAT_OPCIONES[c], n)
    X = pd.DataFrame(data)[codes]
    y_clf = rng.integers(0, 2, n)
    y_reg = rng.uniform(18, 85, n)

    clf = SkPipeline(
        [
            ("prep", n2015._construir_preprocesador(codes)),
            ("model", XGBClassifier(n_estimators=10, eval_metric="logloss")),
        ]
    ).fit(X, y_clf)
    reg = SkPipeline(
        [
            ("prep", n2015._construir_preprocesador(codes)),
            ("model", XGBRegressor(n_estimators=10)),
        ]
    ).fit(X, y_reg)

    dest.mkdir(parents=True, exist_ok=True)
    with open(dest / "model_clasificacion_2015.pkl", "wb") as fh:
        pickle.dump(clf, fh)
    with open(dest / "model_regresion_2015.pkl", "wb") as fh:
        pickle.dump(reg, fh)


@pytest.fixture(scope="module")
def client():
    _build_synthetic_models(_TMP_DIR)
    with TestClient(app) as client:
        yield client


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["models_ready"] is True
    assert body["db_ready"] is True


def test_schema_tiene_23_features(client):
    body = client.get("/schema").json()
    assert len(body["features"]) == 23
    contrato = set(n2015._COLS_NUMERICAS) | set(n2015._COLS_CATEGORICAS)
    assert {f["code"] for f in body["features"]} == contrato


def test_predict_ok_con_opcionales_imputados(client):
    r = client.post(
        "/predict", json={"features": VALID_FEATURES, "edad_cronologica": 64}
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["es_longevo"], bool)
    assert 0.0 <= body["probabilidad"] <= 1.0
    assert body["edad_cronologica"] == 64
    assert body["gap"] == round(body["edad_biologica"] - 64, 1)


def test_predict_sin_edad_cronologica_gap_none(client):
    r = client.post("/predict", json={"features": VALID_FEATURES})
    assert r.status_code == 200
    assert r.json()["gap"] is None


def test_predict_falta_requerido_422(client):
    r = client.post("/predict", json={"features": {"RIAGENDR": 1}})
    assert r.status_code == 422
    assert len(r.json()["detail"]) > 0


def test_predict_categoria_invalida_422(client):
    bad = {**VALID_FEATURES, "RIAGENDR": 9}
    r = client.post("/predict", json={"features": bad})
    assert r.status_code == 422


def test_predict_fuera_de_rango_422(client):
    bad = {**VALID_FEATURES, "BMXBMI": 999}
    r = client.post("/predict", json={"features": bad})
    assert r.status_code == 422


def test_predict_feature_desconocida_422(client):
    bad = {**VALID_FEATURES, "NO_EXISTE": 1}
    r = client.post("/predict", json={"features": bad})
    assert r.status_code == 422


def test_metrics_responde(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_aggregates_refleja_predicciones(client):
    client.post("/predict", json={"features": VALID_FEATURES, "edad_cronologica": 64})
    r = client.get("/aggregates")
    assert r.status_code == 200
    body = r.json()
    assert body["total_predicciones"] >= 1
    assert 0.0 <= body["pct_longevos"] <= 100.0
    assert body["edad_biologica_promedio"] is not None
    assert isinstance(body["edad_biologica_distribucion"], list)
    assert len(body["ultimas"]) >= 1


def test_predict_persiste_en_bd(client):
    antes = db.get_aggregates()["total_predicciones"]
    client.post("/predict", json={"features": VALID_FEATURES})
    despues = db.get_aggregates()["total_predicciones"]
    assert despues == antes + 1


def test_explain_si_shap_disponible(client):
    pytest.importorskip("shap")
    r = client.post("/explain", json={"features": VALID_FEATURES})
    assert r.status_code == 200
    body = r.json()
    assert "contribuciones" in body
    assert len(body["contribuciones"]) > 0