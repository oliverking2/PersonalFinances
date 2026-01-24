// =============================================================================
// Accounts API Composable
// All API functions for connections, accounts, and institutions
// Currently uses mock data - backend builds to this spec
// =============================================================================

import type {
  Connection,
  Account,
  Institution,
  ConnectionListResponse,
  AccountListResponse,
  InstitutionListResponse,
  CreateConnectionRequest,
  CreateConnectionResponse,
  UpdateConnectionRequest,
  UpdateAccountRequest,
  ReauthoriseResponse,
} from '~/types/accounts'

// -----------------------------------------------------------------------------
// Mock Data
// Realistic data for development before backend is ready
// -----------------------------------------------------------------------------

const MOCK_INSTITUTIONS: Institution[] = [
  {
    id: 'NATIONWIDE_NAIAGB21',
    name: 'Nationwide',
    logo_url: 'https://cdn.nordigen.com/ais/NATIONWIDE_NAIAGB21.png',
    countries: ['GB'],
  },
  {
    id: 'LLOYDS_LOYDGB21',
    name: 'Lloyds Bank',
    logo_url: 'https://cdn.nordigen.com/ais/LLOYDS_LOYDGB21.png',
    countries: ['GB'],
  },
  {
    id: 'BARCLAYS_BARCGB22',
    name: 'Barclays',
    logo_url: 'https://cdn.nordigen.com/ais/BARCLAYS_BARCGB22.png',
    countries: ['GB'],
  },
  {
    id: 'AMEX_AABORX21',
    name: 'American Express',
    logo_url: 'https://cdn.nordigen.com/ais/AMEX_AABORX21.png',
    countries: ['GB'],
  },
]

const MOCK_CONNECTIONS: Connection[] = [
  {
    id: 'conn-1',
    friendly_name: 'Personal Banking',
    provider: 'gocardless',
    institution: MOCK_INSTITUTIONS[0]!, // Nationwide
    status: 'active',
    account_count: 2,
    created_at: '2024-01-15T10:30:00Z',
    expires_at: '2024-04-15T10:30:00Z',
  },
  {
    id: 'conn-2',
    friendly_name: 'Credit Card',
    provider: 'gocardless',
    institution: MOCK_INSTITUTIONS[3]!, // Amex
    status: 'expired',
    account_count: 1,
    created_at: '2024-01-10T14:00:00Z',
    expires_at: '2024-01-20T14:00:00Z',
  },
]

const MOCK_ACCOUNTS: Account[] = [
  {
    id: 'acc-1',
    connection_id: 'conn-1',
    display_name: 'Current Account',
    name: 'NBS Current Account',
    iban: 'GB12NAIA12345678901234',
    currency: 'GBP',
    status: 'active',
    balance: {
      amount: 2547.83,
      currency: 'GBP',
      as_of: '2024-01-20T08:00:00Z',
    },
    last_synced_at: '2024-01-20T08:00:00Z',
  },
  {
    id: 'acc-2',
    connection_id: 'conn-1',
    display_name: null, // No custom name set
    name: 'NBS Savings Account',
    iban: 'GB12NAIA12345678905678',
    currency: 'GBP',
    status: 'active',
    balance: {
      amount: 15000.0,
      currency: 'GBP',
      as_of: '2024-01-20T08:00:00Z',
    },
    last_synced_at: '2024-01-20T08:00:00Z',
  },
  {
    id: 'acc-3',
    connection_id: 'conn-2',
    display_name: 'Amex Platinum',
    name: 'American Express Platinum Card',
    iban: null, // Credit cards don't have IBANs
    currency: 'GBP',
    status: 'active',
    balance: {
      amount: -1234.56, // Negative for credit card balance
      currency: 'GBP',
      as_of: '2024-01-18T12:00:00Z',
    },
    last_synced_at: '2024-01-18T12:00:00Z',
  },
]

// -----------------------------------------------------------------------------
// Helper: Simulated delay for realistic mock behavior
// -----------------------------------------------------------------------------

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function randomDelay(): Promise<void> {
  // 200-500ms to simulate network latency
  return delay(200 + Math.random() * 300)
}

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useAccountsApi() {
  // ---------------------------------------------------------------------------
  // Connections API
  // ---------------------------------------------------------------------------

  // Fetch all connections
  async function fetchConnections(): Promise<ConnectionListResponse> {
    console.log('[MOCK] GET /api/connections')
    await randomDelay()
    return {
      connections: [...MOCK_CONNECTIONS],
      total: MOCK_CONNECTIONS.length,
    }
  }

  // Create a new connection (starts bank auth flow)
  async function createConnection(
    req: CreateConnectionRequest,
  ): Promise<CreateConnectionResponse> {
    console.log('[MOCK] POST /api/connections', req)
    await randomDelay()

    // Find the institution for the new connection
    const institution = MOCK_INSTITUTIONS.find(
      (i) => i.id === req.institution_id,
    )
    if (!institution) {
      throw new Error(`Institution not found: ${req.institution_id}`)
    }

    // Generate a new connection ID
    const newId = `conn-${Date.now()}`

    // Add to mock data (simulating backend behavior)
    MOCK_CONNECTIONS.push({
      id: newId,
      friendly_name: req.friendly_name,
      provider: 'gocardless',
      institution,
      status: 'pending',
      account_count: 0,
      created_at: new Date().toISOString(),
    })

    return {
      id: newId,
      auth_url: `https://ob.gocardless.com/mock-auth?ref=${newId}`,
    }
  }

  // Update a connection's friendly name
  async function updateConnection(
    id: string,
    req: UpdateConnectionRequest,
  ): Promise<Connection> {
    console.log('[MOCK] PATCH /api/connections/' + id, req)
    await randomDelay()

    const connection = MOCK_CONNECTIONS.find((c) => c.id === id)
    if (!connection) {
      throw new Error(`Connection not found: ${id}`)
    }

    connection.friendly_name = req.friendly_name
    return { ...connection }
  }

  // Delete a connection and its accounts
  async function deleteConnection(id: string): Promise<void> {
    console.log('[MOCK] DELETE /api/connections/' + id)
    await randomDelay()

    const index = MOCK_CONNECTIONS.findIndex((c) => c.id === id)
    if (index === -1) {
      throw new Error(`Connection not found: ${id}`)
    }

    // Remove connection
    MOCK_CONNECTIONS.splice(index, 1)

    // Remove associated accounts
    const accountIndices = MOCK_ACCOUNTS.map((a, i) =>
      a.connection_id === id ? i : -1,
    )
      .filter((i) => i !== -1)
      .reverse() // Reverse to remove from end first
    accountIndices.forEach((i) => MOCK_ACCOUNTS.splice(i, 1))
  }

  // Reauthorise an expired connection
  async function reauthoriseConnection(
    id: string,
  ): Promise<ReauthoriseResponse> {
    console.log('[MOCK] POST /api/connections/' + id + '/reauthorise')
    await randomDelay()

    const connection = MOCK_CONNECTIONS.find((c) => c.id === id)
    if (!connection) {
      throw new Error(`Connection not found: ${id}`)
    }

    return {
      auth_url: `https://ob.gocardless.com/mock-reauth?ref=${id}`,
    }
  }

  // ---------------------------------------------------------------------------
  // Accounts API
  // ---------------------------------------------------------------------------

  // Fetch accounts, optionally filtered by connection
  async function fetchAccounts(
    connectionId?: string,
  ): Promise<AccountListResponse> {
    console.log(
      '[MOCK] GET /api/accounts',
      connectionId ? { connection_id: connectionId } : '',
    )
    await randomDelay()

    let accounts = [...MOCK_ACCOUNTS]
    if (connectionId) {
      accounts = accounts.filter((a) => a.connection_id === connectionId)
    }

    return {
      accounts,
      total: accounts.length,
    }
  }

  // Update an account's display name
  async function updateAccount(
    id: string,
    req: UpdateAccountRequest,
  ): Promise<Account> {
    console.log('[MOCK] PATCH /api/accounts/' + id, req)
    await randomDelay()

    const account = MOCK_ACCOUNTS.find((a) => a.id === id)
    if (!account) {
      throw new Error(`Account not found: ${id}`)
    }

    account.display_name = req.display_name
    return { ...account }
  }

  // ---------------------------------------------------------------------------
  // Institutions API
  // ---------------------------------------------------------------------------

  // Fetch available institutions (banks)
  async function fetchInstitutions(): Promise<InstitutionListResponse> {
    console.log('[MOCK] GET /api/institutions')
    await randomDelay()
    return {
      institutions: [...MOCK_INSTITUTIONS],
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // Connections
    fetchConnections,
    createConnection,
    updateConnection,
    deleteConnection,
    reauthoriseConnection,

    // Accounts
    fetchAccounts,
    updateAccount,

    // Institutions
    fetchInstitutions,
  }
}
