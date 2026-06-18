# src/ev3_nhanes/pipelines/nhanes_2013/pipeline.py

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    descargar_y_unir_2013,
    preprocesar_datos_2013,
    split_y_escalar,
    entrenar_modelo_clasificacion,
    entrenar_modelo_regresion,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            # ── Nodo 1: Extracción ──────────────────────────────────────────
            node(
                func=descargar_y_unir_2013,
                inputs=None,                        # descarga desde Internet
                outputs="raw_nhanes_2013",
                name="nodo_descarga_nhanes_2013",
            ),

            # ── Nodo 2: Preprocesamiento (sin escalado) ─────────────────────
            node(
                func=preprocesar_datos_2013,
                inputs="raw_nhanes_2013",
                outputs="preprocessed_nhanes_2013",
                name="nodo_preprocesar_nhanes_2013",
            ),

            # ── Nodo 3: Split + Escalado correcto (sin data leakage) ────────
            #   fit_transform() solo sobre X_train
            #   transform()     solo sobre X_test
            node(
                func=split_y_escalar,
                inputs="preprocessed_nhanes_2013",
                outputs=[
                    "X_train_2013",
                    "X_test_2013",
                    "y_train_2013",
                    "y_test_2013",
                ],
                name="nodo_split_y_escalar_nhanes_2013",
            ),

            # ── Nodo 4a: Entrenamiento Clasificación ────────────────────────
            node(
                func=entrenar_modelo_clasificacion,
                inputs=["X_train_2013", "y_train_2013"],
                outputs="modelo_clasificacion_nhanes_2013",
                name="nodo_entrenar_clasificacion_nhanes_2013",
            ),

            # ── Nodo 4b: Entrenamiento Regresión ────────────────────────────
            #   También necesita el df preprocesado para recuperar RIDAGEYR
            #   usando los índices de X_train (target de regresión no escalado)
            node(
                func=entrenar_modelo_regresion,
                inputs=["preprocessed_nhanes_2013", "X_train_2013"],
                outputs="modelo_regresion_nhanes_2013",
                name="nodo_entrenar_regresion_nhanes_2013",
            ),
        ]
    )
