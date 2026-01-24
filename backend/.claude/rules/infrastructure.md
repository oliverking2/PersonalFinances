# Infrastructure Patterns

## Configuration

- Environment variables via `python-dotenv`
- Document all variables in `.env_example`
- Never hard-code credentials
- Use `pydantic-settings` for structured config with validation

```python
import os
API_TOKEN = os.environ["API_TOKEN"]  # Required
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"  # Optional with default
```

## Security

- Validate all external input at system boundaries
- Parameterised queries only (no string formatting for SQL)
- No shell=True with user input
- Sanitise paths to prevent traversal
- Use `secrets.compare_digest()` for token comparison
- Never log secrets, passwords, or tokens

## Observability

- Structured logging with consistent keys: `endpoint=`, `status_code=`, `duration_ms=`
- Health check endpoints: `/health`
- Log levels: DEBUG (flow), INFO (actions), WARNING (recoverable), ERROR (failures)

## Module Structure

```
src/<module>/
├── __init__.py       # Public API exports
├── client.py         # External API client (if applicable)
├── models.py         # Pydantic models
├── exceptions.py     # Custom exceptions
└── enums.py          # StrEnum definitions
```
