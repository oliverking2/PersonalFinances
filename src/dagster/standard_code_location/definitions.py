"""Dagster definition."""

from dagster import Definitions, job, asset


@asset
def say_hello() -> None:
    """Asset."""
    print("Hello from Dagster")


@job
def hello_job() -> None:
    """Job."""
    say_hello()


defs = Definitions(
    jobs=[hello_job],
)
