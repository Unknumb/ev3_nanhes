from kedro.pipeline import Pipeline, node, pipeline
from .nodes import (
    descargar_y_unir_2013,
    preprocesar_datos_2013,
    entrenar_modelo_clasificacion,
    entrenar_modelo_regresion,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=descargar_y_unir_2013,
                inputs=None,  # None porque descarga desde Internet, no lee de tu disco
                outputs="raw_nhanes_2013",
                name="nodo_descarga_nhanes_2013",
            ),
            node(
                func=preprocesar_datos_2013,
                inputs="raw_nhanes_2013",
                outputs="preprocessed_nhanes_2013",
                name="nodo_preprocesar_nhanes_2013",
            ),
            node(
                func=entrenar_modelo_clasificacion,
                inputs="preprocessed_nhanes_2013",
                outputs=[
                    "modelo_clasificacion_nhanes_2013",
                    "reporte_clasificacion_nhanes_2013",
                ],
                name="nodo_entrenar_clasificacion_nhanes_2013",
            ),
            node(
                func=entrenar_modelo_regresion,
                inputs="preprocessed_nhanes_2013",
                outputs=[
                    "modelo_regresion_nhanes_2013",
                    "reporte_regresion_nhanes_2013",
                ],
                name="nodo_entrenar_regresion_nhanes_2013",
            ),
        ]
    )
