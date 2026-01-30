"""Trading 212 API exceptions."""


class Trading212Error(Exception):
    """Base exception for Trading 212 API errors.

    Raised when Trading 212 API operations fail.
    """


class Trading212RateLimitError(Trading212Error):
    """Exception for Trading 212 API rate limit errors.

    Raised when requests exceed the API rate limits.
    """


class Trading212AuthError(Trading212Error):
    """Exception for Trading 212 API authentication errors.

    Raised when the API key is invalid or revoked.
    """
