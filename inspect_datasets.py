"""
Script de inspección inicial de datasets NHANES 2017-2018
Analiza estructura, columnas e identifica campos clave
"""

import pandas as pd
import requests
from io import BytesIO
import pyreadstat

# URLs de los datasets
DATASETS = {
    'DEMO_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DEMO_J.xpt',
    'BMX_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BMX_J.xpt',
    'BPX_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPX_J.xpt',
    'DIQ_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DIQ_J.xpt',
    'SMQ_J': 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/SMQ_J.xpt',
    'MORTALITY': 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat'
}


def load_xpt(url):
    """Carga archivo SAS .xpt desde URL"""
    response = requests.get(url)
    response.raise_for_status()
    df, meta = pyreadstat.read_xport(BytesIO(response.content))
    return df


def load_mortality(url):
    """Carga archivo de mortalidad .dat desde URL con formato de ancho fijo"""
    response = requests.get(url)
    response.raise_for_status()
    
    # El archivo tiene formato de ancho fijo
    # Especificar manualmente las posiciones de columnas basándose en documentación CDC
    # Columnas: SEQN (9 chars), ELIGSTAT (1), MORTSTAT (1), DODPAT (8), DODPAT_DD (2), FUTIME (5)
    
    colspecs = [
        (0, 5),      # SEQN (ID del participante)
        (9, 10),     # ELIGSTAT (Eligibility status)
        (13, 14),    # MORTSTAT (Mortality status) - 0=vivo, 1=muerto
        (14, 22),    # DODPAT (Death date) - formato YYYYMMDD
        (37, 42),    # FUTIME (Months of follow-up) - meses de seguimiento
    ]
    
    # Leer como archivo de ancho fijo
    lines = response.content.decode('latin-1', errors='ignore').strip().split('\n')
    
    data = []
    for line in lines:
        row = {
            'SEQN': line[0:5].strip(),
            'ELIGSTAT': line[9:10].strip(),
            'MORTSTAT': line[13:14].strip(),
            'DODPAT': line[14:22].strip(),
            'FUTIME': line[37:42].strip(),
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Convertir a tipos apropiados
    for col in ['SEQN', 'ELIGSTAT', 'MORTSTAT', 'FUTIME']:
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        except:
            pass
    
    return df


def inspect_dataset(name, df):
    """Inspecciona un dataset y retorna información"""
    info = {
        'nombre': name,
        'filas': df.shape[0],
        'columnas_totales': df.shape[1],
        'columnas': list(df.columns),
        'tiene_seqn': 'SEQN' in df.columns,
        'primeras_filas': df.head(2)
    }
    return info


def generate_report(datasets_info):
    """Genera reporte en texto"""
    report = []
    report.append("=" * 80)
    report.append("INSPECCIÓN INICIAL - DATASETS NHANES 2017-2018")
    report.append("=" * 80)
    report.append("")
    
    for info in datasets_info:
        report.append(f"\n{'─' * 80}")
        report.append(f"DATASET: {info['nombre']}")
        report.append(f"{'─' * 80}")
        report.append(f"Filas: {info['filas']}")
        report.append(f"Columnas totales: {info['columnas_totales']}")
        report.append(f"Tiene SEQN: {info['tiene_seqn']}")
        report.append(f"\nLista de columnas:")
        for i, col in enumerate(info['columnas'], 1):
            report.append(f"  {i:2d}. {col}")
        
        # Identificar columnas candidatas según el dataset
        report.append(f"\nCandidatos identificados:")
        candidates = identify_candidates(info['nombre'], info['columnas'])
        for field, columns in candidates.items():
            report.append(f"  {field}: {', '.join(columns) if columns else 'No encontrado'}")
    
    return "\n".join(report)


def identify_candidates(dataset_name, columns):
    """Identifica columnas candidatas por dataset con reglas mejoradas"""
    candidates = {
        'Edad': [],
        'Sexo': [],
        'IMC': [],
        'Presión Arterial': [],
        'Diabetes': [],
        'Tabaquismo': [],
        'Estado Mortalidad': [],
        'Meses Seguimiento': []
    }
    
    columns_lower = [c.lower() for c in columns]
    
    for i, col in enumerate(columns):
        col_lower = col.lower()
        
        # Edad - solo términos específicos
        if col_lower in ['ridageyr', 'ridagemn'] or col_lower.startswith('age'):
            candidates['Edad'].append(col)
        
        # Sexo/Género - solo términos específicos
        if col_lower in ['riagendr', 'ridsex', 'sex', 'gender'] or col_lower.endswith('sex'):
            candidates['Sexo'].append(col)
        
        # IMC - solo el campo principal
        if col_lower in ['bmxbmi', 'bmi', 'imc'] or 'bmi' in col_lower:
            candidates['IMC'].append(col)
        
        # Presión Arterial - sistólica/diastólica/pulso
        if any(x in col_lower for x in ['bpxsy', 'bpxdi', 'systolic', 'diastolic', 'bpxpul']):
            candidates['Presión Arterial'].append(col)
        
        # Diabetes - campos DIQ principales
        if any(x in col_lower for x in ['diq010', 'diq160', 'diq170', 'diabetes']):
            candidates['Diabetes'].append(col)
        
        # Tabaquismo - campos SMQ principales
        if col_lower in ['smq020', 'smq040', 'smq078', 'smq621', 'smq661'] or 'smq' in col_lower[:3]:
            candidates['Tabaquismo'].append(col)
        
        # Estado Mortalidad
        if col_lower in ['mortstat', 'eligstat', 'dodpat', 'death', 'died']:
            candidates['Estado Mortalidad'].append(col)
        
        # Meses de Seguimiento
        if col_lower in ['futime', 'followup', 'months', 'permth', 'fumonth']:
            candidates['Meses Seguimiento'].append(col)
    
    return candidates


def main():
    print("Iniciando inspección de datasets NHANES 2017-2018...")
    print("(Esto puede tardar unos minutos en descargar los datos)\n")
    
    datasets_info = []
    
    # Cargar y inspeccionar cada dataset
    for name, url in DATASETS.items():
        try:
            print(f"Cargando {name}...", end=" ", flush=True)
            
            if name == 'MORTALITY':
                df = load_mortality(url)
            else:
                df = load_xpt(url)
            
            info = inspect_dataset(name, df)
            datasets_info.append(info)
            print(f"✓ ({df.shape[0]} filas, {df.shape[1]} columnas)")
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    # Generar reporte
    report = generate_report(datasets_info)
    
    # Guardar reporte
    output_path = 'docs/nhanes_inspection_report.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✓ Reporte guardado en: {output_path}")
    print("\n" + report)


if __name__ == '__main__':
    main()
