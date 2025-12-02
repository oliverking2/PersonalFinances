"""Dagster definitions module.

This module aggregates and merges all Dagster definitions from various
ingestion modules to create a unified set of definitions for the
Dagster deployment.
"""

from dagster import Definitions

from src.dagster.ingestion.gocardless.assets import extraction_asset_defs
from src.dagster.resources import resource_defs

defs = Definitions.merge(resource_defs, extraction_asset_defs)
