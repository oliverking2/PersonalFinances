"""Tests for utils definitions module."""

from unittest.mock import patch

import pytest

from src.utils.definitions import (
    dagster_database_url,
    database_url,
    get_postgres_host,
    get_postgres_port,
    gocardless_database_url,
)


class TestGetPostgresHost:
    """Tests for get_postgres_host function."""

    def test_get_postgres_host_local_environment(self) -> None:
        """Test that localhost is returned in local environment."""
        with patch.dict(
            "os.environ",
            {"ENVIRONMENT": "local", "POSTGRES_HOSTNAME": "some-host"},
            clear=True,
        ):
            result = get_postgres_host()

        assert result == "localhost"

    def test_get_postgres_host_production_environment(self) -> None:
        """Test that POSTGRES_HOSTNAME is used in non-local environments."""
        with patch.dict(
            "os.environ",
            {"ENVIRONMENT": "production", "POSTGRES_HOSTNAME": "db.example.com"},
            clear=True,
        ):
            result = get_postgres_host()

        assert result == "db.example.com"

    def test_get_postgres_host_missing_env_var(self) -> None:
        """Test that ValueError is raised when POSTGRES_HOSTNAME is not set."""
        with (
            patch.dict("os.environ", {"ENVIRONMENT": "production"}, clear=True),
            pytest.raises(ValueError, match="POSTGRES_HOSTNAME not set"),
        ):
            get_postgres_host()


class TestGetPostgresPort:
    """Tests for get_postgres_port function."""

    def test_get_postgres_port_default(self) -> None:
        """Test that default port 5432 is returned when not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_postgres_port()

        assert result == 5432

    def test_get_postgres_port_custom(self) -> None:
        """Test that custom port is returned when set."""
        with patch.dict("os.environ", {"POSTGRES_PORT": "5433"}, clear=True):
            result = get_postgres_port()

        assert result == 5433


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
                "POSTGRES_HOSTNAME": "prod-db.example.com",
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

    def test_dagster_database_url_custom_port(self) -> None:
        """Test database URL uses custom port."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "local",
                "POSTGRES_PORT": "5433",
                "POSTGRES_USERNAME": "user",
                "POSTGRES_PASSWORD": "pass",
                "POSTGRES_DAGSTER_DATABASE": "dagster",
            },
            clear=True,
        ):
            result = dagster_database_url()

        assert "localhost:5433" in result


class TestDatabaseUrl:
    """Tests for database_url function."""

    def test_database_url_local(self) -> None:
        """Test database URL generation for local environment."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "local",
                "POSTGRES_USERNAME": "app_user",
                "POSTGRES_PASSWORD": "app_secret",
                "POSTGRES_DATABASE": "app_db",
            },
            clear=True,
        ):
            result = database_url()

        assert "postgresql+psycopg2://" in result
        assert "app_user:app_secret@" in result
        assert "localhost:5432" in result
        assert "app_db" in result

    def test_database_url_production(self) -> None:
        """Test database URL generation for production environment."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "production",
                "POSTGRES_HOSTNAME": "prod-db.example.com",
                "POSTGRES_USERNAME": "prod_user",
                "POSTGRES_PASSWORD": "prod_secret",
                "POSTGRES_DATABASE": "prod_app",
            },
            clear=True,
        ):
            result = database_url()

        assert "prod_user:prod_secret@" in result
        assert "prod-db.example.com:5432" in result
        assert "prod_app" in result


class TestGocardlessDatabaseUrl:
    """Tests for gocardless_database_url function (legacy alias)."""

    def test_gocardless_database_url_is_alias(self) -> None:
        """Test that gocardless_database_url returns same as database_url."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "local",
                "POSTGRES_USERNAME": "user",
                "POSTGRES_PASSWORD": "pass",
                "POSTGRES_DATABASE": "mydb",
            },
            clear=True,
        ):
            gc_result = gocardless_database_url()
            db_result = database_url()

        assert gc_result == db_result
