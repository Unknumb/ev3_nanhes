from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import cargar_dataset_postgres, preparar_tabla_nhanes


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=preparar_tabla_nhanes,
                inputs="preprocessed_nhanes_combined",
                outputs="nhanes_processed_for_db",
                name="preparar_tabla_nhanes_node",
                tags=["load_db", "postgres", "nhanes_combined"],
            ),
            node(
                func=cargar_dataset_postgres,
                inputs=dict(
                    df="nhanes_processed_for_db",
                    table_name="params:load_db.table_name",
                    if_exists="params:load_db.if_exists",
                    schema="params:load_db.schema",
                ),
                outputs="load_db_result",
                name="cargar_dataset_postgres_node",
                tags=["load_db", "postgres", "nhanes_combined"],
            ),
        ]
    )
