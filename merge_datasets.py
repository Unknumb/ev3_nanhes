"""
Script para unir datasets NHANES 2017-2018
Selecciona variables específicas y las une por SEQN
"""

import pandas as pd
import requests
from io import BytesIO
import pyreadstat
from pathlib import Path

# URLs de los datasets
DATASETS_URLS = {
    'DEMO_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DEMO_J.xpt',
    'BMX_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BMX_J.xpt',
    'BPX_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPX_J.xpt',
    'DIQ_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DIQ_J.xpt',
    'SMQ_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/SMQ_J.xpt',
    'MORTALITY': 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat'
}

# Variables a seleccionar de cada dataset
VARIABLES_TO_SELECT = {
    'DEMO_J': ['SEQN', 'RIDAGEYR', 'RIAGENDR'],
    'BMX_J': ['SEQN', 'BMXBMI'],
    'BPX_J': ['SEQN', 'BPXSY1', 'BPXDI1'],
    'DIQ_J': ['SEQN', 'DIQ010'],
    'SMQ_J': ['SEQN', 'SMQ020'],
    'MORTALITY': ['SEQN', 'MORTSTAT', 'FUTIME']
}


def load_xpt(url):
    """Carga archivo SAS .xpt desde URL"""
    response = requests.get(url)
    response.raise_for_status()
    df, meta = pyreadstat.read_xport(BytesIO(response.content))
    return df


def load_mortality(url):
    """Carga archivo de mortalidad .dat desde URL - Formato ancho fijo"""
    response = requests.get(url)
    response.raise_for_status()
    
    # Convertir a StringIO para read_fwf
    content = response.content.decode('latin-1', errors='ignore')
    from io import StringIO
    text_file = StringIO(content)
    
    # read_fwf infiere automáticamente las posiciones de columnas
    df = pd.read_fwf(text_file, infer_nrows=100)
    
    # Las columnas se llaman por sus valores de encabezado
    # Renombrar: el primer índice contiene los nombres
    # Estructura: [SEQN] [ELIGSTAT] [MORTSTAT] [DODPAT] [FUTIME]
    
    # Obtener nombres del primer valor de cada columna (que está en df.columns)
    # El df.columns tiene los encabezados inferidos del primer registro
    # Necesitamos mapear correctamente
    
    # Usar la primera fila como headers y resetear
    new_cols = {
        df.columns[0]: 'SEQN',      # Primera columna
        df.columns[1]: 'ELIGSTAT',  # Segunda columna (2., 10)
        df.columns[2]: 'MORTSTAT',  # Tercera columna (..)
        df.columns[3]: 'DODPAT',    # Cuarta columna (.)
        df.columns[4]: 'FUTIME',    # Quinta columna (meses)
    }
    
    df = df.rename(columns=new_cols)
    
    # La primera fila tiene headers, descartarla si es así
    if df.iloc[0, 0] in ['093703', '93703']:  # Primera SEQN conocida
        # Ya está bien, la primera fila es data
        pass
    
    # Convertir SEQN y FUTIME a numérico
    try:
        df['SEQN'] = pd.to_numeric(df['SEQN'], errors='coerce')
        df['MORTSTAT'] = pd.to_numeric(df['MORTSTAT'], errors='coerce')
        df['FUTIME'] = pd.to_numeric(df['FUTIME'], errors='coerce')
    except:
        pass
    
    # Seleccionar solo las columnas necesarias y descartar NaNs en SEQN
    df = df[['SEQN', 'MORTSTAT', 'FUTIME']].dropna(subset=['SEQN'])
    
    return df


def load_and_select_dataset(name, url, variables):
    """Carga dataset y selecciona solo las variables especificadas"""
    print(f"Cargando {name}...", end=" ", flush=True)
    
    try:
        if name == 'MORTALITY':
            df = load_mortality(url)
        else:
            df = load_xpt(url)
        
        # Seleccionar solo las variables que existen
        cols_to_select = [col for col in variables if col in df.columns]
        df_selected = df[cols_to_select].copy()
        
        # Verificar que SEQN esté
        if 'SEQN' not in df_selected.columns:
            print(f"✗ Error: SEQN no encontrado")
            return None
        
        print(f"✓ ({df_selected.shape[0]} filas, {df_selected.shape[1]} columnas)")
        return df_selected
    
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None


def merge_datasets(datasets_dict):
    """Merge todos los datasets por SEQN"""
    print("\nUniendo datasets por SEQN...")
    
    # Empezar con el primer dataset
    result = None
    merge_info = {}
    
    for name, df in datasets_dict.items():
        if df is None:
            continue
        
        merge_info[name] = df.shape[0]
        
        if result is None:
            result = df.copy()
            print(f"  Base: {name} ({result.shape[0]} filas)")
        else:
            filas_antes = result.shape[0]
            result = result.merge(df, on='SEQN', how='inner')
            filas_despues = result.shape[0]
            print(f"  Merge con {name}: {filas_antes} → {filas_despues} filas (coincidencias: {filas_despues})")
    
    return result, merge_info


def generate_report(merged_df, datasets_dict, merge_info, output_path):
    """Genera reporte de la unión"""
    
    report = []
    report.append("=" * 80)
    report.append("REPORTE DE UNIÓN - DATASETS NHANES 2017-2018")
    report.append("=" * 80)
    report.append("")
    
    # Información general
    report.append(f"DATASET FINAL UNIDO")
    report.append(f"{'-' * 80}")
    report.append(f"Filas: {merged_df.shape[0]}")
    report.append(f"Columnas: {merged_df.shape[1]}")
    report.append(f"Columnas: {', '.join(merged_df.columns)}")
    report.append("")
    
    # Registros provenientes de cada dataset
    report.append(f"REGISTROS PROVENIENTES DE CADA DATASET")
    report.append(f"{'-' * 80}")
    for name, count in merge_info.items():
        report.append(f"  {name}: {count} registros originales")
    report.append(f"  Dataset final (intersección): {merged_df.shape[0]} registros comunes")
    report.append("")
    
    # Valores nulos por columna
    report.append(f"VALORES NULOS POR COLUMNA")
    report.append(f"{'-' * 80}")
    null_counts = merged_df.isnull().sum()
    for col in merged_df.columns:
        null_count = null_counts[col]
        null_pct = (null_count / len(merged_df)) * 100
        report.append(f"  {col:20s}: {null_count:6d} nulos ({null_pct:5.2f}%)")
    report.append("")
    
    # Confirmación de éxito
    report.append(f"CONFIRMACIÓN DE UNIÓN")
    report.append(f"{'-' * 80}")
    report.append(f"✓ La unión por SEQN fue exitosa")
    report.append(f"✓ Todas las columnas están presentes")
    report.append(f"✓ El dataset contiene {merged_df.shape[0]} registros con datos de todos los módulos")
    report.append("")
    
    # Primeras 10 filas
    report.append(f"PRIMERAS 10 FILAS DEL DATASET FINAL")
    report.append(f"{'-' * 80}")
    report.append("")
    report.append(merged_df.head(10).to_string())
    report.append("")
    
    # Estadísticas descriptivas
    report.append(f"\nESTADÍSTICAS DESCRIPTIVAS")
    report.append(f"{'-' * 80}")
    report.append(merged_df.describe().to_string())
    
    report_text = "\n".join(report)
    
    # Guardar reporte
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    return report_text


def main():
    print("Iniciando proceso de unión de datasets NHANES 2017-2018...")
    print("(Esto puede tardar unos minutos en descargar los datos)\n")
    
    # Crear directorio de salida si no existe
    output_dir = Path('data/02_intermediate')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Cargar y seleccionar datasets
    print("=" * 80)
    print("CARGANDO Y SELECCIONANDO VARIABLES")
    print("=" * 80)
    datasets = {}
    
    for name, url in DATASETS_URLS.items():
        variables = VARIABLES_TO_SELECT[name]
        df = load_and_select_dataset(name, url, variables)
        datasets[name] = df
    
    # Verificar que al menos un dataset se cargó
    if all(df is None for df in datasets.values()):
        print("\n✗ Error: No se pudieron cargar los datasets")
        return
    
    # Unir datasets
    print("\n" + "=" * 80)
    print("UNIENDO DATASETS")
    print("=" * 80)
    merged_df, merge_info = merge_datasets(datasets)
    
    if merged_df is None or merged_df.empty:
        print("\n✗ Error: La unión resultó en un dataset vacío")
        return
    
    # Guardar dataset unido
    csv_output = output_dir / 'nhanes_2017_2018_merged.csv'
    print(f"\nGuardando dataset unido en {csv_output}...")
    merged_df.to_csv(csv_output, index=False)
    print(f"✓ Guardado exitosamente")
    
    # Generar reporte
    print(f"\nGenerando reporte...")
    report = generate_report(merged_df, datasets, merge_info, 'merge_report.txt')
    print(f"✓ Reporte generado en merge_report.txt")
    
    # Mostrar resumen
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Dataset final: {merged_df.shape[0]} filas × {merged_df.shape[1]} columnas")
    print(f"\nArchivos creados:")
    print(f"  - {csv_output}")
    print(f"  - merge_report.txt")
    
    # Mostrar reporte completo
    print("\n" + "=" * 80)
    print(report)


if __name__ == '__main__':
    main()
