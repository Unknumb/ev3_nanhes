"""
Script detallado para analizar la estructura del archivo FWF de mortalidad
e identificar correctamente las posiciones de cada campo
"""

import requests
from io import BytesIO

print("=" * 80)
print("ANALISIS DETALLADO DE ESTRUCTURA DEL ARCHIVO MORTSTAT")
print("=" * 80)
print()

url = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat"

try:
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        content = response.content.decode('latin-1', errors='ignore')
        lines = content.strip().split('\n')
        
        print("1. ANALISIS DE PRIMERAS LINEAS")
        print("-" * 80)
        print()
        
        for i in range(min(15, len(lines))):
            line = lines[i]
            print(f"Línea {i+1} (len={len(line)}):")
            print(f"  Raw: |{line}|")
            print(f"  Hex: {line.encode('latin-1')}")
            print()
        
        print()
        print("2. IDENTIFICAR ESTRUCTURA FWF")
        print("-" * 80)
        print()
        
        # Analizar estructura de caracteres
        print("Analizando estructura de columnas...")
        print()
        
        # Tomar algunas líneas de ejemplo
        sample_lines = [lines[0], lines[2], lines[5], lines[100], lines[500]]
        
        print("Estructura identificada (mostrando posiciones):")
        print()
        
        # Imprimir una línea con indicadores de posición
        if len(lines) > 0:
            line = lines[2]  # Usar línea 3 como ejemplo
            print("Posiciones (0-indexed):")
            print("0123456789012345678901234567890123456789012345678")
            print(line)
            print()
            
        # Buscar patrones
        print("Análisis de contenido:")
        print()
        
        # Parece que hay campos separados por espacios
        # Veamos si podemos identificar campos
        
        for i, line in enumerate(sample_lines[:5]):
            print(f"Línea {i+1}: {line}")
            
            # Split por espacios múltiples
            fields = line.split()
            print(f"  Campos separados por espacios: {fields}")
            print()
        
        # 3. BUSCAR DOCUMENTACION
        print()
        print("3. ESTRUCTURA ESPERADA DE NHANES MORT")
        print("-" * 80)
        print()
        
        print("Campos esperados en archivo NHANES_2017_2018_MORT:")
        print()
        print("1. SEQN (Respondent sequence number)")
        print("   - Posición: Inicio del archivo")
        print("   - Tipo: Numérico")
        print("   - Largo: Típicamente 6 dígitos")
        print()
        print("2. MORTSTAT (Mortality Status)")
        print("   - Valores: 0 (Alive), 1 (Deceased), . (Missing)")
        print()
        print("3. FUTIME (Follow-up time in months)")
        print("   - Valores: Numéricos (0-60+)")
        print()
        
        # 4. INVESTIGAR REGISTROS ESPECIFICOS
        print()
        print("4. INVESTIGANDO REGISTROS ESPECIFICOS")
        print("-" * 80)
        print()
        
        # Buscar registros con SEQN conocido del merged
        import pandas as pd
        merged_df = pd.read_csv("data/02_intermediate/nhanes_2017_2018_merged.csv")
        
        # Tomar algunos SEQNs del merged
        sample_seqns = merged_df['SEQN'].head(10).tolist()
        
        print(f"Buscando SEQNs del dataset merged en archivo original...")
        print()
        
        for seqn in sample_seqns:
            seqn_str = str(int(seqn))
            for line in lines:
                if line.startswith(seqn_str):
                    print(f"SEQN {seqn_str}:")
                    print(f"  Línea completa: |{line}|")
                    
                    # Parsear la línea
                    fields = line.split()
                    print(f"  Campos: {fields}")
                    
                    # Mostrar byte por byte
                    print(f"  Posición 0-10: |{line[0:10]}|")
                    print(f"  Posición 10-20: |{line[10:20]}|")
                    print(f"  Posición 20-30: |{line[20:30]}|")
                    print(f"  Posición 30-40: |{line[30:40]}|")
                    print(f"  Posición 40-47: |{line[40:47]}|")
                    print()
                    break
        
        # 5. BUSCAR INFORMACION EN CDC
        print()
        print("5. INFORMACION DE CDC SOBRE FORMATO")
        print("-" * 80)
        print()
        
        print("El archivo NHANES Linked Mortality usa este formato (según CDC):")
        print()
        print("Posición 1-6:    SEQN (Respondent sequence number)")
        print("Posición 7-18:   Various fields (MORTSTAT should be here)")
        print("Posición 40-41:  MORTSTAT (Mortality Status)")
        print("Posición 42-44:  FUTIME (Follow-up time in months)")
        print()
        
        # Intentar extraer con posiciones correctas
        print()
        print("6. EXTRAYENDO CON POSICIONES CORREGIDAS")
        print("-" * 80)
        print()
        
        mortstat_values = []
        seqn_list = []
        
        for i, line in enumerate(lines):
            if len(line) >= 41:
                try:
                    # SEQN en posición 0-6 (pero necesita parsing)
                    seqn_part = line[0:6].strip()
                    if seqn_part.isdigit():
                        seqn = int(seqn_part)
                        seqn_list.append(seqn)
                        
                        # MORTSTAT en posición 40-41 (0-indexed: 39-40)
                        mortstat_char = line[39:40].strip()
                        if mortstat_char:
                            mortstat_values.append((seqn, mortstat_char))
                except:
                    pass
        
        print(f"Registros con SEQN: {len(seqn_list)}")
        print(f"Registros con MORTSTAT: {len(mortstat_values)}")
        print()
        
        if mortstat_values:
            print("Primeros 20 registros con MORTSTAT:")
            for seqn, mortstat in mortstat_values[:20]:
                print(f"  SEQN {seqn}: MORTSTAT = '{mortstat}'")
            print()
            
            print("Valores únicos de MORTSTAT:")
            unique_vals = set(m for s, m in mortstat_values)
            print(f"  {sorted(unique_vals)}")
            print()
            
            # Contar frecuencias
            from collections import Counter
            counts = Counter(m for s, m in mortstat_values)
            print("Distribución de MORTSTAT:")
            for val in sorted(counts.keys()):
                count = counts[val]
                pct = 100 * count / len(mortstat_values)
                print(f"  '{val}': {count} ({pct:.2f}%)")
        
    else:
        print(f"[ERROR] Status: {response.status_code}")
        
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
