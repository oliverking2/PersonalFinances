"""FastAPI middleware for request processing."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Paths to exclude from timing logs
EXCLUDED_PATHS = {"/health"}


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and log timing information.

        :param request: Incoming request.
        :param call_next: Next middleware/handler in chain.
        :returns: Response from handler.
        """
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.debug(
            f"Request completed: method={request.method} path={request.url.path} "
            f"status_code={response.status_code} duration_ms={duration_ms:.2f}"
        )
        return response
