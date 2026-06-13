import pandas as pd
import numpy as np
from typing import Any
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, KFold
from xgboost import XGBClassifier, XGBRegressor

# ──────────────────────────────────────────────────────────────────────
# Constantes de Configuración
# ──────────────────────────────────────────────────────────────────────
_EDAD_LONGEVO = 70

# El ciclo principal que tu grupo analiza
_CICLO_BASE = {"año": "2015", "letra": "I", "nombre": "2015-2016"}

# Los 4 ciclos históricos para rescatar a la clase minoritaria (Longevos)
_CICLOS_HISTORICOS = [
    {"año": "2013", "letra": "H", "nombre": "2013-2014"},
    {"año": "2011", "letra": "G", "nombre": "2011-2012"},
    {"año": "2009", "letra": "F", "nombre": "2009-2010"},
    {"año": "2007", "letra": "E", "nombre": "2007-2008"}
]

_TABLAS_CLAVE = ["DEMO", "BMX", "BPX", "TCHOL", "GLU", "MCQ", "SMQ"]

def _generar_url(tabla: str, año: str, letra: str) -> str:
    """Genera la URL pública de la CDC basada en la tabla, el año y la letra."""
    return f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{año}/DataFiles/{tabla}_{letra}.xpt"

def _limpiar_missing_sas(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte el valor centinela de SAS (5.397605e-79) a verdaderos NaNs."""
    # Solo aplica a columnas numéricas para evitar errores
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
    
    # 1. Bajar tabla maestra (DEMO)
    url_demo = _generar_url("DEMO", año, letra)
    try:
        df_maestra = pd.read_sas(url_demo)
    except Exception as e:
        print(f"Error descargando DEMO para {nombre}: {e}")
        return pd.DataFrame()
        
    df_maestra = _limpiar_missing_sas(df_maestra)
    
    # 2. Aplicar filtro temprano si es un ciclo histórico (Ahorra muchísima RAM)
    if solo_longevos:
        if 'RIDAGEYR' in df_maestra.columns:
            df_maestra = df_maestra[df_maestra['RIDAGEYR'] >= _EDAD_LONGEVO].copy()
            print(f"Rescatados {len(df_maestra)} pacientes longevos.")
        else:
            return pd.DataFrame()
            
    # 3. Descargar el resto de las tablas y unirlas
    for tabla in _TABLAS_CLAVE:
        if tabla == "DEMO": continue
        
        url = _generar_url(tabla, año, letra)
        try:
            df_temp = pd.read_sas(url)
            df_temp = _limpiar_missing_sas(df_temp)
            
            # 💡 TRUCO PRO: Si estamos rescatando longevos, usamos LEFT join.
            # Si usamos Outer, traeríamos pacientes jóvenes de las tablas de laboratorio.
            tipo_join = 'left' if solo_longevos else 'outer'
            df_maestra = pd.merge(df_maestra, df_temp, on='SEQN', how=tipo_join)
            print(f"  ✓ {tabla}_{letra} integrada.")
        except Exception as e:
            print(f"  x No se encontró {tabla}_{letra}: {e}")
            
    # Dejamos una huella del ciclo de origen
    df_maestra['CICLO_ORIGEN'] = nombre
    return df_maestra

def descargar_y_unir_2015() -> pd.DataFrame:
    """
    Nodo de Kedro: Descarga el ciclo 2015-2016 completo y añade pacientes >= 70 años
    de los ciclos 2013, 2011, 2009 y 2007 para balancear la clase minoritaria.
    """
    print("Iniciando Pipeline de Extracción con Data Augmentation Histórico...")
    
    # 1. Descargar ciclo base (Todos los pacientes)
    df_final = _descargar_ciclo(_CICLO_BASE, solo_longevos=False)
    
    # 2. Descargar e inyectar ciclos históricos (Solo longevos)
    for ciclo in _CICLOS_HISTORICOS:
        df_historico = _descargar_ciclo(ciclo, solo_longevos=True)
        if not df_historico.empty:
            # pd.concat alinea automáticamente las columnas, incluso si hay ligeras diferencias entre años
            df_final = pd.concat([df_final, df_historico], ignore_index=True)
            
    print(f"\n¡Extracción Completada con Éxito! Dataset robustecido: {len(df_final)} pacientes totales.")
    return df_final


def preprocesar_datos_2015(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia, imputa y crea variable objetivo IS_LONGEVO."""
    print("Iniciando preprocesamiento de datos...")
    
    # 1. Limpieza inicial: eliminar nulos en la edad y menores de 18 años
    df = df.dropna(subset=['RIDAGEYR'])
    df = df[df['RIDAGEYR'] >= 18].copy()
    
    # 2. Crear variable objetivo (IS_LONGEVO)
    df['IS_LONGEVO'] = (df['RIDAGEYR'] >= _EDAD_LONGEVO).astype(int)
    
    # 3. Identificar y filtrar variables deseadas
    cols_id = ['SEQN']
    cols_demo = ['RIDAGEYR', 'RIAGENDR', 'RIDRETH3', 'DMDEDUC2', 'DMDMARTL', 'DMDHHSIZ', 'DMDFMSIZ', 'INDFMPIR']
    cols_bmx = ['BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST', 'BMXLEG', 'BMXARML', 'BMXARMC']
    cols_bp = ['BPXSY1', 'BPXDI1', 'BPXSY2', 'BPXDI2', 'BPXSY3', 'BPXDI3', 'BPXPLS']
    cols_lab = ['LBXTC', 'LBXGLU']
    
    cols_deseadas = cols_id + cols_demo + cols_bmx + cols_bp + cols_lab + ['IS_LONGEVO', 'CICLO_ORIGEN']
    cols_seleccion = [c for c in cols_deseadas if c in df.columns]
    
    df = df[cols_seleccion].copy()

    cols_categoricas = ['RIAGENDR', 'RIDRETH3', 'DMDEDUC2', 'DMDMARTL']
    cols_categoricas = [c for c in cols_categoricas if c in df.columns]
    
    cols_numericas = [
        'DMDHHSIZ', 'DMDFMSIZ', 'INDFMPIR',
        'BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST', 'BMXLEG', 'BMXARML', 'BMXARMC',
        'BPXSY1', 'BPXDI1', 'BPXSY2', 'BPXDI2', 'BPXSY3', 'BPXDI3', 'BPXPLS',
        'LBXTC', 'LBXGLU',
    ]
    cols_numericas = [c for c in cols_numericas if c in df.columns]
    
    # 4. Imputación de nulos
    knn_imputer = KNNImputer(n_neighbors=5, weights='uniform')
    df[cols_numericas] = knn_imputer.fit_transform(df[cols_numericas])
    
    simple_imputer = SimpleImputer(strategy='most_frequent')
    df[cols_categoricas] = simple_imputer.fit_transform(df[cols_categoricas])
    
    # 5. One-Hot Encoding
    for col in cols_categoricas:
        df[col] = df[col].astype(int).astype(str)
    df_encoded = pd.get_dummies(df, columns=cols_categoricas, drop_first=True, dtype=int)
    
    # 6. Escalado
    cols_a_escalar = [c for c in cols_numericas if c in df_encoded.columns]
    scaler = StandardScaler()
    df_encoded[cols_a_escalar] = scaler.fit_transform(df_encoded[cols_a_escalar])
    
    print(f"Preprocesamiento terminado. Dataset resultante: {df_encoded.shape}")
    return df_encoded


def entrenar_modelo_clasificacion(df: pd.DataFrame) -> Any:
    """Entrena modelo XGBoost de clasificación para IS_LONGEVO."""
    print("Entrenando modelo de clasificación XGBoost...")
    
    cols_excluir = ['SEQN', 'RIDAGEYR', 'IS_LONGEVO', 'CICLO_ORIGEN']
    feature_cols = [c for c in df.columns if c not in cols_excluir]
    
    X = df[feature_cols]
    y = df['IS_LONGEVO']
    
    # Calcular scale_pos_weight para compensar el desbalance
    n_neg = (y == 0).sum()
    n_pos = (y == 1).sum()
    scale_pw = n_neg / n_pos if n_pos > 0 else 1.0
    
    xgb_param_dist = {
        'n_estimators': [100, 200, 300, 500],
        'max_depth': [3, 5, 7, 10],
        'learning_rate': [0.01, 0.05, 0.1, 0.2],
        'subsample': [0.7, 0.8, 0.9, 1.0],
        'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
        'min_child_weight': [1, 3, 5],
    }
    
    xgb_search = RandomizedSearchCV(
        XGBClassifier(
            scale_pos_weight=scale_pw,
            random_state=42,
            eval_metric='logloss',
        ),
        param_distributions=xgb_param_dist,
        n_iter=30,
        scoring='f1',
        cv=StratifiedKFold(5, shuffle=True, random_state=42),
        random_state=42,
        n_jobs=-1
    )
    xgb_search.fit(X, y)
    
    print(f"Clasificación - Mejores hiperparámetros: {xgb_search.best_params_}")
    print(f"Clasificación - Mejor F1 (CV): {xgb_search.best_score_:.4f}")
    
    return xgb_search.best_estimator_


def entrenar_modelo_regresion(df: pd.DataFrame) -> Any:
    """Entrena modelo XGBoost de regresión para RIDAGEYR."""
    print("Entrenando modelo de regresión XGBoost...")
    
    cols_excluir = ['SEQN', 'RIDAGEYR', 'IS_LONGEVO', 'CICLO_ORIGEN']
    feature_cols = [c for c in df.columns if c not in cols_excluir]
    
    X = df[feature_cols]
    y = df['RIDAGEYR']
    
    xgb_param_dist = {
        'n_estimators': [100, 200, 300, 500],
        'max_depth': [3, 5, 7, 10],
        'learning_rate': [0.01, 0.05, 0.1, 0.2],
        'subsample': [0.7, 0.8, 0.9, 1.0],
        'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
        'min_child_weight': [1, 3, 5],
    }
    
    xgb_search = RandomizedSearchCV(
        XGBRegressor(random_state=42, eval_metric='rmse'),
        param_distributions=xgb_param_dist,
        n_iter=30,
        scoring='neg_mean_absolute_error',
        cv=KFold(5, shuffle=True, random_state=42),
        random_state=42,
        n_jobs=-1
    )
    xgb_search.fit(X, y)
    
    print(f"Regresión - Mejores hiperparámetros: {xgb_search.best_params_}")
    print(f"Regresión - Mejor MAE (CV): {-xgb_search.best_score_:.2f} años")
    
    return xgb_search.best_estimator_