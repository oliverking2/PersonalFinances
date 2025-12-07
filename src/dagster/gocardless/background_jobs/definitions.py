"""Definitions for background gocardless jobs."""

from dagster import Definitions

from src.dagster.gocardless.background_jobs.daily_jobs import daily_job_defs

gocardless_background_job_defs = Definitions.merge(daily_job_defs)
