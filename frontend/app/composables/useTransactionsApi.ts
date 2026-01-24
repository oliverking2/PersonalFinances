// =============================================================================
// Transactions API Composable
// API functions for fetching and filtering transactions
// Currently uses mock data - backend builds to this spec
// =============================================================================

import type {
  Transaction,
  TransactionListResponse,
  TransactionQueryParams,
} from '~/types/transactions'

// -----------------------------------------------------------------------------
// Mock Data
// Realistic transactions for development before backend is ready
// Spans the past month with varied merchants, amounts, and categories
// -----------------------------------------------------------------------------

function generateMockTransactions(): Transaction[] {
  const today = new Date()
  const transactions: Transaction[] = []

  // Helper to create a date string N days ago
  const daysAgo = (days: number): string => {
    const date = new Date(today)
    date.setDate(date.getDate() - days)
    return date.toISOString().split('T')[0]!
  }

  // Mock transaction templates with realistic UK data
  const templates = [
    // Income
    {
      merchant: 'ACME Corp',
      desc: 'Salary',
      amount: 3250.0,
      category: 'income',
    },
    {
      merchant: 'HMRC',
      desc: 'Tax Refund',
      amount: 127.45,
      category: 'income',
    },

    // Bills & Utilities
    {
      merchant: 'British Gas',
      desc: 'Energy Bill',
      amount: -89.5,
      category: 'bills',
    },
    {
      merchant: 'Thames Water',
      desc: 'Water Bill',
      amount: -34.0,
      category: 'bills',
    },
    {
      merchant: 'Sky',
      desc: 'TV & Broadband',
      amount: -65.0,
      category: 'bills',
    },
    {
      merchant: 'O2',
      desc: 'Mobile Contract',
      amount: -35.0,
      category: 'bills',
    },
    {
      merchant: 'Council Tax',
      desc: 'Council Tax DD',
      amount: -156.0,
      category: 'bills',
    },

    // Subscriptions
    {
      merchant: 'Netflix',
      desc: 'Subscription',
      amount: -15.99,
      category: 'subscriptions',
    },
    {
      merchant: 'Spotify',
      desc: 'Premium',
      amount: -10.99,
      category: 'subscriptions',
    },
    {
      merchant: 'Amazon Prime',
      desc: 'Membership',
      amount: -8.99,
      category: 'subscriptions',
    },
    {
      merchant: 'Apple',
      desc: 'iCloud Storage',
      amount: -2.99,
      category: 'subscriptions',
    },

    // Groceries
    {
      merchant: 'Tesco',
      desc: 'Groceries',
      amount: -67.32,
      category: 'groceries',
    },
    {
      merchant: 'Sainsburys',
      desc: 'Weekly Shop',
      amount: -84.15,
      category: 'groceries',
    },
    {
      merchant: 'Waitrose',
      desc: 'Food Shop',
      amount: -52.8,
      category: 'groceries',
    },
    {
      merchant: 'Aldi',
      desc: 'Groceries',
      amount: -41.23,
      category: 'groceries',
    },

    // Dining
    {
      merchant: 'Pret A Manger',
      desc: 'Lunch',
      amount: -8.45,
      category: 'dining',
    },
    {
      merchant: 'Costa Coffee',
      desc: 'Coffee',
      amount: -4.2,
      category: 'dining',
    },
    { merchant: 'Wagamama', desc: 'Dinner', amount: -24.5, category: 'dining' },
    {
      merchant: 'Deliveroo',
      desc: 'Food Delivery',
      amount: -32.99,
      category: 'dining',
    },
    { merchant: 'Greggs', desc: 'Lunch', amount: -5.8, category: 'dining' },

    // Transport
    {
      merchant: 'TfL',
      desc: 'Oyster Top-up',
      amount: -40.0,
      category: 'transport',
    },
    { merchant: 'Shell', desc: 'Fuel', amount: -65.0, category: 'transport' },
    { merchant: 'Uber', desc: 'Trip', amount: -18.5, category: 'transport' },
    {
      merchant: 'Trainline',
      desc: 'Train Ticket',
      amount: -47.0,
      category: 'transport',
    },

    // Shopping
    { merchant: 'Amazon', desc: 'Order', amount: -29.99, category: 'shopping' },
    {
      merchant: 'John Lewis',
      desc: 'Homeware',
      amount: -89.0,
      category: 'shopping',
    },
    {
      merchant: 'Boots',
      desc: 'Pharmacy',
      amount: -12.5,
      category: 'shopping',
    },
    {
      merchant: 'Currys',
      desc: 'Electronics',
      amount: -149.0,
      category: 'shopping',
    },

    // Entertainment
    {
      merchant: 'Odeon',
      desc: 'Cinema',
      amount: -24.0,
      category: 'entertainment',
    },
    {
      merchant: 'Gym',
      desc: 'Membership',
      amount: -45.0,
      category: 'entertainment',
    },

    // Transfers
    {
      merchant: null,
      desc: 'Transfer to Savings',
      amount: -500.0,
      category: 'transfer',
    },
    {
      merchant: null,
      desc: 'From Joint Account',
      amount: 250.0,
      category: 'transfer',
    },
  ]

  // Generate ~50 transactions spread over the past month
  let id = 1
  for (let day = 0; day < 30; day++) {
    // Vary number of transactions per day (0-4)
    const numTransactions = Math.floor(Math.random() * 5)

    for (let i = 0; i < numTransactions; i++) {
      const template = templates[Math.floor(Math.random() * templates.length)]!
      const date = daysAgo(day)

      // Add some variance to amounts (except income which stays fixed)
      let amount = template.amount
      if (template.category !== 'income' && template.category !== 'transfer') {
        const variance = 1 + (Math.random() - 0.5) * 0.3 // +/- 15%
        amount = Math.round(template.amount * variance * 100) / 100
      }

      transactions.push({
        id: `txn-${id++}`,
        account_id: day % 3 === 0 ? 'acc-2' : 'acc-1', // Mostly from main account
        booking_date: date,
        value_date: date,
        amount,
        currency: 'GBP',
        description: template.desc,
        merchant_name: template.merchant,
        category: template.category,
      })
    }
  }

  // Sort by date descending
  transactions.sort((a, b) => {
    const dateA = a.booking_date || ''
    const dateB = b.booking_date || ''
    return dateB.localeCompare(dateA)
  })

  return transactions
}

// Generate mock data once
const MOCK_TRANSACTIONS = generateMockTransactions()

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

export function useTransactionsApi() {
  // ---------------------------------------------------------------------------
  // Transactions API
  // ---------------------------------------------------------------------------

  // Fetch transactions with optional filters and pagination
  async function fetchTransactions(
    params: TransactionQueryParams = {},
  ): Promise<TransactionListResponse> {
    console.log('[MOCK] GET /api/transactions', params)
    await randomDelay()

    let filtered = [...MOCK_TRANSACTIONS]

    // Apply filters
    if (params.account_id) {
      filtered = filtered.filter((t) => t.account_id === params.account_id)
    }

    if (params.start_date) {
      filtered = filtered.filter(
        (t) => t.booking_date && t.booking_date >= params.start_date!,
      )
    }

    if (params.end_date) {
      filtered = filtered.filter(
        (t) => t.booking_date && t.booking_date <= params.end_date!,
      )
    }

    if (params.min_amount !== undefined) {
      filtered = filtered.filter((t) => t.amount >= params.min_amount!)
    }

    if (params.max_amount !== undefined) {
      filtered = filtered.filter((t) => t.amount <= params.max_amount!)
    }

    if (params.search) {
      const searchLower = params.search.toLowerCase()
      filtered = filtered.filter(
        (t) =>
          t.description?.toLowerCase().includes(searchLower) ||
          t.merchant_name?.toLowerCase().includes(searchLower),
      )
    }

    // Pagination
    const page = params.page || 1
    const pageSize = params.page_size || 20
    const start = (page - 1) * pageSize
    const end = start + pageSize
    const paginated = filtered.slice(start, end)

    return {
      transactions: paginated,
      total: filtered.length,
      page,
      page_size: pageSize,
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    fetchTransactions,
  }
}
