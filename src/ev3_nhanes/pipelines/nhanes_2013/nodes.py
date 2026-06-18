import pandas as pd
import numpy as np
from typing import Any

from sklearn.compose import ColumnTransformer
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import (
    train_test_split,
    RandomizedSearchCV,
    StratifiedKFold,
    KFold,
)
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from xgboost import XGBClassifier, XGBRegressor

# ──────────────────────────────────────────────────────────────────────
# Configuración del ciclo  (LO ÚNICO que cambia entre 2013 / 2015 / 2017)
# ──────────────────────────────────────────────────────────────────────
_EDAD_LONGEVO = 70
_CICLO_BASE = {"año": "2013", "letra": "H", "nombre": "2013-2014"}
_CICLOS_HISTORICOS = [
    {"año": "2011", "letra": "G", "nombre": "2011-2012"},
    {"año": "2009", "letra": "F", "nombre": "2009-2010"},
    {"año": "2007", "letra": "E", "nombre": "2007-2008"},
    {"año": "2005", "letra": "D", "nombre": "2005-2006"},
]
_TABLAS_CLAVE = ["DEMO", "BMX", "BPX", "TCHOL", "GLU", "MCQ", "SMQ"]

# ──────────────────────────────────────────────────────────────────────
# Contrato de datos del equipo (códigos NHANES originales en inglés)
# ──────────────────────────────────────────────────────────────────────
_COLS_NUMERICAS = [
    "DMDHHSIZ", "DMDFMSIZ", "INDFMPIR",
    "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST", "BMXLEG", "BMXARML", "BMXARMC",
    "BPXSY1", "BPXDI1", "BPXSY2", "BPXDI2", "BPXSY3", "BPXDI3", "BPXPLS",
    "LBXTC", "LBXGLU",
]
_COLS_CATEGORICAS = ["RIAGENDR", "RIDRETH3", "DMDEDUC2", "DMDMARTL"]
_COLS_EXCLUIR = ["SEQN", "RIDAGEYR", "IS_LONGEVO", "CICLO_ORIGEN"]

# Hiperparámetros: prefijo "model__" porque van dentro de un Pipeline sklearn
_PARAM_DIST = {
    "model__n_estimators": [100, 200, 300, 500],
    "model__max_depth": [3, 5, 7, 10],
    "model__learning_rate": [0.01, 0.05, 0.1, 0.2],
    "model__subsample": [0.7, 0.8, 0.9, 1.0],
    "model__colsample_bytree": [0.7, 0.8, 0.9, 1.0],
    "model__min_child_weight": [1, 3, 5],
}


# ──────────────────────────────────────────────────────────────────────
# 1) DESCARGA
# ──────────────────────────────────────────────────────────────────────
def _generar_url(tabla: str, año: str, letra: str) -> str:
    """Genera la URL pública de la CDC basada en la tabla, el año y la letra."""
    return f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{año}/DataFiles/{tabla}_{letra}.xpt"


def _limpiar_missing_sas(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte el centinela de SAS (5.397605e-79) en NaN real."""
    for col in df.select_dtypes(include=[np.number]).columns:
        es_sas_missing = np.isclose(df[col], 5.397605e-79, atol=1e-85)
        df.loc[es_sas_missing, col] = np.nan
    return df


def _descargar_ciclo(config_ciclo: dict, solo_longevos: bool = False) -> pd.DataFrame:
    """Descarga las tablas de un ciclo, las une y limpia los nulos de SAS."""
    año, letra, nombre = config_ciclo["año"], config_ciclo["letra"], config_ciclo["nombre"]
    print(f"\n--- Descargando Ciclo {nombre} ---")

    try:
        df_maestra = pd.read_sas(_generar_url("DEMO", año, letra))
    except Exception as e:
        print(f"Error descargando DEMO para {nombre}: {e}")
        return pd.DataFrame()
    df_maestra = _limpiar_missing_sas(df_maestra)

    # Filtro temprano para los ciclos históricos: solo longevos (ahorra RAM)
    if solo_longevos:
        if "RIDAGEYR" not in df_maestra.columns:
            return pd.DataFrame()
        df_maestra = df_maestra[df_maestra["RIDAGEYR"] >= _EDAD_LONGEVO].copy()
        print(f"Rescatados {len(df_maestra)} pacientes longevos.")

    for tabla in _TABLAS_CLAVE:
        if tabla == "DEMO":
            continue
        try:
            df_temp = _limpiar_missing_sas(pd.read_sas(_generar_url(tabla, año, letra)))
            # LEFT join al rescatar longevos para no traer jóvenes desde laboratorio
            tipo_join = "left" if solo_longevos else "outer"
            df_maestra = pd.merge(df_maestra, df_temp, on="SEQN", how=tipo_join)
            print(f"  ✓ {tabla}_{letra} integrada.")
        except Exception as e:
            print(f"  x No se encontró {tabla}_{letra}: {e}")

    df_maestra["CICLO_ORIGEN"] = nombre
    return df_maestra


def descargar_y_unir_2013() -> pd.DataFrame:
    """Descarga el ciclo base completo + longevos (>=70) de los ciclos históricos."""
    print("Iniciando extracción con Data Augmentation histórico...")
    df_final = _descargar_ciclo(_CICLO_BASE, solo_longevos=False)
    for ciclo in _CICLOS_HISTORICOS:
        df_hist = _descargar_ciclo(ciclo, solo_longevos=True)
        if not df_hist.empty:
            df_final = pd.concat([df_final, df_hist], ignore_index=True)
    print(f"\nExtracción completada: {len(df_final)} pacientes totales.")
    return df_final


# ──────────────────────────────────────────────────────────────────────
# 2) PREPROCESADO  (AHORA solo selecciona/limpia — NO imputa/escala/OHE)
#    Las transformaciones se movieron al Pipeline de modelado para evitar
#    fuga de datos hacia el conjunto de test.
# ──────────────────────────────────────────────────────────────────────
def preprocesar_datos_2013(df: pd.DataFrame) -> pd.DataFrame:
    """Selecciona columnas, filtra adultos y crea IS_LONGEVO. Sin transformar."""
    print("Seleccionando y limpiando (sin transformar)...")
    df = df.dropna(subset=["RIDAGEYR"])
    df = df[df["RIDAGEYR"] >= 18].copy()
    df["IS_LONGEVO"] = (df["RIDAGEYR"] >= _EDAD_LONGEVO).astype(int)

    cols_id = ["SEQN"]
    cols_demo = ["RIDAGEYR", "RIAGENDR", "RIDRETH3", "DMDEDUC2", "DMDMARTL",
                 "DMDHHSIZ", "DMDFMSIZ", "INDFMPIR"]
    cols_bmx = ["BMXWT", "BMXHT", "BMXBMI", "BMXWAIST", "BMXLEG", "BMXARML", "BMXARMC"]
    cols_bp = ["BPXSY1", "BPXDI1", "BPXSY2", "BPXDI2", "BPXSY3", "BPXDI3", "BPXPLS"]
    cols_lab = ["LBXTC", "LBXGLU"]
    cols_deseadas = (
        cols_id + cols_demo + cols_bmx + cols_bp + cols_lab
        + ["IS_LONGEVO", "CICLO_ORIGEN"]
    )

    df = df[[c for c in cols_deseadas if c in df.columns]].copy()
    print(f"Preprocesamiento terminado (datos crudos seleccionados): {df.shape}")
    return df


# ──────────────────────────────────────────────────────────────────────
# 3) PREPROCESADOR INTERNO  (se ajusta SOLO con datos de train)
# ──────────────────────────────────────────────────────────────────────
def _construir_preprocesador(feature_cols: list[str]) -> ColumnTransformer:
    """Imputa+escala numéricas e imputa+codifica categóricas, todo dentro del
    Pipeline para que el fit ocurra únicamente sobre el train de cada fold."""
    num = [c for c in _COLS_NUMERICAS if c in feature_cols]
    cat = [c for c in _COLS_CATEGORICAS if c in feature_cols]
    return ColumnTransformer(
        transformers=[
            ("num", SkPipeline([
                ("imputer", KNNImputer(n_neighbors=5, weights="uniform")),
                ("scaler", StandardScaler()),
            ]), num),
            ("cat", SkPipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                # sin drop_first: XGBoost (árboles) no sufre colinealidad y así
                # 'ignore' tolera categorías no vistas en el split de test
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]), cat),
        ],
        remainder="drop",
    )


# ──────────────────────────────────────────────────────────────────────
# 4) CLASIFICACIÓN  → devuelve (modelo, reporte_texto)
# ──────────────────────────────────────────────────────────────────────
def entrenar_modelo_clasificacion(df: pd.DataFrame) -> tuple[Any, str]:
    """Entrena XGBClassifier para IS_LONGEVO sin fuga de datos."""
    print("Entrenando XGBClassifier (IS_LONGEVO)...")
    feature_cols = [c for c in df.columns if c not in _COLS_EXCLUIR]
    X, y = df[feature_cols], df["IS_LONGEVO"]

    # >>> SPLIT ANTES de cualquier Imputer/Scaler: el test queda intacto
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # scale_pos_weight calculado SOLO con el train (no mira el test)
    n_neg, n_pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    scale_pw = n_neg / n_pos if n_pos > 0 else 1.0

    pipe = SkPipeline([
        ("prep", _construir_preprocesador(feature_cols)),
        ("model", XGBClassifier(scale_pos_weight=scale_pw, random_state=42,
                                eval_metric="logloss")),
    ])

    search = RandomizedSearchCV(
        pipe, param_distributions=_PARAM_DIST, n_iter=30, scoring="f1",
        cv=StratifiedKFold(5, shuffle=True, random_state=42),
        random_state=42, n_jobs=-1,
    )
    search.fit(X_train, y_train)  # el preprocesador se ajusta dentro de cada fold

    best = search.best_estimator_
    y_pred = best.predict(X_test)
    acc, f1 = accuracy_score(y_test, y_pred), f1_score(y_test, y_pred)

    reporte = "\n".join([
        f"REPORTE CLASIFICACIÓN — Ciclo {_CICLO_BASE['nombre']}",
        "=" * 60,
        "Modelo: XGBClassifier + RandomizedSearchCV(StratifiedKFold=5)",
        "Split:  test_size=0.2, stratify=IS_LONGEVO, random_state=42",
        f"Filas train/test: {len(X_train)} / {len(X_test)}",
        "",
        f"Mejor F1 (CV train): {search.best_score_:.4f}",
        f"Accuracy (test):     {acc:.4f}",
        f"F1-score (test):     {f1:.4f}",
        "",
        f"Mejores hiperparámetros: {search.best_params_}",
    ])
    print(reporte)
    return best, reporte


# ──────────────────────────────────────────────────────────────────────
# 5) REGRESIÓN  → devuelve (modelo, reporte_texto)
# ──────────────────────────────────────────────────────────────────────
def entrenar_modelo_regresion(df: pd.DataFrame) -> tuple[Any, str]:
    """Entrena XGBRegressor para RIDAGEYR sin fuga de datos."""
    print("Entrenando XGBRegressor (RIDAGEYR)...")
    feature_cols = [c for c in df.columns if c not in _COLS_EXCLUIR]
    X, y = df[feature_cols], df["RIDAGEYR"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipe = SkPipeline([
        ("prep", _construir_preprocesador(feature_cols)),
        ("model", XGBRegressor(random_state=42, eval_metric="rmse")),
    ])

    search = RandomizedSearchCV(
        pipe, param_distributions=_PARAM_DIST, n_iter=30,
        scoring="neg_mean_absolute_error",
        cv=KFold(5, shuffle=True, random_state=42),
        random_state=42, n_jobs=-1,
    )
    search.fit(X_train, y_train)

    best = search.best_estimator_
    y_pred = best.predict(X_test)
    mae, r2 = mean_absolute_error(y_test, y_pred), r2_score(y_test, y_pred)

    reporte = "\n".join([
        f"REPORTE REGRESIÓN — Ciclo {_CICLO_BASE['nombre']}",
        "=" * 60,
        "Modelo: XGBRegressor + RandomizedSearchCV(KFold=5)",
        "Split:  test_size=0.2, random_state=42",
        f"Filas train/test: {len(X_train)} / {len(X_test)}",
        "",
        f"Mejor MAE (CV train): {-search.best_score_:.2f} años",
        f"MAE (test):           {mae:.2f} años",
        f"R² (test):            {r2:.4f}",
        "",
        f"Mejores hiperparámetros: {search.best_params_}",
    ])
    print(reporte)
    return best, reporte
