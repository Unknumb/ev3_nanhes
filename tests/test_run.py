"""Smoke tests for Kedro pipeline registration."""

from pathlib import Path

from kedro.framework.project import pipelines
from kedro.framework.startup import bootstrap_project


class TestKedroPipelineRegistration:
    def test_default_pipeline_has_nodes(self):
        bootstrap_project(Path.cwd())

        default_pipeline = pipelines["__default__"]

        assert len(default_pipeline.nodes) > 0
        assert "merge_nhanes_2017_2018" in {
            node.name for node in default_pipeline.nodes
        }
