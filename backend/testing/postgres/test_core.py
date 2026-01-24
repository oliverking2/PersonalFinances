"""Tests for core database utilities."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from src.postgres.core import Base, create_session, get_engine, session_scope


class TestGetEngine:
    """Tests for get_engine function."""

    def setup_method(self) -> None:
        """Clear the engine cache before each test."""
        get_engine.cache_clear()

    @patch("src.postgres.core.create_engine")
    def test_get_engine_returns_engine(self, mock_create_engine: MagicMock) -> None:
        """Test that get_engine returns a SQLAlchemy Engine."""
        mock_engine = MagicMock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        engine = get_engine("postgresql://localhost/test")

        assert engine is mock_engine

    @patch("src.postgres.core.create_engine")
    def test_get_engine_caches_result(self, mock_create_engine: MagicMock) -> None:
        """Test that calling get_engine with same URL returns cached engine."""
        mock_engine = MagicMock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        engine1 = get_engine("postgresql://localhost/test")
        engine2 = get_engine("postgresql://localhost/test")

        assert engine1 is engine2
        # create_engine should only be called once due to caching
        mock_create_engine.assert_called_once()

    @patch("src.postgres.core.create_engine")
    def test_get_engine_different_urls_returns_different_engines(
        self, mock_create_engine: MagicMock
    ) -> None:
        """Test that different URLs return different engines."""
        mock_engine1 = MagicMock(spec=Engine)
        mock_engine2 = MagicMock(spec=Engine)
        mock_create_engine.side_effect = [mock_engine1, mock_engine2]

        engine1 = get_engine("postgresql://localhost/test1")
        engine2 = get_engine("postgresql://localhost/test2")

        assert engine1 is not engine2
        assert mock_create_engine.call_count == 2

    @patch("src.postgres.core.create_engine")
    def test_get_engine_configures_pool_settings(self, mock_create_engine: MagicMock) -> None:
        """Test that engine is created with correct pool configuration."""
        mock_create_engine.return_value = MagicMock(spec=Engine)

        get_engine("postgresql://localhost/test")

        mock_create_engine.assert_called_once_with(
            "postgresql://localhost/test",
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
        )


class TestCreateSession:
    """Tests for create_session function."""

    def setup_method(self) -> None:
        """Clear the engine cache before each test."""
        get_engine.cache_clear()

    @patch("src.postgres.core.get_engine")
    @patch("src.postgres.core.sessionmaker")
    def test_create_session_returns_session(
        self, mock_sessionmaker: MagicMock, mock_get_engine: MagicMock
    ) -> None:
        """Test that create_session returns a SQLAlchemy Session."""
        mock_engine = MagicMock(spec=Engine)
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock(spec=Session)
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_factory

        session = create_session("postgresql://localhost/test")

        assert session is mock_session

    @patch("src.postgres.core.get_engine")
    @patch("src.postgres.core.sessionmaker")
    def test_create_session_uses_correct_engine(
        self, mock_sessionmaker: MagicMock, mock_get_engine: MagicMock
    ) -> None:
        """Test that create_session uses the engine from get_engine."""
        mock_engine = MagicMock(spec=Engine)
        mock_get_engine.return_value = mock_engine
        mock_sessionmaker.return_value = MagicMock(return_value=MagicMock(spec=Session))

        create_session("postgresql://localhost/test")

        mock_get_engine.assert_called_once_with("postgresql://localhost/test")
        mock_sessionmaker.assert_called_once_with(
            autocommit=False, autoflush=False, bind=mock_engine
        )

    @patch("src.postgres.core.get_engine")
    @patch("src.postgres.core.sessionmaker")
    def test_create_session_disables_autocommit(
        self, mock_sessionmaker: MagicMock, mock_get_engine: MagicMock
    ) -> None:
        """Test that sessions are created with autocommit disabled."""
        mock_get_engine.return_value = MagicMock(spec=Engine)
        mock_sessionmaker.return_value = MagicMock(return_value=MagicMock(spec=Session))

        create_session("postgresql://localhost/test")

        call_kwargs = mock_sessionmaker.call_args[1]
        assert call_kwargs["autocommit"] is False
        assert call_kwargs["autoflush"] is False


class TestSessionScope:
    """Tests for session_scope context manager."""

    def setup_method(self) -> None:
        """Clear the engine cache before each test."""
        get_engine.cache_clear()

    @patch("src.postgres.core.create_session")
    def test_session_scope_yields_session(self, mock_create_session: MagicMock) -> None:
        """Test that session_scope yields a Session object."""
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session

        with session_scope("postgresql://localhost/test") as session:
            assert session is mock_session

    @patch("src.postgres.core.create_session")
    def test_session_scope_commits_on_success(self, mock_create_session: MagicMock) -> None:
        """Test that session is committed when context exits normally."""
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session

        with session_scope("postgresql://localhost/test"):
            pass

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()

    @patch("src.postgres.core.create_session")
    def test_session_scope_rollback_on_exception(self, mock_create_session: MagicMock) -> None:
        """Test that session is rolled back when an exception occurs."""
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session

        with (
            pytest.raises(ValueError, match="test error"),
            session_scope("postgresql://localhost/test"),
        ):
            raise ValueError("test error")

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

    @patch("src.postgres.core.create_session")
    def test_session_scope_closes_on_exception(self, mock_create_session: MagicMock) -> None:
        """Test that session is closed even when an exception occurs."""
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session

        with pytest.raises(RuntimeError), session_scope("postgresql://localhost/test"):
            raise RuntimeError("unexpected error")

        mock_session.close.assert_called_once()

    @patch("src.postgres.core.create_session")
    def test_session_scope_reraises_exception(self, mock_create_session: MagicMock) -> None:
        """Test that exceptions are re-raised after rollback."""
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session

        with (
            pytest.raises(ValueError, match="original error"),
            session_scope("postgresql://localhost/test"),
        ):
            raise ValueError("original error")

    @patch("src.postgres.core.create_session")
    def test_session_scope_close_called_after_commit(self, mock_create_session: MagicMock) -> None:
        """Test that close is called after commit in success case."""
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session
        call_order: list[str] = []

        mock_session.commit.side_effect = lambda: call_order.append("commit")
        mock_session.close.side_effect = lambda: call_order.append("close")

        with session_scope("postgresql://localhost/test"):
            pass

        assert call_order == ["commit", "close"]

    @patch("src.postgres.core.create_session")
    def test_session_scope_close_called_after_rollback(
        self, mock_create_session: MagicMock
    ) -> None:
        """Test that close is called after rollback in failure case."""
        mock_session = MagicMock(spec=Session)
        mock_create_session.return_value = mock_session
        call_order: list[str] = []

        mock_session.rollback.side_effect = lambda: call_order.append("rollback")
        mock_session.close.side_effect = lambda: call_order.append("close")

        with pytest.raises(ValueError), session_scope("postgresql://localhost/test"):
            raise ValueError("error")

        assert call_order == ["rollback", "close"]


class TestBase:
    """Tests for Base declarative class."""

    def test_base_has_metadata(self) -> None:
        """Test that Base has metadata attribute."""
        assert hasattr(Base, "metadata")

    def test_base_has_registry(self) -> None:
        """Test that Base has registry attribute for ORM mapping."""
        assert hasattr(Base, "registry")

    def test_base_metadata_is_not_none(self) -> None:
        """Test that Base.metadata is initialised."""
        assert Base.metadata is not None
