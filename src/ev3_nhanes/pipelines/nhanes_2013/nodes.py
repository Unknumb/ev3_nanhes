# src/ev3_nhanes/pipelines/nhanes_2013/nodes.py

import pandas as pd
import numpy as np
from typing import Any, Tuple
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold, KFold
from xgboost import XGBClassifier, XGBRegressor

# ──────────────────────────────────────────────────────────────────────
# Constantes de Configuración
# ──────────────────────────────────────────────────────────────────────
_EDAD_LONGEVO = 70
_RANDOM_STATE = 42

_CICLO_BASE = {"año": "2013", "letra": "H", "nombre": "2013-2014"}

_CICLOS_HISTORICOS = [
    {"año": "2011", "letra": "G", "nombre": "2011-2012"},
    {"año": "2009", "letra": "F", "nombre": "2009-2010"},
    {"año": "2007", "letra": "E", "nombre": "2007-2008"},
    {"año": "2005", "letra": "D", "nombre": "2005-2006"},
]

_TABLAS_CLAVE = ["DEMO", "BMX", "BPX", "TCHOL", "GLU", "MCQ", "SMQ"]


# ──────────────────────────────────────────────────────────────────────
# Funciones privadas de descarga
# ──────────────────────────────────────────────────────────────────────

def _generar_url(tabla: str, año: str, letra: str) -> str:
    """Genera la URL pública de la CDC basada en la tabla, el año y la letra."""
    return f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{año}/DataFiles/{tabla}_{letra}.xpt"


def _limpiar_missing_sas(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte el valor centinela de SAS (5.397605e-79) a verdaderos NaNs."""
    cols_num = df.select_dtypes(include=[np.number]).columns
    for col in cols_num:
        es_sas_missing = np.isclose(df[col], 5.397605e-79, atol=1e-85)
        df.loc[es_sas_missing, col] = np.nan
    return df


def _descargar_ciclo(config_ciclo: dict, solo_longevos: bool = False) -> pd.DataFrame:
    """Descarga las 7 tablas de un ciclo, las une y limpia los nulos de SAS."""
    año = config_ciclo["año"]
    letra = config_ciclo["letra"]
    nombre = config_ciclo["nombre"]

    print(f"\n--- Descargando Ciclo {nombre} ---")

    url_demo = _generar_url("DEMO", año, letra)
    try:
        df_maestra = pd.read_sas(url_demo)
    except Exception as e:
        print(f"Error descargando DEMO para {nombre}: {e}")
        return pd.DataFrame()

    df_maestra = _limpiar_missing_sas(df_maestra)

    if solo_longevos:
        if 'RIDAGEYR' in df_maestra.columns:
            df_maestra = df_maestra[df_maestra['RIDAGEYR'] >= _EDAD_LONGEVO].copy()
            print(f"Rescatados {len(df_maestra)} pacientes longevos.")
        else:
            return pd.DataFrame()

    for tabla in _TABLAS_CLAVE:
        if tabla == "DEMO":
            continue
        url = _generar_url(tabla, año, letra)
        try:
            df_temp = pd.read_sas(url)
            df_temp = _limpiar_missing_sas(df_temp)
            tipo_join = 'left' if solo_longevos else 'outer'
            df_maestra = pd.merge(df_maestra, df_temp, on='SEQN', how=tipo_join)
            print(f"  ✓ {tabla}_{letra} integrada.")
        except Exception as e:
            print(f"  x No se encontró {tabla}_{letra}: {e}")

    df_maestra['CICLO_ORIGEN'] = nombre
    return df_maestra


# ──────────────────────────────────────────────────────────────────────
# Nodo 1 – Extracción
# ──────────────────────────────────────────────────────────────────────

def descargar_y_unir_2013() -> pd.DataFrame:
    """
    Nodo de Kedro: Descarga el ciclo 2013-2014 completo y añade pacientes >= 70 años
    de los ciclos 2011, 2009, 2007 y 2005 para balancear la clase minoritaria.
    """
    print("Iniciando Pipeline de Extracción con Data Augmentation Histórico...")

    df_final = _descargar_ciclo(_CICLO_BASE, solo_longevos=False)

    for ciclo in _CICLOS_HISTORICOS:
        df_historico = _descargar_ciclo(ciclo, solo_longevos=True)
        if not df_historico.empty:
            df_final = pd.concat([df_final, df_historico], ignore_index=True)

    print(f"\n¡Extracción Completada! Dataset robustecido: {len(df_final)} pacientes totales.")
    return df_final


# ──────────────────────────────────────────────────────────────────────
# Nodo 2 – Preprocesamiento SIN escalado (limpieza + imputación + OHE)
# ──────────────────────────────────────────────────────────────────────

def preprocesar_datos_2013(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia, imputa y codifica. NO escala.
    El escalado se realiza DESPUÉS del train_test_split para evitar data leakage.
    """
    print("Iniciando preprocesamiento (sin escalado)...")

    # 1. Limpieza inicial
    df = df.dropna(subset=['RIDAGEYR'])
    df = df[df['RIDAGEYR'] >= 18].copy()

    # 2. Crear variable objetivo
    df['IS_LONGEVO'] = (df['RIDAGEYR'] >= _EDAD_LONGEVO).astype(int)

    # 3. Seleccionar columnas
    cols_id     = ['SEQN']
    cols_demo   = ['RIDAGEYR', 'RIAGENDR', 'RIDRETH3', 'DMDEDUC2', 'DMDMARTL',
                   'DMDHHSIZ', 'DMDFMSIZ', 'INDFMPIR']
    cols_bmx    = ['BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST', 'BMXLEG', 'BMXARML', 'BMXARMC']
    cols_bp     = ['BPXSY1', 'BPXDI1', 'BPXSY2', 'BPXDI2', 'BPXSY3', 'BPXDI3', 'BPXPLS']
    cols_lab    = ['LBXTC', 'LBXGLU']

    cols_deseadas = cols_id + cols_demo + cols_bmx + cols_bp + cols_lab + ['IS_LONGEVO', 'CICLO_ORIGEN']
    cols_seleccion = [c for c in cols_deseadas if c in df.columns]
    df = df[cols_seleccion].copy()

    cols_categoricas = [c for c in ['RIAGENDR', 'RIDRETH3', 'DMDEDUC2', 'DMDMARTL'] if c in df.columns]
    cols_numericas = [c for c in [
        'DMDHHSIZ', 'DMDFMSIZ', 'INDFMPIR',
        'BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST', 'BMXLEG', 'BMXARML', 'BMXARMC',
        'BPXSY1', 'BPXDI1', 'BPXSY2', 'BPXDI2', 'BPXSY3', 'BPXDI3', 'BPXPLS',
        'LBXTC', 'LBXGLU',
    ] if c in df.columns]

    # 4. Imputación
    knn_imputer = KNNImputer(n_neighbors=5, weights='uniform')
    df[cols_numericas] = knn_imputer.fit_transform(df[cols_numericas])

    simple_imputer = SimpleImputer(strategy='most_frequent')
    df[cols_categoricas] = simple_imputer.fit_transform(df[cols_categoricas])

    # 5. One-Hot Encoding
    for col in cols_categoricas:
        df[col] = df[col].astype(int).astype(str)
    df_encoded = pd.get_dummies(df, columns=cols_categoricas, drop_first=True, dtype=int)

    # ⚠️  NO se escala aquí — el escalado ocurre en split_y_escalar()
    print(f"Preprocesamiento terminado. Shape: {df_encoded.shape}")
    return df_encoded


# ──────────────────────────────────────────────────────────────────────
# Nodo 3 – Split + Escalado CORRECTO (sin data leakage)
# ──────────────────────────────────────────────────────────────────────

def split_y_escalar(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Orden correcto para evitar data leakage:
      1. train_test_split  — separa primero
      2. fit_transform()   — SOLO sobre X_train (el scaler aprende únicamente del train)
      3. transform()       — SOLO sobre X_test  (aplica los parámetros aprendidos del train)

    Devuelve: X_train_scaled, X_test_scaled, y_train, y_test
    """
    print("Dividiendo en Train/Test y escalando correctamente...")

    cols_excluir = ['SEQN', 'RIDAGEYR', 'IS_LONGEVO', 'CICLO_ORIGEN']
    feature_cols = [c for c in df.columns if c not in cols_excluir]

    cols_a_escalar = [c for c in [
        'DMDHHSIZ', 'DMDFMSIZ', 'INDFMPIR',
        'BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST', 'BMXLEG', 'BMXARML', 'BMXARMC',
        'BPXSY1', 'BPXDI1', 'BPXSY2', 'BPXDI2', 'BPXSY3', 'BPXDI3', 'BPXPLS',
        'LBXTC', 'LBXGLU',
    ] if c in feature_cols]

    X = df[feature_cols].copy()
    y = df['IS_LONGEVO']

    # ── PASO 1: PRIMERO el split ─────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=_RANDOM_STATE,
        stratify=y,
    )

    # ── PASO 2: DESPUÉS el escalado (fit SOLO en train) ──────────────
    scaler = StandardScaler()
    X_train[cols_a_escalar] = scaler.fit_transform(X_train[cols_a_escalar])  # aprende media/std de train
    X_test[cols_a_escalar]  = scaler.transform(X_test[cols_a_escalar])       # aplica esa media/std al test

    print(f"  Train: {X_train.shape}  |  Test: {X_test.shape}")
    print(f"  Proporción IS_LONGEVO en train: {y_train.mean():.2%}")
    print(f"  Proporción IS_LONGEVO en test:  {y_test.mean():.2%}")
    return X_train, X_test, y_train, y_test


# ──────────────────────────────────────────────────────────────────────
# Nodo 4a – Entrenamiento Clasificación
# ──────────────────────────────────────────────────────────────────────

def entrenar_modelo_clasificacion(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> Any:
    """Entrena modelo XGBoost de clasificación para IS_LONGEVO."""
    print("Entrenando modelo de clasificación XGBoost...")

    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    scale_pw = n_neg / n_pos if n_pos > 0 else 1.0

    xgb_param_dist = {
        'n_estimators':      [100, 200, 300, 500],
        'max_depth':         [3, 5, 7, 10],
        'learning_rate':     [0.01, 0.05, 0.1, 0.2],
        'subsample':         [0.7, 0.8, 0.9, 1.0],
        'colsample_bytree':  [0.7, 0.8, 0.9, 1.0],
        'min_child_weight':  [1, 3, 5],
    }

    xgb_search = RandomizedSearchCV(
        XGBClassifier(
            scale_pos_weight=scale_pw,
            random_state=_RANDOM_STATE,
            eval_metric='logloss',
        ),
        param_distributions=xgb_param_dist,
        n_iter=30,
        scoring='f1',
        cv=StratifiedKFold(5, shuffle=True, random_state=_RANDOM_STATE),
        random_state=_RANDOM_STATE,
        n_jobs=-1,
    )
    xgb_search.fit(X_train, y_train)

    print(f"Clasificación - Mejores hiperparámetros: {xgb_search.best_params_}")
    print(f"Clasificación - Mejor F1 (CV): {xgb_search.best_score_:.4f}")
    return xgb_search.best_estimator_


# ──────────────────────────────────────────────────────────────────────
# Nodo 4b – Entrenamiento Regresión
# ──────────────────────────────────────────────────────────────────────

def entrenar_modelo_regresion(
    df: pd.DataFrame,
    X_train: pd.DataFrame,
) -> Any:
    """
    Entrena modelo XGBoost de regresión para RIDAGEYR (edad cronológica).
    Recupera y_train de regresión usando los índices de X_train sobre el df original.
    """
    print("Entrenando modelo de regresión XGBoost...")

    # Reconstruimos el target de regresión alineado con los índices de X_train
    y_train_reg = df.loc[X_train.index, 'RIDAGEYR']

    xgb_param_dist = {
        'n_estimators':      [100, 200, 300, 500],
        'max_depth':         [3, 5, 7, 10],
        'learning_rate':     [0.01, 0.05, 0.1, 0.2],
        'subsample':         [0.7, 0.8, 0.9, 1.0],
        'colsample_bytree':  [0.7, 0.8, 0.9, 1.0],
        'min_child_weight':  [1, 3, 5],
    }

    xgb_search = RandomizedSearchCV(
        XGBRegressor(random_state=_RANDOM_STATE, eval_metric='rmse'),
        param_distributions=xgb_param_dist,
        n_iter=30,
        scoring='neg_mean_absolute_error',
        cv=KFold(5, shuffle=True, random_state=_RANDOM_STATE),
        random_state=_RANDOM_STATE,
        n_jobs=-1,
    )
    xgb_search.fit(X_train, y_train_reg)

    print(f"Regresión - Mejores hiperparámetros: {xgb_search.best_params_}")
    print(f"Regresión - Mejor MAE (CV): {-xgb_search.best_score_:.2f} años")
    return xgb_search.best_estimator_
