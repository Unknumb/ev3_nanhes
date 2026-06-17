"""Inspeccionar formato de mortalidad"""
import requests
from io import BytesIO
import pandas as pd

url = 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat'
response = requests.get(url)
lines = response.content.decode('latin-1', errors='ignore').strip().split('\n')

data = []
for i, line in enumerate(lines[:10]):
    print(f'Línea {i}: {repr(line[:50])}')
    row = {
        'SEQN': line[0:5].strip(),
        'ELIGSTAT': line[9:10].strip(),
        'MORTSTAT': line[13:14].strip(),
        'DODPAT': line[14:22].strip(),
        'FUTIME': line[37:42].strip(),
    }
    data.append(row)
    print(f'  SEQN={row["SEQN"]}, MORTSTAT={row["MORTSTAT"]}, FUTIME={row["FUTIME"]}')

# Crear dataframe
df = pd.DataFrame(data)
print('\nDatos parseados:')
print(df)
print(f'\nTipo de SEQN: {df["SEQN"].dtype}')
print(f'Primeros SEQN: {df["SEQN"].head().tolist()}')

# Convertir a numérico
df['SEQN'] = pd.to_numeric(df['SEQN'], errors='coerce')
print(f'\nDespués de conversión a numérico:')
print(f'Tipo: {df["SEQN"].dtype}')
print(f'Valores: {df["SEQN"].head().tolist()}')
