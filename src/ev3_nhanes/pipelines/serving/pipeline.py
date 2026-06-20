"""Definición del pipeline 'serving'."""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import bendecir_modelos_serving


def create_pipeline(**kwargs) -> Pipeline:
    """Bendice el modelo de producción (2015) a data/09_serving/.

    Consume los modelos versionados del pipeline nhanes_2015 (toma la versión
    más reciente persistida) y los copia a una ruta estable que lee la API.
    """
    return pipeline(
        [
            node(
                func=bendecir_modelos_serving,
                inputs=[
                    "modelo_clasificacion_nhanes_2015",
                    "modelo_regresion_nhanes_2015",
                ],
                outputs=[
                    "modelo_serving_clasificacion",
                    "modelo_serving_regresion",
                    "serving_metadata",
                ],
                name="bendecir_modelos_serving",
            ),
        ]
    )
