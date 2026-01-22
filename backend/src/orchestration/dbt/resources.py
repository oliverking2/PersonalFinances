"""Dagster Resources for dbt."""

from dagster_dbt import DbtCliResource, DbtProject

from src.filepaths import PROJECT_ROOT

DBT_PROJECT_DIR = PROJECT_ROOT / "dbt"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)

dbt_resource = DbtCliResource(project_dir=dbt_project)
