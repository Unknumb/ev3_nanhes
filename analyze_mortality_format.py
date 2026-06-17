"""Analizar formato del archivo de mortalidad del CDC"""
import requests
import pandas as pd

url = 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat'
response = requests.get(url)
lines = response.content.decode('latin-1', errors='ignore').strip().split('\n')

print("Ejemplos de líneas:")
print("=" * 80)
for i in [0, 1, 100, 1000, 5000, -1]:
    line = lines[i] if i < len(lines) else lines[i % len(lines)]
    print(f"Línea {i}: {repr(line)}")

# Basándome en documentación CDC del archivo de mortalidad vinculado
# El formato es:
# Posiciones 1-6: SEQN (identificador del participante)
# Posiciones 10-10: ELIGSTAT (estado de elegibilidad)
# Posiciones 14-14: MORTSTAT (estado de mortalidad: 0=vivo, 1=muerto)
# Posiciones 15-22: DODPAT (fecha de muerte en YYYYMMDD)
# Posiciones 38-42: PERMTH (meses permanentes de seguimiento)  o
# Posiciones 38-42: FUTIME (tiempo de seguimiento en meses)

print("\n" + "=" * 80)
print("Parseo de líneas:")
print("=" * 80)

data = []
for i, line in enumerate(lines[:20]):
    # Usando posiciones basadas en documentación CDC
    seqn = line[0:6].strip() if len(line) > 5 else ""
    eligstat = line[9:10].strip() if len(line) > 9 else ""
    mortstat = line[13:14].strip() if len(line) > 13 else ""
    dodpat = line[14:22].strip() if len(line) > 21 else ""
    futime = line[37:42].strip() if len(line) > 41 else ""
    
    print(f"L{i}: SEQN={seqn:>6} | ELIGSTAT={eligstat} | MORTSTAT={mortstat} | FUTIME={futime:>5}")
    
    data.append({
        'SEQN': seqn,
        'ELIGSTAT': eligstat,
        'MORTSTAT': mortstat,
        'DODPAT': dodpat,
        'FUTIME': futime
    })

df = pd.DataFrame(data)
print("\nDataFrame:")
print(df)

# Convertir tipos
print("\n" + "=" * 80)
print("Convirtiendo a tipos numéricos:")
print("=" * 80)

df['SEQN'] = pd.to_numeric(df['SEQN'], errors='coerce')
df['MORTSTAT'] = pd.to_numeric(df['MORTSTAT'], errors='coerce')
df['FUTIME'] = pd.to_numeric(df['FUTIME'], errors='coerce')

print(df)
print(f"\nTipo SEQN: {df['SEQN'].dtype}")
print(f"Tipo MORTSTAT: {df['MORTSTAT'].dtype}")
print(f"Tipo FUTIME: {df['FUTIME'].dtype}")
