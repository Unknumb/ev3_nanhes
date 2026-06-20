"""Pipeline definition for NHANES 2017-2018."""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    build_nhanes_2017_feature_expanded,
    merge_nhanes_2017_data,
    prepare_nhanes_2017_model_input,
    train_nhanes_2017_logistic_model,
    train_nhanes_2017_xgb_classifier,
    train_nhanes_2017_xgb_regressor,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the NHANES 2017-2018 longevity pipeline."""
    return pipeline(
        [
            node(
                func=merge_nhanes_2017_data,
                inputs=[
                    "raw_nhanes_2017_demo",
                    "raw_nhanes_2017_bmx",
                    "raw_nhanes_2017_bpx",
                    "raw_nhanes_2017_diq",
                    "raw_nhanes_2017_smq",
                    "raw_nhanes_2017_mortality",
                ],
                outputs="nhanes_2017_merged",
                name="merge_nhanes_2017",
            ),
            node(
                func=build_nhanes_2017_feature_expanded,
                inputs=[
                    "nhanes_2017_merged",
                    "raw_nhanes_2017_demo",
                    "raw_nhanes_2017_bmx",
                    "raw_nhanes_2017_bpx",
                    "raw_nhanes_2017_smq",
                ],
                outputs="nhanes_2017_feature_expanded",
                name="build_nhanes_2017_feature_expanded",
            ),
            node(
                func=prepare_nhanes_2017_model_input,
                inputs="nhanes_2017_feature_expanded",
                outputs="nhanes_2017_model_input",
                name="prepare_nhanes_2017_model_input",
            ),
            node(
                func=train_nhanes_2017_logistic_model,
                inputs="nhanes_2017_model_input",
                outputs="nhanes_2017_report",
                name="train_nhanes_2017_logistic_model",
            ),
            node(
                func=train_nhanes_2017_xgb_classifier,
                inputs="nhanes_2017_model_input",
                outputs=[
                    "modelo_clasificacion_nhanes_2017",
                    "nhanes_2017_clasificacion_report",
                ],
                name="train_nhanes_2017_xgb_classifier",
            ),
            node(
                func=train_nhanes_2017_xgb_regressor,
                inputs="nhanes_2017_model_input",
                outputs=[
                    "modelo_regresion_nhanes_2017",
                    "nhanes_2017_regresion_report",
                ],
                name="train_nhanes_2017_xgb_regressor",
            ),
        ]
    )
