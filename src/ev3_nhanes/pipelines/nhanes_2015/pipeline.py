from kedro.pipeline import Pipeline, node, pipeline
from .nodes import descargar_y_unir_2015

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=descargar_y_unir_2015,
                inputs=None, # None porque descarga desde Internet, no lee de tu disco
                outputs="raw_nhanes_2015", # El nombre con el que guardaremos el resultado
                name="nodo_descarga_nhanes_2015",
            )
        ]
    )