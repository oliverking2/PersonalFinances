# API Patterns

## FastAPI Structure

```
src/api/<resource>/
├── __init__.py       # Exports router
├── endpoints.py      # Route handlers
└── models.py         # Pydantic request/response models
```

## Endpoints

- Separate request and response Pydantic models
- Use FastAPI's `Depends()` for database sessions and auth
- Catch domain exceptions, convert to HTTPException
- Log errors with context before raising

```python
@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: str, db: Session = Depends(get_db)) -> ItemResponse:
    try:
        item = get_item_by_id(db, item_id)
        return ItemResponse.model_validate(item)
    except ItemNotFoundError:
        raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")
```

## Pydantic Models

- Explicit field constraints with `Field(...)`
- `model_config = {"from_attributes": True}` for ORM conversion
- Separate Create/Update/Response models

## HTTP Clients

- Use `requests` for sync, `httpx` for async
- Always set explicit timeouts
- Use session/client for connection pooling
- Implement retry with exponential backoff for transient errors
- Handle rate limits (429) with Retry-After header

## Authentication

- Use `HTTPBearer` for token auth
- Constant-time comparison with `secrets.compare_digest()`
- Never log tokens
