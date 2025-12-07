"""Dagster definitions module.

This module aggregates and merges all Dagster definitions from various
ingestion modules to create a unified set of definitions for the
Dagster deployment.
"""

from dagster import Definitions

from src.dagster.dbt.definitions import dbt_defs
from src.dagster.gocardless.definitions import gocardless_defs
from src.dagster.resources import resource_defs

defs = Definitions.merge(resource_defs, gocardless_defs, dbt_defs)
