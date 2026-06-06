import pandas as pd

def descargar_y_unir_2015() -> pd.DataFrame:
    """
    Descarga los archivos .XPT de la CDC para 2015-2016 (Ciclo I)
    y los une usando el Sequence Number (SEQN).
    """
    print("Iniciando descarga de NHANES 2015-2016...")
    
    # URLs exactas de la CDC para el ciclo "I" (2015-2016)
    url_demo = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/DEMO_I.xpt"
    url_bpx = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/BPX_I.xpt"  # Presión Arterial
    
    # 1. Descargar Demografía (La tabla principal)
    print("Descargando datos demográficos (DEMO_I)...")
    df_demo = pd.read_sas(url_demo)
    
    # 2. Descargar Presión Arterial
    print("Descargando datos de presión arterial (BPX_I)...")
    df_bpx = pd.read_sas(url_bpx)
    
    # 3. Unir (Merge) ambas tablas por la columna SEQN (ID del paciente)
    print("Cruzando tablas por SEQN...")
    df_maestra = pd.merge(df_demo, df_bpx, on='SEQN', how='outer')
    
    print(f"¡Éxito! Tabla maestra creada con {df_maestra.shape[0]} pacientes y {df_maestra.shape[1]} columnas.")
    
    return df_maestra