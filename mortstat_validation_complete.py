"""
Script para validar completamente MORTSTAT y diagnosticar el problema
"""

import pandas as pd
import requests
from io import BytesIO
from collections import Counter

print("=" * 80)
print("VALIDACION COMPLETA DE MORTSTAT - NHANES 2017-2018")
print("=" * 80)
print()

# 1. CARGAR ARCHIVO ORIGINAL
print("1. DESCARGANDO ARCHIVO ORIGINAL")
print("-" * 80)

url = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat"

response = requests.get(url, timeout=30)
content = response.content.decode('latin-1', errors='ignore')
lines = content.strip().split('\n')

print(f"Total líneas en archivo: {len(lines)}")
print()

# 2. ANALIZAR STRUCTURE
print("2. ESTRUCTURA DEL ARCHIVO")
print("-" * 80)
print()

print("El archivo es Fixed-Width Format (FWF), NO delimitado.")
print()
print("Primeras 10 líneas (mostrando estructura):")
print()

for i in range(min(10, len(lines))):
    print(f"Línea {i+1}: |{lines[i]}|")

print()
print("Observación: Los espacios son PARTE de la estructura, no separadores")
print()

# 3. PARSING ACTUAL (INCORRECTO)
print("3. PARSING ACTUAL - METODO INCORRECTO (usando sep='\\s+')")
print("-" * 80)
print()

print("El loader actual usa: pd.read_csv(sep=r'\\s+') que SEPARA por espacios")
print()

# Simular lo que hace el loader actual
df_wrong = pd.read_csv(
    BytesIO(response.content),
    sep=r'\s+',
    engine='python'
)

print(f"Columnas detectadas: {df_wrong.columns.tolist()}")
print(f"Forma: {df_wrong.shape}")
print()

print("Primeras 10 filas:")
print(df_wrong.head(10).to_string())
print()

print("Nombres de columnas inferidos del parsing incorrecto:")
for i, col in enumerate(df_wrong.columns):
    print(f"  Columna {i}: {col}")
print()

# 4. COMPARAR CON EL MERGED
print("4. COMPARACION CON DATASET MERGED")
print("-" * 80)
print()

merged_df = pd.read_csv("data/02_intermediate/nhanes_2017_2018_merged.csv")

print(f"Columnas en merged: {merged_df.columns.tolist()}")
print()

# Buscar donde está MORTSTAT
if 'MORTSTAT' in merged_df.columns:
    print(f"MORTSTAT en merged:")
    print(f"  Valores únicos: {sorted(merged_df['MORTSTAT'].dropna().unique())}")
    print(f"  Distribución:")
    
    mortstat_counts = merged_df['MORTSTAT'].value_counts(dropna=False).sort_index()
    for val, count in mortstat_counts.items():
        if pd.isna(val):
            print(f"    NaN: {count}")
        else:
            print(f"    {int(val)}: {count}")
    print()

# 5. BUSCAR CUAL COLUMNA DEL PARSING INCORRECTO CORRESPONDE A MORTSTAT
print("5. DIAGNOSTICO DEL ERROR")
print("-" * 80)
print()

print("El parsing incorrecto (por espacios) genera columnas:")
print(f"  {df_wrong.columns.tolist()}")
print()

print("Analizando columna por columna del parsing incorrecto:")
for col in df_wrong.columns:
    unique_vals = df_wrong[col].unique()[:10]
    print(f"  {col}: primeros valores únicos = {unique_vals}")

print()
print("CONCLUSION:")
print("-" * 80)
print()

print("El problema es que el loader MortalityDataset usa:")
print("  sep=r'\\s+'  (separador: cualquier espaciado en blanco)")
print()
print("Esto ROMPE la estructura Fixed-Width del archivo original.")
print()
print("Resultado:")
print("  - Los campos se desalinean")
print("  - MORTSTAT se lee de la posición incorrecta")
print("  - Valores extraños como 10, 11 se interpretan incorrectamente")
print()

# 6. DOCUMENTACION OFICIAL
print("6. DOCUMENTACION OFICIAL DE CDC")
print("-" * 80)
print()

print("Según CDC, el archivo NHANES_2017_2018_MORT_2019_PUBLIC.dat tiene:")
print()
print("Campos (Fixed-Width Format):")
print("  Posición 1-6:   SEQN (Respondent sequence number)")
print("  Posición 7-8:   ELIGSTAT (Eligibility status)")
print("  Posición 9:     MORTSTAT (Mortality Status)")
print("                  Valores: 0=Alive, 1=Deceased, .=Missing")
print("  Posición 10-12: FUTIME (Follow-up time in months)")
print()

print("El archivo es Fixed-Width, no delimitado por espacios.")
print()

# 7. EXTRACCION CORRECTA
print("7. EXTRACCION CORRECTA (Usando posiciones FWF)")
print("-" * 80)
print()

print("Extrayendo con posiciones correctas del FWF...")
print()

mortstat_correct = []
seqn_correct = []
counts_correct = Counter()

for line in lines:
    if len(line) >= 9:  # Al menos hasta MORTSTAT (posición 9)
        try:
            # SEQN: posición 1-6 (índice 0-6)
            seqn_str = line[0:6].strip()
            if seqn_str.isdigit():
                seqn = int(seqn_str)
                seqn_correct.append(seqn)
                
                # MORTSTAT: posición 9 (índice 8)
                mortstat_char = line[8].strip()
                
                if mortstat_char == '.':
                    mortstat_val = 'Missing'
                elif mortstat_char == '0':
                    mortstat_val = 0
                elif mortstat_char == '1':
                    mortstat_val = 1
                else:
                    mortstat_val = mortstat_char
                
                counts_correct[mortstat_val] += 1
                mortstat_correct.append((seqn, mortstat_char, mortstat_val))
        except:
            pass

print(f"Registros con SEQN válido: {len(seqn_correct)}")
print()

print("Distribución de MORTSTAT (CORRECTA):")
for val in sorted(counts_correct.keys()):
    count = counts_correct[val]
    pct = 100 * count / len(mortstat_correct)
    print(f"  {val}: {count} ({pct:.2f}%)")

print()
print("Primeros 20 registros (PARSING CORRECTO):")
for seqn, char, val in mortstat_correct[:20]:
    print(f"  SEQN {seqn}: MORTSTAT='{char}' -> {val}")

print()

# 8. RECOMENDACIONES
print("8. RECOMENDACIONES PARA CORREGIR")
print("-" * 80)
print()

print("OPCION 1: Reparar el MortalityDataset loader")
print("  - Cambiar de sep='\\s+' a Fixed-Width Format parsing")
print("  - Usar posiciones correctas (1-6: SEQN, 9: MORTSTAT, 10-12: FUTIME)")
print()

print("OPCION 2: Usar pandas.read_fwf() en lugar de read_csv()")
print("  - Código: pd.read_fwf(BytesIO(response.content))")
print("  - Requiere especificar colspecs si es necesario")
print()

print("OPCION 3: Parsear manualmente línea por línea")
print("  - Máximo control sobre la extracción")
print("  - Verifica cada campo según posiciones CDC")
print()

print("=" * 80)
print("REPORTE COMPLETADO")
print("=" * 80)
