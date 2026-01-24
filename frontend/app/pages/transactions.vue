<!-- ==========================================================================
Transactions Page
Main page for viewing and filtering transactions
Displays transactions grouped by day with infinite scroll
============================================================================ -->

<script setup lang="ts">
import type { Account, Connection } from '~/types/accounts'
import type {
  Transaction,
  TransactionDayGroup,
  TransactionQueryParams,
} from '~/types/transactions'

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const { fetchTransactions } = useTransactionsApi()
const { fetchAccounts, fetchConnections } = useAccountsApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Data
const transactions = ref<Transaction[]>([])
const accounts = ref<Account[]>([])
const connections = ref<Connection[]>([])
const total = ref(0)

// Filters
const filters = ref<TransactionQueryParams>({
  page: 1,
  page_size: 20,
})

// Loading states
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')

// Infinite scroll sentinel element ref
const sentinelRef = ref<HTMLDivElement | null>(null)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Check if there are more transactions to load
const hasMore = computed(() => transactions.value.length < total.value)

// Map of connection_id to friendly_name for building account display strings
const connectionNames = computed((): Record<string, string> => {
  const names: Record<string, string> = {}
  for (const connection of connections.value) {
    names[connection.id] = connection.friendly_name
  }
  return names
})

// Map of account_id to display name for showing in transaction rows
const accountNames = computed((): Record<string, string> => {
  const names: Record<string, string> = {}
  for (const account of accounts.value) {
    names[account.id] =
      account.display_name || account.name || 'Unknown Account'
  }
  return names
})

// Group transactions by booking_date for display
const dayGroups = computed((): TransactionDayGroup[] => {
  // Group transactions by date
  const groups: Record<string, Transaction[]> = {}

  for (const txn of transactions.value) {
    const date = txn.booking_date || 'unknown'
    const existing = groups[date]
    if (existing) {
      existing.push(txn)
    } else {
      groups[date] = [txn]
    }
  }

  // Convert to array and sort by date descending
  const sortedDates = Object.keys(groups).sort((a, b) => b.localeCompare(a))

  return sortedDates.map((date) => {
    const dayTransactions = groups[date]!
    const dayTotal = dayTransactions.reduce((sum, t) => sum + t.amount, 0)

    return {
      date,
      dateDisplay: formatDateDisplay(date),
      transactions: dayTransactions,
      dayTotal,
    }
  })
})

// Check if there are no transactions (after loading)
const isEmpty = computed(
  () => !loading.value && !error.value && transactions.value.length === 0,
)

// Check if filters are active (for empty state messaging)
const hasActiveFilters = computed(() => {
  const f = filters.value
  return !!(
    f.account_id ||
    f.start_date ||
    f.end_date ||
    f.min_amount !== undefined ||
    f.max_amount !== undefined ||
    f.search
  )
})

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

// Format date for display: "Today", "Yesterday", or "Mon 20 Jan"
function formatDateDisplay(dateStr: string): string {
  if (dateStr === 'unknown') return 'Unknown Date'

  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  // Reset times for comparison
  const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const todayOnly = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  )
  const yesterdayOnly = new Date(
    yesterday.getFullYear(),
    yesterday.getMonth(),
    yesterday.getDate(),
  )

  if (dateOnly.getTime() === todayOnly.getTime()) {
    return 'Today'
  }
  if (dateOnly.getTime() === yesterdayOnly.getTime()) {
    return 'Yesterday'
  }

  // Format as "Mon 20 Jan"
  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

// Load initial data (transactions and accounts for filter dropdown)
async function loadData() {
  loading.value = true
  error.value = ''

  try {
    // Fetch transactions, accounts, and connections in parallel
    const [txnResponse, accountsResponse, connectionsResponse] =
      await Promise.all([
        fetchTransactions(filters.value),
        fetchAccounts(),
        fetchConnections(),
      ])

    transactions.value = txnResponse.transactions
    total.value = txnResponse.total
    accounts.value = accountsResponse.accounts
    connections.value = connectionsResponse.connections
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load transactions'
  } finally {
    loading.value = false
  }
}

// Load more transactions (infinite scroll)
async function loadMore() {
  if (loadingMore.value || !hasMore.value) return

  loadingMore.value = true

  try {
    const nextPage = (filters.value.page || 1) + 1
    const response = await fetchTransactions({
      ...filters.value,
      page: nextPage,
    })

    // Append new transactions
    transactions.value = [...transactions.value, ...response.transactions]
    filters.value.page = nextPage
    total.value = response.total
  } catch (e) {
    console.error('Failed to load more transactions:', e)
    // Don't show error for load more failures - user can scroll again
  } finally {
    loadingMore.value = false
  }
}

// Handle filter changes - reset and reload
async function handleFiltersChange(newFilters: TransactionQueryParams) {
  filters.value = { ...newFilters, page: 1 }
  loading.value = true
  error.value = ''

  try {
    const response = await fetchTransactions(filters.value)
    transactions.value = response.transactions
    total.value = response.total
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load transactions'
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Infinite Scroll (IntersectionObserver)
// ---------------------------------------------------------------------------

let observer: IntersectionObserver | null = null

function setupIntersectionObserver() {
  if (!sentinelRef.value) return

  // Disconnect existing observer
  if (observer) {
    observer.disconnect()
  }

  // Create new observer
  // rootMargin: load early when sentinel is 100px from viewport
  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      if (entry?.isIntersecting && hasMore.value && !loadingMore.value) {
        loadMore()
      }
    },
    {
      rootMargin: '100px',
    },
  )

  observer.observe(sentinelRef.value)
}

// Watch for sentinel ref changes
watch(sentinelRef, () => {
  setupIntersectionObserver()
})

// Cleanup observer on unmount
onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
})

// Load data on mount
onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold sm:text-3xl">Transactions</h1>
      <p class="mt-1 text-muted">View and search your transaction history</p>
    </div>

    <!-- Filters -->
    <TransactionsTransactionFilters
      :accounts="accounts"
      :connection-names="connectionNames"
      :model-value="filters"
      @update:model-value="handleFiltersChange"
    />

    <!-- Loading state (initial load) -->
    <div v-if="loading" class="py-12 text-center text-muted">
      Loading transactions...
    </div>

    <!-- Error state -->
    <div
      v-else-if="error"
      class="rounded-lg border border-negative/50 bg-negative/10 px-6 py-4 text-negative"
    >
      {{ error }}
      <button
        type="button"
        class="ml-2 underline hover:no-underline"
        @click="loadData"
      >
        Retry
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="isEmpty"
      class="rounded-lg border border-border bg-surface px-6 py-12 text-center"
    >
      <!-- Receipt icon -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="1.5"
        stroke="currentColor"
        class="mx-auto h-12 w-12 text-muted"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M9 14.25l6-6m4.5-3.493V21.75l-3.75-1.5-3.75 1.5-3.75-1.5-3.75 1.5V4.757c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0c1.1.128 1.907 1.077 1.907 2.185ZM9.75 9h.008v.008H9.75V9Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm4.125 4.5h.008v.008h-.008V13.5Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
        />
      </svg>
      <h3 class="mt-4 font-semibold text-foreground">
        {{
          hasActiveFilters ? 'No matching transactions' : 'No transactions yet'
        }}
      </h3>
      <p class="mt-1 text-sm text-muted">
        {{
          hasActiveFilters
            ? "Try adjusting your filters to find what you're looking for."
            : 'Transactions will appear here once your accounts start syncing.'
        }}
      </p>
    </div>

    <!-- Transaction list grouped by day -->
    <div v-else>
      <TransactionsTransactionDayGroup
        v-for="group in dayGroups"
        :key="group.date"
        :group="group"
        :account-names="accountNames"
      />

      <!-- Infinite scroll sentinel -->
      <!-- This invisible element triggers loading more when scrolled into view -->
      <div v-if="hasMore" ref="sentinelRef" class="flex justify-center py-4">
        <span v-if="loadingMore" class="text-muted">Loading more...</span>
      </div>

      <!-- End of list indicator -->
      <div v-else class="py-4 text-center text-sm text-muted">
        Showing all {{ transactions.length }} transactions
      </div>
    </div>
  </div>
</template>
