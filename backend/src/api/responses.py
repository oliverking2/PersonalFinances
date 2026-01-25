"""Standard API error responses for OpenAPI documentation."""

from typing import Any

ResponseDict = dict[int | str, dict[str, Any]]

UNAUTHORIZED: ResponseDict = {401: {"description": "Not authenticated"}}
NOT_FOUND: ResponseDict = {404: {"description": "Resource not found"}}
BAD_REQUEST: ResponseDict = {400: {"description": "Invalid request"}}
CONFLICT: ResponseDict = {409: {"description": "Resource conflict"}}
INTERNAL_ERROR: ResponseDict = {500: {"description": "Internal server error"}}
BAD_GATEWAY: ResponseDict = {502: {"description": "External service error"}}

# Common combinations
RESOURCE_RESPONSES: ResponseDict = {**UNAUTHORIZED, **NOT_FOUND}
RESOURCE_WRITE_RESPONSES: ResponseDict = {**UNAUTHORIZED, **NOT_FOUND, **BAD_REQUEST}
