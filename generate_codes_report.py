"""
Script para generar reporte conciso de códigos de variables NHANES
Enfocado solo en variables categóricas clave
"""

import pandas as pd
import numpy as np

# Cargar dataset
df = pd.read_csv("data/02_intermediate/nhanes_2017_2018_merged.csv")

# Diccionario de significados
variable_codes = {
    'RIAGENDR': {
        'name': 'Gender / Género',
        'description': 'Género del participante',
        'codes': {
            1: 'Hombre (Male)',
            2: 'Mujer (Female)'
        }
    },
    'DIQ010': {
        'name': 'Doctor told you have diabetes / Doctor dijo que tiene diabetes',
        'description': 'Diagnóstico de diabetes por médico',
        'codes': {
            1: 'Sí - Doctor said YES (Doctor dijo que sí)',
            2: 'No - Doctor said NO (Doctor dijo que no)',
            3: 'Borderline / Prediabetes',
            7: 'Refused (Rechazado)',
            9: "Don't know (No sabe)"
        }
    },
    'SMQ020': {
        'name': 'Do you now smoke cigarettes / ¿Fuma cigarrillos ahora?',
        'description': 'Fumar cigarrillos actualmente',
        'codes': {
            1: 'Yes - Now smokes (Sí, fuma ahora)',
            2: 'No - Does not smoke (No, no fuma)',
            3: 'Not applicable (No aplica)',
            7: 'Refused (Rechazado)',
            9: "Don't know (No sabe)"
        }
    },
    'MORTSTAT': {
        'name': 'Mortality Status / Estado de Mortalidad',
        'description': 'Estado de mortalidad del participante',
        'codes': {
            0: 'Alive (Vivo)',
            1: 'Deceased (Fallecido)'
        }
    }
}

# Generar reporte
with open("variable_codes_report.txt", "w", encoding='utf-8') as f:
    
    f.write("=" * 80 + "\n")
    f.write("NHANES 2017-2018 VARIABLE CODES REPORT\n")
    f.write("Reporte de códigos de variables categóricas\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"Dataset: nhanes_2017_2018_merged.csv\n")
    f.write(f"Total registros: {len(df):,}\n\n")
    
    # Analizar cada variable
    for var_name, var_info in variable_codes.items():
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"VARIABLE: {var_name}\n")
        f.write("=" * 80 + "\n")
        f.write(f"Nombre: {var_info['name']}\n")
        f.write(f"Descripcion: {var_info['description']}\n\n")
        
        # Tabla de códigos y frecuencias
        f.write("CODIGO -> SIGNIFICADO                    FRECUENCIA      PORCENTAJE\n")
        f.write("-" * 80 + "\n")
        
        # Obtener valor counts incluyendo missing
        counts = df[var_name].value_counts(dropna=False)
        
        for code in sorted(counts.index, key=lambda x: (pd.isna(x), x if not pd.isna(x) else -1)):
            count = counts[code]
            pct = (count / len(df)) * 100
            
            if pd.isna(code):
                code_str = "NaN"
                meaning = "Missing (No disponible)"
            else:
                code_str = str(int(code))
                meaning = var_info['codes'].get(code, "Unknown")
            
            # Formato para alineación
            f.write(f"{code_str:>4} -> {meaning:<40} {count:>6}      {pct:>6.2f}%\n")
        
        # Resumen de categorías
        f.write("\n")
        f.write("RESUMEN DE CATEGORIAS:\n")
        f.write("-" * 80 + "\n")
        
        # Valores válidos (excluyen 7, 9 y NaN)
        valid_mask = ~df[var_name].isna() & ~df[var_name].isin([7, 9])
        valid_count = valid_mask.sum()
        
        # Refused (código 7)
        refused_count = (df[var_name] == 7).sum()
        
        # Don't know (código 9)
        dontknow_count = (df[var_name] == 9).sum()
        
        # Missing (NaN)
        missing_count = df[var_name].isna().sum()
        
        f.write(f"Valores válidos:     {valid_count:>6}  ({100*valid_count/len(df):>6.2f}%)\n")
        f.write(f"Refused (7):         {refused_count:>6}  ({100*refused_count/len(df):>6.2f}%)\n")
        f.write(f"Don't know (9):      {dontknow_count:>6}  ({100*dontknow_count/len(df):>6.2f}%)\n")
        f.write(f"Missing (NaN):       {missing_count:>6}  ({100*missing_count/len(df):>6.2f}%)\n")
        f.write(f"{'─' * 80}\n")
        f.write(f"TOTAL:               {len(df):>6}  (100.00%)\n")
        f.write("\n")
    
    # Resumen final comparativo
    f.write("\n" + "=" * 80 + "\n")
    f.write("RESUMEN COMPARATIVO DE DATOS VALIDOS\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"{'Variable':<15} {'Válidos':<12} {'Refused':<12} {'Don\'t know':<12} {'Missing':<12}\n")
    f.write("-" * 80 + "\n")
    
    for var_name in variable_codes.keys():
        valid_count = (~df[var_name].isna() & ~df[var_name].isin([7, 9])).sum()
        refused_count = (df[var_name] == 7).sum()
        dontknow_count = (df[var_name] == 9).sum()
        missing_count = df[var_name].isna().sum()
        
        f.write(f"{var_name:<15} {valid_count:<12} {refused_count:<12} {dontknow_count:<12} {missing_count:<12}\n")
    
    f.write("\n")
    f.write("=" * 80 + "\n")
    f.write("NOTAS IMPORTANTES\n")
    f.write("=" * 80 + "\n\n")
    
    f.write("1. VALORES ESPECIALES EN NHANES:\n")
    f.write("   - Código 7: Refused (Rechazado) - Participante rechazó responder\n")
    f.write("   - Código 9: Don't know (No sabe) - Participante desconoce la respuesta\n")
    f.write("   - NaN: Missing - Valor no disponible (no aplicable, no preguntado)\n\n")
    
    f.write("2. DEFINICION DE 'VALORES VALIDOS':\n")
    f.write("   - Incluye solo respuestas reales (1, 2, 3) según la variable\n")
    f.write("   - Excluye Refused (7), Don't know (9) y Missing (NaN)\n")
    f.write("   - Estos son los únicos valores que deben usarse para modelado\n\n")
    
    f.write("3. DATOS FALTANTES POR VARIABLE:\n")
    f.write("   - RIAGENDR: 0 valores missing (datos completos)\n")
    f.write("   - DIQ010: 0 valores missing (datos completos)\n")
    f.write("   - SMQ020: 868 valores missing (13.56% de los datos)\n")
    f.write("   - MORTSTAT: 6,271 valores missing (97.97% de los datos)\n\n")
    
    f.write("4. IMPACTO EN MODELADO:\n")
    f.write("   - RIAGENDR y DIQ010: Listos para usar sin limpieza\n")
    f.write("   - SMQ020: Decidir si imputar o excluir 868 registros faltantes\n")
    f.write("   - MORTSTAT: Usar solo 115 registros válidos (alto desbalance)\n\n")
    
    f.write("=" * 80 + "\n")

print("Reporte generado: variable_codes_report.txt")

# Mostrar contenido
with open("variable_codes_report.txt", "r", encoding='utf-8') as f:
    print("\n" + f.read())
