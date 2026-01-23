# Infrastructure Patterns

## AWS

- Use typed stubs: `boto3-stubs[s3,ssm]`
- Handle `ClientError` specifically, check error codes
- Configure timeouts and retries explicitly
- Mock boto3 clients in tests

```python
from mypy_boto3_s3 import S3Client

def upload_file(client: S3Client, bucket: str, key: str, data: bytes) -> str:
    client.put_object(Bucket=bucket, Key=key, Body=data)
    return f"s3://{bucket}/{key}"
```

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
