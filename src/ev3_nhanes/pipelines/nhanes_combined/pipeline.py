from kedro.pipeline import Pipeline, node, pipeline
from .nodes import (
    descargar_y_unir_combinado,
    preprocesar_datos_combinado,
    entrenar_modelo_clasificacion,
    entrenar_modelo_regresion,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Pipeline combinado: descarga TODOS los ciclos del equipo y entrena UN
    clasificador + UN regresor sobre el contrato rico de 23 features."""
    return pipeline(
        [
            node(
                func=descargar_y_unir_combinado,
                inputs=None,  # None porque descarga desde Internet, no lee de tu disco
                outputs="raw_nhanes_combined",
                name="nodo_descarga_nhanes_combined",
            ),
            node(
                func=preprocesar_datos_combinado,
                inputs="raw_nhanes_combined",
                outputs="preprocessed_nhanes_combined",
                name="nodo_preprocesar_nhanes_combined",
            ),
            node(
                func=entrenar_modelo_clasificacion,
                inputs="preprocessed_nhanes_combined",
                outputs=[
                    "modelo_clasificacion_nhanes_combined",
                    "reporte_clasificacion_nhanes_combined",
                ],
                name="nodo_entrenar_clasificacion_nhanes_combined",
            ),
            node(
                func=entrenar_modelo_regresion,
                inputs="preprocessed_nhanes_combined",
                outputs=[
                    "modelo_regresion_nhanes_combined",
                    "reporte_regresion_nhanes_combined",
                ],
                name="nodo_entrenar_regresion_nhanes_combined",
            ),
        ]
    )
