"""GoCardless Dagster Definitions."""

from dagster import Definitions

from src.dagster.gocardless.extraction.assets import extraction_asset_defs

gocardless_defs = Definitions.merge(extraction_asset_defs)
