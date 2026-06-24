from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    descargar_features_mortalidad,
    entrenar_modelo_mortalidad,
    preparar_dataset_mortalidad,
)


def create_pipeline(**kwargs) -> Pipeline:
    """MVP de mortalidad a 10 años: descarga → une mortalidad → entrena."""
    return pipeline(
        [
            node(
                func=descargar_features_mortalidad,
                inputs=None,
                outputs="raw_mort_features",
                name="nodo_descarga_features_mortalidad",
            ),
            node(
                func=preparar_dataset_mortalidad,
                inputs=[
                    "raw_mort_features",
                    "raw_mort_2017", "raw_mort_2015", "raw_mort_2013",
                    "raw_mort_2011", "raw_mort_2009", "raw_mort_2007", "raw_mort_2005",
                ],
                outputs="dataset_mortalidad",
                name="nodo_preparar_dataset_mortalidad",
            ),
            node(
                func=entrenar_modelo_mortalidad,
                inputs="dataset_mortalidad",
                outputs=["modelo_mortalidad_10y", "reporte_mortalidad_10y"],
                name="nodo_entrenar_modelo_mortalidad",
            ),
        ]
    )
