"""
Análisis ultra-detallado de la estructura del archivo FWF de mortalidad
"""

import requests
from io import BytesIO

print("=" * 80)
print("ANALISIS ULTRA-DETALLADO DE ESTRUCTURA FWF")
print("=" * 80)
print()

url = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat"

response = requests.get(url, timeout=30)
content = response.content.decode('latin-1', errors='ignore')
lines = content.strip().split('\n')

print("1. EXAMINANDO ESTRUCTURA CARACTER POR CARACTER")
print("-" * 80)
print()

# Tomar 3 líneas de ejemplo
examples = [lines[0], lines[2], lines[4], lines[6]]

for ex_num, line in enumerate(examples):
    print(f"Línea {ex_num+1}: {line}")
    print(f"Longitud: {len(line)}")
    print()
    
    # Mostrar cada carácter con índice
    print("Posición (0-indexed) -> Carácter (hex)")
    for i, char in enumerate(line):
        if char == ' ':
            char_repr = 'SPACE'
        elif char == '.':
            char_repr = '.'
        else:
            char_repr = char
        
        print(f"  {i:2d} -> '{char_repr}' ({ord(char):02x})", end="")
        if (i + 1) % 5 == 0:
            print()
        else:
            print(" | ", end="")
    print()
    print()

print()
print("2. INTERPRETANDO ESTRUCTURA")
print("-" * 80)
print()

# Analizar primer línea en detalle
line1 = lines[0]
print(f"Primera línea: {line1}")
print()

print("Sectores identificados:")
print()

# Parece que hay campos visibles:
# '093703' + espacios + '2.' + espacios + '..' + espacios + '.' + espacios + '.'

fields_visual = []
current_field = ""
in_space = False

for i, char in enumerate(line1):
    if char == ' ':
        if not in_space and current_field:
            fields_visual.append((i, current_field))
            current_field = ""
        in_space = True
    else:
        if in_space:
            start = i
        in_space = False
        current_field += char

if current_field:
    fields_visual.append((i, current_field))

print("Campos detectados (por cambios espacio->no-espacio):")
for start, field in fields_visual:
    print(f"  Posición ~{start}: '{field}'")

print()
print("3. MAPEO A CAMPOS NHANES ESPERADOS")
print("-" * 80)
print()

print("Según CDC, estructura esperada:")
print("  Pos 1-6: SEQN (6 dígitos)")
print("  Pos 7-8: ELIGSTAT (2 caracteres)")
print("  Pos 9: MORTSTAT (1 carácter)")
print("  Pos 10-12: FUTIME (3 dígitos)")
print()

print("Pero mirando el archivo real, cada línea tiene:")
print("  - 6 dígitos: SEQN")
print("  - Espacios: padding")
print("  - 1-2 caracteres: MORTSTAT?")
print("  - Espacios: padding")
print("  - 2 caracteres: algo (quizás FUTIME?)")
print("  - Espacios: padding")
print("  - 1-2 caracteres")
print("  - Espacios: padding")
print("  - 1-2 caracteres")
print()

# 4. EXTRAER CAMPOS VISIBLES
print("4. EXTRAYENDO CAMPOS VISIBLES DEL ARCHIVO")
print("-" * 80)
print()

print("Extrayendo campos no-espaciados de cada línea...")
print()

all_fields_by_line = []

for line_num, line in enumerate(lines[:20]):
    fields = []
    current_field = ""
    
    for char in line:
        if char == ' ':
            if current_field:
                fields.append(current_field)
                current_field = ""
        else:
            current_field += char
    
    if current_field:
        fields.append(current_field)
    
    all_fields_by_line.append(fields)
    print(f"Línea {line_num+1}: {fields}")

print()

# 5. ANALIZAR PATRON
print("5. ANALIZAR PATRON DE CAMPOS")
print("-" * 80)
print()

# Campo por campo
for col_idx in range(5):  # Hasta 5 campos
    print(f"Campo #{col_idx + 1} en todas las líneas:")
    
    values_in_column = []
    for fields in all_fields_by_line:
        if col_idx < len(fields):
            values_in_column.append(fields[col_idx])
        else:
            values_in_column.append("MISSING")
    
    print(f"  Valores: {values_in_column}")
    print()

# 6. MAPA
print("6. CONCLUSION - MAPEO A NHANES")
print("-" * 80)
print()

print("CAMPO 1: Son los SEQN (6 dígitos)")
print("  Valores: 93703, 93704, 93705, etc.")
print("  Correspondencia: SEQN ✓")
print()

print("CAMPO 2: MORTSTAT?")
print("  Valores: '2.', '2.', '10', '10', '2.', '10', '10', '2.', '10', '10', etc.")
print("  Problema: '2.' y '10' no son valores válidos de MORTSTAT (0, 1, .)")
print()

print("POSIBLE EXPLICACION:")
print("  - La decodificación del archivo podría estar mal")
print("  - O el archivo tiene estructura diferente a la documentada")
print("  - O necesitamos usar colspecs específicas con read_fwf()")
print()

# 7. INTENTAR CON read_fwf
print("7. INTENTO CON read_fwf()")
print("-" * 80)
print()

import pandas as pd

print("Intentando pandas.read_fwf() con auto-detección de columnas...")
print()

try:
    df_fwf = pd.read_fwf(BytesIO(response.content), infer_nrows=100)
    print(f"Columnas detectadas: {df_fwf.columns.tolist()}")
    print(f"Shape: {df_fwf.shape}")
    print()
    print("Primeras filas:")
    print(df_fwf.head(15).to_string())
    print()
    
    # Ver valores únicos de cada columna
    print("Valores únicos por columna:")
    for col in df_fwf.columns:
        unique_vals = df_fwf[col].unique()[:10]
        print(f"  {col}: {unique_vals}")
    
except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 80)
