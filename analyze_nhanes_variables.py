"""
Script para analizar el dataset NHANES 2017-2018 mergeado
Genera reporte con significado de códigos, distribuciones y conteos
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Cargar dataset
csv_path = "data/02_intermediate/nhanes_2017_2018_merged.csv"
print("Cargando dataset:", csv_path)
df = pd.read_csv(csv_path)

print(f"Dataset cargado: {df.shape[0]} registros, {df.shape[1]} columnas")
print()

# Diccionario de significados de variables NHANES
variable_meanings = {
    'SEQN': {
        'nombre': 'Respondent sequence number',
        'descripcion': 'Identificador único del participante',
        'codigos': 'Variable numérica continua'
    },
    'RIDAGEYR': {
        'nombre': 'Age in years at screening',
        'descripcion': 'Edad en años al momento del examen',
        'codigos': 'Variable numérica continua (años)',
        'rango': 'Típicamente 0-85+ años'
    },
    'RIAGENDR': {
        'nombre': 'Gender',
        'descripcion': 'Género/Sexo del participante',
        'codigos': {
            1: 'Hombre (Male)',
            2: 'Mujer (Female)'
        }
    },
    'BMXBMI': {
        'nombre': 'Body Mass Index',
        'descripcion': 'Índice de Masa Corporal (BMI)',
        'codigos': 'Variable numérica continua (kg/m2)',
        'rango': 'Típicamente 10-60 kg/m2'
    },
    'BPXSY1': {
        'nombre': 'Systolic blood pressure',
        'descripcion': 'Presión arterial sistólica (1er lectura)',
        'codigos': 'Variable numérica continua (mmHg)'
    },
    'BPXDI1': {
        'nombre': 'Diastolic blood pressure',
        'descripcion': 'Presión arterial diastólica (1er lectura)',
        'codigos': 'Variable numérica continua (mmHg)'
    },
    'DIQ010': {
        'nombre': 'Doctor told you have diabetes',
        'descripcion': 'Diagnostico de diabetes por médico',
        'codigos': {
            1: 'Sí (Yes)',
            2: 'No (No)',
            3: 'Borderline/Prediabetes (Borderline)',
            7: 'Rechazado (Refused)',
            9: 'No sabe (Don\'t know)',
            np.nan: 'Missing'
        }
    },
    'SMQ020': {
        'nombre': 'Do you now smoke cigarettes',
        'descripcion': 'Fuma actualmente cigarrillos',
        'codigos': {
            1: 'Sí (Yes)',
            2: 'No (No)',
            3: 'No aplica (Not applicable)',
            7: 'Rechazado (Refused)',
            9: 'No sabe (Don\'t know)',
            np.nan: 'Missing'
        }
    },
    'MORTSTAT': {
        'nombre': 'Mortality Status',
        'descripcion': 'Estado de mortalidad del participante',
        'codigos': {
            0: 'Vivo (Alive)',
            1: 'Fallecido (Deceased)',
            np.nan: 'Missing/No confirmado'
        }
    },
    'FUTIME': {
        'nombre': 'Follow-up time in months',
        'descripcion': 'Tiempo de seguimiento en meses desde baseline',
        'codigos': 'Variable numérica continua (meses)',
        'rango': 'Desde 0 hasta ~60+ meses'
    }
}

# Abrir archivo de salida
output_file = "variable_dictionary_report.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    
    # Encabezado
    f.write("=" * 80 + "\n")
    f.write("REPORTE DE ANÁLISIS DE VARIABLES NHANES 2017-2018\n")
    f.write("Dataset: nhanes_2017_2018_merged.csv\n")
    f.write("=" * 80 + "\n")
    f.write("\n")
    
    # Información general
    f.write("INFORMACION GENERAL DEL DATASET\n")
    f.write("-" * 80 + "\n")
    f.write(f"Total de registros: {df.shape[0]}\n")
    f.write(f"Total de variables: {df.shape[1]}\n")
    f.write(f"Columnas: {', '.join(df.columns.tolist())}\n")
    f.write("\n")
    
    # Analizar cada variable
    for col in df.columns:
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write(f"VARIABLE: {col}\n")
        f.write("=" * 80 + "\n")
        f.write("\n")
        
        # Información del diccionario
        if col in variable_meanings:
            info = variable_meanings[col]
            f.write(f"Nombre NHANES: {info.get('nombre', 'N/A')}\n")
            f.write(f"Descripcion: {info.get('descripcion', 'N/A')}\n")
            f.write("\n")
            
            # Significado de codigos
            f.write("SIGNIFICADO DE CODIGOS:\n")
            f.write("-" * 80 + "\n")
            
            codigos = info.get('codigos', {})
            if isinstance(codigos, str):
                f.write(f"  {codigos}\n")
            elif isinstance(codigos, dict):
                for code, meaning in codigos.items():
                    if pd.isna(code):
                        f.write(f"  NaN: {meaning}\n")
                    else:
                        f.write(f"  {code}: {meaning}\n")
            
            if 'rango' in info:
                f.write(f"\n  Rango típico: {info['rango']}\n")
        else:
            f.write("Información no disponible en diccionario\n")
        
        f.write("\n")
        
        # Tipo de dato y estadísticas básicas
        f.write("TIPO DE DATO:\n")
        f.write("-" * 80 + "\n")
        f.write(f"  {df[col].dtype}\n")
        f.write("\n")
        
        # Estadísticas según tipo
        if df[col].dtype in ['float64', 'int64']:
            f.write("ESTADISTICAS DESCRIPTIVAS:\n")
            f.write("-" * 80 + "\n")
            f.write(f"  Cuenta (no-nulls): {df[col].count()}\n")
            f.write(f"  Media: {df[col].mean():.4f}\n")
            f.write(f"  Mediana: {df[col].median():.4f}\n")
            f.write(f"  Desviacion estándar: {df[col].std():.4f}\n")
            f.write(f"  Minimo: {df[col].min():.4f}\n")
            f.write(f"  Máximo: {df[col].max():.4f}\n")
            f.write("\n")
        
        # Distribución de frecuencias
        f.write("DISTRIBUCION DE FRECUENCIAS:\n")
        f.write("-" * 80 + "\n")
        
        # Contar valores
        value_counts = df[col].value_counts(dropna=False).sort_index()
        
        f.write(f"{'Valor':<20} {'Frecuencia':<15} {'Porcentaje':<15} {'Significado'}\n")
        f.write("-" * 80 + "\n")
        
        for value, count in value_counts.items():
            percentage = (count / len(df)) * 100
            
            # Obtener significado
            significado = ""
            if col in variable_meanings:
                info = variable_meanings[col]
                codigos = info.get('codigos', {})
                if isinstance(codigos, dict):
                    if pd.isna(value):
                        significado = codigos.get(np.nan, "Missing/Unknown")
                    else:
                        significado = codigos.get(value, "Unknown")
            
            # Formato de valor
            if pd.isna(value):
                valor_str = "NaN (Missing)"
            else:
                valor_str = str(value)
            
            f.write(f"{valor_str:<20} {count:<15} {percentage:>6.2f}%       {significado}\n")
        
        f.write("\n")
        
        # Resumen de missing
        missing_count = df[col].isna().sum()
        missing_pct = (missing_count / len(df)) * 100
        f.write("RESUMEN DE VALORES FALTANTES:\n")
        f.write("-" * 80 + "\n")
        f.write(f"  Registros con valores válidos: {df[col].count()}\n")
        f.write(f"  Registros faltantes (NaN): {missing_count}\n")
        f.write(f"  Porcentaje faltante: {missing_pct:.2f}%\n")
        f.write("\n")
    
    # Sección de resumen de códigos especiales
    f.write("\n")
    f.write("=" * 80 + "\n")
    f.write("RESUMEN DE CODIGOS ESPECIALES NHANES\n")
    f.write("=" * 80 + "\n")
    f.write("\n")
    
    f.write("CODIGOS ESPECIALES ESTANDARIZADOS EN NHANES:\n")
    f.write("-" * 80 + "\n")
    f.write("\nEstos códigos se usan en múltiples variables:\n")
    f.write("  7: Rechazado (Refused) - Participante se negó a responder\n")
    f.write("  9: No sabe (Don't Know) - Participante no conoce la respuesta\n")
    f.write("  NaN/Missing: Valor no disponible (no aplicable, no preguntado, etc.)\n")
    f.write("\n")
    
    f.write("VARIABLES CON RESPUESTAS BINARIAS (Sí/No):\n")
    f.write("-" * 80 + "\n")
    f.write("  1 = Sí (Yes)\n")
    f.write("  2 = No (No)\n")
    f.write("  3 = Borderline/No aplica (variable específica)\n")
    f.write("  7 = Rechazado\n")
    f.write("  9 = No sabe\n")
    f.write("\n")
    
    # Sección de análisis específico para variables clave
    f.write("\n")
    f.write("=" * 80 + "\n")
    f.write("ANALISIS DETALLADO DE VARIABLES CLAVE\n")
    f.write("=" * 80 + "\n")
    
    # RIAGENDR
    f.write("\n")
    f.write("1. RIAGENDR (Género/Sexo)\n")
    f.write("-" * 80 + "\n")
    riagendr_counts = df['RIAGENDR'].value_counts().sort_index()
    for code, count in riagendr_counts.items():
        label = "Hombre" if code == 1 else "Mujer" if code == 2 else "Desconocido"
        pct = (count / len(df)) * 100
        f.write(f"  {int(code)} ({label}): {count} registros ({pct:.2f}%)\n")
    f.write(f"  Missing: {df['RIAGENDR'].isna().sum()}\n")
    f.write("\n")
    
    # DIQ010
    f.write("2. DIQ010 (Diagnostico de Diabetes)\n")
    f.write("-" * 80 + "\n")
    diq010_counts = df['DIQ010'].value_counts(dropna=False).sort_index()
    for code, count in diq010_counts.items():
        if pd.isna(code):
            label = "Missing"
        elif code == 1:
            label = "Sí (Doctor said yes)"
        elif code == 2:
            label = "No (Doctor said no)"
        elif code == 3:
            label = "Borderline/Prediabetes"
        elif code == 7:
            label = "Rechazado (Refused)"
        elif code == 9:
            label = "No sabe (Don't know)"
        else:
            label = "Desconocido"
        
        pct = (count / len(df)) * 100
        if pd.isna(code):
            f.write(f"  NaN ({label}): {count} registros ({pct:.2f}%)\n")
        else:
            f.write(f"  {int(code)} ({label}): {count} registros ({pct:.2f}%)\n")
    f.write("\n")
    
    # SMQ020
    f.write("3. SMQ020 (¿Fuma actualmente cigarrillos?)\n")
    f.write("-" * 80 + "\n")
    smq020_counts = df['SMQ020'].value_counts(dropna=False).sort_index()
    for code, count in smq020_counts.items():
        if pd.isna(code):
            label = "Missing"
        elif code == 1:
            label = "Sí (Now smokes)"
        elif code == 2:
            label = "No (Does not smoke)"
        elif code == 3:
            label = "No aplica (Not applicable)"
        elif code == 7:
            label = "Rechazado (Refused)"
        elif code == 9:
            label = "No sabe (Don't know)"
        else:
            label = "Desconocido"
        
        pct = (count / len(df)) * 100
        if pd.isna(code):
            f.write(f"  NaN ({label}): {count} registros ({pct:.2f}%)\n")
        else:
            f.write(f"  {int(code)} ({label}): {count} registros ({pct:.2f}%)\n")
    f.write("\n")
    
    # MORTSTAT
    f.write("4. MORTSTAT (Estado de Mortalidad)\n")
    f.write("-" * 80 + "\n")
    mortstat_counts = df['MORTSTAT'].value_counts(dropna=False).sort_index()
    for code, count in mortstat_counts.items():
        if pd.isna(code):
            label = "Missing/No confirmado"
        elif code == 0:
            label = "Vivo (Alive)"
        elif code == 1:
            label = "Fallecido (Deceased)"
        else:
            label = "Desconocido"
        
        pct = (count / len(df)) * 100
        if pd.isna(code):
            f.write(f"  NaN ({label}): {count} registros ({pct:.2f}%)\n")
        else:
            f.write(f"  {int(code)} ({label}): {count} registros ({pct:.2f}%)\n")
    f.write("\n")
    
    # Tabla resumen de conteos
    f.write("\n")
    f.write("=" * 80 + "\n")
    f.write("TABLA RESUMEN: REGISTROS POR CATEGORIA\n")
    f.write("=" * 80 + "\n")
    f.write("\n")
    
    f.write("GENERO (RIAGENDR):\n")
    f.write("-" * 80 + "\n")
    hombres = (df['RIAGENDR'] == 1).sum()
    mujeres = (df['RIAGENDR'] == 2).sum()
    f.write(f"  Hombres:        {hombres:>6} ({100*hombres/len(df):>6.2f}%)\n")
    f.write(f"  Mujeres:        {mujeres:>6} ({100*mujeres/len(df):>6.2f}%)\n")
    f.write(f"  Total válidos:  {hombres + mujeres:>6}\n")
    f.write("\n")
    
    f.write("DIABETES (DIQ010):\n")
    f.write("-" * 80 + "\n")
    diq_yes = (df['DIQ010'] == 1).sum()
    diq_no = (df['DIQ010'] == 2).sum()
    diq_border = (df['DIQ010'] == 3).sum()
    diq_refused = (df['DIQ010'] == 7).sum()
    diq_dontknow = (df['DIQ010'] == 9).sum()
    diq_missing = df['DIQ010'].isna().sum()
    
    f.write(f"  Sí (Diabético):        {diq_yes:>6} ({100*diq_yes/len(df):>6.2f}%)\n")
    f.write(f"  No (No diabético):     {diq_no:>6} ({100*diq_no/len(df):>6.2f}%)\n")
    f.write(f"  Borderline:            {diq_border:>6} ({100*diq_border/len(df):>6.2f}%)\n")
    f.write(f"  Rechazado:             {diq_refused:>6} ({100*diq_refused/len(df):>6.2f}%)\n")
    f.write(f"  No sabe:               {diq_dontknow:>6} ({100*diq_dontknow/len(df):>6.2f}%)\n")
    f.write(f"  Missing:               {diq_missing:>6} ({100*diq_missing/len(df):>6.2f}%)\n")
    f.write(f"  Total válidos:         {diq_yes + diq_no + diq_border:>6}\n")
    f.write("\n")
    
    f.write("FUMAR (SMQ020):\n")
    f.write("-" * 80 + "\n")
    smq_yes = (df['SMQ020'] == 1).sum()
    smq_no = (df['SMQ020'] == 2).sum()
    smq_na = (df['SMQ020'] == 3).sum()
    smq_refused = (df['SMQ020'] == 7).sum()
    smq_dontknow = (df['SMQ020'] == 9).sum()
    smq_missing = df['SMQ020'].isna().sum()
    
    f.write(f"  Sí (Fuma):             {smq_yes:>6} ({100*smq_yes/len(df):>6.2f}%)\n")
    f.write(f"  No (No fuma):          {smq_no:>6} ({100*smq_no/len(df):>6.2f}%)\n")
    f.write(f"  No aplica:             {smq_na:>6} ({100*smq_na/len(df):>6.2f}%)\n")
    f.write(f"  Rechazado:             {smq_refused:>6} ({100*smq_refused/len(df):>6.2f}%)\n")
    f.write(f"  No sabe:               {smq_dontknow:>6} ({100*smq_dontknow/len(df):>6.2f}%)\n")
    f.write(f"  Missing:               {smq_missing:>6} ({100*smq_missing/len(df):>6.2f}%)\n")
    f.write(f"  Total válidos:         {smq_yes + smq_no:>6}\n")
    f.write("\n")
    
    f.write("MORTALIDAD (MORTSTAT):\n")
    f.write("-" * 80 + "\n")
    mort_alive = (df['MORTSTAT'] == 0).sum()
    mort_deceased = (df['MORTSTAT'] == 1).sum()
    mort_missing = df['MORTSTAT'].isna().sum()
    
    f.write(f"  Vivo:                  {mort_alive:>6} ({100*mort_alive/len(df):>6.2f}%)\n")
    f.write(f"  Fallecido:             {mort_deceased:>6} ({100*mort_deceased/len(df):>6.2f}%)\n")
    f.write(f"  Missing:               {mort_missing:>6} ({100*mort_missing/len(df):>6.2f}%)\n")
    f.write(f"  Total válidos:         {mort_alive + mort_deceased:>6}\n")
    f.write("\n")
    
    # Notas finales
    f.write("\n")
    f.write("=" * 80 + "\n")
    f.write("NOTAS IMPORTANTES\n")
    f.write("=" * 80 + "\n")
    f.write("\n")
    f.write("1. VALORES ESPECIALES:\n")
    f.write("   - Rechazado (7): Participante se negó a responder\n")
    f.write("   - No sabe (9): Participante no sabe la respuesta\n")
    f.write("   - Missing (NaN): Valor no disponible o no aplicable\n")
    f.write("\n")
    f.write("2. VARIABLES CONTINUAS:\n")
    f.write("   - RIDAGEYR, BMXBMI, BPXSY1, BPXDI1, FUTIME son numéricas continuas\n")
    f.write("   - Se presentan sus estadísticas descriptivas en secciones individuales\n")
    f.write("\n")
    f.write("3. MORTALIDAD:\n")
    f.write("   - Alto porcentaje de missing es ESPERADO\n")
    f.write("   - Archivo publicado en 2019 con seguimiento limitado\n")
    f.write("   - Solo 12 fallecidos confirmados de 6,401 participantes (0.19%)\n")
    f.write("\n")
    f.write("4. PREPARACION PARA MODELADO:\n")
    f.write("   - Decidir cómo manejar valores especiales (7, 9)\n")
    f.write("   - Considerar clase_weight='balanced' por desbalance en MORTSTAT\n")
    f.write("   - Evaluar si excluir \"No aplica\" y otros valores especiales\n")
    f.write("\n")
    f.write("=" * 80 + "\n")
    f.write("FIN DEL REPORTE\n")
    f.write("=" * 80 + "\n")

print(f"\nReporte guardado en: {output_file}")
print("\nContenido del reporte generado con éxito.")
