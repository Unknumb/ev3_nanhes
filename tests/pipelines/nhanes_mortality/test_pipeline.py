"""Tests del MVP de mortalidad: la lógica de censura del target a 10 años."""

import numpy as np
import pandas as pd

from ev3_nhanes.pipelines.nhanes_mortality.nodes import _derivar_target_10y
from ev3_nhanes.pipelines.nhanes_mortality.pipeline import create_pipeline


def test_pipeline_tiene_los_tres_nodos():
    nombres = {n.name for n in create_pipeline().nodes}
    assert nombres == {
        "nodo_descarga_features_mortalidad",
        "nodo_preparar_dataset_mortalidad",
        "nodo_entrenar_modelo_mortalidad",
    }


def test_target_10y_maneja_censura():
    # FUTIME en meses; 120 = 10 años.
    df = pd.DataFrame(
        {
            "MORTSTAT": [0, 1, 1, 0],
            "FUTIME": [150, 60, 150, 60],
        }
    )
    t = _derivar_target_10y(df)

    # vivo con 150 meses (>10 años) -> sobrevivió -> 0
    assert t.iloc[0] == 0
    # murió a los 60 meses (<10 años) -> 1
    assert t.iloc[1] == 1
    # murió a los 150 meses (>10 años) -> sobrevivió la ventana -> 0
    assert t.iloc[2] == 0
    # vivo con solo 60 meses de seguimiento -> censurado -> NaN (se descarta)
    assert np.isnan(t.iloc[3])
