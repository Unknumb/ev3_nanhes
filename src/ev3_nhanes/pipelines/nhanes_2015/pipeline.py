from kedro.pipeline import Pipeline, node, pipeline
from .nodes import (
    descargar_y_unir_2015,
    preprocesar_datos_2015,
    entrenar_modelo_clasificacion,
    entrenar_modelo_regresion,
)

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=descargar_y_unir_2015,
                inputs=None, # None porque descarga desde Internet, no lee de tu disco
                outputs="raw_nhanes_2015", # El nombre con el que guardaremos el resultado
                name="nodo_descarga_nhanes_2015",
            ),
            node(
                func=preprocesar_datos_2015,
                inputs="raw_nhanes_2015",
                outputs="preprocessed_nhanes_2015",
                name="nodo_preprocesar_nhanes_2015",
            ),
            node(
                func=entrenar_modelo_clasificacion,
                inputs="preprocessed_nhanes_2015",
                outputs="modelo_clasificacion_nhanes_2015",
                name="nodo_entrenar_clasificacion_nhanes_2015",
            ),
            node(
                func=entrenar_modelo_regresion,
                inputs="preprocessed_nhanes_2015",
                outputs="modelo_regresion_nhanes_2015",
                name="nodo_entrenar_regresion_nhanes_2015",
            )
        ]
    )