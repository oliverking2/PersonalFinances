"""Dagster Resources for dbt."""

import os

from dagster_dbt import DbtCliResource, DbtProject

from src.filepaths import BACKEND_DIR

DBT_PROJECT_DIR = BACKEND_DIR / "dbt"

# Ensure DUCKDB_PATH is set to a valid absolute path before dbt runs.
# dbt's profiles.yml reads this env var. If not set or empty, compute the
# correct default path here (don't rely on filepaths.DUCKDB_PATH which may
# have already been computed with an incorrect value).
if "DUCKDB_PATH" not in os.environ or not os.environ["DUCKDB_PATH"]:
    default_duckdb_path = BACKEND_DIR / "data" / "analytics.duckdb"
    os.environ["DUCKDB_PATH"] = str(default_duckdb_path)

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)
dbt_project.prepare_if_dev()  # Auto-parses manifest in dev mode; no-op in production

dbt_resource = DbtCliResource(project_dir=dbt_project)
