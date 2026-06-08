import pandas as pd

def descargar_y_unir_2015() -> pd.DataFrame:
    """
    Descarga los archivos clave de NHANES para predecir la Edad Biológica / Longevidad
    (Ciclo 2015-2016) y los une usando el Sequence Number (SEQN).
    """
    print("Iniciando descarga de NHANES 2015-2016...")
    
    # Diccionario con las URLs oficiales actualizadas. 
    # Solo seleccionamos variables vitales para predecir salud a largo plazo.
    tablas_urls = {
        "DEMO": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/DEMO_I.xpt",  # 1. Demografía (Edad, Género)
        "BMX":  "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/BMX_I.xpt",   # 2. Medidas Corporales (Peso, Altura, IMC)
        "BPX":  "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/BPX_I.xpt",   # 3. Presión Arterial
        "TCHOL":"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/TCHOL_I.xpt", # 4. Colesterol Total
        "GLU":  "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/GLU_I.xpt",   # 5. Glucosa en Ayunas (Diabetes)
        "MCQ":  "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/MCQ_I.xpt",   # 6. Condiciones Médicas Históricas
        "SMQ":  "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/SMQ_I.xpt"    # 7. Hábitos de Fumador
    }
    
    # 1. Descargar Demografía (La tabla principal a la que se unen las demás)
    print("Descargando Tabla Base (DEMO)...")
    df_maestra = pd.read_sas(tablas_urls["DEMO"])
    
    # 2. Iterar sobre el resto de las tablas, descargarlas y unirlas automáticamente
    for nombre, url in tablas_urls.items():
        if nombre == "DEMO":
            continue # Saltamos DEMO porque ya la descargamos arriba
            
        print(f"Descargando e integrando {nombre}...")
        try:
            df_temp = pd.read_sas(url)
            # Unimos (Merge) usando Outer Join por SEQN para no perder ningún paciente
            df_maestra = pd.merge(df_maestra, df_temp, on='SEQN', how='outer')
        except Exception as e:
            print(f"Error al descargar {nombre}: {e}")
            
    print("-" * 50)
    print(f"¡Éxito! Tabla maestra final creada con {df_maestra.shape[0]} pacientes y {df_maestra.shape[1]} columnas.")
    print("-" * 50)
    
    return df_maestra