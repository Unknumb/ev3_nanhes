"""Leer archivo de mortalidad con read_fwf"""
import requests
from io import BytesIO, StringIO
import pandas as pd

url = 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat'
response = requests.get(url)
content = response.content.decode('latin-1', errors='ignore')

# Guardar en StringIO
text_file = StringIO(content)

# Usando read_fwf con posiciones específicas basadas en CDC
# El formato documenta que SEQN siempre está en posiciones 1-6 (indexado 0-5 en Python)
# Pero mirando los datos, parece que hay más columnas ocultas

# Intentar primero con infer_nrows
print("Intentando read_fwf con inferencia automática...")
text_file.seek(0)
try:
    df = pd.read_fwf(text_file, infer_nrows=100)
    print(f"Columnas inferidas: {df.columns.tolist()}")
    print(f"Shape: {df.shape}")
    print("\nPrimeras filas:")
    print(df.head(20))
except Exception as e:
    print(f"Error: {e}")

# Intentar manualmente
print("\n" + "=" * 80)
print("Parsing manual de líneas:")
print("=" * 80)

lines = content.strip().split('\n')
data = []

# Documentación CDC NHANES Linked Mortality File (2017-2018):
# Variable Name | Byte Position | Type | Values
# SEQN          | 1-6           | num  | 93703-102956
# (ELIGSTAT)    | 9-10          | char | (eligibility status code)
# (MORTSTAT)    | 14-14         | char | (1=death, 0=alive, .)=missing)
# (DODPAT)      | 15-22         | char | (date of death YYYYMMDD or ..)
# (PERMTH)      | 38-42         | num  | (months of follow-up)

for i, line in enumerate(lines[:20]):
    # Ajustar para indexing 0-based
    seqn_str = line[0:6].strip()
    eligstat_str = line[8:10].strip()
    mortstat_str = line[13:14].strip()
    dodpat_str = line[14:22].strip()
    futime_str = line[37:42].strip()
    
    # Limpieza
    seqn = int(seqn_str) if seqn_str.isdigit() else None
    mortstat = int(mortstat_str) if mortstat_str.isdigit() else None
    futime = int(futime_str) if futime_str.isdigit() else None
    
    data.append({
        'SEQN': seqn,
        'MORTSTAT': mortstat,
        'FUTIME': futime,
    })
    
    if i < 10:
        print(f"L{i}: Line={repr(line)}")
        print(f"     SEQN={seqn}, MORTSTAT={mortstat}, FUTIME={futime}")

df = pd.DataFrame(data)
print("\nDataFrame final:")
print(df.head(20))
print(f"\nTotal: {len(df)} registros")
print(f"\nUn icos SEQN: {df['SEQN'].nunique()}")
