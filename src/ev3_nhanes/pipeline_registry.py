# src/ev3_nhanes/pipeline_registry.py
"""Project pipelines."""
from __future__ import annotations

from kedro.pipeline import Pipeline
from ev3_nhanes.pipelines.nhanes_2013 import create_pipeline as nhanes_2013_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    nhanes_2013 = nhanes_2013_pipeline()

    return {
        "nhanes_2013": nhanes_2013,
        "__default__": nhanes_2013,
    }

