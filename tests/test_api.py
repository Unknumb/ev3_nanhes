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

import pytest

# La API y deps pesadas son opcionales: saltar limpio si faltan (antes de importarlas).
pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("xgboost")
pytest.importorskip("sqlalchemy")

# Apuntar la API a un dir temporal ANTES de importarla (rutas y DATABASE_URL se
# resuelven en tiempo de import dentro de model_registry/db).
_TMP_DIR = Path(tempfile.mkdtemp(prefix="ev3_serving_test_"))
os.environ["MODEL_DIR"] = str(_TMP_DIR)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR / 'test_predictions.db'}"
# Mailer en modo demo aislado: escribe a un outbox temporal, no al repo.
os.environ["MAIL_OUTBOX_DIR"] = str(_TMP_DIR / "outbox")
os.environ.pop("SMTP_HOST", None)  # forzar modo demo aunque el entorno tenga SMTP

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from sklearn.pipeline import Pipeline as SkPipeline
from xgboost import XGBClassifier, XGBRegressor

from api import db
from api.main import app
from ev3_nhanes.pipelines.nhanes_combined import nodes as ncomb

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
    "HSD010": [1, 2, 3, 4, 5],
    "SMQ020": [1, 2],
    "DIQ010": [1, 2, 3],
    "MCQ_CVD": [0, 1],
}


def _build_synthetic_models(dest: Path) -> None:
    """Entrena modelos diminutos con el preprocesador real y los persiste."""
    rng = np.random.default_rng(42)
    codes = ncomb._COLS_NUMERICAS + ncomb._COLS_CATEGORICAS
    n = 200
    data: dict = {c: rng.uniform(20, 150, n) for c in ncomb._COLS_NUMERICAS}
    for c in ncomb._COLS_CATEGORICAS:
        data[c] = rng.choice(_CAT_OPCIONES[c], n)
    X = pd.DataFrame(data)[codes]
    y_clf = rng.integers(0, 2, n)
    y_reg = rng.uniform(18, 85, n)

    clf = SkPipeline(
        [
            ("prep", ncomb._construir_preprocesador(codes)),
            ("model", XGBClassifier(n_estimators=10, eval_metric="logloss")),
        ]
    ).fit(X, y_clf)
    reg = SkPipeline(
        [
            ("prep", ncomb._construir_preprocesador(codes)),
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


def test_schema_coincide_con_contrato_combinado(client):
    body = client.get("/schema").json()
    assert len(body["features"]) == 36
    contrato = set(ncomb._COLS_NUMERICAS) | set(ncomb._COLS_CATEGORICAS)
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


# --- Campos opcionales (reduccion de friccion del formulario) ----------------


def test_predict_ok_sin_labs_opcionales(client):
    """LBXTC/LBXGLU y RIDRETH3 ahora son opcionales: el modelo los imputa."""
    minimo = {
        "RIAGENDR": 1,
        "BMXWT": 82,
        "BMXHT": 175,
        "BMXBMI": 26.8,
        "BMXWAIST": 98,
        "BPXSY1": 128,
        "BPXDI1": 80,
        "BPXPLS": 72,
    }
    r = client.post("/predict", json={"features": minimo, "edad_cronologica": 40})
    assert r.status_code == 200
    assert isinstance(r.json()["es_longevo"], bool)


# --- /feature-importance -----------------------------------------------------


def test_feature_importance_default(client):
    r = client.get("/feature-importance")
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "clasificacion"
    assert body["clinical_only"] is False
    assert len(body["importancias"]) >= 1
    primero = body["importancias"][0]
    assert {"feature", "label", "importance", "pct"} <= set(primero)


def test_feature_importance_clinical_only_filtra(client):
    r = client.get("/feature-importance", params={"clinical_only": True, "top_n": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["clinical_only"] is True
    assert len(body["importancias"]) <= 5
    # Ningun codigo socioeconomico/demografico-secundario debe aparecer.
    no_clinicos = {"DMDMARTL", "DMDEDUC2", "INDFMPIR", "DMDHHSIZ", "DMDFMSIZ"}
    devueltos = {i["feature"] for i in body["importancias"]}
    assert devueltos.isdisjoint(no_clinicos)


def test_feature_importance_regresion(client):
    r = client.get("/feature-importance", params={"model": "regresion"})
    assert r.status_code == 200
    assert r.json()["model"] == "regresion"


def test_feature_importance_modelo_invalido_422(client):
    r = client.get("/feature-importance", params={"model": "otro"})
    assert r.status_code == 422


# --- /report (modo demo) -----------------------------------------------------


def test_report_genera_html_sin_email(client):
    r = client.post(
        "/report", json={"features": VALID_FEATURES, "edad_cronologica": 50}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["html"].lstrip().startswith("<!doctype html>")
    assert body["emailed"] is False
    assert body["email_mode"] == "none"
    assert body["guardado"] is False


def test_report_envia_demo_y_escribe_outbox(client):
    outbox = Path(os.environ["MAIL_OUTBOX_DIR"])
    antes = len(list(outbox.glob("*.html"))) if outbox.exists() else 0
    r = client.post(
        "/report",
        json={
            "features": VALID_FEATURES,
            "edad_cronologica": 50,
            "email": "demo@example.com",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["emailed"] is True
    assert body["email_mode"] == "demo"
    despues = len(list(outbox.glob("*.html")))
    assert despues == antes + 1


def test_report_email_invalido_422(client):
    r = client.post(
        "/report", json={"features": VALID_FEATURES, "email": "no-es-un-email"}
    )
    assert r.status_code == 422


# --- /history (guardar por correo, sin login) --------------------------------


def test_history_requiere_consentimiento(client):
    email = "guardo@example.com"
    # Sin guardar=True: NO debe aparecer en el historial.
    client.post("/report", json={"features": VALID_FEATURES, "email": email})
    r = client.get("/history", params={"email": email})
    assert r.status_code == 200
    assert r.json()["predicciones"] == []


def test_history_con_consentimiento_lista(client):
    email = "guardo2@example.com"
    client.post(
        "/report",
        json={
            "features": VALID_FEATURES,
            "edad_cronologica": 60,
            "email": email,
            "guardar": True,
        },
    )
    r = client.get("/history", params={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == email
    assert len(body["predicciones"]) >= 1
    assert "edad_biologica" in body["predicciones"][0]


def test_history_email_invalido_422(client):
    r = client.get("/history", params={"email": "x"})
    assert r.status_code == 422
