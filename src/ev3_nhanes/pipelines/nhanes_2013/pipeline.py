# src/ev3_nhanes/pipelines/nhanes_2013/pipeline.py
from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    download_demo,
    download_biopro,
    download_bmx,
    download_bpx,
    download_smq,
    load_mortality,
    merge_datasets,
    engineer_features,
    split_data,
    train_cox_model,
    evaluate_model,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            # --- EXTRACCIÓN / CARGA ---
            node(
                func=download_demo,
                inputs=None,
                outputs="nhanes_2013_demo_raw",
                name="download_demo_node",
                tags=["nhanes_2013", "download"],
            ),
            node(
                func=download_biopro,
                inputs=None,
                outputs="nhanes_2013_biopro_raw",
                name="download_biopro_node",
                tags=["nhanes_2013", "download"],
            ),
            node(
                func=download_bmx,
                inputs=None,
                outputs="nhanes_2013_bmx_raw",
                name="download_bmx_node",
                tags=["nhanes_2013", "download"],
            ),
            node(
                func=download_bpx,
                inputs=None,
                outputs="nhanes_2013_bpx_raw",
                name="download_bpx_node",
                tags=["nhanes_2013", "download"],
            ),
            node(
                func=download_smq,
                inputs=None,
                outputs="nhanes_2013_smq_raw",
                name="download_smq_node",
                tags=["nhanes_2013", "download"],
            ),
            node(
                func=load_mortality,
                inputs=None,
                outputs="nhanes_2013_mortality_raw",
                name="download_mortality_node",
                tags=["nhanes_2013", "download"],
            ),

            # --- PROCESAMIENTO ---
            node(
                func=merge_datasets,
                inputs=[
                    "nhanes_2013_demo_raw",
                    "nhanes_2013_biopro_raw",
                    "nhanes_2013_bmx_raw",
                    "nhanes_2013_bpx_raw",
                    "nhanes_2013_smq_raw",
                    "nhanes_2013_mortality_raw",
                ],
                outputs="nhanes_2013_merged",
                name="merge_node",
                tags=["nhanes_2013", "processing"],
            ),
            node(
                func=engineer_features,
                inputs=[
                    "nhanes_2013_merged",
                    "params:features.demographic",
                    "params:features.labs",
                    "params:model.duration_col",
                    "params:model.event_col",
                ],
                outputs="nhanes_2013_features",
                name="features_node",
                tags=["nhanes_2013", "processing"],
            ),
            node(
                func=split_data,
                inputs=[
                    "nhanes_2013_features",
                    "params:model.test_size",
                    "params:model.random_state",
                    "params:model.event_col",
                ],
                outputs=["nhanes_2013_train", "nhanes_2013_test"],
                name="split_node",
                tags=["nhanes_2013", "modeling"],
            ),

            # --- MODELADO ---
            node(
                func=train_cox_model,
                inputs=[
                    "nhanes_2013_train",
                    "params:model.duration_col",
                    "params:model.event_col",
                ],
                outputs="nhanes_2013_cox_model",
                name="train_node",
                tags=["nhanes_2013", "modeling"],
            ),
            node(
                func=evaluate_model,
                inputs=[
                    "nhanes_2013_cox_model",
                    "nhanes_2013_test",
                    "params:model.duration_col",
                    "params:model.event_col",
                ],
                outputs="nhanes_2013_metrics",
                name="evaluate_node",
                tags=["nhanes_2013", "modeling"],
            ),
        ]
    )