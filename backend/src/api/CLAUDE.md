# API CLAUDE.md

API-specific guidance. See also `backend/CLAUDE.md` for backend patterns.

## Endpoint Docstrings

Docstrings appear in Swagger UI at `/docs`. Keep them clean and readable.

### For Public Endpoints (routes)

Use **plain English** descriptions, not Sphinx markup:

```python
# Good - clean in Swagger UI
@router.get("/{item_id}", responses=RESOURCE_RESPONSES)
def get_item(item_id: UUID) -> ItemResponse:
    """Retrieve a specific item by its UUID."""

# Bad - Sphinx renders literally in Swagger
def get_item(item_id: UUID) -> ItemResponse:
    """Get an item.

    :param item_id: Item UUID.
    :returns: Item details.
    :raises HTTPException: If not found.
    """
```

**Guidelines:**

- Single line for simple endpoints
- Multi-line only when there's important context (side effects, business rules)
- No `:param:`, `:returns:`, or `:raises:` tags
- Document errors via `responses=` parameter instead

### For Helper Functions (prefixed with `_`)

Keep **Sphinx-style** docstrings - they're not shown in Swagger:

```python
def _to_response(item: Item) -> ItemResponse:
    """Convert an Item model to API response.

    :param item: Database model.
    :returns: API response model.
    """
```

## Error Response Documentation

Use standard responses from `src/api/responses.py`:

```python
from src.api.responses import RESOURCE_RESPONSES, RESOURCE_WRITE_RESPONSES

# Read operations
@router.get("/{id}", responses=RESOURCE_RESPONSES)  # 401, 404

# Write operations
@router.patch("/{id}", responses=RESOURCE_WRITE_RESPONSES)  # 401, 404, 400

# Custom combinations
@router.post("", responses={**RESOURCE_RESPONSES, **INTERNAL_ERROR})
```

Available responses:

- `UNAUTHORIZED` - 401
- `NOT_FOUND` - 404
- `BAD_REQUEST` - 400
- `CONFLICT` - 409
- `INTERNAL_ERROR` - 500
- `BAD_GATEWAY` - 502
- `RESOURCE_RESPONSES` - 401 + 404
- `RESOURCE_WRITE_RESPONSES` - 401 + 404 + 400
