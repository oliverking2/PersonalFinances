# Accounts Management View

**Date**: 2026-01-24
**Scope**: frontend (with backend API spec for parallel development)

## Goal

Create a full accounts management page showing bank connections grouped with their nested accounts. Supports viewing, editing display names, creating new connections, and handling expired connections.

## Background

Previously implemented in Streamlit with separate accounts and connections pages. This PRD defines the Nuxt 4 implementation with a unified view and a clean API specification for the backend to implement in parallel.

---

## Frontend Implementation

### Files to Create

```
frontend/app/
├── pages/accounts.vue                          # Main page
├── types/accounts.ts                           # TypeScript interfaces
├── composables/useAccountsApi.ts               # API + mocks
└── components/accounts/
    ├── StatusIndicator.vue                     # Status badge (active/expired/pending)
    ├── AccountRow.vue                          # Account row with edit action
    ├── ConnectionCard.vue                      # Connection card with nested accounts
    ├── EditDisplayNameModal.vue                # Modal for editing names
    └── CreateConnectionModal.vue               # Modal for new connection flow
```

### Files to Modify

- `frontend/app/pages/dashboard.vue` - Make Accounts card link to `/accounts`

### UI Layout

```
+------------------------------------------------------------------+
| Accounts                                    [+ New Connection]    |
+------------------------------------------------------------------+
|                                                                  |
| [ConnectionCard: Nationwide - Personal]          Status: Active  |
|   [AccountRow: Current Account - GB12...1234]    GBP  [Edit]    |
|   [AccountRow: Savings - GB12...5678]            GBP  [Edit]    |
|                                                                  |
| [ConnectionCard: Amex]                      Status: Expired      |
|   [Warning: Connection expired]             [Reauthorise]        |
|   [AccountRow: Amex Platinum - XXXX...1111]      GBP            |
|                                                                  |
+------------------------------------------------------------------+
```

### Component Details

**StatusIndicator**: Visual badge for connection status

| Status   | Colour                  | Label     |
|----------|-------------------------|-----------|
| active   | Green (`text-positive`) | Connected |
| expired  | Red (`text-negative`)   | Expired   |
| pending  | Amber (`text-warning`)  | Pending   |
| error    | Red (`text-negative`)   | Error     |

**ConnectionCard**: Card containing connection info and nested accounts

- Shows: friendly_name, institution name/logo, status, account count
- Actions: Edit name, Reauthorise (if expired), Delete (overflow menu)

**AccountRow**: Single account display

- Shows: display_name (fallback to name), masked IBAN, currency badge
- Actions: Edit display_name

**Modals**:

- EditDisplayNameModal: Edit account or connection names
- CreateConnectionModal: Institution dropdown + friendly name input

### Mock Strategy

Frontend mocks all API calls initially. Backend implements to the spec below. Mock functions:

- Return realistic data with 200-500ms simulated delay
- Log `[MOCK]` prefix to console for visibility
- Are swapped out when real endpoints are ready

---

## Backend API Specification

### TypeScript Types (Frontend)

```typescript
export type ConnectionStatus = 'active' | 'expired' | 'pending' | 'error'
export type AccountStatus = 'active' | 'inactive'
export type Provider = 'gocardless' | 'vanguard' | 'trading212'

export interface Institution {
  id: string
  name: string
  logo_url?: string
  countries?: string[]
}

export interface Connection {
  id: string
  friendly_name: string
  provider: Provider
  institution: Institution
  status: ConnectionStatus
  account_count: number
  created_at: string      // ISO 8601
  expires_at?: string     // ISO 8601, when auth expires
}

export interface AccountBalance {
  amount: number
  currency: string
  as_of: string           // ISO 8601
}

export interface Account {
  id: string
  connection_id: string
  display_name: string | null   // User-editable
  name: string | null           // From provider (read-only)
  iban: string | null
  currency: string | null
  status: AccountStatus
  balance?: AccountBalance
  last_synced_at?: string
}
```

### Connections API

**`GET /api/connections`** - List all connections

```json
{
  "connections": [
    {
      "id": "uuid",
      "friendly_name": "Personal Banking",
      "provider": "gocardless",
      "institution": {
        "id": "NATIONWIDE_NAIAGB21",
        "name": "Nationwide",
        "logo_url": "https://..."
      },
      "status": "active",
      "account_count": 2,
      "created_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-04-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

**`POST /api/connections`** - Create new connection

```json
// Request
{ "institution_id": "NATIONWIDE_NAIAGB21", "friendly_name": "Personal Banking" }

// Response
{ "id": "uuid", "auth_url": "https://gocardless.com/..." }
```

**`PATCH /api/connections/{id}`** - Update connection

```json
// Request
{ "friendly_name": "New Name" }

// Response: Updated connection object
```

**`DELETE /api/connections/{id}`** - Delete connection
Returns 204 No Content. Cascades to delete associated accounts.

**`POST /api/connections/{id}/reauthorise`** - Refresh expired connection

```json
// Response
{ "auth_url": "https://gocardless.com/..." }
```

### Accounts API

**`GET /api/accounts`** - List all accounts

```json
{
  "accounts": [
    {
      "id": "uuid",
      "connection_id": "uuid",
      "display_name": "Current Account",
      "name": "NBS Current Account",
      "iban": "GB12NAIA12345678901234",
      "currency": "GBP",
      "status": "active",
      "balance": {
        "amount": 1234.56,
        "currency": "GBP",
        "as_of": "2024-01-20T08:00:00Z"
      },
      "last_synced_at": "2024-01-20T08:00:00Z"
    }
  ],
  "total": 2
}
```

**`GET /api/accounts?connection_id={id}`** - Filter by connection

**`PATCH /api/accounts/{id}`** - Update account

```json
// Request
{ "display_name": "My Savings" }

// Response: Updated account object
```

### Institutions API

**`GET /api/institutions`** - List available banks

```json
{
  "institutions": [
    {
      "id": "NATIONWIDE_NAIAGB21",
      "name": "Nationwide",
      "logo_url": "https://...",
      "countries": ["GB"]
    }
  ]
}
```

---

## Design Decisions

1. **Connections vs Accounts separation**: Connections are auth links (one per bank login), Accounts are the actual bank accounts within.
2. **`provider` field**: Future-proofs for Vanguard/Trading212 - each will be a different provider type.
3. **Normalised status values**: Simple enum instead of provider-specific codes (GoCardless LN/EX/CR mapped to active/expired/pending).
4. **`display_name` vs `name`**: `display_name` is user-editable, `name` is provider-sourced and read-only.
5. **Optional balance**: Some providers give balance info, some don't. Make it optional.
6. **`connection_id` on accounts**: Previously `requisition_id` - renamed for consistency and provider-agnosticism.

---

## Verification

1. Run `cd frontend && make check` after implementation
2. Manual testing:
   - [ ] Page loads with empty state when no connections
   - [ ] Connections display with nested accounts grouped
   - [ ] Status indicators show correct colours
   - [ ] Edit display_name saves and updates UI
   - [ ] Create connection modal opens, validates, shows mock result
   - [ ] Delete shows confirmation dialog
   - [ ] Expired connection shows warning + reauthorise button
   - [ ] Dashboard card links to /accounts
