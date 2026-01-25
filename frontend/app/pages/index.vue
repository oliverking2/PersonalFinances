<!-- ==========================================================================
Home Page
Main dashboard showing net worth, spending metrics, and recent transactions
============================================================================ -->

<script setup lang="ts">
import type { Account } from '~/types/accounts'
import type { Transaction } from '~/types/transactions'
import type { Tag } from '~/types/tags'
import type { Dataset, DatasetQueryResponse } from '~/types/analytics'

useHead({ title: 'Home | Finances' })

const authStore = useAuthStore()
const toast = useToastStore()
const {
  fetchAccounts,
  fetchConnections,
  triggerConnectionSync,
  fetchJob,
  fetchJobs,
} = useAccountsApi()
const { fetchTransactions } = useTransactionsApi()
const { fetchTags, createTag, addTagsToTransaction, removeTagFromTransaction } =
  useTagsApi()
const { fetchDatasets, queryDataset, fetchAnalyticsStatus, triggerRefresh } =
  useAnalyticsApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Data
const accounts = ref<Account[]>([])
const recentTransactions = ref<Transaction[]>([])
const tags = ref<Tag[]>([])
const monthlyTrends = ref<DatasetQueryResponse | null>(null)
const dailySpendingByTag = ref<DatasetQueryResponse | null>(null)

// Detail modal state
const detailModalTransaction = ref<Transaction | null>(null)
const showDetailModal = computed(() => detailModalTransaction.value !== null)

// Loading states
const loadingAccounts = ref(true)
const loadingTransactions = ref(true)
const loadingAnalytics = ref(true)

// Error states
const errorAccounts = ref('')
const errorTransactions = ref('')
const analyticsAvailable = ref(false)

// Dataset IDs (looked up on mount)
const monthlyTrendsDatasetId = ref<string | null>(null)
const dailySpendingDatasetId = ref<string | null>(null)

// Refresh states
const refreshingAll = ref(false)
const refreshingAnalytics = ref(false)

// ---------------------------------------------------------------------------
// Computed: Date ranges
// ---------------------------------------------------------------------------

// Current month: 1st of month to today (YYYY-MM-DD format)
const currentMonthStart = computed(() => {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .slice(0, 10)
})
const today = computed(() => {
  return new Date().toISOString().slice(0, 10)
})

// Last month: same day range as current month (1st to same day of month)
// e.g., if today is Jan 25, compare Dec 1-25
const lastMonthStart = computed(() => {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth() - 1, 1)
    .toISOString()
    .slice(0, 10)
})
const lastMonthSameDay = computed(() => {
  const now = new Date()
  // Same day of last month, capped at last day of that month
  // e.g., Jan 31 -> Dec 31, but Mar 31 -> Feb 28/29 (since Feb doesn't have 31)
  const lastDayOfPrevMonth = new Date(
    now.getFullYear(),
    now.getMonth(),
    0,
  ).getDate()
  const day = Math.min(now.getDate(), lastDayOfPrevMonth)
  return new Date(now.getFullYear(), now.getMonth() - 1, day)
    .toISOString()
    .slice(0, 10)
})

// ---------------------------------------------------------------------------
// Computed: Metrics
// ---------------------------------------------------------------------------

// Net worth: sum of all account balances
const netWorth = computed(() => {
  return accounts.value.reduce(
    (sum, acc) => sum + (acc.balance?.amount || 0),
    0,
  )
})

// This month's spending (from monthly trends)
const thisMonthSpending = computed(() => {
  if (!monthlyTrends.value?.rows?.length) return null
  // Sum spending across all rows for current month
  // Monthly trends may have multiple rows per currency
  const total = monthlyTrends.value.rows.reduce(
    (sum, row) => sum + ((row.total_spending as number) || 0),
    0,
  )
  return total
})

// Last month's spending (calculated from trends)
const lastMonthSpending = computed(() => {
  // We query separately for last month, store in a ref
  return lastMonthSpendingValue.value
})
const lastMonthSpendingValue = ref<number | null>(null)

// Spending change percentage
const spendingChangePercent = computed(() => {
  if (thisMonthSpending.value === null || lastMonthSpending.value === null)
    return null
  if (lastMonthSpending.value === 0) return null
  return (
    ((thisMonthSpending.value - lastMonthSpending.value) /
      lastMonthSpending.value) *
    100
  )
})

// This month's transaction count
const thisMonthTransactionCount = computed(() => {
  if (!monthlyTrends.value?.rows?.length) return null
  const total = monthlyTrends.value.rows.reduce(
    (sum, row) => sum + ((row.total_transactions as number) || 0),
    0,
  )
  return total
})

// Net change this month from monthly trends data
const thisMonthNetChange = computed(() => {
  if (!monthlyTrends.value?.rows?.length) return null
  return monthlyTrends.value.rows.reduce(
    (sum, row) => sum + ((row.net_change as number) || 0),
    0,
  )
})

// Previous month's net worth (approximated: current net worth minus this month's net change)
const previousNetWorth = computed(() => {
  if (thisMonthNetChange.value === null) return null
  return netWorth.value - thisMonthNetChange.value
})

// Net worth percentage change from last month
const netWorthChangePercent = computed(() => {
  if (previousNetWorth.value === null || previousNetWorth.value === 0)
    return null
  return (
    ((netWorth.value - previousNetWorth.value) /
      Math.abs(previousNetWorth.value)) *
    100
  )
})

// Top spending category this month (includes "Untagged" for transactions without tags)
const topCategory = computed(() => {
  if (!dailySpendingByTag.value?.rows?.length) return null

  // Aggregate by tag_name across all days
  const byTag = new Map<
    string,
    { name: string; total: number; colour: string }
  >()

  for (const row of dailySpendingByTag.value.rows) {
    // Treat null/undefined tag_name as "Untagged"
    const rawTagName = row.tag_name as string | null | undefined
    const tagName = rawTagName || 'Untagged'
    const spending = (row.total_spending as number) || 0
    // Use grey for untagged, otherwise use tag colour
    const colour = rawTagName
      ? (row.tag_colour as string) || '#6ee7b7'
      : '#6b7280'

    const existing = byTag.get(tagName)
    if (existing) {
      existing.total += spending
    } else {
      byTag.set(tagName, { name: tagName, total: spending, colour })
    }
  }

  // Find the tag with highest spending
  let top: { name: string; total: number; colour: string } | null = null
  for (const tag of byTag.values()) {
    if (!top || tag.total > top.total) {
      top = tag
    }
  }

  return top
})

// ---------------------------------------------------------------------------
// Computed: Navigation links for metric cards
// ---------------------------------------------------------------------------

// Top category link - navigates to transactions filtered by this tag
const topCategoryLink = computed(() => {
  if (!topCategory.value || !analyticsAvailable.value) return undefined
  const params = new URLSearchParams()
  params.set('start_date', currentMonthStart.value)
  params.set('end_date', today.value)
  if (topCategory.value.name === 'Untagged') {
    params.set('untagged', 'true')
  } else {
    params.set('tag', topCategory.value.name)
  }
  return `/transactions?${params.toString()}`
})

// Transactions link - navigates to transactions for this month
const transactionsLink = computed(() => {
  if (!analyticsAvailable.value) return undefined
  const params = new URLSearchParams()
  params.set('start_date', currentMonthStart.value)
  params.set('end_date', today.value)
  return `/transactions?${params.toString()}`
})

// ---------------------------------------------------------------------------
// Computed: Display helpers
// ---------------------------------------------------------------------------

const hasAccounts = computed(() => accounts.value.length > 0)
const hasTransactions = computed(() => recentTransactions.value.length > 0)

// Group transactions by day for display
const transactionsByDay = computed(() => {
  const groups = new Map<string, Transaction[]>()

  for (const txn of recentTransactions.value) {
    const date = txn.booking_date || txn.value_date || 'Unknown'
    const existing = groups.get(date)
    if (existing) {
      existing.push(txn)
    } else {
      groups.set(date, [txn])
    }
  }

  // Convert to array sorted by date descending
  return Array.from(groups.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, txns]) => ({ date, transactions: txns }))
})

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function formatDateLabel(dateStr: string): string {
  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (dateStr === today.toISOString().slice(0, 10)) {
    return 'Today'
  }
  if (dateStr === yesterday.toISOString().slice(0, 10)) {
    return 'Yesterday'
  }

  return date.toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

async function loadAccounts() {
  loadingAccounts.value = true
  errorAccounts.value = ''
  try {
    const response = await fetchAccounts()
    accounts.value = response.accounts
  } catch (e) {
    errorAccounts.value =
      e instanceof Error ? e.message : 'Failed to load accounts'
  } finally {
    loadingAccounts.value = false
  }
}

async function loadRecentTransactions() {
  loadingTransactions.value = true
  errorTransactions.value = ''
  try {
    const response = await fetchTransactions({ page_size: 10 })
    recentTransactions.value = response.transactions
  } catch (e) {
    errorTransactions.value =
      e instanceof Error ? e.message : 'Failed to load transactions'
  } finally {
    loadingTransactions.value = false
  }
}

async function loadAnalytics() {
  loadingAnalytics.value = true
  try {
    // Check if analytics is available
    const status = await fetchAnalyticsStatus()
    analyticsAvailable.value =
      status.duckdb_available && status.manifest_available

    if (!analyticsAvailable.value) {
      loadingAnalytics.value = false
      return
    }

    // Look up dataset IDs
    const datasetsResponse = await fetchDatasets()
    const datasets = datasetsResponse.datasets

    const monthlyTrendsDs = datasets.find(
      (ds: Dataset) => ds.dataset_name === 'fct_monthly_trends',
    )
    const dailySpendingDs = datasets.find(
      (ds: Dataset) => ds.dataset_name === 'fct_daily_spending_by_tag',
    )

    monthlyTrendsDatasetId.value = monthlyTrendsDs?.id || null
    dailySpendingDatasetId.value = dailySpendingDs?.id || null

    // Query monthly trends for current period and same period last month
    // Uses same day range for fair comparison (e.g., Jan 1-25 vs Dec 1-25)
    if (monthlyTrendsDatasetId.value) {
      const [currentMonth, lastMonth] = await Promise.all([
        queryDataset(monthlyTrendsDatasetId.value, {
          start_date: currentMonthStart.value,
          end_date: today.value,
        }),
        queryDataset(monthlyTrendsDatasetId.value, {
          start_date: lastMonthStart.value,
          end_date: lastMonthSameDay.value,
        }),
      ])

      monthlyTrends.value = currentMonth

      // Calculate last month spending
      if (lastMonth.rows?.length) {
        lastMonthSpendingValue.value = lastMonth.rows.reduce(
          (sum, row) => sum + ((row.total_spending as number) || 0),
          0,
        )
      }
    }

    // Query daily spending by tag for current period (for top category)
    if (dailySpendingDatasetId.value) {
      dailySpendingByTag.value = await queryDataset(
        dailySpendingDatasetId.value,
        {
          start_date: currentMonthStart.value,
          end_date: today.value,
        },
      )
    }
  } catch (e) {
    // Analytics errors are non-fatal - we still show net worth from accounts
    console.error('Failed to load analytics:', e)
    analyticsAvailable.value = false
  } finally {
    loadingAnalytics.value = false
  }
}

async function loadTags() {
  try {
    const response = await fetchTags()
    tags.value = response.tags
  } catch (e) {
    console.error('Failed to load tags:', e)
  }
}

// ---------------------------------------------------------------------------
// Transaction tag handlers
// ---------------------------------------------------------------------------

async function handleAddTag(transactionId: string, tagId: string) {
  try {
    const response = await addTagsToTransaction(transactionId, {
      tag_ids: [tagId],
    })
    // Update the transaction's tags in our list
    const txn = recentTransactions.value.find((t) => t.id === transactionId)
    if (txn) {
      txn.tags = response.tags
    }
    // Also update detail modal if open
    if (detailModalTransaction.value?.id === transactionId) {
      detailModalTransaction.value.tags = response.tags
    }
  } catch (e) {
    console.error('Failed to add tag:', e)
  }
}

async function handleRemoveTag(transactionId: string, tagId: string) {
  try {
    const response = await removeTagFromTransaction(transactionId, tagId)
    // Update the transaction's tags in our list
    const txn = recentTransactions.value.find((t) => t.id === transactionId)
    if (txn) {
      txn.tags = response.tags
    }
    // Also update detail modal if open
    if (detailModalTransaction.value?.id === transactionId) {
      detailModalTransaction.value.tags = response.tags
    }
  } catch (e) {
    console.error('Failed to remove tag:', e)
  }
}

async function handleCreateTag(transactionId: string, name: string) {
  try {
    // Create the tag first
    const newTag = await createTag({ name })
    tags.value.push(newTag)
    // Then add it to the transaction
    await handleAddTag(transactionId, newTag.id)
  } catch (e) {
    console.error('Failed to create tag:', e)
  }
}

// ---------------------------------------------------------------------------
// Detail modal handlers
// ---------------------------------------------------------------------------

function handleOpenDetail(transaction: Transaction) {
  detailModalTransaction.value = transaction
}

function handleCloseDetail() {
  detailModalTransaction.value = null
}

// ---------------------------------------------------------------------------
// Refresh handlers
// ---------------------------------------------------------------------------

// Sync all bank connections to get latest transactions
async function handleRefreshAll() {
  if (refreshingAll.value) return

  refreshingAll.value = true
  try {
    // Get all connections
    const { connections } = await fetchConnections()

    if (connections.length === 0) {
      toast.info('No bank connections to sync')
      return
    }

    toast.info(`Syncing ${connections.length} bank connection(s)...`)

    // Trigger sync for each connection and wait for completion
    const syncPromises = connections.map(async (conn) => {
      const job = await triggerConnectionSync(conn.id)
      await pollJobStatus(job.id)
    })

    await Promise.all(syncPromises)

    // Reload data after sync
    await Promise.all([loadAccounts(), loadRecentTransactions()])
    toast.success('Bank connections synced successfully')
  } catch (e) {
    console.error('Failed to refresh:', e)
    const message =
      e instanceof Error ? e.message : 'Failed to sync connections'
    errorAccounts.value = message
    toast.error(message)
  } finally {
    refreshingAll.value = false
  }
}

// Trigger analytics rebuild (dbt)
async function handleRefreshAnalytics() {
  if (refreshingAnalytics.value) return

  refreshingAnalytics.value = true
  try {
    // Check if there's already a running analytics refresh job
    // Backend creates these with job_type='sync' and entity_type='analytics'
    const existingJobs = await fetchJobs({
      entity_type: 'analytics',
      job_type: 'sync',
      limit: 5,
    })
    const runningJob = existingJobs.jobs.find(
      (job) => job.status === 'pending' || job.status === 'running',
    )

    if (runningJob) {
      // Poll the existing job instead of starting a new one
      toast.info(
        'Analytics refresh already in progress, waiting for it to complete...',
      )
      await pollJobStatus(runningJob.id)
    } else {
      // Start a new refresh
      toast.info('Starting analytics refresh...')
      const response = await triggerRefresh()

      // Check if Dagster is unavailable
      if (response.status === 'failed') {
        toast.error(response.message || 'Failed to start analytics refresh')
        return
      }

      await pollJobStatus(response.job_id)
    }

    // Reload analytics after refresh
    await loadAnalytics()
    toast.success('Analytics refreshed successfully')
  } catch (e) {
    console.error('Failed to refresh analytics:', e)
    toast.error(e instanceof Error ? e.message : 'Failed to refresh analytics')
  } finally {
    refreshingAnalytics.value = false
  }
}

// Poll job status until completed or failed
async function pollJobStatus(jobId: string) {
  const maxAttempts = 60 // 5 minutes max
  let attempts = 0

  while (attempts < maxAttempts) {
    const job = await fetchJob(jobId)

    if (job.status === 'completed') {
      return
    }

    if (job.status === 'failed') {
      throw new Error('Job failed')
    }

    // Wait 5 seconds before next poll
    await new Promise((resolve) => setTimeout(resolve, 5000))
    attempts++
  }

  throw new Error('Job timed out')
}

// Load all data on mount
onMounted(() => {
  loadAccounts()
  loadRecentTransactions()
  loadTags()
  loadAnalytics()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page header with refresh buttons -->
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">
          Welcome back,
          {{ authStore.user?.first_name || authStore.user?.username }}
        </h1>
        <p class="mt-1 text-muted">Here's your financial overview</p>
      </div>

      <!-- Refresh buttons -->
      <div class="flex gap-2">
        <!-- Refresh Analytics button -->
        <AppButton
          :disabled="refreshingAnalytics || refreshingAll"
          @click="handleRefreshAnalytics"
        >
          <span class="flex items-center gap-2">
            <!-- Spinner when refreshing -->
            <svg
              v-if="refreshingAnalytics"
              class="h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <!-- Chart icon -->
            <svg
              v-else
              class="h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            {{ refreshingAnalytics ? 'Refreshing...' : 'Refresh Analytics' }}
          </span>
        </AppButton>

        <!-- Refresh All button (sync bank connections) -->
        <AppButton
          :disabled="refreshingAll || refreshingAnalytics"
          @click="handleRefreshAll"
        >
          <span class="flex items-center gap-2">
            <!-- Spinner when refreshing -->
            <svg
              v-if="refreshingAll"
              class="h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <!-- Refresh icon -->
            <svg
              v-else
              class="h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            {{ refreshingAll ? 'Syncing...' : 'Refresh All' }}
          </span>
        </AppButton>
      </div>
    </div>

    <!-- Error states -->
    <div
      v-if="errorAccounts"
      class="rounded-lg border border-negative/50 bg-negative/10 p-4 text-negative"
    >
      {{ errorAccounts }}
    </div>

    <!-- No accounts state -->
    <div
      v-if="!loadingAccounts && !hasAccounts"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p class="text-muted">No bank accounts connected yet.</p>
      <NuxtLink
        to="/accounts"
        class="mt-4 inline-block text-primary hover:text-primary-hover"
      >
        Connect a bank account →
      </NuxtLink>
    </div>

    <!-- Metrics grid -->
    <div
      v-if="hasAccounts || loadingAccounts"
      class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
    >
      <!-- Net Worth - links to accounts page -->
      <HomeMetricCard
        label="Net Worth"
        :value="formatCurrency(netWorth)"
        :trend="netWorthChangePercent"
        :trend-inverted="true"
        :subtitle="netWorthChangePercent !== null ? 'vs last month' : undefined"
        :loading="loadingAccounts"
        to="/accounts"
      />

      <!-- This Month Spending - links to analytics page -->
      <HomeMetricCard
        label="Spent This Month"
        :value="
          thisMonthSpending !== null ? formatCurrency(thisMonthSpending) : '—'
        "
        :loading="loadingAnalytics"
        :muted="!analyticsAvailable && !loadingAnalytics"
        :to="analyticsAvailable ? '/analytics' : undefined"
      />

      <!-- vs Last Month (positive = spending more = bad = red) - links to analytics page -->
      <HomeMetricCard
        label="vs Last Month"
        :value="
          spendingChangePercent !== null
            ? `${spendingChangePercent >= 0 ? '+' : ''}${spendingChangePercent.toFixed(1)}%`
            : '—'
        "
        :subtitle="
          spendingChangePercent !== null
            ? spendingChangePercent >= 0
              ? 'more'
              : 'less'
            : ''
        "
        :value-color="
          spendingChangePercent !== null
            ? spendingChangePercent >= 0
              ? 'negative'
              : 'positive'
            : undefined
        "
        :loading="loadingAnalytics"
        :muted="!analyticsAvailable && !loadingAnalytics"
        :to="analyticsAvailable ? '/analytics' : undefined"
      />

      <!-- Top Category (this month) - links to transactions filtered by tag -->
      <HomeMetricCard
        label="Top Category"
        :value="topCategory?.name || '—'"
        :subtitle="
          topCategory
            ? `${formatCurrency(topCategory.total)} this month`
            : 'this month'
        "
        :loading="loadingAnalytics"
        :muted="!analyticsAvailable && !loadingAnalytics"
        :to="topCategoryLink"
      />

      <!-- Transaction Count - links to transactions for this month -->
      <HomeMetricCard
        label="Transactions"
        :value="
          thisMonthTransactionCount !== null
            ? thisMonthTransactionCount.toString()
            : '—'
        "
        subtitle="this month"
        :loading="loadingAnalytics"
        :muted="!analyticsAvailable && !loadingAnalytics"
        :to="transactionsLink"
      />
    </div>

    <!-- Analytics unavailable notice -->
    <div
      v-if="!loadingAnalytics && !analyticsAvailable && hasAccounts"
      class="rounded-lg border border-warning/50 bg-warning/10 p-3 text-sm text-warning"
    >
      Analytics data is being prepared. Spending metrics will appear after the
      next data refresh.
    </div>

    <!-- Recent Transactions Section -->
    <div v-if="hasAccounts || loadingAccounts" class="space-y-4">
      <!-- Section header -->
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">Recent Transactions</h2>
        <NuxtLink
          to="/transactions"
          class="text-sm text-primary hover:text-primary-hover"
        >
          View all →
        </NuxtLink>
      </div>

      <!-- Loading state -->
      <div
        v-if="loadingTransactions"
        class="space-y-3 rounded-lg border border-border bg-surface p-4"
      >
        <div v-for="i in 3" :key="i" class="flex items-center justify-between">
          <div class="space-y-2">
            <div class="h-4 w-32 animate-pulse rounded bg-border" />
            <div class="h-3 w-20 animate-pulse rounded bg-border" />
          </div>
          <div class="h-5 w-16 animate-pulse rounded bg-border" />
        </div>
      </div>

      <!-- No transactions -->
      <div
        v-else-if="!hasTransactions"
        class="rounded-lg border border-border bg-surface p-6 text-center text-muted"
      >
        No transactions yet.
      </div>

      <!-- Transaction list grouped by day -->
      <div v-else class="rounded-lg border border-border bg-surface">
        <div
          v-for="(group, groupIdx) in transactionsByDay"
          :key="group.date"
          :class="{ 'border-t border-border': groupIdx > 0 }"
        >
          <!-- Day header -->
          <div class="border-b border-border bg-background/50 px-4 py-2">
            <span class="text-sm font-medium text-muted">
              {{ formatDateLabel(group.date) }}
            </span>
          </div>

          <!-- Transactions for this day -->
          <TransactionsTransactionRow
            v-for="txn in group.transactions"
            :key="txn.id"
            :transaction="txn"
            :available-tags="tags"
            :selectable="false"
            @add-tag="handleAddTag(txn.id, $event)"
            @remove-tag="handleRemoveTag(txn.id, $event)"
            @create-tag="handleCreateTag(txn.id, $event)"
            @open-detail="handleOpenDetail(txn)"
          />
        </div>
      </div>
    </div>

    <!-- Transaction Detail Modal -->
    <TransactionsTransactionDetailModal
      :show="showDetailModal"
      :transaction="detailModalTransaction"
      :available-tags="tags"
      @close="handleCloseDetail"
      @add-tag="(txnId, tagId) => handleAddTag(txnId, tagId)"
      @remove-tag="(txnId, tagId) => handleRemoveTag(txnId, tagId)"
      @create-tag="(txnId, name) => handleCreateTag(txnId, name)"
    />
  </div>
</template>
