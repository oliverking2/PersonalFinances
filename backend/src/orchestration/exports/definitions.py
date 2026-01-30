"""Dagster definitions for dataset exports."""

from dagster import Definitions, job

from src.orchestration.exports.ops import export_dataset


@job(name="dataset_export_job")
def dataset_export_job() -> None:
    """Job for exporting datasets to S3."""
    export_dataset()


export_defs = Definitions(jobs=[dataset_export_job])
