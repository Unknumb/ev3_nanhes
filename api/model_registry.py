"""Carga los modelos bendecidos (data/09_serving/) y expone predict / explain.

Los pickles son Pipelines sklearn autocontenidos (preprocesador + XGBoost), por
lo que esta capa NO reimplementa imputacion/escalado: solo arma un DataFrame con
las columnas NHANES crudas y delega en el modelo.
"""

from __future__ import annotations

import json
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap

_ROOT = Path(os.getenv("EV3_ROOT", Path(__file__).resolve().parent.parent))
SCHEMA_PATH = Path(os.getenv("FEATURE_SCHEMA_PATH", _ROOT / "feature_schema.json"))
SERVING_DIR = Path(os.getenv("MODEL_DIR", _ROOT / "data" / "09_serving"))
CLF_PATH = SERVING_DIR / "model_clasificacion_2015.pkl"
REG_PATH = SERVING_DIR / "model_regresion_2015.pkl"

LONGEVITY_THRESHOLD = 0.5


@lru_cache(maxsize=1)
def load_schema() -> dict:
    """Carga feature_schema.json (fuente unica de verdad del contrato)."""
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def feature_codes() -> list[str]:
    return [f["code"] for f in load_schema()["features"]]


def feature_labels() -> dict[str, str]:
    """Mapa codigo NHANES -> etiqueta legible (para graficos del front)."""
    return {f["code"]: f["label"] for f in load_schema()["features"]}


def _load_pickle(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro el modelo bendecido en {path}. "
            "Corre primero: kedro run --pipeline serving"
        )
    with open(path, "rb") as fh:
        return pickle.load(fh)


@lru_cache(maxsize=1)
def get_classifier() -> Any:
    return _load_pickle(CLF_PATH)


@lru_cache(maxsize=1)
def get_regressor() -> Any:
    return _load_pickle(REG_PATH)


def load_models() -> None:
    """Precarga ambos modelos en memoria durante el startup de FastAPI."""
    get_classifier()
    get_regressor()


def models_ready() -> bool:
    return CLF_PATH.exists() and REG_PATH.exists()


def _to_frame(features: dict[str, Any]) -> pd.DataFrame:
    """Arma un DataFrame de 1 fila con TODAS las columnas del contrato.

    Los campos ausentes/None quedan como NaN y el imputador del Pipeline
    (ajustado en entrenamiento) los completa. El ColumnTransformer selecciona
    por nombre.
    """
    row = {code: features.get(code) for code in feature_codes()}
    return pd.DataFrame([row], columns=feature_codes())


def predict(features: dict[str, Any], edad_cronologica: float | None = None) -> dict:
    """Devuelve clase de longevidad, probabilidad y edad biologica estimada."""
    X = _to_frame(features)

    clf = get_classifier()
    proba = float(clf.predict_proba(X)[0, 1])
    es_longevo = bool(proba >= LONGEVITY_THRESHOLD)

    edad_biologica = float(get_regressor().predict(X)[0])
    gap = (
        round(edad_biologica - edad_cronologica, 1)
        if edad_cronologica is not None
        else None
    )

    return {
        "es_longevo": es_longevo,
        "probabilidad": round(proba, 4),
        "edad_biologica": round(edad_biologica, 1),
        "edad_cronologica": edad_cronologica,
        "gap": gap,
    }


def explain(features: dict[str, Any], top_n: int = 8) -> dict:
    """SHAP sobre el clasificador: contribucion por feature NHANES original.

    SHAP corre sobre el paso XGBoost (espacio transformado); luego se reagrupan
    las columnas one-hot de cada categorica a su feature de origen para devolver
    nombres limpios (RIAGENDR en vez de cat__RIAGENDR_2.0).
    """
    clf = get_classifier()
    prep = clf.named_steps["prep"]
    model = clf.named_steps["model"]

    X = _to_frame(features)
    X_trans = prep.transform(X)
    trans_names = list(prep.get_feature_names_out())

    try:
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_trans)
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("shap no esta instalado: pip install shap") from exc

    shap_row = np.asarray(shap_vals)[0]

    agg: dict[str, float] = {}
    for name, val in zip(trans_names, shap_row):
        base = name.split("__", 1)[-1]
        if base not in feature_codes():
            base = base.rsplit("_", 1)[0]
        agg[base] = agg.get(base, 0.0) + float(val)

    ranked = sorted(agg.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_n]
    contribs = [
        {
            "feature": code,
            "shap": round(val, 4),
            "empuja": "longevo" if val > 0 else "no_longevo",
        }
        for code, val in ranked
    ]
    return {
        "base_value": round(float(explainer.expected_value), 4),
        "contribuciones": contribs,
    }


def _regroup_to_nhanes(trans_name: str) -> str:
    """'num__BMXBMI' -> 'BMXBMI'; 'cat__RIAGENDR_2.0' -> 'RIAGENDR'."""
    base = trans_name.split("__", 1)[-1]  # quita prefijo num__/cat__
    if base not in feature_codes():
        base = base.rsplit("_", 1)[0]  # quita sufijo de la categoria one-hot
    return base


def global_importance(top_n: int = 10) -> dict:
    """Importancia GLOBAL de features del clasificador (gain de XGBoost).

    A diferencia de `explain` (SHAP por-paciente), esto es una sola vista del modelo
    util para el grafico introductorio del front. Reagrupa las columnas one-hot al
    codigo NHANES de origen y adjunta etiquetas legibles. No requiere SHAP.
    """
    clf = get_classifier()
    prep = clf.named_steps["prep"]
    model = clf.named_steps["model"]

    importances = model.feature_importances_
    trans_names = list(prep.get_feature_names_out())
    labels = feature_labels()

    agg: dict[str, float] = {}
    for name, val in zip(trans_names, importances):
        base = _regroup_to_nhanes(name)
        agg[base] = agg.get(base, 0.0) + float(val)

    total = sum(agg.values()) or 1.0
    ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return {
        "importancias": [
            {
                "feature": code,
                "label": labels.get(code, code),
                "importance": round(val, 4),
                "pct": round(val / total * 100, 1),
            }
            for code, val in ranked
        ]
    }
