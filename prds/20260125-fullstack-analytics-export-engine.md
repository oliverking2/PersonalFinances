# PRD: Analytics Export Engine

**Status**: Draft
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-30
**Scope**: Fullstack (Backend + Frontend)

---

## Overview

Asynchronous dataset export engine using Dagster jobs, enabling users to export analytics datasets (CSV/Parquet) with parameterised filters. Exports are stored in S3 with time-limited signed URLs for secure downloads. Includes a frontend datasets page for browsing available datasets and initiating exports.

## Problem Statement

Users need to export their financial data for external analysis, record-keeping, or migration. The current analytics API only supports JSON responses with pagination limits (10,000 rows), which is insufficient for bulk data extraction.

## Goals

- Export any discoverable dataset to CSV or Parquet format
- Apply same filters as query API (date range, account_ids, tag_ids)
- Async execution via Dagster for large exports
- User data isolation maintained
- Secure downloads via S3 signed URLs (no authentication needed for download)
- Telegram notification on completion (if user has linked account)

## Non-Goals

- Scheduled/recurring exports
- Email notifications on completion
- Streaming exports (WebSocket progress)
- In-app notifications (future roadmap item)

---

## User Stories

1. **As a** user, **I want to** export my transactions to CSV, **so that** I can analyse them in Excel
2. **As a** user, **I want to** filter exports by date range, **so that** I only get relevant data
3. **As a** user, **I want to** check export progress, **so that** I know when my file is ready
4. **As a** user, **I want to** download completed exports, **so that** I can use the data offline
5. **As a** user, **I want to** receive a Telegram notification when my export is ready, **so that** I don't have to keep polling

---

## Proposed Solution

### High-Level Design

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   POST /exports │────▶│   Dagster Job   │────▶│   S3 Bucket     │
│   (create job)  │     │   (async exec)  │     │   (storage)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Job record    │────▶│   Update job    │────▶│  Telegram msg   │
│   (PostgreSQL)  │     │   metadata      │     │  (if linked)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  GET /status    │
                                                │  (signed URL)   │
                                                └─────────────────┘
```

### API Endpoints

| Method | Path                              | Description                          |
|--------|-----------------------------------|--------------------------------------|
| POST   | `/api/analytics/exports`          | Create export job                    |
| GET    | `/api/analytics/exports/{job_id}` | Get status + signed download URL     |

Note: No separate download endpoint needed - the status endpoint returns a signed S3 URL that can be used directly.

### Request/Response Models

#### POST /api/analytics/exports

Request:

```json
{
  "dataset_id": "uuid",
  "format": "csv",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "account_ids": ["uuid1", "uuid2"],
  "tag_ids": ["uuid3"]
}
```

Response (202 Accepted):

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Export job created"
}
```

#### GET /api/analytics/exports/{job_id}

Response (completed):

```json
{
  "job_id": "uuid",
  "status": "completed",
  "dataset_id": "uuid",
  "dataset_name": "fct_transactions",
  "format": "csv",
  "row_count": 1234,
  "file_size_bytes": 56789,
  "download_url": "https://bucket.s3.region.amazonaws.com/exports/user_id/job_id.csv?X-Amz-...",
  "expires_at": "2026-01-26T12:00:00Z",
  "created_at": "2026-01-25T12:00:00Z",
  "completed_at": "2026-01-25T12:00:05Z"
}
```

Response (pending/running):

```json
{
  "job_id": "uuid",
  "status": "running",
  "dataset_id": "uuid",
  "dataset_name": "fct_transactions",
  "format": "csv",
  "download_url": null,
  "expires_at": null,
  "created_at": "2026-01-25T12:00:00Z",
  "completed_at": null
}
```

---

## Technical Design

### Database Schema Change

Add `metadata` JSONB column to existing `jobs` table:

```python
from sqlalchemy.dialects.postgresql import JSONB

# In Job model
metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

Export metadata stored:

```json
{
  "dataset_id": "uuid",
  "dataset_name": "fct_transactions",
  "format": "csv",
  "filters": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "account_ids": ["uuid1"],
    "tag_ids": []
  },
  "s3_key": "exports/{user_id}/{job_id}.csv",
  "row_count": 1234,
  "file_size_bytes": 56789
}
```

### S3 Storage

- **Bucket**: Configured via `S3_EXPORTS_BUCKET` env var
- **Key pattern**: `exports/{user_id}/{job_id}.{format}`
- **Retention**: 24 hours via S3 lifecycle rule (configure in AWS console)
- **Downloads**: Pre-signed URLs with 1-hour expiry (regenerated on each status request)

### S3 Provider Module

New module at `src/providers/s3/`:

```python
# src/providers/s3/client.py
import boto3
from botocore.config import Config

def get_s3_client():
    """Get configured S3 client."""
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "eu-west-2"),
        config=Config(signature_version="s3v4"),
    )

def upload_export(
    content: bytes,
    user_id: UUID,
    job_id: UUID,
    format: str,
) -> str:
    """Upload export file to S3.

    :param content: File content as bytes.
    :param user_id: User ID for path isolation.
    :param job_id: Job ID for unique filename.
    :param format: File format (csv/parquet).
    :returns: S3 key of uploaded file.
    """
    bucket = os.environ["S3_EXPORTS_BUCKET"]
    key = f"exports/{user_id}/{job_id}.{format}"

    client = get_s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content,
        ContentType="text/csv" if format == "csv" else "application/octet-stream",
    )
    return key

def generate_download_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate pre-signed download URL.

    :param s3_key: S3 object key.
    :param expires_in: URL expiry in seconds (default 1 hour).
    :returns: Pre-signed URL for download.
    """
    bucket = os.environ["S3_EXPORTS_BUCKET"]
    client = get_s3_client()

    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": s3_key},
        ExpiresIn=expires_in,
    )
```

### Query Builder

Reuse existing `build_dataset_query()` from `duckdb/queries.py`. No separate export module needed - just pass a large limit (or modify the function to accept `limit=None` for unlimited).

### Dagster Job

Op-based job (not asset-based - exports are ephemeral):

```python
# src/orchestration/exports/ops.py
from typing import Optional
from dagster import Config, OpExecutionContext, op

class DatasetExportConfig(Config):
    job_id: str
    user_id: str
    dataset_id: str
    format: str  # "csv" or "parquet"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account_ids: Optional[list[str]] = None
    tag_ids: Optional[list[str]] = None

@op(required_resource_keys={"postgres_database"})
def export_dataset(context: OpExecutionContext, config: DatasetExportConfig) -> None:
    """Export a dataset to S3.

    1. Load dataset schema from manifest
    2. Build query using existing build_dataset_query()
    3. Execute against DuckDB, get results
    4. Write CSV/Parquet to buffer
    5. Upload to S3
    6. Update Job metadata with file info
    """
    ...
```

### Telegram Notification

On export completion, send a Telegram message to the user (if they have linked their account):

```python
# In the Dagster op, after successful upload
from src.telegram.client import TelegramClient
from src.telegram.utils.config import get_telegram_config

def send_export_notification(
    user: User,
    dataset_name: str,
    row_count: int,
    download_url: str,
) -> None:
    """Send Telegram notification for completed export.

    Only sends if user has linked their Telegram account.
    """
    if not user.telegram_chat_id:
        return

    config = get_telegram_config()
    if not config.bot_token:
        return

    client = TelegramClient(bot_token=config.bot_token)
    message = (
        f"<b>Export Ready</b>\n\n"
        f"Your <b>{dataset_name}</b> export is ready.\n"
        f"Rows: {row_count:,}\n\n"
        f"<a href=\"{download_url}\">Download CSV</a>\n\n"
        f"<i>Link expires in 1 hour</i>"
    )
    client.send_message_sync(text=message, chat_id=user.telegram_chat_id)
```

The export op needs access to the user's `telegram_chat_id`, so we'll pass the user_id in config and look up the user in the op.

### Existing Infrastructure

The following already exist and will be reused:

- `JobType.EXPORT` - already defined in `postgres/common/enums.py`
- `JobStatus` enum - PENDING, RUNNING, COMPLETED, FAILED
- `build_dataset_query()` - handles user isolation and filters
- `boto3` dependency - already in `pyproject.toml`
- `dagster-aws` dependency - already in `pyproject.toml`
- `TelegramClient.send_message_sync()` - sync method for Dagster ops
- `User.telegram_chat_id` - stored on user model when linked

### New Modules

```
backend/
├── src/
│   ├── api/analytics/
│   │   └── exports.py           # Export endpoints
│   ├── orchestration/
│   │   └── exports/
│   │       ├── __init__.py
│   │       ├── definitions.py   # Dagster job definition
│   │       └── ops.py           # Export operation
│   └── providers/
│       └── s3/
│           ├── __init__.py
│           └── client.py        # S3 upload and signed URL generation
└── alembic/versions/
    └── xxx_add_job_metadata.py  # Migration
```

### Modified Files

| File                                     | Change                                      |
|------------------------------------------|---------------------------------------------|
| `src/postgres/common/models.py`          | Add `metadata` JSONB column to Job          |
| `src/postgres/common/operations/jobs.py` | Add `metadata` param to create/update funcs |
| `src/providers/dagster/client.py`        | Add `build_export_run_config()` helper      |
| `src/orchestration/definitions.py`       | Merge `export_defs`                         |
| `backend/.env_example`                   | Add S3 config variables                     |

### Environment Variables

Add to `.env_example`:

```bash
# S3 Exports
S3_EXPORTS_BUCKET=your-exports-bucket-name
AWS_REGION=eu-west-2
# AWS credentials via standard methods (env vars, IAM role, ~/.aws/credentials)
```

---

## Implementation Plan

### Phase 1: Database & Model

- [ ] Add `metadata` JSONB column to Job model
- [ ] Create Alembic migration
- [ ] Update `create_job()` to accept optional `metadata` dict
- [ ] Update `update_job_status()` to accept optional `metadata` updates

### Phase 2: S3 Provider

- [ ] Create `src/providers/s3/__init__.py`
- [ ] Create `src/providers/s3/client.py` with upload and signed URL functions
- [ ] Add env vars to `.env_example`
- [ ] Unit tests for S3 client (mocked boto3)

### Phase 3: Dagster Export Job

- [ ] Create `src/orchestration/exports/__init__.py`
- [ ] Create `src/orchestration/exports/ops.py` with export op
- [ ] Create `src/orchestration/exports/definitions.py` with job
- [ ] Wire up in `src/orchestration/definitions.py`
- [ ] Add `build_export_run_config()` to Dagster client

### Phase 4: API Layer

- [ ] Create `src/api/analytics/exports.py` with endpoints
- [ ] Add Pydantic request/response models
- [ ] Wire into existing analytics router (or create sub-router)
- [ ] Unit tests for endpoints (mocked Dagster + S3)

### Phase 5: Telegram Notification

- [ ] Add Telegram notification to export op (after S3 upload)
- [ ] Look up user's `telegram_chat_id` in op
- [ ] Graceful skip if user hasn't linked Telegram

---

## Security Considerations

- **User isolation**: Queries always filter by `user_id`
- **S3 key isolation**: Keys include `user_id` to prevent cross-user access
- **Ownership validation**: Status endpoint checks job belongs to authenticated user
- **Signed URLs**: Time-limited (1 hour), no auth needed for download itself
- **Account/tag validation**: Reuse existing validation helpers
- **No path traversal**: S3 keys constructed programmatically

---

## Testing Strategy

- Unit tests for S3 client (mocked boto3)
- Unit tests for API endpoints (mocked Dagster + S3)
- Integration tests for Dagster op (localstack or mocked S3)
- Manual E2E test: create export → poll → download via signed URL

---

## Verification

```bash
# Run migrations
cd backend && alembic upgrade head

# Run tests
cd backend && make check

# Manual test - create export
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "uuid", "format": "csv"}' \
  http://localhost:8000/api/analytics/exports

# Poll status (returns signed URL when complete)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analytics/exports/{job_id}

# Download via signed URL (no auth header needed)
curl -o export.csv "https://bucket.s3.region.amazonaws.com/exports/..."
```

---

## Design Decisions

| Decision                   | Choice         | Rationale                                              |
|----------------------------|----------------|--------------------------------------------------------|
| Storage                    | S3             | Offloads serving, automatic lifecycle, signed URLs     |
| Signed URL expiry          | 1 hour         | Regenerated on each status check, balances security/UX |
| File retention             | 24 hours       | S3 lifecycle rule, user can re-export if needed        |
| Separate download endpoint | No             | Signed URL in status response is simpler               |
| Query builder              | Reuse existing | `build_dataset_query()` already handles all filters    |
| Job type                   | Use existing   | `JobType.EXPORT` already exists in enums               |
| Telegram notification      | On completion  | Reuse existing client, skip if not linked              |

---

## AWS Setup Notes

1. **S3 Bucket**: Create bucket with private ACL (no public access)
2. **Lifecycle Rule**: Add rule to delete objects with prefix `exports/` after 1 day
3. **IAM Permissions**: App needs `s3:PutObject` and `s3:GetObject` on the bucket
4. **CORS** (if needed for browser downloads): Configure CORS policy on bucket

---

## Frontend: Datasets Page

### Route

`/analytics/datasets` - accessible from Analytics nav dropdown or link on Analytics page.

### Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Datasets                                                   │
│  Export your financial data for external analysis           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Transactions                              [Export]  │   │
│  │  All transactions with tags and accounts             │   │
│  │  Time grain: daily                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Daily Spending by Tag                     [Export]  │   │
│  │  Daily spending totals grouped by tag                │   │
│  │  Time grain: daily                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Monthly Trends                            [Export]  │   │
│  │  Monthly income vs spending trends                   │   │
│  │  Time grain: monthly                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Export Modal

Clicking "Export" opens a modal with filter options:

```
┌─────────────────────────────────────────────────────────────┐
│  Export: Transactions                                   [×] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Format                                                     │
│  ┌─────────────┐ ┌─────────────┐                           │
│  │ CSV (•)     │ │ Parquet     │                           │
│  └─────────────┘ └─────────────┘                           │
│                                                             │
│  Date Range                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ Start date          │  │ End date            │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  Accounts (optional)                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Select accounts...                              [▼] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Tags (optional)                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Select tags...                                  [▼] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                          [Cancel]  [Start Export]          │
└─────────────────────────────────────────────────────────────┘
```

### Export Progress

After starting export, modal shows progress:

```
┌─────────────────────────────────────────────────────────────┐
│  Export: Transactions                                   [×] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │           ⏳ Export in progress...                  │   │
│  │                                                     │   │
│  │     We'll notify you via Telegram when ready       │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                                            [Close]          │
└─────────────────────────────────────────────────────────────┘
```

Or completed state:

```
┌─────────────────────────────────────────────────────────────┐
│  Export: Transactions                                   [×] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │           ✓ Export complete!                        │   │
│  │                                                     │   │
│  │     1,234 rows • 56 KB                              │   │
│  │                                                     │   │
│  │              [Download CSV]                         │   │
│  │                                                     │   │
│  │     Link expires in 1 hour                          │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                                            [Close]          │
└─────────────────────────────────────────────────────────────┘
```

### Frontend Files

```
frontend/app/
├── pages/
│   └── analytics/
│       └── datasets.vue          # Datasets list page
├── components/
│   └── datasets/
│       ├── DatasetCard.vue       # Dataset info card with export button
│       └── ExportModal.vue       # Export configuration modal
└── composables/
    └── useExportsApi.ts          # API composable for exports
```

### Implementation Plan (Frontend)

- [ ] Create `useExportsApi.ts` composable (POST create, GET status)
- [ ] Create `DatasetCard.vue` component
- [ ] Create `ExportModal.vue` component with form + progress states
- [ ] Create `/analytics/datasets` page
- [ ] Add link to datasets page from Analytics page
- [ ] Poll for export status after starting (5-second interval)
- [ ] Open download URL in new tab when complete
