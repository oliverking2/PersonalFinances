"""Dagster definitions module.

This module aggregates and merges all Dagster definitions from various
ingestion modules to create a unified set of definitions for the
Dagster deployment.
"""

from dagster import Definitions

from src.orchestration.dbt.definitions import dbt_defs
from src.orchestration.gocardless.definitions import gocardless_defs
from src.orchestration.recurring_patterns.definitions import recurring_patterns_defs
from src.orchestration.resources import resource_defs

defs = Definitions.merge(resource_defs, gocardless_defs, dbt_defs, recurring_patterns_defs)
