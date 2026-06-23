"""Definición del pipeline 'serving'."""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import bendecir_modelos_serving


def create_pipeline(**kwargs) -> Pipeline:
    """Bendice el modelo de producción (COMBINADO) a data/09_serving/.

    Consume los modelos versionados del pipeline nhanes_combined (toma la
    versión más reciente persistida) y los copia a una ruta estable que lee la
    API. El modelo combinado se entrena con TODOS los ciclos del equipo.
    """
    return pipeline(
        [
            node(
                func=bendecir_modelos_serving,
                inputs=[
                    "modelo_clasificacion_nhanes_combined",
                    "modelo_regresion_nhanes_combined",
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
