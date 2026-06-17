"""
Script para validar la variable MORTSTAT
Compara el archivo original con los datos después del merge
"""

import pandas as pd
import requests
from io import BytesIO
import numpy as np

print("=" * 80)
print("VALIDACION DE VARIABLE MORTSTAT - NHANES 2017-2018")
print("=" * 80)
print()

# 1. DESCARGAR Y PARSEAR ARCHIVO ORIGINAL
print("1. DESCARGANDO ARCHIVO ORIGINAL")
print("-" * 80)

url = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat"
print(f"URL: {url}")
print()

try:
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        print(f"[OK] Archivo descargado exitosamente")
        print(f"    Tamaño: {len(response.content) / 1024:.2f} KB")
        
        # Parsear como Fixed Width Format
        content = response.content.decode('latin-1', errors='ignore')
        lines = content.strip().split('\n')
        print(f"    Total líneas: {len(lines)}")
        print()
        
        # Analizar estructura
        print("2. ANALISIS DE ESTRUCTURA DEL ARCHIVO")
        print("-" * 80)
        
        if len(lines) > 0:
            sample_line = lines[0]
            print(f"Primera línea (sample): {sample_line}")
            print(f"Longitud: {len(sample_line)} caracteres")
            print()
            
            # Mostrar primeras 5 líneas
            print("Primeras 5 líneas del archivo:")
            for i, line in enumerate(lines[:5]):
                print(f"  {i+1}: {line}")
            print()
    else:
        print(f"[ERROR] No se pudo descargar el archivo. Status: {response.status_code}")
        lines = []
        
except Exception as e:
    print(f"[ERROR] {e}")
    lines = []

# 2. EXTRAER MORTSTAT DEL ARCHIVO ORIGINAL
if lines:
    print("3. EXTRAYENDO MORTSTAT DEL ARCHIVO ORIGINAL")
    print("-" * 80)
    
    # Según la documentación FWF de CDC, MORTSTAT está en posición específica
    # Necesitamos identificar la posición correcta
    
    mortstat_values = []
    seqn_values = []
    
    for line_num, line in enumerate(lines):
        if len(line) >= 20:
            # SEQN está típicamente en las primeras posiciones (1-6)
            # MORTSTAT está típicamente en posición 13 (1-indexed) o 12 (0-indexed)
            
            try:
                seqn_str = line[0:6].strip()
                if seqn_str:
                    seqn = int(seqn_str)
                    seqn_values.append(seqn)
                    
                    # Probar diferentes posiciones para MORTSTAT
                    # Posición 13-13 (1-indexed) = índice 12
                    if len(line) > 12:
                        mortstat_char = line[12].strip()
                        if mortstat_char:
                            try:
                                mortstat = int(mortstat_char)
                                mortstat_values.append(mortstat)
                            except:
                                mortstat_values.append(mortstat_char)
            except:
                pass
    
    print(f"Registros extraídos: {len(mortstat_values)}")
    print(f"SEQN válidos: {len(seqn_values)}")
    print()
    
    # 3. VALORES UNICOS DE MORTSTAT EN ARCHIVO ORIGINAL
    print("4. VALORES UNICOS DE MORTSTAT EN ARCHIVO ORIGINAL")
    print("-" * 80)
    
    unique_mortstat = pd.Series(mortstat_values).value_counts().sort_index()
    
    print(f"Total de valores únicos: {len(unique_mortstat)}")
    print()
    print("Valor | Frecuencia | Porcentaje")
    print("-" * 80)
    
    total_records = len(mortstat_values)
    for value, count in unique_mortstat.items():
        pct = (count / total_records) * 100 if total_records > 0 else 0
        print(f" {value:<5} | {count:>10} | {pct:>6.2f}%")
    
    print()
    
else:
    print("[ERROR] No se pudo procesar el archivo original")

# 4. CARGAR DATOS POST-MERGE
print("5. DATOS DE MORTSTAT DESPUES DEL MERGE")
print("-" * 80)

merged_df = pd.read_csv("data/02_intermediate/nhanes_2017_2018_merged.csv")

print(f"Total registros en merged: {len(merged_df)}")
print()

merged_mortstat_counts = merged_df['MORTSTAT'].value_counts(dropna=False).sort_index()

print("Valor | Frecuencia | Porcentaje")
print("-" * 80)

for value, count in merged_mortstat_counts.items():
    pct = (count / len(merged_df)) * 100
    if pd.isna(value):
        print(f" NaN  | {count:>10} | {pct:>6.2f}%")
    else:
        print(f" {int(value):<5} | {count:>10} | {pct:>6.2f}%")

print()

# 5. COMPARACION
print("6. COMPARACION: ORIGINAL vs POST-MERGE")
print("-" * 80)
print()

if len(mortstat_values) > 0:
    original_total = len(mortstat_values)
    merged_total = len(merged_df)
    
    print(f"Registros en archivo original:    {original_total:,}")
    print(f"Registros en dataset merged:      {merged_total:,}")
    print(f"Diferencia (pérdida):              {original_total - merged_total:,} ({100*(original_total-merged_total)/original_total:.2f}%)")
    print()
    
    print("Valores únicos en ORIGINAL:")
    original_values = set(pd.Series(mortstat_values).dropna().unique())
    print(f"  {sorted(original_values)}")
    print()
    
    print("Valores únicos en POST-MERGE:")
    post_merge_values = set(merged_df['MORTSTAT'].dropna().unique())
    print(f"  {sorted(post_merge_values)}")
    print()
    
    print("Valores nuevos introducidos en merge:")
    new_values = post_merge_values - original_values
    if new_values:
        print(f"  {sorted(new_values)}")
    else:
        print(f"  Ninguno (sin cambios)")
    print()
    
    print("Valores perdidos después del merge:")
    lost_values = original_values - post_merge_values
    if lost_values:
        print(f"  {sorted(lost_values)}")
    else:
        print(f"  Ninguno (sin cambios)")
    print()

# 6. DOCUMENTACION OFICIAL NHANES
print("7. SIGNIFICADO DE CODIGOS MORTSTAT (NHANES Official)")
print("-" * 80)
print()

mortstat_meaning = {
    0: "Alive (Vivo)",
    1: "Deceased (Fallecido)",
    '.': "Missing/Not applicable (Faltante/No aplica)"
}

print("Según documentación oficial CDC NHANES:")
print()
for code, meaning in mortstat_meaning.items():
    print(f"  {code}: {meaning}")

print()
print("NOTAS SOBRE CODIGOS NO ESPERADOS:")
print("-" * 80)
print()
print("En el dataset encontramos códigos 10 y 11 que NO están en la documentación oficial.")
print("Posibles explicaciones:")
print()
print("1. ERRORES DE PARSING:")
print("   - El archivo FWF podría no estar siendo parseado correctamente")
print("   - Las posiciones de caracteres podrían estar mal identificadas")
print()
print("2. CARACTERES ESPECIALES:")
print("   - Códigos 10 y 11 podrían ser artefactos de la decodificación")
print("   - Posibles caracteres de control o espacios mal interpretados")
print()
print("3. FUSION/MERGE INCORRECTO:")
print("   - Los registros podrían no corresponder a MORTSTAT")
print("   - Otro campo podría estar siendo interpretado como MORTSTAT")
print()

# 8. RECOMENDACIONES
print("8. RECOMENDACIONES Y PROXIMOS PASOS")
print("-" * 80)
print()

print("ACCIONES NECESARIAS:")
print()
print("1. REVISAR POSICIONES DEL ARCHIVO FWF:")
print("   - Confirmar exactamente en qué posiciones están SEQN y MORTSTAT")
print("   - Descargar especificaciones oficiales de CDC para NHANES_2017_2018_MORT")
print()
print("2. REINTENTAR PARSING:")
print("   - Usar las posiciones correctas del FWF")
print("   - Validar que cada campo se lee correctamente")
print()
print("3. VALIDAR MERGE:")
print("   - Verificar que el merge en 'SEQN' sea correcto")
print("   - Asegurar que no hay duplicados introducidos")
print()
print("4. LIMPIAR MORTSTAT:")
print("   - Excluir/reinterpretar códigos 10, 11")
print("   - Dejar solo: 0 (Alive), 1 (Deceased), NaN (Missing)")
print()

print("=" * 80)
print("VALIDACION COMPLETADA")
print("=" * 80)
