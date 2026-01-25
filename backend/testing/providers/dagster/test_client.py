"""Tests for Dagster API client."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.providers.dagster.client import (
    GOCARDLESS_CONNECTION_SYNC_JOB,
    GOCARDLESS_CONNECTION_SYNC_OPS,
    _execute_graphql,
    _get_dagster_url,
    build_gocardless_run_config,
    get_run_status,
    trigger_job,
)


class TestBuildGocardlessRunConfig:
    """Tests for build_gocardless_run_config function."""

    def test_builds_config_with_connection_id(self) -> None:
        """Should build run config with connection_id for all ops."""
        connection_id = "test-conn-123"
        result = build_gocardless_run_config(connection_id)

        assert "ops" in result
        for op_name in GOCARDLESS_CONNECTION_SYNC_OPS:
            assert op_name in result["ops"]
            assert result["ops"][op_name]["config"]["connection_id"] == connection_id


class TestGetDagsterUrl:
    """Tests for _get_dagster_url function."""

    def test_returns_default_url(self) -> None:
        """Should return default URL when env var not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = _get_dagster_url()
            assert result == "http://localhost:3001"

    def test_returns_env_url(self) -> None:
        """Should return URL from environment variable."""
        with patch.dict("os.environ", {"DAGSTER_URL": "http://dagster.example.com"}):
            result = _get_dagster_url()
            assert result == "http://dagster.example.com"


class TestExecuteGraphql:
    """Tests for _execute_graphql function."""

    @pytest.fixture
    def mock_post(self) -> MagicMock:
        """Create a mock for requests.post."""
        with patch("src.providers.dagster.client.requests.post") as mock:
            yield mock

    def test_successful_request(self, mock_post: MagicMock) -> None:
        """Should return data from successful response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"test": "value"}}
        mock_post.return_value = mock_response

        result = _execute_graphql("query { test }")

        assert result == {"test": "value"}
        mock_post.assert_called_once()

    def test_request_with_variables(self, mock_post: MagicMock) -> None:
        """Should include variables in request payload."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"test": "value"}}
        mock_post.return_value = mock_response

        _execute_graphql("query { test }", {"var": "value"})

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["variables"] == {"var": "value"}

    def test_graphql_errors_returns_none(self, mock_post: MagicMock) -> None:
        """Should return None when response contains GraphQL errors."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "errors": [{"message": "Something went wrong"}],
            "data": None,
        }
        mock_post.return_value = mock_response

        result = _execute_graphql("query { test }")

        assert result is None

    def test_connection_error_returns_none(self, mock_post: MagicMock) -> None:
        """Should return None when connection fails."""
        mock_post.side_effect = requests.exceptions.ConnectionError()

        result = _execute_graphql("query { test }")

        assert result is None

    def test_timeout_returns_none(self, mock_post: MagicMock) -> None:
        """Should return None when request times out."""
        mock_post.side_effect = requests.exceptions.Timeout()

        result = _execute_graphql("query { test }")

        assert result is None

    def test_request_exception_returns_none(self, mock_post: MagicMock) -> None:
        """Should return None for general request exceptions."""
        mock_post.side_effect = requests.RequestException("Network error")

        result = _execute_graphql("query { test }")

        assert result is None


class TestTriggerJob:
    """Tests for trigger_job function."""

    @pytest.fixture
    def mock_execute(self) -> MagicMock:
        """Create a mock for _execute_graphql."""
        with patch("src.providers.dagster.client._execute_graphql") as mock:
            yield mock

    def test_successful_trigger_returns_run_id(self, mock_execute: MagicMock) -> None:
        """Should return run ID on successful trigger."""
        mock_execute.return_value = {
            "launchRun": {
                "__typename": "LaunchRunSuccess",
                "run": {"runId": "test-run-123"},
            }
        }

        result = trigger_job(GOCARDLESS_CONNECTION_SYNC_JOB)

        assert result == "test-run-123"

    def test_trigger_with_run_config(self, mock_execute: MagicMock) -> None:
        """Should pass run config to execution params."""
        mock_execute.return_value = {
            "launchRun": {
                "__typename": "LaunchRunSuccess",
                "run": {"runId": "test-run-123"},
            }
        }
        run_config = build_gocardless_run_config("conn-123")

        trigger_job(GOCARDLESS_CONNECTION_SYNC_JOB, run_config=run_config)

        call_args = mock_execute.call_args
        variables = call_args[0][1]
        assert variables["executionParams"]["runConfigData"] == run_config

    def test_dagster_unavailable_returns_none(self, mock_execute: MagicMock) -> None:
        """Should return None when Dagster is unavailable."""
        mock_execute.return_value = None

        result = trigger_job("test_job")

        assert result is None

    def test_run_config_validation_invalid(self, mock_execute: MagicMock) -> None:
        """Should return None and log error for invalid config."""
        mock_execute.return_value = {
            "launchRun": {
                "__typename": "RunConfigValidationInvalid",
                "errors": [
                    {"message": "Invalid config for op"},
                    {"message": "Missing required field"},
                ],
            }
        }

        result = trigger_job("test_job", run_config={"bad": "config"})

        assert result is None

    def test_python_error(self, mock_execute: MagicMock) -> None:
        """Should return None for Python errors."""
        mock_execute.return_value = {
            "launchRun": {
                "__typename": "PythonError",
                "message": "ImportError: module not found",
            }
        }

        result = trigger_job("test_job")

        assert result is None

    def test_run_conflict(self, mock_execute: MagicMock) -> None:
        """Should return None for run conflicts."""
        mock_execute.return_value = {
            "launchRun": {
                "__typename": "RunConflict",
                "message": "A run is already in progress",
            }
        }

        result = trigger_job("test_job")

        assert result is None


class TestGetRunStatus:
    """Tests for get_run_status function."""

    @pytest.fixture
    def mock_execute(self) -> MagicMock:
        """Create a mock for _execute_graphql."""
        with patch("src.providers.dagster.client._execute_graphql") as mock:
            yield mock

    def test_returns_status_for_existing_run(self, mock_execute: MagicMock) -> None:
        """Should return status for an existing run."""
        mock_execute.return_value = {
            "runOrError": {
                "__typename": "Run",
                "status": "SUCCESS",
            }
        }

        result = get_run_status("test-run-123")

        assert result == "SUCCESS"

    def test_returns_queued_status(self, mock_execute: MagicMock) -> None:
        """Should return QUEUED status."""
        mock_execute.return_value = {
            "runOrError": {
                "__typename": "Run",
                "status": "QUEUED",
            }
        }

        result = get_run_status("test-run-123")

        assert result == "QUEUED"

    def test_returns_started_status(self, mock_execute: MagicMock) -> None:
        """Should return STARTED status."""
        mock_execute.return_value = {
            "runOrError": {
                "__typename": "Run",
                "status": "STARTED",
            }
        }

        result = get_run_status("test-run-123")

        assert result == "STARTED"

    def test_returns_failure_status(self, mock_execute: MagicMock) -> None:
        """Should return FAILURE status."""
        mock_execute.return_value = {
            "runOrError": {
                "__typename": "Run",
                "status": "FAILURE",
            }
        }

        result = get_run_status("test-run-123")

        assert result == "FAILURE"

    def test_run_not_found_returns_none(self, mock_execute: MagicMock) -> None:
        """Should return None when run is not found."""
        mock_execute.return_value = {
            "runOrError": {
                "__typename": "RunNotFoundError",
                "message": "Run not found",
            }
        }

        result = get_run_status("nonexistent-run")

        assert result is None

    def test_python_error_returns_none(self, mock_execute: MagicMock) -> None:
        """Should return None for Python errors."""
        mock_execute.return_value = {
            "runOrError": {
                "__typename": "PythonError",
                "message": "Something went wrong",
            }
        }

        result = get_run_status("test-run-123")

        assert result is None

    def test_dagster_unavailable_returns_none(self, mock_execute: MagicMock) -> None:
        """Should return None when Dagster is unavailable."""
        mock_execute.return_value = None

        result = get_run_status("test-run-123")

        assert result is None
