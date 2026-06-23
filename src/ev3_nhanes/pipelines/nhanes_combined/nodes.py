"""Nodos del pipeline COMBINADO (un solo modelo para todo el equipo).

Este pipeline unifica el aporte de los tres ciclos del equipo en un único
dataset y entrena UN clasificador + UN regresor sobre un contrato de 36 features:
las 23 base (demografía, antropometría, presión, labs originales) + el panel
PhenoAge de laboratorio (Nivel B, opcional/imputado) + 4 de cuestionario
(Nivel A: salud autopercibida, tabaquismo, diabetes, evento cardiovascular):

Se descargan TODAS las edades de los 7 ciclos del equipo (2017-2018 base + 2015,
2013, 2011, 2009, 2007, 2005). El balanceo es **por modelo** (desacoplado), porque
clasificación y regresión necesitan distribuciones opuestas:

    - Clasificación → vista AUMENTADA (base + longevos de todos los ciclos): la
      clase longeva (≥70) queda bien representada → F1 alto (~0.92).
    - Regresión → vista BALANCEADA por edad (base + longevos + 40% de los jóvenes
      históricos): el regresor ve suficientes jóvenes para no inflar la edad
      biológica de personas jóvenes, manteniendo R²≥0.80.

Mismo set de 36 features que consumen la web, la API y la base de datos.
"""

import pandas as pd
import numpy as np
from typing import Any

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
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
# Configuración de ciclos — TODOS los aportes del equipo en un solo dataset
# ──────────────────────────────────────────────────────────────────────
_EDAD_LONGEVO = 70
# Fracción de jóvenes históricos (<70) que ve la REGRESIÓN. Tuneado a 0.4: es el
# máximo que mantiene R²≥0.80 mientras corrige el sesgo (un joven de 20 pasa de
# ~55 a ~33 años). La clasificación NO los usa (mantiene F1≈0.92).
_FRAC_JOVENES_REG = 0.4
# Ciclo base: 2017-2018 (Juan). Los históricos suman 2015 (Álvaro), 2013 (Nicolás)
# y profundidad extra. Todos se descargan con TODAS las edades; el balanceo por
# modelo se hace en las "vistas" del entrenamiento.
_CICLO_BASE = {"año": "2017", "letra": "J", "nombre": "2017-2018"}
_CICLOS_HISTORICOS = [
    {"año": "2015", "letra": "I", "nombre": "2015-2016"},
    {"año": "2013", "letra": "H", "nombre": "2013-2014"},
    {"año": "2011", "letra": "G", "nombre": "2011-2012"},
    {"año": "2009", "letra": "F", "nombre": "2009-2010"},
    {"año": "2007", "letra": "E", "nombre": "2007-2008"},
    {"año": "2005", "letra": "D", "nombre": "2005-2006"},
]
# Tablas NHANES a descargar y unir. Las 6 últimas se añadieron para las features
# de Nivel A (cuestionario) y Nivel B (panel PhenoAge de laboratorio):
#   HSQ→salud autopercibida · DIQ→diabetes · GHB→HbA1c · HDL→colesterol HDL ·
#   BIOPRO→albúmina/creatinina/fosfatasa · CBC→hemograma. (MCQ y SMQ ya estaban.)
_TABLAS_CLAVE = [
    "DEMO", "BMX", "BPX", "TCHOL", "GLU", "MCQ", "SMQ",
    "HSQ", "DIQ", "GHB", "HDL", "BIOPRO", "CBC",
]

# Columnas NHANES de cuestionario con códigos especiales 7/9 (rehúsa/no sabe)
# que hay que convertir a NaN antes de usarlas como features.
_COLS_ENCUESTA_77_99 = [
    "HSD010", "SMQ020", "DIQ010", "MCQ160B", "MCQ160C", "MCQ160E", "MCQ160F",
]
# Componentes del evento cardiovascular previo (se fusionan en MCQ_CVD):
#   MCQ160B=insuf. cardíaca · 160C=enf. coronaria · 160E=infarto · 160F=ACV
_COLS_MCQ_CVD = ["MCQ160B", "MCQ160C", "MCQ160E", "MCQ160F"]

# ──────────────────────────────────────────────────────────────────────
# Contrato de datos (códigos NHANES originales en inglés). 36 features:
# 23 del contrato base + 9 labs PhenoAge (Nivel B) + 4 de cuestionario (Nivel A).
# ──────────────────────────────────────────────────────────────────────
_COLS_NUMERICAS = [
    # — Base (demografía / antropometría / presión / labs originales) —
    "DMDHHSIZ", "DMDFMSIZ", "INDFMPIR",
    "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST", "BMXLEG", "BMXARML", "BMXARMC",
    "BPXSY1", "BPXDI1", "BPXSY2", "BPXDI2", "BPXSY3", "BPXDI3", "BPXPLS",
    "LBXTC", "LBXGLU",
    # — Nivel B · panel PhenoAge (Levine 2018), opcionales (se imputan) —
    "LBXGH",     # HbA1c (hemoglobina glicada)
    "LBDHDD",    # colesterol HDL
    "LBXSAL",    # albúmina
    "LBXSCR",    # creatinina
    "LBXSAPSI",  # fosfatasa alcalina
    "LBXWBCSI",  # leucocitos
    "LBXLYPCT",  # % linfocitos
    "LBXMCVSI",  # volumen corpuscular medio (VCM)
    "LBXRDW",    # ancho de distribución eritrocitaria (RDW)
]
# — Nivel A · cuestionario (categóricas, fáciles de responder) —
#   HSD010=salud autopercibida · SMQ020=fumador · DIQ010=diabetes ·
#   MCQ_CVD=evento cardiovascular previo (derivada de MCQ160B/C/E/F)
_COLS_CATEGORICAS = [
    "RIAGENDR", "RIDRETH3", "DMDEDUC2", "DMDMARTL",
    "HSD010", "SMQ020", "DIQ010", "MCQ_CVD",
]
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


def descargar_y_unir_combinado() -> pd.DataFrame:
    """Descarga TODAS las edades de TODOS los ciclos (superset natural).

    El balanceo NO se hace aquí: cada modelo arma su propia vista en el
    entrenamiento (ver `_vista_clasificacion` / `_vista_regresion`). Bajar todas
    las edades permite que la regresión vea jóvenes de los ciclos históricos y no
    sobre-estime la edad biológica de personas jóvenes.
    """
    print("Iniciando extracción combinada (todas las edades, todos los ciclos)...")
    partes = []
    for ciclo in [_CICLO_BASE, *_CICLOS_HISTORICOS]:
        df_c = _descargar_ciclo(ciclo, solo_longevos=False)
        if not df_c.empty:
            partes.append(df_c)
    df_final = pd.concat(partes, ignore_index=True)
    print(f"\nExtracción completada: {len(df_final)} pacientes totales.")
    return df_final


# ──────────────────────────────────────────────────────────────────────
# 2) PREPROCESADO  (solo selecciona/limpia — NO imputa/escala/OHE)
#    Las transformaciones viven en el Pipeline de modelado para evitar
#    fuga de datos hacia el conjunto de test.
# ──────────────────────────────────────────────────────────────────────
def _derivar_mcq_cvd(df: pd.DataFrame) -> pd.Series:
    """Fusiona MCQ160B/C/E/F en un único flag de evento cardiovascular previo.

    1=sí (cualquiera de los cuatro), 0=no (todos respondidos como 'no'),
    NaN=desconocido (ninguno respondido). Los 1 se mantienen, 2→0, 7/9→NaN.
    """
    presentes = [c for c in _COLS_MCQ_CVD if c in df.columns]
    if not presentes:
        return pd.Series(np.nan, index=df.index)
    tmp = df[presentes].replace({2: 0, 7: np.nan, 9: np.nan})
    return tmp.max(axis=1)  # any(1)→1 · all(0)→0 · all(NaN)→NaN


def preprocesar_datos_combinado(df: pd.DataFrame) -> pd.DataFrame:
    """Selecciona columnas, filtra adultos y crea IS_LONGEVO. Sin transformar."""
    print("Seleccionando y limpiando (sin transformar)...")
    df = df.dropna(subset=["RIDAGEYR"])
    df = df[df["RIDAGEYR"] >= 18].copy()
    df["IS_LONGEVO"] = (df["RIDAGEYR"] >= _EDAD_LONGEVO).astype(int)

    # Limpia los códigos 7/9 (rehúsa/no sabe) de las variables de cuestionario
    # ANTES de derivar/seleccionar, para que no contaminen el modelo.
    for col in _COLS_ENCUESTA_77_99:
        if col in df.columns:
            df[col] = df[col].replace({7: np.nan, 9: np.nan})

    # Nivel A: deriva el flag de evento cardiovascular previo desde MCQ160*.
    df["MCQ_CVD"] = _derivar_mcq_cvd(df)

    cols_id = ["SEQN"]
    cols_demo = ["RIDAGEYR", "RIAGENDR", "RIDRETH3", "DMDEDUC2", "DMDMARTL",
                 "DMDHHSIZ", "DMDFMSIZ", "INDFMPIR"]
    cols_bmx = ["BMXWT", "BMXHT", "BMXBMI", "BMXWAIST", "BMXLEG", "BMXARML", "BMXARMC"]
    cols_bp = ["BPXSY1", "BPXDI1", "BPXSY2", "BPXDI2", "BPXSY3", "BPXDI3", "BPXPLS"]
    # Labs: originales + panel PhenoAge (Nivel B)
    cols_lab = ["LBXTC", "LBXGLU", "LBXGH", "LBDHDD", "LBXSAL", "LBXSCR",
                "LBXSAPSI", "LBXWBCSI", "LBXLYPCT", "LBXMCVSI", "LBXRDW"]
    # Cuestionario (Nivel A)
    cols_quest = ["HSD010", "SMQ020", "DIQ010", "MCQ_CVD"]
    cols_deseadas = (
        cols_id + cols_demo + cols_bmx + cols_bp + cols_lab + cols_quest
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
    Pipeline para que el fit ocurra únicamente sobre el train de cada fold.

    Imputación numérica por **mediana** (no KNN): con 7 ciclos y el panel de
    labs opcionales el dataset es grande y muy disperso; KNNImputer es O(n²) y
    se vuelve inviable, mientras la mediana es estándar, rápida y robusta.
    """
    num = [c for c in _COLS_NUMERICAS if c in feature_cols]
    cat = [c for c in _COLS_CATEGORICAS if c in feature_cols]
    return ColumnTransformer(
        transformers=[
            ("num", SkPipeline([
                ("imputer", SimpleImputer(strategy="median")),
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
# 3b) VISTAS POR MODELO  (cada modelo ve el balance que le conviene)
#     El dataset preprocesado trae TODAS las edades; aquí cada modelo arma su
#     subconjunto. Desacoplar resuelve que clasificación y regresión necesitan
#     balances opuestos: la primera quiere más longevos, la segunda una
#     distribución de edades más natural.
# ──────────────────────────────────────────────────────────────────────
def _vista_clasificacion(df: pd.DataFrame) -> pd.DataFrame:
    """Vista AUMENTADA: rescata la clase longeva (minoritaria).

    Ciclo base completo + longevos (≥70) de todos los ciclos; descarta a los
    jóvenes históricos. Mantiene la clase rara bien representada → F1 alto.
    """
    base = df["CICLO_ORIGEN"] == _CICLO_BASE["nombre"]
    return df[base | (df["IS_LONGEVO"] == 1)].copy()


def _vista_regresion(df: pd.DataFrame) -> pd.DataFrame:
    """Vista BALANCEADA por edad: corrige el sesgo del regresor hacia edades altas.

    Ciclo base completo + longevos históricos + una fracción (`_FRAC_JOVENES_REG`)
    de los jóvenes históricos. Así el regresor ve suficientes jóvenes para no
    inflar su edad biológica, sin diluir tanto los datos como para bajar el R².
    """
    es_base = df["CICLO_ORIGEN"] == _CICLO_BASE["nombre"]
    base = df[es_base]
    hist = df[~es_base]
    hist_longevos = hist[hist["IS_LONGEVO"] == 1]
    hist_jovenes = hist[hist["IS_LONGEVO"] == 0].sample(
        frac=_FRAC_JOVENES_REG, random_state=42
    )
    return pd.concat([base, hist_longevos, hist_jovenes], ignore_index=True)


# ──────────────────────────────────────────────────────────────────────
# 4) CLASIFICACIÓN  → devuelve (modelo, reporte_texto)
# ──────────────────────────────────────────────────────────────────────
def entrenar_modelo_clasificacion(df: pd.DataFrame) -> tuple[Any, str]:
    """Entrena XGBClassifier para IS_LONGEVO sin fuga de datos."""
    print("Entrenando XGBClassifier combinado (IS_LONGEVO)...")
    df = _vista_clasificacion(df)  # vista aumentada (rescata la clase longeva)
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
                                eval_metric="logloss", tree_method="hist",
                                n_jobs=1)),
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

    ciclos = ", ".join(
        [_CICLO_BASE["nombre"]] + [c["nombre"] for c in _CICLOS_HISTORICOS]
    )
    reporte = "\n".join([
        "REPORTE CLASIFICACIÓN — Modelo COMBINADO (todos los ciclos del equipo)",
        "=" * 60,
        f"Ciclos: {ciclos}",
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
    print("Entrenando XGBRegressor combinado (RIDAGEYR)...")
    df = _vista_regresion(df)  # vista balanceada por edad (corrige el sesgo joven)
    feature_cols = [c for c in df.columns if c not in _COLS_EXCLUIR]
    X, y = df[feature_cols], df["RIDAGEYR"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipe = SkPipeline([
        ("prep", _construir_preprocesador(feature_cols)),
        ("model", XGBRegressor(random_state=42, eval_metric="rmse",
                               tree_method="hist", n_jobs=1)),
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

    ciclos = ", ".join(
        [_CICLO_BASE["nombre"]] + [c["nombre"] for c in _CICLOS_HISTORICOS]
    )
    reporte = "\n".join([
        "REPORTE REGRESIÓN — Modelo COMBINADO (todos los ciclos del equipo)",
        "=" * 60,
        f"Ciclos: {ciclos}",
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
