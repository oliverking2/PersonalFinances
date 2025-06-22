"""Dagster Definitions."""

from dagster import Definitions

import src.dagster.ingestion.gocardless.definitions as gocardless_defs

defs = Definitions.merge(
    gocardless_defs.defs,
)
