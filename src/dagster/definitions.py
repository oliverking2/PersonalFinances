"""Dagster definitions module.

This module aggregates and merges all Dagster definitions from various
ingestion modules to create a unified set of definitions for the
Dagster deployment.
"""

from dagster import Definitions

import src.dagster.ingestion.gocardless.definitions as gocardless_defs

defs = Definitions.merge(
    gocardless_defs.defs,
)
