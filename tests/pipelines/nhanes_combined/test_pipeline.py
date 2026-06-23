"""Tests del pipeline combinado (sin red: solo estructura + preprocesado)."""

import numpy as np
import pandas as pd

from ev3_nhanes.pipelines.nhanes_combined.nodes import preprocesar_datos_combinado
from ev3_nhanes.pipelines.nhanes_combined.pipeline import create_pipeline


def test_pipeline_tiene_los_cuatro_nodos():
    nombres = {node.name for node in create_pipeline().nodes}
    assert nombres == {
        "nodo_descarga_nhanes_combined",
        "nodo_preprocesar_nhanes_combined",
        "nodo_entrenar_clasificacion_nhanes_combined",
        "nodo_entrenar_regresion_nhanes_combined",
    }


def test_preprocesar_filtra_adultos_y_crea_target():
    df = pd.DataFrame(
        {
            "SEQN": [1, 2, 3],
            "RIDAGEYR": [10, 45, 72],  # el de 10 años se descarta (<18)
            "RIAGENDR": [1, 2, 1],
            "BMXBMI": [18.0, 25.0, 28.0],
            "CICLO_ORIGEN": ["2017-2018", "2017-2018", "2015-2016"],
        }
    )

    out = preprocesar_datos_combinado(df)

    assert len(out) == 2  # se elimina el menor de edad
    assert "IS_LONGEVO" in out.columns
    # IS_LONGEVO = 1 solo para el de 72 años (>=70)
    assert out.set_index("SEQN").loc[3, "IS_LONGEVO"] == 1
    assert out.set_index("SEQN").loc[2, "IS_LONGEVO"] == 0


def test_deriva_mcq_cvd_y_limpia_codigos():
    df = pd.DataFrame(
        {
            "SEQN": [1, 2, 3, 4],
            "RIDAGEYR": [40, 50, 60, 70],
            "RIAGENDR": [1, 2, 1, 2],
            "HSD010": [1, 7, 9, 3],          # 7/9 -> NaN
            "SMQ020": [1, 2, 7, 1],          # 7 -> NaN
            "MCQ160E": [1, 2, 2, np.nan],    # infarto
            "MCQ160F": [2, 2, 9, np.nan],    # ACV (9 -> NaN)
            "MCQ160B": [2, 2, 2, np.nan],
            "MCQ160C": [2, 2, 2, np.nan],
            "CICLO_ORIGEN": ["2017-2018"] * 4,
        }
    )

    out = preprocesar_datos_combinado(df).set_index("SEQN")

    # MCQ_CVD: fila1 tiene infarto(1) -> 1; fila2 todos no -> 0;
    # fila3 todos no salvo ACV=NaN -> 0; fila4 todo NaN -> NaN
    assert out.loc[1, "MCQ_CVD"] == 1
    assert out.loc[2, "MCQ_CVD"] == 0
    assert out.loc[3, "MCQ_CVD"] == 0
    assert pd.isna(out.loc[4, "MCQ_CVD"])
    # Códigos 7/9 limpiados a NaN
    assert pd.isna(out.loc[2, "HSD010"])
    assert pd.isna(out.loc[3, "HSD010"])
    assert pd.isna(out.loc[3, "SMQ020"])
    # Las columnas crudas MCQ160* no quedan como features
    assert "MCQ160E" not in out.columns


def test_preprocesar_descarta_filas_sin_edad():
    df = pd.DataFrame(
        {
            "SEQN": [1, 2],
            "RIDAGEYR": [np.nan, 50],
            "RIAGENDR": [1, 2],
            "CICLO_ORIGEN": ["2017-2018", "2017-2018"],
        }
    )

    out = preprocesar_datos_combinado(df)

    assert len(out) == 1
    assert out.iloc[0]["SEQN"] == 2
