"""Tests for utils definitions module."""

from unittest.mock import patch

import pytest

from src.utils.definitions import (
    dagster_database_url,
    get_host,
    gocardless_database_url,
)


class TestGetHost:
    """Tests for get_host function."""

    def test_get_host_local_environment(self) -> None:
        """Test that localhost is returned in local environment."""
        with patch.dict(
            "os.environ",
            {"ENVIRONMENT": "local", "POSTGRES_HOST": "some-host"},
            clear=True,
        ):
            result = get_host()

        assert result == "localhost"

    def test_get_host_production_environment(self) -> None:
        """Test that POSTGRES_HOST is used in non-local environments."""
        with patch.dict(
            "os.environ",
            {"ENVIRONMENT": "production", "POSTGRES_HOST": "db.example.com"},
            clear=True,
        ):
            result = get_host()

        assert result == "db.example.com"

    def test_get_host_missing_env_var(self) -> None:
        """Test that ValueError is raised when POSTGRES_HOST is not set."""
        with (
            patch.dict("os.environ", {"ENVIRONMENT": "production"}, clear=True),
            pytest.raises(ValueError, match="POSTGRES_HOST not set"),
        ):
            get_host()


class TestDagsterDatabaseUrl:
    """Tests for dagster_database_url function."""

    def test_dagster_database_url_local(self) -> None:
        """Test database URL generation for local environment."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "local",
                "POSTGRES_USERNAME": "dagster_user",
                "POSTGRES_PASSWORD": "secret123",
                "POSTGRES_DAGSTER_DATABASE": "dagster_db",
            },
            clear=True,
        ):
            result = dagster_database_url()

        assert "postgresql+psycopg2://" in result
        assert "dagster_user:secret123@" in result
        assert "localhost:5432" in result
        assert "dagster_db" in result

    def test_dagster_database_url_production(self) -> None:
        """Test database URL generation for production environment."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "production",
                "POSTGRES_HOST": "prod-db.example.com",
                "POSTGRES_USERNAME": "prod_user",
                "POSTGRES_PASSWORD": "prod_secret",
                "POSTGRES_DAGSTER_DATABASE": "prod_dagster",
            },
            clear=True,
        ):
            result = dagster_database_url()

        assert "prod_user:prod_secret@" in result
        assert "prod-db.example.com:5432" in result
        assert "prod_dagster" in result


class TestGocardlessDatabaseUrl:
    """Tests for gocardless_database_url function."""

    def test_gocardless_database_url_local(self) -> None:
        """Test database URL generation for local environment."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "local",
                "POSTGRES_USERNAME": "gc_user",
                "POSTGRES_PASSWORD": "gc_secret",
                "POSTGRES_GOCARDLESS_DATABASE": "gocardless_db",
            },
            clear=True,
        ):
            result = gocardless_database_url()

        assert "postgresql+psycopg2://" in result
        assert "gc_user:gc_secret@" in result
        assert "localhost:5432" in result
        assert "gocardless_db" in result

    def test_gocardless_database_url_production(self) -> None:
        """Test database URL generation for production environment."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "production",
                "POSTGRES_HOST": "prod-db.example.com",
                "POSTGRES_USERNAME": "prod_user",
                "POSTGRES_PASSWORD": "prod_secret",
                "POSTGRES_GOCARDLESS_DATABASE": "prod_gocardless",
            },
            clear=True,
        ):
            result = gocardless_database_url()

        assert "prod_user:prod_secret@" in result
        assert "prod-db.example.com:5432" in result
        assert "prod_gocardless" in result
