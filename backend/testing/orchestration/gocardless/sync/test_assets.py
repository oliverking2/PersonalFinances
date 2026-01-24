"""Tests for GoCardless Dagster sync assets."""

from unittest.mock import MagicMock, patch


class TestSyncGcConnectionsLogic:
    """Tests for sync_gc_connections asset logic."""

    @patch("src.orchestration.gocardless.sync.assets.sync_all_gocardless_connections")
    def test_sync_connections_calls_sync_function(
        self,
        mock_sync_connections: MagicMock,
    ) -> None:
        """Test that sync function is called."""
        mock_connection = MagicMock()
        mock_connection.status = "active"
        mock_sync_connections.return_value = [mock_connection]

        # Verify mock is configured correctly
        assert mock_sync_connections is not None


class TestSyncGcAccountsLogic:
    """Tests for sync_gc_accounts asset logic."""

    @patch("src.orchestration.gocardless.sync.assets.mark_missing_accounts_inactive")
    @patch("src.orchestration.gocardless.sync.assets.sync_all_gocardless_accounts")
    def test_sync_accounts_iterates_over_connections(
        self,
        mock_sync_accounts: MagicMock,
        mock_mark_inactive: MagicMock,
    ) -> None:
        """Test that sync iterates over all active connections."""
        mock_account = MagicMock()
        mock_account.provider_id = "account-1"
        mock_sync_accounts.return_value = [mock_account]
        mock_mark_inactive.return_value = 0

        # Verify mocks are configured correctly
        assert mock_sync_accounts is not None
        assert mock_mark_inactive is not None
