# PRD: Background Jobs System with Dagster Integration

**Date:** 2026-01-24
**Scope:** fullstack
**Status:** In Progress

## Goal

1. Create a general-purpose background jobs table (usable for sync, exports, etc.)
2. Trigger scoped Dagster sync for a specific connection after OAuth and via manual refresh
3. Show sync status in UI as a separate indicator (not changing connection.status)

## Design

### Jobs Table Schema

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,        -- 'sync', 'export', etc.
    status VARCHAR(20) NOT NULL,          -- 'pending', 'running', 'completed', 'failed'
    user_id UUID NOT NULL REFERENCES users(id),
    entity_type VARCHAR(50),              -- 'connection', 'account', null for global
    entity_id UUID,                       -- FK to the related entity
    dagster_run_id VARCHAR(64),           -- Dagster run ID for tracking
    error_message TEXT,                   -- Error details if failed
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_jobs_user_status ON jobs(user_id, status);
CREATE INDEX idx_jobs_entity ON jobs(entity_type, entity_id);
```

### Job Status Flow

```
pending → running → completed
                  → failed
```

### Scoped Dagster Job

Pass `connection_id` as run config to Dagster job. The extraction assets will filter to only that connection's accounts.

**Run config structure:**

```python
{
    "ops": {
        "gocardless_extract_transactions": {
            "config": {"connection_id": "uuid-here"}
        },
        # ... same for other ops
    }
}
```

## Implementation

### Phase 1: Jobs Infrastructure

#### 1.1 Database Model

**New file:** `backend/src/postgres/common/models.py` (add to existing)

```python
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    dagster_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

#### 1.2 Job Enums

**File:** `backend/src/postgres/common/enums.py`

```python
class JobType(StrEnum):
    SYNC = "sync"
    EXPORT = "export"

class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

#### 1.3 Database Operations

**New file:** `backend/src/postgres/common/operations/jobs.py`

```python
def create_job(session, user_id, job_type, entity_type=None, entity_id=None) -> Job
def update_job_status(session, job_id, status, dagster_run_id=None, error_message=None) -> Job
def get_latest_job_for_entity(session, entity_type, entity_id) -> Job | None
def get_jobs_by_user(session, user_id, job_type=None, limit=20) -> list[Job]
```

#### 1.4 Migration

```bash
poetry run alembic revision --autogenerate -m "add jobs table"
```

### Phase 2: Dagster Integration

#### 2.1 Dagster Client

**New file:** `backend/src/providers/dagster/client.py`

```python
def trigger_job(job_name: str, run_config: dict | None = None) -> str | None:
    """Trigger Dagster job, return run_id or None if unavailable."""

def get_run_status(run_id: str) -> str | None:
    """Get Dagster run status: 'STARTED', 'SUCCESS', 'FAILURE', etc."""
```

#### 2.2 Update Dagster Assets for Connection Filtering

**File:** `backend/src/orchestration/gocardless/extraction/assets.py`

Update assets to accept optional `connection_id` config:

```python
@asset(...)
def gocardless_extract_transactions(context: AssetExecutionContext, ...):
    connection_id = context.op_config.get("connection_id")

    if connection_id:
        # Filter to accounts for this specific connection
        accounts = get_accounts_for_connection(session, connection_id)
    else:
        # Full sync - all active accounts
        accounts = get_active_accounts(session)
```

#### 2.3 Job Definition with Config Schema

**File:** `backend/src/orchestration/gocardless/definitions.py`

```python
gocardless_connection_sync_job = define_asset_job(
    name="gocardless_connection_sync_job",
    selection=AssetSelection.groups("gocardless"),
    config={
        "ops": {
            "*": {
                "config": {
                    "connection_id": Field(str, is_required=False)
                }
            }
        }
    }
)
```

### Phase 3: API Endpoints

#### 3.1 Sync Endpoint

**File:** `backend/src/api/connections/endpoints.py`

```python
@router.post("/{connection_id}/sync", status_code=202, response_model=JobResponse)
def trigger_connection_sync(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Trigger a sync for a specific connection."""
    # Verify ownership
    connection = get_connection_by_id(db, connection_id)
    if not connection or connection.user_id != current_user.id:
        raise HTTPException(404)

    # Create job record
    job = create_job(
        db,
        user_id=current_user.id,
        job_type=JobType.SYNC,
        entity_type="connection",
        entity_id=connection_id,
    )

    # Trigger Dagster
    run_config = {"ops": {"*": {"config": {"connection_id": str(connection_id)}}}}
    run_id = trigger_job("gocardless_connection_sync_job", run_config)

    if run_id:
        update_job_status(db, job.id, JobStatus.RUNNING, dagster_run_id=run_id)
    else:
        update_job_status(db, job.id, JobStatus.FAILED, error_message="Dagster unavailable")

    db.commit()
    return JobResponse.model_validate(job)
```

#### 3.2 Job Status Endpoint

**File:** `backend/src/api/jobs/endpoints.py` (new)

```python
@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, ...) -> JobResponse:
    """Get job status."""

@router.get("", response_model=JobListResponse)
def list_jobs(entity_type: str = None, entity_id: UUID = None, ...) -> JobListResponse:
    """List jobs, optionally filtered by entity."""
```

### Phase 4: Job Status Sync (Dagster → Postgres)

#### 4.1 Background Task or Dagster Sensor

Option A: **Dagster sensor** that updates job status in Postgres when runs complete
Option B: **Polling endpoint** that frontend calls, which checks Dagster and updates

**Recommended: Option B** - simpler, no Dagster code changes needed

```python
@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, ...) -> JobResponse:
    job = get_job_by_id(db, job_id)

    # If still running, check Dagster for actual status
    if job.status == JobStatus.RUNNING and job.dagster_run_id:
        dagster_status = get_run_status(job.dagster_run_id)
        if dagster_status == "SUCCESS":
            update_job_status(db, job.id, JobStatus.COMPLETED)
        elif dagster_status in ("FAILURE", "CANCELED"):
            update_job_status(db, job.id, JobStatus.FAILED)
        db.commit()

    return JobResponse.model_validate(job)
```

### Phase 5: Frontend

#### 5.1 Accounts Page Refresh Button

**File:** `frontend/app/pages/accounts.vue`

```vue
<button @click="triggerSync" :disabled="syncing">
  <RefreshIcon :class="{ 'animate-spin': syncing }" />
  {{ syncing ? 'Syncing...' : 'Refresh' }}
</button>
```

#### 5.2 Connection Card Sync Status

**File:** `frontend/app/components/accounts/ConnectionCard.vue`

Add sync status badge next to the connection status:

```vue
<template>
  <!-- Existing status indicator -->
  <AccountsStatusIndicator :status="connection.status" />

  <!-- Sync status (if recent sync exists) -->
  <span v-if="syncJob?.status === 'running'" class="text-sm text-muted">
    <SpinnerIcon class="animate-spin" /> Syncing...
  </span>
  <span v-else-if="syncJob?.status === 'failed'" class="text-sm text-negative">
    Sync failed
  </span>
</template>
```

#### 5.3 API Composable

**File:** `frontend/app/composables/useAccountsApi.ts`

```typescript
async function triggerConnectionSync(connectionId: string): Promise<Job> {
  return authenticatedFetch(`/api/connections/${connectionId}/sync`, { method: 'POST' })
}

async function getJob(jobId: string): Promise<Job> {
  return authenticatedFetch(`/api/jobs/${jobId}`)
}

async function getLatestSyncJob(connectionId: string): Promise<Job | null> {
  const jobs = await authenticatedFetch(`/api/jobs?entity_type=connection&entity_id=${connectionId}&limit=1`)
  return jobs.jobs[0] || null
}
```

#### 5.4 Polling for Status

```typescript
async function triggerSync() {
  syncing.value = true
  const job = await triggerConnectionSync(connectionId)

  // Poll until complete
  const pollInterval = setInterval(async () => {
    const updated = await getJob(job.id)
    if (updated.status === 'completed') {
      clearInterval(pollInterval)
      syncing.value = false
      toast.success('Sync complete')
      await loadData()
    } else if (updated.status === 'failed') {
      clearInterval(pollInterval)
      syncing.value = false
      toast.error('Sync failed')
    }
  }, 2000)
}
```

### Phase 6: OAuth Callback Integration

**File:** `backend/src/api/connections/endpoints.py`

In `oauth_callback()` after setting status to ACTIVE:

```python
if new_status == "LN":
    update_connection_status(db, connection.id, ConnectionStatus.ACTIVE)

    # Auto-trigger sync for the new connection
    job = create_job(db, user_id=connection.user_id, job_type=JobType.SYNC,
                     entity_type="connection", entity_id=connection.id)
    run_id = trigger_job("gocardless_connection_sync_job",
                         {"ops": {"*": {"config": {"connection_id": str(connection.id)}}}})
    if run_id:
        update_job_status(db, job.id, JobStatus.RUNNING, dagster_run_id=run_id)
```

## Files to Create/Modify

| File                                                        | Action                           |
|-------------------------------------------------------------|----------------------------------|
| `backend/src/postgres/common/models.py`                     | Add `Job` model                  |
| `backend/src/postgres/common/enums.py`                      | Add `JobType`, `JobStatus`       |
| `backend/src/postgres/common/operations/jobs.py`            | **New** - Job CRUD               |
| `backend/src/providers/dagster/client.py`                   | **New** - Dagster API client     |
| `backend/src/api/jobs/endpoints.py`                         | **New** - Jobs API               |
| `backend/src/api/jobs/models.py`                            | **New** - Job Pydantic models    |
| `backend/src/api/connections/endpoints.py`                  | Add sync endpoint, OAuth trigger |
| `backend/src/orchestration/gocardless/extraction/assets.py` | Add connection_id config         |
| `backend/src/orchestration/gocardless/sync/assets.py`       | Add connection_id config         |
| `backend/src/orchestration/gocardless/definitions.py`       | Add config schema to job         |
| `backend/.env_example`                                      | Add `DAGSTER_URL`                |
| `frontend/app/pages/accounts.vue`                           | Add Refresh button, sync status  |
| `frontend/app/components/accounts/ConnectionCard.vue`       | Add sync status badge            |
| `frontend/app/composables/useAccountsApi.ts`                | Add sync/job functions           |
| `frontend/app/types/jobs.ts`                                | **New** - Job types              |

## Verification

1. **Database:** Run migration, verify jobs table created
2. **API:** Test `POST /api/connections/{id}/sync` returns job with status
3. **Dagster:** Verify job runs with connection_id config, only syncs that connection
4. **Frontend:** Click Refresh, see spinner, see completion/failure
5. **OAuth:** Complete OAuth flow, verify auto-sync triggers
6. **Status:** Verify sync status shows on connection card during/after sync
