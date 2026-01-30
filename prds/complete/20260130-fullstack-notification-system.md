# PRD: In-App Notification System

**Date**: 2026-01-30
**Scope**: fullstack
**Status**: Complete

## Overview

Replace the current `SpendingAlert` system with a unified `Notification` model that supports multiple notification types. This provides a consistent way for users to see important events (budget warnings, export completions, sync status) without leaving the app.

## Goals

1. Unified notification model for all notification types
2. Bell icon in header with unread count badge
3. Dropdown panel showing recent notifications
4. Auto-create notifications for system events
5. Replace and deprecate the current SpendingAlert system

## Non-Goals

- Real-time push notifications (WebSocket/SSE) - polling is sufficient
- Email notifications - out of scope
- Mobile push notifications - out of scope
- Notification preferences/settings - defer to later iteration

## User Stories

1. **As a user**, I want to see a notification when my budget export is ready, so I can download it without checking the jobs page.
2. **As a user**, I want to see a notification when my spending approaches my budget limit, so I can adjust my spending.
3. **As a user**, I want to see a notification when my bank sync completes, so I know my data is up to date.
4. **As a user**, I want to mark notifications as read, so I can track which ones I've seen.

## Design

### Notification Types

| Type              | Trigger                                     | Title Example     | Message Example                                      |
|-------------------|---------------------------------------------|-------------------|------------------------------------------------------|
| `budget_warning`  | Spending >= warning threshold (default 80%) | "Budget Warning"  | "Groceries budget at 85%"                            |
| `budget_exceeded` | Spending >= 100%                            | "Budget Exceeded" | "Groceries budget exceeded (105% spent)"             |
| `export_complete` | Export job finishes successfully            | "Export Ready"    | "Your Transactions export is ready to download"      |
| `export_failed`   | Export job fails                            | "Export Failed"   | "Your Transactions export failed. Please try again." |
| `sync_complete`   | Sync job finishes successfully              | "Sync Complete"   | "Successfully synced your accounts"                  |
| `sync_failed`     | Sync job fails                              | "Sync Failed"     | "Failed to sync: Connection expired"                 |

### UI Components

1. **NotificationBell** - Header icon with unread count badge (red dot with number)
2. **NotificationDropdown** - Shows 10 most recent notifications, "Mark all read" button
3. **NotificationItem** - Individual notification with icon, title, message, timestamp

### Data Model

```
Notification
├── id: UUID
├── user_id: UUID (FK)
├── notification_type: string
├── title: string (max 100)
├── message: string (max 500)
├── read: boolean
├── metadata: JSONB (type-specific data)
├── created_at: datetime
└── read_at: datetime | null
```

### API Endpoints

- `GET /api/notifications` - List (paginated, newest first)
- `GET /api/notifications/count` - Unread count
- `PUT /api/notifications/{id}/read` - Mark read
- `PUT /api/notifications/read-all` - Mark all read
- `DELETE /api/notifications/{id}` - Delete

### Behaviour

- **Polling**: Frontend polls `/notifications/count` every 60 seconds when tab is active
- **Retention**: Read notifications older than 30 days are auto-deleted
- **Deduplication**: Budget alerts are deduplicated per budget per period (one warning per month)

## Technical Approach

### Backend

1. Add `NotificationType` enum to `postgres/common/enums.py`
2. Add `Notification` model to `postgres/common/models.py`
3. Create operations module at `postgres/common/operations/notifications.py`
4. Create API endpoints at `api/notifications/`
5. Add notification triggers to:
   - `orchestration/exports/ops.py` (export complete/failed)
   - `orchestration/gocardless/sync/assets.py` (budget checks after sync)
   - `api/jobs/endpoints.py` (sync complete/failed)

### Frontend

1. Create types at `types/notifications.ts`
2. Create composable at `composables/useNotificationsApi.ts`
3. Create components in `components/notifications/`
4. Add NotificationBell to header in `layouts/default.vue`

### Migration

1. Create `notifications` table
2. Migrate existing `spending_alerts` data
3. Remove `SpendingAlert` model and related code
4. Drop `spending_alerts` table

## Success Criteria

- [x] Notification bell visible in header
- [x] Unread count badge displays correctly
- [x] Dropdown shows notifications with correct icons and formatting
- [x] Mark as read works (individual and bulk)
- [x] Export completion triggers notification
- [x] Budget warning triggers notification after sync
- [x] Sync completion triggers notification
- [x] Old read notifications are cleaned up after 30 days (daily Dagster job at 4am)

## Future Enhancements (Out of Scope)

- Notification preferences (enable/disable by type)
- ~~Click-through to related entity (e.g., click budget notification -> budgets page)~~ **Implemented**
- Real-time updates via WebSocket
- Email notifications for critical alerts
