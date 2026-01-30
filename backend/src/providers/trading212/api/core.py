"""Trading 212 API client.

Provides access to the Trading 212 Invest API for fetching account
information, cash balances, orders, dividends, and transactions.

API Reference: https://t212public-api-docs.redoc.ly/
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.providers.trading212.exceptions import (
    Trading212AuthError,
    Trading212Error,
    Trading212RateLimitError,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://live.trading212.com/api/v0"
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RATE_LIMIT_STATUS_CODE = 429
SERVER_ERROR_MIN = 500
SERVER_ERROR_MAX = 600

# Rate limits from T212 API docs
RATE_LIMIT_CASH_SECONDS = 2  # 1 request per 2 seconds
RATE_LIMIT_ACCOUNT_INFO_SECONDS = 30  # 1 request per 30 seconds
RATE_LIMIT_ORDERS_SECONDS = 5  # 1 request per 5 seconds
RATE_LIMIT_DIVIDENDS_SECONDS = 30  # 1 request per 30 seconds
RATE_LIMIT_TRANSACTIONS_SECONDS = 30  # 1 request per 30 seconds

# Pagination defaults
DEFAULT_HISTORY_LIMIT = 50  # Items per page for history endpoints


def _is_retryable_error(exception: BaseException) -> bool:
    """Determine if an exception should trigger a retry.

    Retries on:
    - Connection errors (network issues)
    - Timeout errors
    - Server errors (5xx status codes)

    Does NOT retry on:
    - Auth errors (401/403) - API key is invalid
    - Rate limit errors (429) - should be handled by caller

    :param exception: The exception to check.
    :returns: True if the request should be retried.
    """
    if isinstance(exception, requests.exceptions.ConnectionError):
        return True
    if isinstance(exception, requests.exceptions.Timeout):
        return True
    if isinstance(exception, requests.exceptions.HTTPError):
        response = exception.response
        if response is not None and SERVER_ERROR_MIN <= response.status_code < SERVER_ERROR_MAX:
            return True
    return False


def _log_retry(retry_state: Any) -> None:
    """Log retry attempts for debugging.

    :param retry_state: The tenacity retry state.
    """
    exception = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    logger.warning(f"Request failed (attempt {attempt}/{MAX_RETRIES}): {exception!s}")


@dataclass
class CashBalance:
    """Trading 212 cash balance data.

    All values are in the account's base currency.
    """

    free: Decimal
    """Free cash available for trading."""

    blocked: Decimal
    """Cash blocked by pending orders."""

    invested: Decimal
    """Cash invested in open positions."""

    pie_cash: Decimal
    """Cash allocated to pies."""

    ppl: Decimal
    """Unrealised profit/loss."""

    result: Decimal
    """Realised profit/loss."""

    total: Decimal
    """Total account value (free + invested + ppl)."""


@dataclass
class AccountInfo:
    """Trading 212 account information."""

    currency_code: str
    """Account base currency (e.g., 'GBP')."""

    account_id: str
    """Unique account identifier."""


@dataclass
class HistoryOrder:
    """Trading 212 historical order."""

    order_id: str
    """Unique order identifier."""

    parent_order_id: str | None
    """Parent order ID if this is a child order."""

    ticker: str
    """Instrument ticker symbol."""

    instrument_name: str | None
    """Human-readable instrument name."""

    order_type: str
    """Order type: MARKET, LIMIT, STOP, STOP_LIMIT."""

    status: str
    """Order status: FILLED, REJECTED, CANCELLED."""

    quantity: Decimal | None
    """Requested quantity."""

    filled_quantity: Decimal | None
    """Filled quantity."""

    filled_value: Decimal | None
    """Total filled value in account currency."""

    limit_price: Decimal | None
    """Limit price for LIMIT/STOP_LIMIT orders."""

    stop_price: Decimal | None
    """Stop price for STOP/STOP_LIMIT orders."""

    fill_price: Decimal | None
    """Average fill price."""

    currency: str
    """Account currency."""

    date_created: datetime
    """When the order was created."""

    date_executed: datetime | None
    """When the order was executed."""

    date_modified: datetime | None
    """When the order was last modified."""


@dataclass
class HistoryDividend:
    """Trading 212 dividend payment."""

    reference: str
    """Unique dividend reference."""

    ticker: str
    """Instrument ticker symbol."""

    instrument_name: str | None
    """Human-readable instrument name."""

    amount: Decimal
    """Net dividend amount received."""

    amount_in_euro: Decimal | None
    """Amount converted to EUR."""

    gross_amount_per_share: Decimal | None
    """Gross dividend per share."""

    quantity: Decimal | None
    """Number of shares held."""

    currency: str
    """Payment currency."""

    dividend_type: str | None
    """Dividend type: ORDINARY, SPECIAL, etc."""

    paid_on: datetime
    """Payment date."""


@dataclass
class HistoryTransaction:
    """Trading 212 cash transaction."""

    reference: str
    """Unique transaction reference."""

    transaction_type: str
    """Type: DEPOSIT, WITHDRAWAL, DIVIDEND, INTEREST, FEE, etc."""

    amount: Decimal
    """Transaction amount (positive for credits, negative for debits)."""

    currency: str
    """Transaction currency."""

    date_time: datetime
    """Transaction timestamp."""


@dataclass
class PaginatedResponse:
    """Paginated response wrapper."""

    items: list[Any]
    """Items in this page."""

    next_page_path: str | None
    """Path for next page, or None if this is the last page."""


class Trading212Client:
    """Trading 212 API client.

    Provides authenticated access to Trading 212 Invest API endpoints.
    Handles rate limiting and retries automatically.

    Usage:
        client = Trading212Client(api_key="your_api_key")
        info = client.get_account_info()
        cash = client.get_cash()
    """

    def __init__(self, api_key: str) -> None:
        """Initialise the Trading 212 client.

        :param api_key: Trading 212 API key.
        """
        self._api_key = api_key
        self._session = requests.Session()
        self._last_cash_request: float = 0
        self._last_account_info_request: float = 0
        self._last_orders_request: float = 0
        self._last_dividends_request: float = 0
        self._last_transactions_request: float = 0

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication.

        :returns: Headers dict with Authorization.
        """
        return {"Authorization": self._api_key}

    def _check_response(self, response: requests.Response) -> None:
        """Check response for errors.

        :param response: HTTP response to check.
        :raises Trading212AuthError: If API key is invalid.
        :raises Trading212RateLimitError: If rate limited.
        :raises Trading212Error: For other API errors.
        """
        if response.status_code == RATE_LIMIT_STATUS_CODE:
            raise Trading212RateLimitError(f"Rate limited by Trading 212 API: {response.text}")

        if response.status_code in (401, 403):
            raise Trading212AuthError(f"Trading 212 authentication failed: {response.text}")

        if not response.ok:
            raise Trading212Error(
                f"Trading 212 API error ({response.status_code}): {response.text}"
            )

    def _wait_for_rate_limit(self, last_request: float, interval: float) -> float:
        """Wait if necessary to respect rate limits.

        :param last_request: Timestamp of last request to this endpoint.
        :param interval: Minimum seconds between requests.
        :returns: Current timestamp after any necessary wait.
        """
        now = time.time()
        elapsed = now - last_request
        if elapsed < interval:
            wait_time = interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        return time.time()

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
    def _make_get_request(self, endpoint: str) -> dict[str, Any]:
        """Make a GET request to the Trading 212 API.

        :param endpoint: API endpoint path (e.g., '/equity/account/cash').
        :returns: Parsed JSON response.
        :raises Trading212Error: If request fails.
        """
        url = f"{BASE_URL}{endpoint}"
        response = self._session.get(
            url,
            headers=self._get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        self._check_response(response)
        return response.json()

    def get_cash(self) -> CashBalance:
        """Get current cash balance.

        Rate limit: 1 request per 2 seconds.

        :returns: CashBalance dataclass with balance components.
        :raises Trading212Error: If request fails.
        """
        self._last_cash_request = self._wait_for_rate_limit(
            self._last_cash_request, RATE_LIMIT_CASH_SECONDS
        )

        data = self._make_get_request("/equity/account/cash")

        return CashBalance(
            free=Decimal(str(data.get("free", 0))),
            blocked=Decimal(str(data.get("blocked", 0))),
            invested=Decimal(str(data.get("invested", 0))),
            pie_cash=Decimal(str(data.get("pieCash", 0))),
            ppl=Decimal(str(data.get("ppl", 0))),
            result=Decimal(str(data.get("result", 0))),
            total=Decimal(str(data.get("total", 0))),
        )

    def get_account_info(self) -> AccountInfo:
        """Get account information.

        Rate limit: 1 request per 30 seconds.

        :returns: AccountInfo dataclass with account details.
        :raises Trading212Error: If request fails.
        """
        self._last_account_info_request = self._wait_for_rate_limit(
            self._last_account_info_request, RATE_LIMIT_ACCOUNT_INFO_SECONDS
        )

        data = self._make_get_request("/equity/account/info")

        return AccountInfo(
            currency_code=data.get("currencyCode", ""),
            account_id=str(data.get("id", "")),
        )

    def validate_api_key(self) -> AccountInfo:
        """Validate API key by fetching account info.

        Useful for initial connection setup to verify the API key works.

        :returns: AccountInfo if key is valid.
        :raises Trading212AuthError: If API key is invalid.
        :raises Trading212Error: If request fails.
        """
        return self.get_account_info()

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse ISO 8601 datetime string from T212 API.

        :param value: ISO datetime string or None.
        :returns: Parsed datetime or None.
        """
        if not value:
            return None
        # T212 returns ISO 8601 format, e.g., "2024-01-15T10:30:00.000Z"
        try:
            # Handle both with and without milliseconds
            if "." in value:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(f"Failed to parse datetime: {value}")
            return None

    def _parse_decimal(self, value: Any) -> Decimal | None:
        """Parse decimal value from API response.

        :param value: Numeric value or None.
        :returns: Decimal or None.
        """
        if value is None:
            return None
        return Decimal(str(value))

    def _get_orders_page(
        self, cursor: int | None = None, limit: int = DEFAULT_HISTORY_LIMIT
    ) -> PaginatedResponse:
        """Fetch a single page of order history.

        :param cursor: Cursor for pagination.
        :param limit: Maximum items to return.
        :returns: PaginatedResponse with orders.
        """
        self._last_orders_request = self._wait_for_rate_limit(
            self._last_orders_request, RATE_LIMIT_ORDERS_SECONDS
        )

        endpoint = f"/equity/history/orders?limit={limit}"
        if cursor is not None:
            endpoint += f"&cursor={cursor}"

        data = self._make_get_request(endpoint)

        orders = []
        for item in data.get("items", []):
            orders.append(
                HistoryOrder(
                    order_id=str(item.get("id", "")),
                    parent_order_id=item.get("parentOrder"),
                    ticker=item.get("ticker", ""),
                    instrument_name=item.get("name"),
                    order_type=item.get("type", ""),
                    status=item.get("status", ""),
                    quantity=self._parse_decimal(item.get("quantity")),
                    filled_quantity=self._parse_decimal(item.get("filledQuantity")),
                    filled_value=self._parse_decimal(item.get("filledValue")),
                    limit_price=self._parse_decimal(item.get("limitPrice")),
                    stop_price=self._parse_decimal(item.get("stopPrice")),
                    fill_price=self._parse_decimal(item.get("fillPrice")),
                    currency=item.get("currency", ""),
                    date_created=self._parse_datetime(item.get("dateCreated")) or datetime.min,
                    date_executed=self._parse_datetime(item.get("dateExecuted")),
                    date_modified=self._parse_datetime(item.get("dateModified")),
                )
            )

        return PaginatedResponse(
            items=orders,
            next_page_path=data.get("nextPagePath"),
        )

    def get_orders(self, limit: int | None = None) -> list[HistoryOrder]:
        """Get all historical orders with automatic pagination.

        Rate limit: 1 request per 5 seconds.

        :param limit: Maximum total orders to fetch (None for all).
        :returns: List of HistoryOrder objects.
        """
        all_orders: list[HistoryOrder] = []
        cursor: int | None = None

        while True:
            response = self._get_orders_page(cursor=cursor)
            all_orders.extend(response.items)

            if limit and len(all_orders) >= limit:
                return all_orders[:limit]

            if not response.next_page_path:
                break

            # Extract cursor from next_page_path
            # Format: /api/v0/equity/history/orders?cursor=12345
            try:
                cursor = int(response.next_page_path.split("cursor=")[1].split("&")[0])
            except (IndexError, ValueError):
                break

        return all_orders

    def _get_dividends_page(
        self, cursor: int | None = None, limit: int = DEFAULT_HISTORY_LIMIT
    ) -> PaginatedResponse:
        """Fetch a single page of dividend history.

        :param cursor: Cursor for pagination.
        :param limit: Maximum items to return.
        :returns: PaginatedResponse with dividends.
        """
        self._last_dividends_request = self._wait_for_rate_limit(
            self._last_dividends_request, RATE_LIMIT_DIVIDENDS_SECONDS
        )

        endpoint = f"/equity/history/dividends?limit={limit}"
        if cursor is not None:
            endpoint += f"&cursor={cursor}"

        data = self._make_get_request(endpoint)

        dividends = []
        for item in data.get("items", []):
            dividends.append(
                HistoryDividend(
                    reference=str(item.get("reference", "")),
                    ticker=item.get("ticker", ""),
                    instrument_name=item.get("name"),
                    amount=Decimal(str(item.get("amount", 0))),
                    amount_in_euro=self._parse_decimal(item.get("amountInEuro")),
                    gross_amount_per_share=self._parse_decimal(item.get("grossAmountPerShare")),
                    quantity=self._parse_decimal(item.get("quantity")),
                    currency=item.get("currency", ""),
                    dividend_type=item.get("type"),
                    paid_on=self._parse_datetime(item.get("paidOn")) or datetime.min,
                )
            )

        return PaginatedResponse(
            items=dividends,
            next_page_path=data.get("nextPagePath"),
        )

    def get_dividends(self, limit: int | None = None) -> list[HistoryDividend]:
        """Get all dividend payments with automatic pagination.

        Rate limit: 1 request per 30 seconds.

        :param limit: Maximum total dividends to fetch (None for all).
        :returns: List of HistoryDividend objects.
        """
        all_dividends: list[HistoryDividend] = []
        cursor: int | None = None

        while True:
            response = self._get_dividends_page(cursor=cursor)
            all_dividends.extend(response.items)

            if limit and len(all_dividends) >= limit:
                return all_dividends[:limit]

            if not response.next_page_path:
                break

            try:
                cursor = int(response.next_page_path.split("cursor=")[1].split("&")[0])
            except (IndexError, ValueError):
                break

        return all_dividends

    def _get_transactions_page(
        self, cursor: int | None = None, limit: int = DEFAULT_HISTORY_LIMIT
    ) -> PaginatedResponse:
        """Fetch a single page of transaction history.

        :param cursor: Cursor for pagination.
        :param limit: Maximum items to return.
        :returns: PaginatedResponse with transactions.
        """
        self._last_transactions_request = self._wait_for_rate_limit(
            self._last_transactions_request, RATE_LIMIT_TRANSACTIONS_SECONDS
        )

        endpoint = f"/equity/history/transactions?limit={limit}"
        if cursor is not None:
            endpoint += f"&cursor={cursor}"

        data = self._make_get_request(endpoint)

        transactions = []
        for item in data.get("items", []):
            transactions.append(
                HistoryTransaction(
                    reference=str(item.get("reference", "")),
                    transaction_type=item.get("type", ""),
                    amount=Decimal(str(item.get("amount", 0))),
                    currency=item.get("currency", ""),
                    date_time=self._parse_datetime(item.get("dateTime")) or datetime.min,
                )
            )

        return PaginatedResponse(
            items=transactions,
            next_page_path=data.get("nextPagePath"),
        )

    def get_transactions(self, limit: int | None = None) -> list[HistoryTransaction]:
        """Get all cash transactions with automatic pagination.

        Rate limit: 1 request per 30 seconds.

        :param limit: Maximum total transactions to fetch (None for all).
        :returns: List of HistoryTransaction objects.
        """
        all_transactions: list[HistoryTransaction] = []
        cursor: int | None = None

        while True:
            response = self._get_transactions_page(cursor=cursor)
            all_transactions.extend(response.items)

            if limit and len(all_transactions) >= limit:
                return all_transactions[:limit]

            if not response.next_page_path:
                break

            try:
                cursor = int(response.next_page_path.split("cursor=")[1].split("&")[0])
            except (IndexError, ValueError):
                break

        return all_transactions
