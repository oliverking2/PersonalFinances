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
const { fetchAccounts } = useAccountsApi()
const { fetchTransactions } = useTransactionsApi()
const { fetchTags, createTag, addTagsToTransaction, removeTagFromTransaction } =
  useTagsApi()
const { fetchDatasets, queryDataset, fetchAnalyticsStatus } = useAnalyticsApi()

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
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold sm:text-3xl">
        Welcome back,
        {{ authStore.user?.first_name || authStore.user?.username }}
      </h1>
      <p class="mt-1 text-muted">Here's your financial overview</p>
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
      <!-- Net Worth -->
      <HomeMetricCard
        label="Net Worth"
        :value="formatCurrency(netWorth)"
        :loading="loadingAccounts"
      />

      <!-- This Month Spending -->
      <HomeMetricCard
        label="Spent This Month"
        :value="
          thisMonthSpending !== null ? formatCurrency(thisMonthSpending) : '—'
        "
        :loading="loadingAnalytics"
        :muted="!analyticsAvailable && !loadingAnalytics"
      />

      <!-- vs Last Month (positive = spending more = bad = red) -->
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
      />

      <!-- Top Category (this month) -->
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
      />

      <!-- Transaction Count -->
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
