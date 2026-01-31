"""Dagster API client for triggering jobs and checking run status.

This module provides functions to interact with the Dagster GraphQL API
for triggering jobs and monitoring their status.
"""

import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30  # seconds
DEFAULT_DAGSTER_URL = "http://localhost:3001"

# GoCardless connection sync ops (excludes global assets like institutions/requisitions)
# bank_accounts must be first to create BankAccount records before other assets can use them
GOCARDLESS_CONNECTION_SYNC_OPS = [
    "source__gocardless__extract__bank_accounts",
    "source__gocardless__extract__account_balances",
    "source__gocardless__extract__account_details",
    "source__gocardless__extract__transactions",
    "sync__gocardless__accounts",
    "sync__gocardless__transactions",
]

# Job name for connection-scoped syncs
GOCARDLESS_CONNECTION_SYNC_JOB = "gocardless_connection_sync_job"

# Trading 212 sync ops
TRADING212_SYNC_OPS = [
    "source__trading212__extract__cash",
    "source__trading212__extract__orders",
    "source__trading212__extract__dividends",
    "source__trading212__extract__transactions",
    "sync__trading212__connections",
    "sync__trading212__accounts",
    "sync__trading212__transactions",
]

# Job name for Trading 212 syncs
TRADING212_SYNC_JOB = "trading212_sync_job"

# Dataset export job
DATASET_EXPORT_JOB = "dataset_export_job"
DATASET_EXPORT_OPS = ["export_dataset"]


def build_gocardless_run_config(connection_id: str, *, full_sync: bool = False) -> dict[str, Any]:
    """Build run config for GoCardless connection sync job.

    :param connection_id: Connection UUID as string.
    :param full_sync: If True, ignore watermark and fetch all transactions.
    :returns: Run config dict for Dagster.
    """
    config: dict[str, Any] = {"connection_id": connection_id}
    if full_sync:
        config["full_sync"] = True

    return {"ops": {op_name: {"config": config} for op_name in GOCARDLESS_CONNECTION_SYNC_OPS}}


def build_trading212_run_config(api_key_id: str | None = None) -> dict[str, Any]:
    """Build run config for Trading 212 sync job.

    :param api_key_id: Optional API key UUID to scope sync to single key.
    :returns: Run config dict for Dagster.
    """
    config: dict[str, Any] = {}
    if api_key_id:
        config = {"api_key_id": api_key_id}

    return {"ops": {op_name: {"config": config} for op_name in TRADING212_SYNC_OPS}}


def build_export_run_config(
    job_id: str,
    user_id: str,
    dataset_id: str,
    file_format: str = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    account_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    enum_filters: list[dict[str, Any]] | None = None,
    numeric_filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build run config for dataset export job.

    :param job_id: Job UUID as string.
    :param user_id: User UUID as string.
    :param dataset_id: Dataset UUID as string.
    :param file_format: Export format (csv or parquet).
    :param start_date: Optional start date filter (ISO format).
    :param end_date: Optional end date filter (ISO format).
    :param account_ids: Optional list of account UUIDs.
    :param tag_ids: Optional list of tag UUIDs.
    :param enum_filters: Optional enum filters (column + values).
    :param numeric_filters: Optional numeric filters (column + min/max).
    :returns: Run config dict for Dagster.
    """
    config: dict[str, Any] = {
        "job_id": job_id,
        "user_id": user_id,
        "dataset_id": dataset_id,
        "file_format": file_format,
    }

    if start_date:
        config["start_date"] = start_date
    if end_date:
        config["end_date"] = end_date
    if account_ids:
        config["account_ids"] = account_ids
    if tag_ids:
        config["tag_ids"] = tag_ids
    # Encode filters as JSON strings (Dagster Config doesn't support list[dict])
    if enum_filters:
        config["enum_filters_json"] = json.dumps(enum_filters)
    if numeric_filters:
        config["numeric_filters_json"] = json.dumps(numeric_filters)

    return {"ops": {op_name: {"config": config} for op_name in DATASET_EXPORT_OPS}}


def _get_dagster_url() -> str:
    """Get the Dagster webserver URL from environment.

    :returns: Dagster URL.
    """
    return os.environ.get("DAGSTER_URL", DEFAULT_DAGSTER_URL)


def _execute_graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Execute a GraphQL query against Dagster.

    :param query: GraphQL query string.
    :param variables: Optional variables for the query.
    :returns: Response data, or None if request failed.
    """
    url = f"{_get_dagster_url()}/graphql"
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            return None

        return result.get("data")

    except requests.exceptions.ConnectionError:
        logger.warning(f"Could not connect to Dagster at {url}")
        return None
    except requests.exceptions.Timeout:
        logger.warning(f"Dagster request timed out after {REQUEST_TIMEOUT}s")
        return None
    except requests.RequestException as e:
        logger.exception(f"Dagster request failed: {e}")
        return None


def trigger_job(
    job_name: str,
    run_config: dict[str, Any] | None = None,
    repository_name: str = "__repository__",
    location_name: str = "personal_finances",
) -> str | None:
    """Trigger a Dagster job and return the run ID.

    :param job_name: Name of the Dagster job to run.
    :param run_config: Optional run configuration dict.
    :param repository_name: Name of the repository containing the job.
    :param location_name: Name of the code location.
    :returns: Run ID if successful, None if Dagster is unavailable or job trigger failed.
    """
    query = """
    mutation LaunchRun($executionParams: ExecutionParams!) {
        launchRun(executionParams: $executionParams) {
            __typename
            ... on LaunchRunSuccess {
                run {
                    runId
                }
            }
            ... on PythonError {
                message
                stack
            }
            ... on InvalidStepError {
                invalidStepKey
            }
            ... on InvalidOutputError {
                invalidOutputName
            }
            ... on RunConflict {
                message
            }
            ... on UnauthorizedError {
                message
            }
            ... on ConflictingExecutionParamsError {
                message
            }
            ... on PresetNotFoundError {
                message
            }
            ... on RunConfigValidationInvalid {
                errors {
                    message
                }
            }
            ... on NoModeProvidedError {
                message
            }
        }
    }
    """

    variables = {
        "executionParams": {
            "selector": {
                "repositoryLocationName": location_name,
                "repositoryName": repository_name,
                "jobName": job_name,
            },
            "runConfigData": run_config or {},
        }
    }

    data = _execute_graphql(query, variables)
    if data is None:
        logger.warning(f"Failed to trigger job {job_name}: Dagster unavailable")
        return None

    result = data.get("launchRun", {})
    typename = result.get("__typename")

    if typename == "LaunchRunSuccess":
        run_id = result["run"]["runId"]
        logger.info(f"Triggered job {job_name}: run_id={run_id}")
        return run_id

    # Handle various error types
    error_msg = result.get("message", "Unknown error")
    if typename == "RunConfigValidationInvalid":
        errors = result.get("errors", [])
        error_msg = "; ".join(e.get("message", "") for e in errors)

    logger.error(f"Failed to trigger job {job_name}: {typename} - {error_msg}")
    return None


def get_run_status(run_id: str) -> str | None:
    """Get the status of a Dagster run.

    :param run_id: The run ID to check.
    :returns: Run status string ('QUEUED', 'STARTED', 'SUCCESS', 'FAILURE',
              'CANCELED', etc.), or None if Dagster is unavailable or run not found.
    """
    query = """
    query RunStatus($runId: ID!) {
        runOrError(runId: $runId) {
            __typename
            ... on Run {
                status
            }
            ... on RunNotFoundError {
                message
            }
            ... on PythonError {
                message
            }
        }
    }
    """

    variables = {"runId": run_id}

    data = _execute_graphql(query, variables)
    if data is None:
        return None

    result = data.get("runOrError", {})
    typename = result.get("__typename")

    if typename == "Run":
        status = result["status"]
        logger.debug(f"Run {run_id} status: {status}")
        return status

    if typename == "RunNotFoundError":
        logger.warning(f"Run not found: {run_id}")
        return None

    logger.error(f"Error getting run status: {result.get('message', 'Unknown error')}")
    return None
