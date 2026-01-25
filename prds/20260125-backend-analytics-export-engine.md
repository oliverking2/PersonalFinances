# PRD: Analytics Export Engine

**Status**: Draft
**Author**: Claude
**Created**: 2026-01-25

---

## Overview

Asynchronous dataset export engine using Dagster jobs, enabling users to export analytics datasets (CSV/Parquet) with parameterised filters. This extends the existing analytics API with background job processing for large exports.

## Problem Statement

Users need to export their financial data for external analysis, record-keeping, or migration. The current analytics API only supports JSON responses with pagination limits (10,000 rows), which is insufficient for bulk data extraction.

## Goals

- Export any discoverable dataset to CSV or Parquet format
- Apply same filters as query API (date range, account_ids, tag_ids)
- Async execution via Dagster for large exports
- User data isolation maintained
- Download completed exports via API

## Non-Goals

- Scheduled/recurring exports
- Email notifications on completion
- Cloud storage (S3) - can be added later
- Streaming exports (WebSocket progress)

---

## User Stories

1. **As a** user, **I want to** export my transactions to CSV, **so that** I can analyse them in Excel
2. **As a** user, **I want to** filter exports by date range, **so that** I only get relevant data
3. **As a** user, **I want to** check export progress, **so that** I know when my file is ready
4. **As a** user, **I want to** download completed exports, **so that** I can use the data offline

---

## Proposed Solution

### High-Level Design

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   POST /exports │────▶│   Dagster Job   │────▶│   Local File    │
│   (create job)  │     │   (async exec)  │     │   (exports/)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Job record    │────▶│   Update job    │────▶│  GET /download  │
│   (PostgreSQL)  │     │   metadata      │     │  (stream file)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### API Endpoints

| Method   | Path                                       | Description             |
|----------|--------------------------------------------|-------------------------|
| POST     | `/api/analytics/exports`                   | Create export job       |
| GET      | `/api/analytics/exports/{job_id}`          | Get export status       |
| GET      | `/api/analytics/exports/{job_id}/download` | Download completed file |

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
  "download_url": "/api/analytics/exports/{job_id}/download",
  "expires_at": "2026-01-26T12:00:00Z",
  "created_at": "2026-01-25T12:00:00Z",
  "completed_at": "2026-01-25T12:00:05Z"
}
```

---

## Technical Design

### Database Schema Change

Add `metadata` JSONB column to existing `jobs` table:

```python
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
  "output_path": "/path/to/exports/user_id/job_id.csv",
  "row_count": 1234,
  "file_size_bytes": 56789,
  "expires_at": "2026-01-26T12:00:00Z"
}
```

### File Storage

- Location: `backend/exports/{user_id}/{job_id}.{format}`
- Retention: 24 hours (cleanup via daily job or on-demand)
- Serving: FastAPI `FileResponse` with streaming

### Dagster Job

Op-based job (not asset-based - exports are ephemeral):

```python
@op(required_resource_keys={"postgres_database"})
def export_dataset(context: OpExecutionContext, config: DatasetExportConfig) -> None:
    # 1. Load dataset schema from manifest
    # 2. Build query (reuse build_dataset_query, no pagination)
    # 3. Execute against DuckDB, get DataFrame
    # 4. Write CSV/Parquet to exports directory
    # 5. Update Job metadata with file info
```

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
│   └── duckdb/
│       └── export.py            # Export query builder (no row limit)
└── alembic/versions/
    └── xxx_add_job_metadata.py  # Migration
```

### Modified Files

| File                                     | Change                            |
|------------------------------------------|-----------------------------------|
| `src/filepaths.py`                       | Add `EXPORTS_DIR`                 |
| `src/postgres/common/models.py`          | Add `metadata` column to Job      |
| `src/postgres/common/operations/jobs.py` | Support metadata in create/update |
| `src/providers/dagster/client.py`        | Add `build_export_run_config()`   |
| `src/orchestration/definitions.py`       | Merge export_defs                 |

---

## Implementation Plan

### Phase 1: Database & Model

- [ ] Add `metadata` JSONB column to Job model
- [ ] Create Alembic migration
- [ ] Update job operations to handle metadata

### Phase 2: Export Infrastructure

- [ ] Add `EXPORTS_DIR` to filepaths.py
- [ ] Create `duckdb/export.py` with unlimited query builder
- [ ] Create `orchestration/exports/ops.py` with export op
- [ ] Create `orchestration/exports/definitions.py` with job
- [ ] Wire up in main definitions.py

### Phase 3: API Layer

- [ ] Create `api/analytics/exports.py` with endpoints
- [ ] Add Pydantic request/response models
- [ ] Register router in app

### Phase 4: Dagster Client

- [ ] Add `DATASET_EXPORT_JOB` constant
- [ ] Add `build_export_run_config()` helper

### Phase 5: Cleanup (Optional)

- [ ] Add file cleanup logic (24h retention)

---

## Security Considerations

- **User isolation**: Queries always filter by `user_id`
- **Ownership validation**: Download endpoint checks job belongs to user
- **Path traversal**: Paths constructed programmatically, no user input
- **Account/tag validation**: Reuse existing validation helpers

---

## Testing Strategy

- Unit tests for export query builder
- Unit tests for API endpoints (mocked Dagster)
- Integration tests for Dagster op
- E2E test: create export → poll → download

---

## Verification

```bash
# Run migrations
cd backend && alembic upgrade head

# Run tests
cd backend && make check

# Manual test
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "uuid", "format": "csv"}' \
  http://localhost:8000/api/analytics/exports

# Poll status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analytics/exports/{job_id}

# Download
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analytics/exports/{job_id}/download -o export.csv
```

---

## Design Decisions

- **File retention**: 24 hours, then auto-cleanup
- **Export limits**: None - single-user project, keep it simple
- **Concurrent exports**: Unlimited
