"""Dagster Resources for dbt."""

from dagster_dbt import DbtCliResource, DbtProject

from src.filepaths import BACKEND_DIR

DBT_PROJECT_DIR = BACKEND_DIR / "dbt"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)
dbt_project.prepare_if_dev()  # Auto-parses manifest in dev mode; no-op in production

dbt_resource = DbtCliResource(project_dir=dbt_project)
