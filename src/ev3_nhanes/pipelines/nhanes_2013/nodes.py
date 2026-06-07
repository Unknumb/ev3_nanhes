# src/ev3_nhanes/pipelines/nhanes_2013/nodes.py
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyreadstat

logger = logging.getLogger(__name__)

BASE_DIR = Path("data/01_raw/nhanes_2013_2014")


def download_xpt(name: str) -> pd.DataFrame:
    path = BASE_DIR / f"{name.upper()}_H.XPT"

    if not path.exists():
        raise FileNotFoundError(
            f"Archivo no encontrado: {path}\n"
            f"Descarga el archivo manualmente y guárdalo en: {BASE_DIR}"
        )

    df, _ = pyreadstat.read_xport(str(path))
    logger.info("%s: %s filas, %s columnas", name.upper(), df.shape[0], df.shape[1])

    if "SEQN" in df.columns:
        df["SEQN"] = pd.to_numeric(df["SEQN"], errors="coerce").astype("Int64")

    return df


def download_demo() -> pd.DataFrame:
    return download_xpt("demo")


def download_biopro() -> pd.DataFrame:
    return download_xpt("biopro")


def download_bmx() -> pd.DataFrame:
    return download_xpt("bmx")


def download_bpx() -> pd.DataFrame:
    return download_xpt("bpx")


def download_smq() -> pd.DataFrame:
    return download_xpt("smq")


def load_mortality() -> pd.DataFrame:
    path = BASE_DIR / "NHANES_2013_2014_MORT_2019_PUBLIC.dat"

    if not path.exists():
        raise FileNotFoundError(
            f"Archivo de mortalidad no encontrado: {path}\n"
            f"Descarga el archivo manualmente y guárdalo en: {BASE_DIR}"
        )

    cols = [
        ("publicid", (0, 14)),
        ("eligstat", (14, 15)),
        ("mortstat", (15, 16)),
        ("ucod_leading", (16, 19)),
        ("diabetes", (19, 20)),
        ("hyperten", (20, 21)),
        ("permth_int", (42, 45)),
        ("permth_exm", (45, 48)),
    ]

    mortality = pd.read_fwf(
        path,
        colspecs=[c[1] for c in cols],
        names=[c[0] for c in cols],
        dtype=str,
    )

    mortality["SEQN"] = pd.to_numeric(
        mortality["publicid"].str.strip(), errors="coerce"
    ).astype("Int64")
    mortality["eligstat"] = mortality["eligstat"].astype(str).str.strip()
    mortality["mortstat"] = pd.to_numeric(mortality["mortstat"], errors="coerce")
    mortality["permth_int"] = pd.to_numeric(mortality["permth_int"], errors="coerce")
    mortality["permth_exm"] = pd.to_numeric(mortality["permth_exm"], errors="coerce")

    mortality = mortality[mortality["eligstat"] == "1"].copy()
    mortality = mortality.dropna(subset=["SEQN", "mortstat", "permth_int"])

    logger.info("Mortalidad: %s participantes elegibles", len(mortality))
    logger.info(
        "Tasa de mortalidad observada: %.2f%%",
        mortality["mortstat"].mean() * 100,
    )

    return mortality


def _prepare_module(
    df: pd.DataFrame,
    key: str = "SEQN",
    keep: list[str] | None = None,
) -> pd.DataFrame:
    df = df.copy()

    if key not in df.columns:
        raise KeyError(f"La columna clave '{key}' no existe en el dataframe.")

    df[key] = pd.to_numeric(df[key], errors="coerce").astype("Int64")
    df = df.dropna(subset=[key]).copy()
    df = df.drop_duplicates(subset=[key]).copy()

    if keep is not None:
        cols = [c for c in keep if c in df.columns]
        if key not in cols:
            cols = [key] + cols
        df = df.loc[:, list(dict.fromkeys(cols))].copy()

    return df


def merge_datasets(
    demo: pd.DataFrame,
    biopro: pd.DataFrame,
    bmx: pd.DataFrame,
    bpx: pd.DataFrame,
    smq: pd.DataFrame,
    mortality: pd.DataFrame,
) -> pd.DataFrame:
    """Une módulos NHANES y mortalidad por SEQN."""
    demo_keep = ["SEQN", "RIDAGEYR", "RIAGENDR"]
    biopro_keep = ["SEQN", "LBXSCR"]
    bmx_keep = ["SEQN", "BMXBMI"]
    bpx_keep = ["SEQN", "BPXSY1", "BPXDI1"]
    smq_keep = ["SEQN", "SMQ020"]
    mortality_keep = ["SEQN", "mortstat", "permth_int", "permth_exm", "ucod_leading"]

    demo = _prepare_module(demo, keep=demo_keep)
    biopro = _prepare_module(biopro, keep=biopro_keep)
    bmx = _prepare_module(bmx, keep=bmx_keep)
    bpx = _prepare_module(bpx, keep=bpx_keep)
    smq = _prepare_module(smq, keep=smq_keep)
    mortality = _prepare_module(mortality, keep=mortality_keep)

    merged = demo.merge(biopro, on="SEQN", how="inner", validate="one_to_one")
    merged = merged.merge(bmx, on="SEQN", how="left", validate="one_to_one")
    merged = merged.merge(bpx, on="SEQN", how="left", validate="one_to_one")
    merged = merged.merge(smq, on="SEQN", how="left", validate="one_to_one")
    merged = merged.merge(mortality, on="SEQN", how="inner", validate="one_to_one")

    merged = merged.loc[:, ~merged.columns.duplicated()].copy()

    logger.info(
        "Dataset final mergeado: %s participantes, %s columnas",
        merged.shape[0],
        merged.shape[1],
    )
    logger.info("Columnas merged (primeras 40): %s", list(merged.columns)[:40])
    logger.info("RIDAGEYR presente?: %s", "RIDAGEYR" in merged.columns)

    return merged


def engineer_features(
    df: pd.DataFrame,
    demographic_features: list,
    lab_features: list,
    duration_col: str,
    event_col: str,
) -> pd.DataFrame:
    """Feature engineering para predicción de supervivencia."""
    df = df.copy()

    rename_map = {}
    if "permth_int_mort" in df.columns and duration_col not in df.columns:
        rename_map["permth_int_mort"] = duration_col
    if "mortstat_mort" in df.columns and event_col not in df.columns:
        rename_map["mortstat_mort"] = event_col
    if rename_map:
        df = df.rename(columns=rename_map)

    if "RIAGENDR" in df.columns:
        sex = pd.to_numeric(df["RIAGENDR"], errors="coerce")
        df["is_female"] = sex.eq(2).astype("int8")

    if {"LBXSCR", "RIDAGEYR", "is_female"}.issubset(df.columns):
        creatinine = pd.to_numeric(df["LBXSCR"], errors="coerce")
        age = pd.to_numeric(df["RIDAGEYR"], errors="coerce")
        df["egfr"] = np.where(
            df["is_female"].eq(1),
            186 * (creatinine ** -1.154) * (age ** -0.203) * 0.742,
            186 * (creatinine ** -1.154) * (age ** -0.203),
        )

    if "BMXBMI" in df.columns:
        df["bmi"] = pd.to_numeric(df["BMXBMI"], errors="coerce")

    if {"BPXSY1", "BPXDI1"}.issubset(df.columns):
        systolic = pd.to_numeric(df["BPXSY1"], errors="coerce")
        diastolic = pd.to_numeric(df["BPXDI1"], errors="coerce")
        df["map"] = diastolic + (systolic - diastolic) / 3

    if "SMQ020" in df.columns:
        smoking = pd.to_numeric(df["SMQ020"], errors="coerce")
        df["ever_smoked"] = smoking.eq(1).astype("int8")

    base_features = list(dict.fromkeys(list(demographic_features) + list(lab_features)))
    engineered_features = ["is_female", "egfr", "bmi", "map", "ever_smoked"]

    requested = base_features + engineered_features + [duration_col, event_col]
    keep_cols = [c for c in requested if c in df.columns]

    result = df.loc[:, keep_cols].copy()
    result = result.loc[:, ~result.columns.duplicated()].copy()

    numeric_cols = [c for c in result.columns if c != event_col]
    result[numeric_cols] = result[numeric_cols].apply(pd.to_numeric, errors="coerce")

    result = result.dropna(subset=[duration_col, event_col]).copy()
    result[event_col] = pd.to_numeric(result[event_col], errors="coerce")
    result = result.dropna(subset=[event_col]).copy()
    result[event_col] = result[event_col].astype("int8")

    logger.info(
        "Features finales: %s columnas, %s registros válidos",
        len(result.columns),
        len(result),
    )
    logger.info("Columnas finales: %s", list(result.columns))

    return result


def split_data(
    df: pd.DataFrame,
    test_size: float,
    random_state: int,
    event_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide train/test estratificando por evento."""
    from sklearn.model_selection import train_test_split

    train, test = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df[event_col],
    )

    logger.info("Train: %s | Test: %s", len(train), len(test))
    return train, test


def train_cox_model(
    train_df: pd.DataFrame,
    duration_col: str,
    event_col: str,
) -> Any:
    """Entrena un modelo Cox Proportional Hazards."""
    from lifelines import CoxPHFitter

    train_df = train_df.copy()

    numeric_cols = [
        c for c in train_df.columns
        if c not in {duration_col, event_col}
    ]

    train_df[numeric_cols] = train_df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    train_df[duration_col] = pd.to_numeric(train_df[duration_col], errors="coerce")
    train_df[event_col] = pd.to_numeric(train_df[event_col], errors="coerce")

    before = len(train_df)
    train_df = train_df.dropna(subset=[duration_col, event_col] + numeric_cols).copy()
    after = len(train_df)

    logger.info("Filas antes de cox: %s | después de dropna: %s", before, after)

    cph = CoxPHFitter(penalizer=0.1)
    cph.fit(
        train_df,
        duration_col=duration_col,
        event_col=event_col,
        show_progress=False,
    )

    logger.info("Cox C-index (train): %.4f", cph.concordance_index_)
    return cph


def evaluate_model(
    model: Any,
    test_df: pd.DataFrame,
    duration_col: str,
    event_col: str,
) -> dict[str, float]:
    """Evalúa el modelo de supervivencia con concordance index."""
    from lifelines.utils import concordance_index

    test_df = test_df.copy()

    cols = [c for c in test_df.columns if c not in {duration_col, event_col}]
    test_df[cols] = test_df[cols].apply(pd.to_numeric, errors="coerce")
    test_df[duration_col] = pd.to_numeric(test_df[duration_col], errors="coerce")
    test_df[event_col] = pd.to_numeric(test_df[event_col], errors="coerce")

    before = len(test_df)
    test_df = test_df.dropna(subset=[duration_col, event_col] + cols).copy()
    after = len(test_df)
    logger.info("Filas antes de evaluar: %s | después de dropna: %s", before, after)

    risk_scores = model.predict_partial_hazard(test_df)
    c_index = concordance_index(
        test_df[duration_col],
        -risk_scores,
        test_df[event_col],
    )

    metrics = {"c_index_test": round(float(c_index), 4)}
    logger.info("C-index test: %.4f", c_index)
    return metrics