"""Dagster Resources for dbt."""

from dagster_dbt import DbtCliResource, DbtProject

from filepaths import ROOT_DIR

DBT_PROJECT_DIR = ROOT_DIR / "dbt"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)

dbt_resource = DbtCliResource(project_dir=dbt_project)
