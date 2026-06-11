import pandas as pd
import numpy as np

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