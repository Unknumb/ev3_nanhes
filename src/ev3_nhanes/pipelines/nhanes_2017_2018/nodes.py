"""Nodes for the NHANES 2017-2018 mortality pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_COLUMNS = {
    "demo": ["SEQN", "RIDAGEYR", "RIAGENDR"],
    "bmx": ["SEQN", "BMXBMI"],
    "bpx": ["SEQN", "BPXSY1", "BPXDI1"],
    "diq": ["SEQN", "DIQ010"],
    "smq": ["SEQN", "SMQ020"],
    "mortality": ["SEQN", "MORTSTAT", "FUTIME"],
}

FEATURE_COLUMNS = {
    "demo": ["SEQN", "RIDRETH3", "INDFMPIR"],
    "bmx": ["SEQN", "BMXWAIST"],
    "bpx": [
        "SEQN",
        "BPXPLS",
        "BPXSY2",
        "BPXSY3",
        "BPXDI2",
        "BPXDI3",
    ],
    "smq": ["SEQN", "SMQ040"],
}

BASELINE_RENAME = {
    "RIDAGEYR": "edad",
    "RIAGENDR": "sexo",
    "BMXBMI": "imc",
    "BPXSY1": "presion_sistolica",
    "BPXDI1": "presion_diastolica",
    "DIQ010": "diabetes",
    "SMQ020": "fumador",
    "MORTSTAT": "mortalidad",
    "FUTIME": "tiempo_supervivencia",
}

FEATURE_RENAME = {
    "RIDAGEYR": "edad",
    "RIAGENDR": "sexo",
    "BMXBMI": "imc",
    "DIQ010": "diabetes",
    "SMQ020": "fumador",
    "MORTSTAT": "mortalidad",
    "FUTIME": "tiempo_supervivencia",
    "RIDRETH3": "raza_etnia",
    "INDFMPIR": "indice_pobreza_ingreso",
    "BMXWAIST": "circunferencia_cintura",
    "BPXPLS": "pulso",
    "SMQ040": "estado_tabaquismo_actual",
}

FEATURE_MODEL_COLUMNS = [
    "edad",
    "sexo",
    "imc",
    "diabetes",
    "fumador",
    "mortalidad",
    "raza_etnia",
    "indice_pobreza_ingreso",
    "circunferencia_cintura",
    "pulso",
    "presion_sistolica_promedio",
    "presion_diastolica_promedio",
]

PREDICTORS = [
    "edad",
    "sexo",
    "imc",
    "diabetes",
    "fumador",
    "raza_etnia",
    "indice_pobreza_ingreso",
    "circunferencia_cintura",
    "pulso",
    "presion_sistolica_promedio",
    "presion_diastolica_promedio",
]

CONTINUOUS_FEATURES = [
    "edad",
    "imc",
    "indice_pobreza_ingreso",
    "circunferencia_cintura",
    "pulso",
    "presion_sistolica_promedio",
    "presion_diastolica_promedio",
]

BINARY_CATEGORICAL_FEATURES = ["sexo", "diabetes", "fumador"]
ONE_HOT_FEATURES = ["raza_etnia"]


def _check_columns(df: pd.DataFrame, columns: list[str], dataset_name: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{dataset_name} is missing expected columns: {missing}")


def _recode_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    output["sexo"] = output["sexo"].map({1: 0, 2: 1, 0: 0}).astype(float)
    output["diabetes"] = (
        output["diabetes"]
        .map({1: 1, 2: 0, 3: 1, 7: np.nan, 9: np.nan, 0: 0})
        .astype(float)
    )
    output["fumador"] = output["fumador"].map({1: 1, 2: 0, 0: 0}).astype(float)
    output["mortalidad"] = output["mortalidad"].map({0: 0, 1: 1}).astype(float)
    return output


def merge_nhanes_data(
    demo_data: pd.DataFrame,
    bmx_data: pd.DataFrame,
    bpx_data: pd.DataFrame,
    diq_data: pd.DataFrame,
    smq_data: pd.DataFrame,
    mortality_data: pd.DataFrame,
) -> pd.DataFrame:
    """Merge selected NHANES modules by SEQN."""
    datasets = {
        "demo": demo_data,
        "bmx": bmx_data,
        "bpx": bpx_data,
        "diq": diq_data,
        "smq": smq_data,
        "mortality": mortality_data,
    }

    selected = {}
    for name, df in datasets.items():
        columns = BASE_COLUMNS[name]
        _check_columns(df, columns, name)
        selected[name] = df[columns].copy()

    invalid_mortstat = sorted(
        selected["mortality"].loc[
            selected["mortality"]["MORTSTAT"].notna()
            & ~selected["mortality"]["MORTSTAT"].isin([0, 1]),
            "MORTSTAT",
        ].unique()
    )
    if invalid_mortstat:
        raise ValueError(f"Invalid MORTSTAT values found: {invalid_mortstat}")

    merged = selected["demo"]
    for name in ["bmx", "bpx", "diq", "smq", "mortality"]:
        merged = merged.merge(selected[name], on="SEQN", how="inner")

    return merged


def build_baseline_model_input(merged_data: pd.DataFrame) -> pd.DataFrame:
    """Build the original baseline model input used for comparison."""
    baseline = merged_data.copy().rename(columns=BASELINE_RENAME)
    baseline = _recode_common_columns(baseline)
    return baseline.dropna(subset=["mortalidad", "fumador", "imc"]).copy()


def build_feature_expanded_dataset(
    merged_data: pd.DataFrame,
    demo_data: pd.DataFrame,
    bmx_data: pd.DataFrame,
    bpx_data: pd.DataFrame,
    smq_data: pd.DataFrame,
) -> pd.DataFrame:
    """Add feature-expanded variables and derived average blood pressure."""
    feature_sources = {
        "demo": demo_data,
        "bmx": bmx_data,
        "bpx": bpx_data,
        "smq": smq_data,
    }

    expanded = merged_data.copy()
    for name, df in feature_sources.items():
        columns = FEATURE_COLUMNS[name]
        _check_columns(df, columns, name)
        expanded = expanded.merge(df[columns].copy(), on="SEQN", how="left")

    expanded["presion_sistolica_promedio"] = expanded[
        ["BPXSY1", "BPXSY2", "BPXSY3"]
    ].mean(axis=1, skipna=True)
    expanded["presion_diastolica_promedio"] = expanded[
        ["BPXDI1", "BPXDI2", "BPXDI3"]
    ].mean(axis=1, skipna=True)

    expanded = expanded.rename(columns=FEATURE_RENAME)

    return expanded[
        [
            "SEQN",
            "edad",
            "sexo",
            "imc",
            "diabetes",
            "fumador",
            "mortalidad",
            "tiempo_supervivencia",
            "raza_etnia",
            "indice_pobreza_ingreso",
            "circunferencia_cintura",
            "pulso",
            "estado_tabaquismo_actual",
            "presion_sistolica_promedio",
            "presion_diastolica_promedio",
        ]
    ].copy()


def prepare_feature_expanded_model_input(
    feature_expanded_data: pd.DataFrame,
) -> pd.DataFrame:
    """Clean and code the feature-expanded data for model training."""
    model_input = feature_expanded_data[FEATURE_MODEL_COLUMNS].copy()
    model_input = _recode_common_columns(model_input)
    return model_input.dropna(subset=["mortalidad"]).copy()


def _make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _format_confusion_matrix(matrix: np.ndarray) -> str:
    return (
        f"[[TN={matrix[0, 0]}, FP={matrix[0, 1]}],\n"
        f" [FN={matrix[1, 0]}, TP={matrix[1, 1]}]]"
    )


def train_feature_expanded_logistic_model(model_input: pd.DataFrame) -> str:
    """Train the current best Logistic Regression model and return a report."""
    x = model_input[PREDICTORS]
    y = model_input["mortalidad"].astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "continuous",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                CONTINUOUS_FEATURES,
            ),
            (
                "binary_categorical",
                SimpleImputer(strategy="most_frequent"),
                BINARY_CATEGORICAL_FEATURES,
            ),
            (
                "race",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", _make_one_hot_encoder()),
                    ]
                ),
                ONE_HOT_FEATURES,
            ),
        ],
        remainder="drop",
    )

    model = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    solver="lbfgs",
                    class_weight="balanced",
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    y_proba = model.predict_proba(x_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba)
    matrix = confusion_matrix(y_test, y_pred, labels=[0, 1])

    return "\n".join(
        [
            "FEATURE-EXPANDED LOGISTIC REGRESSION REPORT",
            "=" * 80,
            "Model: LogisticRegression(class_weight='balanced')",
            "Split: test_size=0.2, random_state=42, stratify=mortalidad",
            "",
            f"Rows used: {len(model_input)}",
            f"Train rows: {len(x_train)}",
            f"Test rows: {len(x_test)}",
            f"Train mortality distribution: 0={(y_train == 0).sum()}, 1={(y_train == 1).sum()}",
            f"Test mortality distribution: 0={(y_test == 0).sum()}, 1={(y_test == 1).sum()}",
            "",
            f"Accuracy: {accuracy:.4f}",
            f"Precision: {precision:.4f}",
            f"Recall: {recall:.4f}",
            f"F1-score: {f1:.4f}",
            f"ROC-AUC: {roc_auc:.4f}",
            "",
            "Confusion matrix:",
            _format_confusion_matrix(matrix),
            "",
            "Predictors:",
            ", ".join(PREDICTORS),
        ]
    )
