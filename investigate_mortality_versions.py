"""
Script para investigar versiones disponibles del archivo de mortalidad enlazada
NHANES 2017-2018 de CDC
"""

import requests
from datetime import datetime
import re

print("=" * 80)
print("INVESTIGACION DE VERSIONES DE MORTALIDAD ENLAZADA NHANES 2017-2018")
print("=" * 80)
print()

# URLs base del CDC para mortalidad enlazada
base_url = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/"

# Archivos conocidos y potenciales a buscar
potential_files = [
    "NHANES_2017_2018_MORT_2019_PUBLIC.dat",  # Original
    "NHANES_2017_2018_MORT_2020_PUBLIC.dat",  # Posible actualizacion 2020
    "NHANES_2017_2018_MORT_2021_PUBLIC.dat",  # Posible actualizacion 2021
    "NHANES_2017_2018_MORT_2022_PUBLIC.dat",  # Posible actualizacion 2022
    "NHANES_2017_2018_MORT_2023_PUBLIC.dat",  # Posible actualizacion 2023
    "NHANES_2017_2018_MORT_2024_PUBLIC.dat",  # Posible actualizacion 2024
]

print("1. BUSCANDO VERSIONES DISPONIBLES")
print("=" * 80)
print()

available_versions = {}

for filename in potential_files:
    url = base_url + filename
    try:
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            # Obtener informacion del header
            size = response.headers.get('Content-Length', 'N/A')
            last_modified = response.headers.get('Last-Modified', 'N/A')
            
            available_versions[filename] = {
                'url': url,
                'status': 200,
                'size': int(size) if size != 'N/A' else 0,
                'last_modified': last_modified,
                'exists': True
            }
            
            print("[FOUND] " + filename)
            print("  URL: " + url)
            if size != 'N/A':
                print("  Tamanio: %.2f MB" % (int(size) / 1024 / 1024))
            else:
                print("  Tamanio: N/A")
            print("  Ultima modificacion: " + last_modified)
            print()
        else:
            available_versions[filename] = {
                'exists': False,
                'status': response.status_code
            }
    except Exception as e:
        available_versions[filename] = {
            'exists': False,
            'error': str(e)
        }
        print("[NOT FOUND] " + filename + " - Error: " + str(e)[:50])

print()
found_count = sum(1 for v in available_versions.values() if v.get('exists', False))
print("Total de versiones encontradas: " + str(found_count))
print()

# Filtrar solo las que existen
existing_versions = {k: v for k, v in available_versions.items() if v.get('exists', False)}

if not existing_versions:
    print("[WARNING] No se encontraron versiones adicionales")
    print("Usando la version conocida de 2019")
    existing_versions = {
        'NHANES_2017_2018_MORT_2019_PUBLIC.dat': {
            'url': 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat',
            'year': 2019,
            'exists': True
        }
    }

print()
print("2. ANALISIS DE VERSIONES ENCONTRADAS")
print("=" * 80)
print()

# Extraer ano de cada version
versioned_info = []
for filename, info in existing_versions.items():
    match = re.search(r'MORT_(\d{4})', filename)
    if match:
        year = int(match.group(1))
        versioned_info.append({
            'filename': filename,
            'year': year,
            'size': info.get('size', 0),
            'info': info
        })

# Ordenar por ano
versioned_info.sort(key=lambda x: x['year'])

print("Versiones disponibles (ordenadas por ano de publicacion):")
print()

for i, item in enumerate(versioned_info, 1):
    print(str(i) + ". " + item['filename'])
    print("   Publicacion: " + str(item['year']))
    if item['size'] > 0:
        print("   Tamanio: %.2f MB" % (item['size'] / 1024 / 1024))
    else:
        print("   Tamanio: N/A")
    print()

print()
print("3. VERSION MAS RECIENTE")
print("=" * 80)
print()

if versioned_info:
    latest = versioned_info[-1]
    print("Archivo: " + latest['filename'])
    print("Publicado: " + str(latest['year']))
    print("URL: " + latest['info']['url'])
    print()
else:
    print("[ERROR] No se pudieron identificar versiones")

print()
print("4. RECOMENDACION PARA MODELO DE PREDICCION DE SUPERVIVENCIA")
print("=" * 80)
print()

print("Para un modelo de prediccion de supervivencia (vida/muerte), se recomienda:")
print()
print("a) VERSION MAS RECIENTE DISPONIBLE:")
print("   - Proporciona el seguimiento mas extendido")
print("   - Maximiza el numero de eventos de muerte observados")
print("   - Mayor validez temporal en predicciones")
print()
print("b) CONSIDERACIONES ESPECIALES:")
print()
print("   VENTAJAS de usar la version MAS RECIENTE:")
print("   + Mayor numero de meses de seguimiento (hasta 5+ anos)")
print("   + Mas defunciones confirmadas (mas eventos para entrenar)")
print("   + Informacion mas completa y actualizada")
print("   + Mejor para modelos de supervivencia a largo plazo")
print()
print("   VENTAJAS de usar version 2019:")
print("   + Datos mas 'limpios' (revisor de calidad establecido)")
print("   + Seguimiento estandarizado inicial")
print("   + Mejor documentacion")
print()
print("c) SOLUCION OPTIMA:")
print()
print("   Para prediccion de SUPERVIVENCIA / MORTALIDAD:")
print("   [RECOMENDADO] Usar LA VERSION MAS RECIENTE disponible")
print("   Razon: Necesitas maximizar eventos de muerte para entrenar")
print("   Importante para: Modelos de riesgo proporcional, Survival Analysis")
print()
print("   Sugerencia adicional:")
print("   - Verificar con CDC que sea version FINAL no preliminar")
print("   - Confirmar completitud de seguimiento hasta fecha de corte")
print()
print("d) RAZON TECNICA:")
print("   - Modelos de supervivencia necesitan variabilidad en resultado")
print("   - Mas eventos = mejor estimacion de coeficientes")
print("   - Mas seguimiento = predicciones mas precisas a largo plazo")
print("   - Validacion temporal sobre datos mas recientes")
print()

print("=" * 80)
print("5. INFORMACION SOBRE FALLECIDOS POR VERSION")
print("=" * 80)
print()

# Intentar descargar y contar fallecidos en cada version
for item in versioned_info:
    filename = item['filename']
    url = item['info']['url']
    year = item['year']
    
    print("Analizando: " + filename + " (" + str(year) + ")")
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            content = response.content.decode('latin-1', errors='ignore')
            lines = content.strip().split('\n')
            
            # Contar fallecidos (MORTSTAT = 1)
            total_records = len(lines)
            deaths = 0
            alive = 0
            missing = 0
            
            for line in lines:
                if len(line) > 13:
                    mortstat_char = line[13:14].strip()
                    if mortstat_char == '1':
                        deaths += 1
                    elif mortstat_char == '0':
                        alive += 1
                    else:
                        missing += 1
            
            print("  Total registros: " + str(total_records))
            print("  Fallecidos (1): %d (%.2f%%)" % (deaths, 100*deaths/total_records if total_records > 0 else 0))
            print("  Vivos (0): %d (%.2f%%)" % (alive, 100*alive/total_records if total_records > 0 else 0))
            print("  Valores faltantes: %d (%.2f%%)" % (missing, 100*missing/total_records if total_records > 0 else 0))
            print()
            
        else:
            print("  [ERROR] Status: " + str(response.status_code))
            print()
            
    except Exception as e:
        print("  [ERROR] " + str(e)[:60])
        print()

print()
print("=" * 80)
print("6. RECOMENDACION FINAL")
print("=" * 80)
print()

if versioned_info:
    latest = versioned_info[-1]
    print()
    print("VERSION RECOMENDADA: " + latest['filename'] + " (Publicado " + str(latest['year']) + ")")
    print()
    print("JUSTIFICACION:")
    print("1. Es la version mas reciente disponible en CDC")
    print("2. Contiene seguimiento extendido (mayor tiempo de observacion)")
    print("3. Incluye mas eventos de muerte confirmados")
    print("4. Optima para modelos de prediccion de supervivencia/mortalidad")
    print()
    print("USO SUGERIDO:")
    print("- Primario: Usar esta version mas reciente")
    print("- Validacion: Comparar con version 2019 para verificar estabilidad")
    print()
    print("NOTA IMPORTANTE:")
    print("- Esta version corresponde a NHANES 2017-2018")
    print("- El seguimiento se extiende hasta el ano de publicacion (" + str(latest['year']) + ")")
    print("- Para actualizar el modelo, buscar versiones posteriores cuando esten disponibles")
    print()
else:
    print("No se pudieron determinar versiones")

print()
print("=" * 80)
print("INVESTIGACION COMPLETADA")
print("=" * 80)
