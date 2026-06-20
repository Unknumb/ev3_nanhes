"""Nodes for the NHANES 2017-2018 longevity pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    KFold,
    RandomizedSearchCV,
    StratifiedKFold,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor


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

MODEL_INPUT_COLUMNS = [
    "SEQN",
    "RIDAGEYR",
    "RIAGENDR",
    "BMXBMI",
    "DIQ010",
    "SMQ020",
    "RIDRETH3",
    "INDFMPIR",
    "BMXWAIST",
    "BPXPLS",
    "BPXSY_AVG",
    "BPXDI_AVG",
    "IS_LONGEVO",
]

PREDICTORS = [
    "RIAGENDR",
    "BMXBMI",
    "DIQ010",
    "SMQ020",
    "RIDRETH3",
    "INDFMPIR",
    "BMXWAIST",
    "BPXPLS",
    "BPXSY_AVG",
    "BPXDI_AVG",
]

CONTINUOUS_FEATURES = [
    "BMXBMI",
    "INDFMPIR",
    "BMXWAIST",
    "BPXPLS",
    "BPXSY_AVG",
    "BPXDI_AVG",
]

CATEGORICAL_FEATURES = ["RIAGENDR", "DIQ010", "SMQ020", "RIDRETH3"]


def _check_columns(df: pd.DataFrame, columns: list[str], dataset_name: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{dataset_name} is missing expected columns: {missing}")


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


def _build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
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
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", _make_one_hot_encoder()),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def _format_params(params: dict[str, Any]) -> str:
    return "\n".join(f"- {key}: {value}" for key, value in sorted(params.items()))


def merge_nhanes_2017_data(
    raw_nhanes_2017_demo: pd.DataFrame,
    raw_nhanes_2017_bmx: pd.DataFrame,
    raw_nhanes_2017_bpx: pd.DataFrame,
    raw_nhanes_2017_diq: pd.DataFrame,
    raw_nhanes_2017_smq: pd.DataFrame,
    raw_nhanes_2017_mortality: pd.DataFrame,
) -> pd.DataFrame:
    """Merge selected NHANES 2017-2018 modules by SEQN."""
    datasets = {
        "demo": raw_nhanes_2017_demo,
        "bmx": raw_nhanes_2017_bmx,
        "bpx": raw_nhanes_2017_bpx,
        "diq": raw_nhanes_2017_diq,
        "smq": raw_nhanes_2017_smq,
        "mortality": raw_nhanes_2017_mortality,
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


def build_nhanes_2017_feature_expanded(
    nhanes_2017_merged: pd.DataFrame,
    raw_nhanes_2017_demo: pd.DataFrame,
    raw_nhanes_2017_bmx: pd.DataFrame,
    raw_nhanes_2017_bpx: pd.DataFrame,
    raw_nhanes_2017_smq: pd.DataFrame,
) -> pd.DataFrame:
    """Add feature-expanded variables and derived BP averages."""
    feature_sources = {
        "demo": raw_nhanes_2017_demo,
        "bmx": raw_nhanes_2017_bmx,
        "bpx": raw_nhanes_2017_bpx,
        "smq": raw_nhanes_2017_smq,
    }

    expanded = nhanes_2017_merged.copy()
    for name, df in feature_sources.items():
        columns = FEATURE_COLUMNS[name]
        _check_columns(df, columns, name)
        expanded = expanded.merge(df[columns].copy(), on="SEQN", how="left")

    expanded["BPXSY_AVG"] = expanded[["BPXSY1", "BPXSY2", "BPXSY3"]].mean(
        axis=1,
        skipna=True,
    )
    expanded["BPXDI_AVG"] = expanded[["BPXDI1", "BPXDI2", "BPXDI3"]].mean(
        axis=1,
        skipna=True,
    )

    return expanded[
        [
            "SEQN",
            "RIDAGEYR",
            "RIAGENDR",
            "BMXBMI",
            "BPXSY1",
            "BPXDI1",
            "DIQ010",
            "SMQ020",
            "MORTSTAT",
            "FUTIME",
            "RIDRETH3",
            "INDFMPIR",
            "BMXWAIST",
            "BPXPLS",
            "SMQ040",
            "BPXSY_AVG",
            "BPXDI_AVG",
        ]
    ].copy()


def prepare_nhanes_2017_model_input(
    nhanes_2017_feature_expanded: pd.DataFrame,
) -> pd.DataFrame:
    """Create IS_LONGEVO and prepare model input using original NHANES names."""
    model_input = nhanes_2017_feature_expanded.copy()
    model_input = model_input.dropna(subset=["RIDAGEYR"]).copy()
    model_input["IS_LONGEVO"] = (model_input["RIDAGEYR"] >= 70).astype(int)

    model_input["DIQ010"] = model_input["DIQ010"].replace({7: np.nan, 9: np.nan})
    model_input["SMQ020"] = model_input["SMQ020"].replace({7: np.nan, 9: np.nan})

    return model_input[MODEL_INPUT_COLUMNS].copy()


def train_nhanes_2017_logistic_model(nhanes_2017_model_input: pd.DataFrame) -> str:
    """Train the NHANES 2017 longevity Logistic Regression model."""
    x = nhanes_2017_model_input[PREDICTORS]
    y = nhanes_2017_model_input["IS_LONGEVO"].astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = Pipeline(
        [
            ("preprocessor", _build_preprocessor()),
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

    translated_columns = {
        "edad",
        "sexo",
        "imc",
        "diabetes",
        "fumador",
        "mortalidad",
        "tiempo_supervivencia",
    }
    leaked_translated = sorted(
        translated_columns.intersection(nhanes_2017_model_input.columns)
    )

    return "\n".join(
        [
            "NHANES 2017-2018 LONGEVITY LOGISTIC REGRESSION REPORT",
            "=" * 80,
            "Target: IS_LONGEVO = 1 if RIDAGEYR >= 70, else 0",
            "MORTSTAT is not used as target or predictor.",
            "Model: LogisticRegression(class_weight='balanced')",
            "Split: test_size=0.2, random_state=42, stratify=IS_LONGEVO",
            "",
            f"Rows used: {len(nhanes_2017_model_input)}",
            f"Train rows: {len(x_train)}",
            f"Test rows: {len(x_test)}",
            f"Train IS_LONGEVO distribution: 0={(y_train == 0).sum()}, 1={(y_train == 1).sum()}",
            f"Test IS_LONGEVO distribution: 0={(y_test == 0).sum()}, 1={(y_test == 1).sum()}",
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
            "",
            "Validation:",
            "Target column: IS_LONGEVO",
            "MORTSTAT used as target: no",
            f"Translated columns in model input: {leaked_translated}",
            "Reports location: data/08_reporting",
        ]
    )


def train_nhanes_2017_xgb_classifier(
    nhanes_2017_model_input: pd.DataFrame,
) -> tuple[Pipeline, str]:
    """Train an XGBClassifier for the NHANES 2017 longevity target."""
    x = nhanes_2017_model_input[PREDICTORS]
    y = nhanes_2017_model_input["IS_LONGEVO"].astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    n_negative = int((y_train == 0).sum())
    n_positive = int((y_train == 1).sum())
    scale_pos_weight = n_negative / n_positive

    model = Pipeline(
        [
            ("preprocessor", _build_preprocessor()),
            (
                "model",
                XGBClassifier(
                    objective="binary:logistic",
                    eval_metric="logloss",
                    random_state=42,
                    scale_pos_weight=scale_pos_weight,
                    tree_method="hist",
                    n_jobs=1,
                ),
            ),
        ]
    )

    search = RandomizedSearchCV(
        estimator=model,
        param_distributions={
            "model__n_estimators": [100, 200, 300],
            "model__max_depth": [3, 4, 5],
            "model__learning_rate": [0.01, 0.05, 0.1],
            "model__subsample": [0.8, 0.9, 1.0],
            "model__colsample_bytree": [0.8, 0.9, 1.0],
            "model__min_child_weight": [1, 3, 5],
        },
        n_iter=12,
        scoring="f1",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        random_state=42,
        n_jobs=1,
        refit=True,
    )
    search.fit(x_train, y_train)

    best_model = search.best_estimator_
    y_pred = best_model.predict(x_test)
    y_proba = best_model.predict_proba(x_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba)
    matrix = confusion_matrix(y_test, y_pred, labels=[0, 1])

    report = "\n".join(
        [
            "NHANES 2017-2018 XGBCLASSIFIER REPORT",
            "=" * 80,
            "Target: IS_LONGEVO = 1 if RIDAGEYR >= 70, else 0",
            "MORTSTAT is not used as target or predictor.",
            "Model: XGBClassifier with RandomizedSearchCV",
            "CV: StratifiedKFold(n_splits=5, shuffle=True, random_state=42)",
            "Scoring: f1",
            "Split: test_size=0.2, random_state=42, stratify=IS_LONGEVO",
            "",
            f"Rows used: {len(nhanes_2017_model_input)}",
            f"Train rows: {len(x_train)}",
            f"Test rows: {len(x_test)}",
            f"Train IS_LONGEVO distribution: 0={n_negative}, 1={n_positive}",
            f"Test IS_LONGEVO distribution: 0={(y_test == 0).sum()}, 1={(y_test == 1).sum()}",
            f"scale_pos_weight: {scale_pos_weight:.4f}",
            "",
            f"Best CV F1-score: {search.best_score_:.4f}",
            f"Accuracy: {accuracy:.4f}",
            f"Precision: {precision:.4f}",
            f"Recall: {recall:.4f}",
            f"F1-score: {f1:.4f}",
            f"ROC-AUC: {roc_auc:.4f}",
            "",
            "Confusion matrix:",
            _format_confusion_matrix(matrix),
            "",
            "Best parameters:",
            _format_params(search.best_params_),
            "",
            "Predictors:",
            ", ".join(PREDICTORS),
        ]
    )
    return best_model, report


def train_nhanes_2017_xgb_regressor(
    nhanes_2017_model_input: pd.DataFrame,
) -> tuple[Pipeline, str]:
    """Train an XGBRegressor to estimate chronological age from NHANES features."""
    x = nhanes_2017_model_input[PREDICTORS]
    y = nhanes_2017_model_input["RIDAGEYR"].astype(float)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
    )

    model = Pipeline(
        [
            ("preprocessor", _build_preprocessor()),
            (
                "model",
                XGBRegressor(
                    objective="reg:squarederror",
                    eval_metric="rmse",
                    random_state=42,
                    tree_method="hist",
                    n_jobs=1,
                ),
            ),
        ]
    )

    search = RandomizedSearchCV(
        estimator=model,
        param_distributions={
            "model__n_estimators": [100, 200, 300],
            "model__max_depth": [3, 4, 5],
            "model__learning_rate": [0.01, 0.05, 0.1],
            "model__subsample": [0.8, 0.9, 1.0],
            "model__colsample_bytree": [0.8, 0.9, 1.0],
            "model__min_child_weight": [1, 3, 5],
        },
        n_iter=12,
        scoring="neg_mean_absolute_error",
        cv=KFold(n_splits=5, shuffle=True, random_state=42),
        random_state=42,
        n_jobs=1,
        refit=True,
    )
    search.fit(x_train, y_train)

    best_model = search.best_estimator_
    y_pred = best_model.predict(x_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    report = "\n".join(
        [
            "NHANES 2017-2018 XGBREGRESSOR REPORT",
            "=" * 80,
            "Target: RIDAGEYR",
            "Purpose: estimate chronological age as a later proxy for biological age.",
            "Model: XGBRegressor with RandomizedSearchCV",
            "CV: KFold(n_splits=5, shuffle=True, random_state=42)",
            "Scoring: neg_mean_absolute_error",
            "Split: test_size=0.2, random_state=42",
            "",
            f"Rows used: {len(nhanes_2017_model_input)}",
            f"Train rows: {len(x_train)}",
            f"Test rows: {len(x_test)}",
            "",
            f"Best CV MAE: {-search.best_score_:.4f}",
            f"Test MAE: {mae:.4f}",
            f"Test RMSE: {rmse:.4f}",
            f"Test R2: {r2:.4f}",
            "",
            "Best parameters:",
            _format_params(search.best_params_),
            "",
            "Predictors:",
            ", ".join(PREDICTORS),
        ]
    )
    return best_model, report
