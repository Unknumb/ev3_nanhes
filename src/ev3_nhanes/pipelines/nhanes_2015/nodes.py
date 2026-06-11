import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────
# Constantes internas
# ──────────────────────────────────────────────────────────────────────

# Umbral para considerar a un paciente como "longevo" (≥ 70 años)
_EDAD_LONGEVO = 70

# Valor centinela que SAS XPT usa para representar missing values especiales.
# Pandas los lee como float ≈ 5.397605e-79 en vez de NaN.
_SAS_MISSING_SENTINEL = 5.397605346934028e-79

# ── URLs de las 7 tablas clínicas por ciclo NHANES ─────────────────
# Letra I = 2015-2016 (base), H = 2013-2014, G = 2011-2012
_BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"

_TABLAS = {
    "DEMO":  "Demografía (Edad, Género)",
    "BMX":   "Medidas Corporales (Peso, Altura, IMC)",
    "BPX":   "Presión Arterial",
    "TCHOL": "Colesterol Total",
    "GLU":   "Glucosa en Ayunas (Diabetes)",
    "MCQ":   "Condiciones Médicas Históricas",
    "SMQ":   "Hábitos de Fumador",
}

# Mapeo: letra de ciclo → año de publicación (necesario para la URL)
_CICLOS_HISTORICOS = {
    "H": {"anio": "2013", "label": "2013-2014"},
    "G": {"anio": "2011", "label": "2011-2012"},
    "F": {"anio": "2009", "label": "2009-2010"},
    "E": {"anio": "2007", "label": "2007-2008"},
}

_CICLO_BASE = {
    "letra": "I",
    "anio": "2015",
    "label": "2015-2016",
}


# ──────────────────────────────────────────────────────────────────────
# Funciones auxiliares (privadas)
# ──────────────────────────────────────────────────────────────────────

def _url_tabla(nombre_tabla: str, letra_ciclo: str, anio: str) -> str:
    """Construye la URL del archivo .xpt para una tabla y ciclo dados."""
    return f"{_BASE_URL}/{anio}/DataFiles/{nombre_tabla}_{letra_ciclo}.xpt"


def _corregir_missing_sas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reemplaza los missing values especiales de SAS (~5.397605e-79) por NaN.
    SAS XPT codifica ciertos tipos de missing (.A, .B, etc.) como valores
    float extremadamente pequeños que pandas no reconoce como NaN.
    """
    # Seleccionamos solo columnas numéricas para la corrección
    cols_num = df.select_dtypes(include=[np.number]).columns
    for col in cols_num:
        mask = np.isclose(df[col], _SAS_MISSING_SENTINEL, atol=1e-85)
        df.loc[mask, col] = np.nan
    return df


def _descargar_y_unir_ciclo(letra: str, anio: str, label: str) -> pd.DataFrame:
    """
    Descarga las 7 tablas de un ciclo NHANES y las une por SEQN.
    Aplica corrección de missing values de SAS.

    Parámetros
    ----------
    letra : str  –  Letra del ciclo (I, H, G …)
    anio  : str  –  Año de publicación (2015, 2013, 2011 …)
    label : str  –  Etiqueta legible ("2015-2016", "2013-2014" …)

    Retorna
    -------
    pd.DataFrame con todas las tablas unidas por SEQN.
    """
    print(f"\n{'='*60}")
    print(f"  Descargando ciclo {label} (Letra {letra})")
    print(f"{'='*60}")

    # 1. Descargar tabla base (DEMO)
    url_demo = _url_tabla("DEMO", letra, anio)
    print(f"  📥 Descargando DEMO_{letra} …")
    df_ciclo = pd.read_sas(url_demo)

    # 2. Descargar y unir el resto de tablas
    for nombre in _TABLAS:
        if nombre == "DEMO":
            continue
        url = _url_tabla(nombre, letra, anio)
        print(f"  📥 Descargando {nombre}_{letra} …")
        try:
            df_temp = pd.read_sas(url)
            df_ciclo = pd.merge(df_ciclo, df_temp, on="SEQN", how="outer")
        except Exception as e:
            print(f"  ⚠️  Error al descargar {nombre}_{letra}: {e}")

    # 3. Corregir missing values especiales de SAS → NaN
    df_ciclo = _corregir_missing_sas(df_ciclo)

    print(f"  ✅ Ciclo {label}: {df_ciclo.shape[0]:,} pacientes, "
          f"{df_ciclo.shape[1]} columnas descargadas.")

    return df_ciclo


# ──────────────────────────────────────────────────────────────────────
# Función pública (nodo Kedro)
# ──────────────────────────────────────────────────────────────────────

def descargar_y_unir_2015() -> pd.DataFrame:
    """
    Descarga los datos NHANES 2015-2016 y aplica **Data Augmentation**
    con los ciclos históricos 2013-2014 (H), 2011-2012 (G), 2009-2010 (F)
    y 2007-2008 (E) para resolver el desbalance de clases en la población
    de longevos (RIDAGEYR >= 70).

    Flujo
    -----
    1. **Ciclo Base completo** (I – 2015-2016): se descarga íntegramente
       (todos los pacientes, todas las edades).
    2. **Ciclos Históricos – Filtro de Rescate** (H, G, F, E): se descargan
       las mismas 7 tablas, pero se conservan **únicamente** los
       pacientes con RIDAGEYR >= 70 (longevos).
    3. **Concatenación vertical**: los registros longevos rescatados
       se apilan debajo del dataframe del ciclo base.
    4. **Control de calidad**: se aplica corrección de missing values
       de SAS, se alinean columnas, y se añade la columna
       ``CICLO_ORIGEN`` para trazabilidad.

    Retorna
    -------
    pd.DataFrame – Tabla maestra enriquecida lista para Notebook 02.
    """
    print("🚀 Iniciando descarga de NHANES 2015-2016 + Data Augmentation …\n")

    # ── PASO 1: Ciclo Base (2015-2016) completo ──────────────────────
    df_base = _descargar_y_unir_ciclo(
        _CICLO_BASE["letra"], _CICLO_BASE["anio"], _CICLO_BASE["label"]
    )
    df_base["CICLO_ORIGEN"] = _CICLO_BASE["label"]

    n_longevos_base = (df_base["RIDAGEYR"] >= _EDAD_LONGEVO).sum()
    n_total_base = df_base.shape[0]
    pct_base = (n_longevos_base / n_total_base * 100) if n_total_base else 0
    print(f"\n📊 Ciclo base {_CICLO_BASE['label']}:")
    print(f"   Total pacientes:  {n_total_base:,}")
    print(f"   Longevos (≥{_EDAD_LONGEVO}):  {n_longevos_base:,}  ({pct_base:.1f}%)")

    # ── PASO 2: Ciclos Históricos — Filtro de Rescate ────────────────
    frames_rescate = []

    for letra, info in _CICLOS_HISTORICOS.items():
        df_hist = _descargar_y_unir_ciclo(letra, info["anio"], info["label"])

        # Filtrar: conservar SOLO pacientes con RIDAGEYR >= 70
        # (primero descartamos filas sin RIDAGEYR para evitar falsos positivos)
        df_longevos = df_hist[
            df_hist["RIDAGEYR"].notna() & (df_hist["RIDAGEYR"] >= _EDAD_LONGEVO)
        ].copy()

        df_longevos["CICLO_ORIGEN"] = info["label"]

        n_rescatados = df_longevos.shape[0]
        n_hist_total = df_hist.shape[0]
        print(f"\n🔍 Filtro de rescate {info['label']}:")
        print(f"   Total del ciclo:   {n_hist_total:,}")
        print(f"   Longevos rescatados: {n_rescatados:,}")

        if n_rescatados > 0:
            frames_rescate.append(df_longevos)

    # ── PASO 3: Concatenación vertical ───────────────────────────────
    if frames_rescate:
        # Alinear columnas: usar solo las columnas presentes en el ciclo base
        # para evitar introducir variables que no existen en 2015-2016.
        columnas_base = set(df_base.columns)
        frames_alineados = []
        for df_r in frames_rescate:
            # Conservar solo columnas compartidas con el ciclo base
            cols_comunes = [c for c in df_base.columns if c in df_r.columns]
            df_alineado = df_r[cols_comunes].copy()
            frames_alineados.append(df_alineado)

        df_maestra = pd.concat(
            [df_base] + frames_alineados,
            axis=0,
            ignore_index=True,  # Reiniciar índice para evitar duplicados
        )
    else:
        print("\n⚠️  No se rescataron longevos de ciclos históricos.")
        df_maestra = df_base.copy()

    # ── PASO 4: Resumen final ────────────────────────────────────────
    n_total_final = df_maestra.shape[0]
    n_longevos_final = (
        df_maestra["RIDAGEYR"].notna() & (df_maestra["RIDAGEYR"] >= _EDAD_LONGEVO)
    ).sum()
    pct_final = (n_longevos_final / n_total_final * 100) if n_total_final else 0

    n_inyectados = n_longevos_final - n_longevos_base

    print(f"\n{'='*60}")
    print(f"  ✅ TABLA MAESTRA FINAL — Data Augmentation completado")
    print(f"{'='*60}")
    print(f"  📦 Pacientes totales:     {n_total_final:,}")
    print(f"  👴 Longevos (≥{_EDAD_LONGEVO}) totales: {n_longevos_final:,}  ({pct_final:.1f}%)")
    print(f"  💉 Longevos inyectados:   {n_inyectados:,}  (de ciclos H + G)")
    print(f"  📐 Columnas:              {df_maestra.shape[1]}")
    print(f"  🏷️  Ciclos presentes:      {df_maestra['CICLO_ORIGEN'].value_counts().to_dict()}")
    print(f"{'='*60}\n")

    return df_maestra