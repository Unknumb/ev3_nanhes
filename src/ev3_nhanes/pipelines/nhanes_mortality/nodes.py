"""Nodos del MVP de mortalidad a 10 años.

Reusa la descarga y el preprocesado del pipeline combinado (todas las edades, 7
ciclos), une los archivos de mortalidad enlazada por ciclo, deriva el target
`murio_10y` manejando la censura, y entrena un XGBClassifier.

Target (con manejo de censura, FUTIME en meses):
  - FUTIME ≥ 120 (≥10 años observados vivo)            → 0 (sobrevivió la ventana)
  - MORTSTAT==1 y FUTIME < 120 (murió dentro de 10 años) → 1
  - vivo con FUTIME < 120 (censurado, desenlace desconocido) → se DESCARTA
"""

import numpy as np
import pandas as pd
from typing import Any

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    train_test_split,
)
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from ev3_nhanes.pipelines.nhanes_combined.nodes import (
    _COLS_CATEGORICAS,
    _COLS_NUMERICAS,
    _PARAM_DIST,
    descargar_y_unir_combinado,
    preprocesar_datos_combinado,
)

_HORIZONTE_MESES = 120  # 10 años
_TARGET = "murio_10y"

# La EDAD es feature aquí (predictor clave de mortalidad); en el modelo de edad
# biológica era target y se excluía.
_NUM_MORT = [*_COLS_NUMERICAS, "RIDAGEYR"]
_CAT_MORT = _COLS_CATEGORICAS
_COLS_EXCLUIR_MORT = [
    "SEQN", "CICLO_ORIGEN", "IS_LONGEVO", _TARGET,
    "MORTSTAT", "FUTIME", "ELIGSTAT",
]

# Orden de los df de mortalidad que recibe el nodo (mismo orden que el pipeline).
_CICLOS_MORT = [
    "2017-2018", "2015-2016", "2013-2014", "2011-2012",
    "2009-2010", "2007-2008", "2005-2006",
]


# ──────────────────────────────────────────────────────────────────────
# 1) DESCARGA de features (reusa el combinado: todas las edades, 7 ciclos)
# ──────────────────────────────────────────────────────────────────────
def descargar_features_mortalidad() -> pd.DataFrame:
    """Descarga las features (idéntico al combinado)."""
    return descargar_y_unir_combinado()


# ──────────────────────────────────────────────────────────────────────
# 2) DATASET de mortalidad: une mortalidad + deriva target + maneja censura
# ──────────────────────────────────────────────────────────────────────
def _derivar_target_10y(df: pd.DataFrame) -> pd.Series:
    """Target binario a 10 años con censura (NaN = censurado, se descarta)."""
    fut = df["FUTIME"]
    target = pd.Series(np.nan, index=df.index, dtype="float64")
    target[fut >= _HORIZONTE_MESES] = 0.0  # sobrevivió la ventana de 10 años
    target[(df["MORTSTAT"] == 1) & (fut < _HORIZONTE_MESES)] = 1.0  # murió en 10 años
    return target


def preparar_dataset_mortalidad(
    raw_features: pd.DataFrame,
    raw_mort_2017: pd.DataFrame,
    raw_mort_2015: pd.DataFrame,
    raw_mort_2013: pd.DataFrame,
    raw_mort_2011: pd.DataFrame,
    raw_mort_2009: pd.DataFrame,
    raw_mort_2007: pd.DataFrame,
    raw_mort_2005: pd.DataFrame,
) -> pd.DataFrame:
    """Une features + mortalidad por ciclo y deriva el target a 10 años."""
    df = preprocesar_datos_combinado(raw_features)  # SEQN, RIDAGEYR, 36 feats, CICLO_ORIGEN

    morts = [raw_mort_2017, raw_mort_2015, raw_mort_2013, raw_mort_2011,
             raw_mort_2009, raw_mort_2007, raw_mort_2005]
    partes = []
    for nombre, m in zip(_CICLOS_MORT, morts):
        mm = m[["SEQN", "ELIGSTAT", "MORTSTAT", "FUTIME"]].copy()
        mm["CICLO_ORIGEN"] = nombre
        partes.append(mm)
    mort = pd.concat(partes, ignore_index=True)

    # SEQN se repite entre ciclos → unir por (SEQN, CICLO_ORIGEN).
    df = df.merge(mort, on=["SEQN", "CICLO_ORIGEN"], how="inner")
    df = df[df["ELIGSTAT"] == 1].copy()  # solo elegibles para el enlace

    df[_TARGET] = _derivar_target_10y(df)
    n_antes = len(df)
    df = df.dropna(subset=[_TARGET]).copy()  # descarta censurados
    df[_TARGET] = df[_TARGET].astype(int)

    print(
        f"Dataset mortalidad: {len(df)} filas usables "
        f"({n_antes - len(df)} censuradas descartadas) · "
        f"murieron en 10 años: {df[_TARGET].mean() * 100:.1f}%"
    )
    return df


# ──────────────────────────────────────────────────────────────────────
# 3) ENTRENAMIENTO
# ──────────────────────────────────────────────────────────────────────
def _construir_preprocesador_mort(feature_cols: list[str]) -> ColumnTransformer:
    num = [c for c in _NUM_MORT if c in feature_cols]
    cat = [c for c in _CAT_MORT if c in feature_cols]
    return ColumnTransformer(
        transformers=[
            ("num", SkPipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]), num),
            ("cat", SkPipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]), cat),
        ],
        remainder="drop",
    )


def entrenar_modelo_mortalidad(df: pd.DataFrame) -> tuple[Any, str]:
    """Entrena XGBClassifier para `murio_10y`. Reporta accuracy + AUC."""
    print("Entrenando XGBClassifier de mortalidad a 10 años...")
    feature_cols = [c for c in df.columns if c not in _COLS_EXCLUIR_MORT]
    X, y = df[feature_cols], df[_TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    pipe = SkPipeline([
        ("prep", _construir_preprocesador_mort(feature_cols)),
        ("model", XGBClassifier(random_state=42, eval_metric="logloss",
                                tree_method="hist", n_jobs=1)),
    ])
    search = RandomizedSearchCV(
        pipe, param_distributions=_PARAM_DIST, n_iter=30, scoring="roc_auc",
        cv=StratifiedKFold(5, shuffle=True, random_state=42),
        random_state=42, n_jobs=-1,
    )
    search.fit(X_train, y_train)

    best = search.best_estimator_
    y_pred = best.predict(X_test)
    y_proba = best.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

    reporte = "\n".join([
        "REPORTE MORTALIDAD A 10 AÑOS (MVP) — XGBClassifier",
        "=" * 60,
        "Target: murio_10y (1 si falleció dentro de 10 años; censurados descartados)",
        "Features: contrato de 36 + RIDAGEYR (la edad SÍ es feature aquí)",
        f"Filas train/test: {len(X_train)} / {len(X_test)}",
        f"Murieron en 10 años (test): {int((y_test == 1).sum())} / {len(y_test)} "
        f"({y_test.mean() * 100:.1f}%)",
        "",
        f"Accuracy (test): {acc:.4f}",
        f"ROC-AUC (test):  {auc:.4f}",
        f"Precision:       {prec:.4f}",
        f"Recall:          {rec:.4f}",
        f"F1-score:        {f1:.4f}",
        "",
        "Matriz de confusión [[TN, FP], [FN, TP]]:",
        f"  [[{cm[0, 0]}, {cm[0, 1]}], [{cm[1, 0]}, {cm[1, 1]}]]",
        "",
        f"Mejores hiperparámetros: {search.best_params_}",
        "",
        "Nota: la edad domina la predicción de mortalidad; comparar contra un",
        "baseline solo-edad para medir el aporte de los biomarcadores (futuro).",
    ])
    print(reporte)
    return best, reporte
