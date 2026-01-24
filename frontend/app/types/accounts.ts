// =============================================================================
// Accounts Types
// TypeScript interfaces for connections, accounts, and institutions
// =============================================================================

// -----------------------------------------------------------------------------
// Status Enums
// -----------------------------------------------------------------------------

// Connection status - mapped from provider-specific codes to simple states
export type ConnectionStatus = 'active' | 'expired' | 'pending' | 'error'

// Account status - whether the account is actively syncing
export type AccountStatus = 'active' | 'inactive'

// Provider types - each bank integration source
export type Provider = 'gocardless' | 'vanguard' | 'trading212'

// -----------------------------------------------------------------------------
// Institution (Bank)
// -----------------------------------------------------------------------------

export interface Institution {
  id: string // e.g. "NATIONWIDE_NAIAGB21"
  name: string // e.g. "Nationwide"
  logo_url?: string // Optional bank logo
  countries?: string[] // e.g. ["GB"]
}

// -----------------------------------------------------------------------------
// Connection (Bank Link)
// Represents an authenticated connection to a bank
// -----------------------------------------------------------------------------

export interface Connection {
  id: string
  friendly_name: string // User-editable name, e.g. "Personal Banking"
  provider: Provider
  institution: Institution
  status: ConnectionStatus
  account_count: number // Number of accounts in this connection
  created_at: string // ISO timestamp
  expires_at?: string // ISO timestamp - when auth expires
}

// -----------------------------------------------------------------------------
// Account (Bank Account)
// Individual bank account within a connection
// -----------------------------------------------------------------------------

export interface AccountBalance {
  amount: number
  currency: string
  as_of: string // ISO timestamp - when balance was fetched
}

export interface Account {
  id: string
  connection_id: string // Links to parent connection
  display_name: string | null // User-editable display name
  name: string | null // Provider-sourced name (read-only)
  iban: string | null // e.g. "GB12NAIA12345678901234"
  currency: string | null // e.g. "GBP"
  status: AccountStatus
  balance?: AccountBalance // Optional - not all providers give balance
  last_synced_at?: string // ISO timestamp
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface ConnectionListResponse {
  connections: Connection[]
  total: number
}

export interface AccountListResponse {
  accounts: Account[]
  total: number
}

export interface InstitutionListResponse {
  institutions: Institution[]
}

// -----------------------------------------------------------------------------
// API Request Types
// -----------------------------------------------------------------------------

export interface CreateConnectionRequest {
  institution_id: string
  friendly_name: string
}

export interface CreateConnectionResponse {
  id: string
  auth_url: string // Redirect user here to complete bank auth
}

export interface UpdateConnectionRequest {
  friendly_name: string
}

export interface UpdateAccountRequest {
  display_name: string
}

export interface ReauthoriseResponse {
  auth_url: string // Redirect user here to re-authenticate
}
