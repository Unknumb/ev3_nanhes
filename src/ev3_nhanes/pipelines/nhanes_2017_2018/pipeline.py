"""Pipeline definition for NHANES 2017-2018."""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    build_baseline_model_input,
    build_feature_expanded_dataset,
    merge_nhanes_data,
    prepare_feature_expanded_model_input,
    train_feature_expanded_logistic_model,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the NHANES 2017-2018 mortality pipeline."""
    return pipeline(
        [
            node(
                func=merge_nhanes_data,
                inputs=[
                    "demo_data",
                    "bmx_data",
                    "bpx_data",
                    "diq_data",
                    "smq_data",
                    "mortality_data",
                ],
                outputs="nhanes_2017_2018_merged",
                name="merge_nhanes_2017_2018",
            ),
            node(
                func=build_baseline_model_input,
                inputs="nhanes_2017_2018_merged",
                outputs="nhanes_2017_2018_model_baseline",
                name="build_baseline_model_input",
            ),
            node(
                func=build_feature_expanded_dataset,
                inputs=[
                    "nhanes_2017_2018_merged",
                    "demo_data",
                    "bmx_data",
                    "bpx_data",
                    "smq_data",
                ],
                outputs="nhanes_2017_2018_feature_expanded",
                name="build_feature_expanded_dataset",
            ),
            node(
                func=prepare_feature_expanded_model_input,
                inputs="nhanes_2017_2018_feature_expanded",
                outputs="nhanes_2017_2018_model_input",
                name="prepare_feature_expanded_model_input",
            ),
            node(
                func=train_feature_expanded_logistic_model,
                inputs="nhanes_2017_2018_model_input",
                outputs="feature_expanded_logistic_report",
                name="train_feature_expanded_logistic_model",
            ),
        ]
    )
