<!-- ==========================================================================
Home Page
Main dashboard showing net worth, spending metrics, and recent transactions
============================================================================ -->

<script setup lang="ts">
import type { Account } from '~/types/accounts'
import type { Transaction, SplitRequest } from '~/types/transactions'
import type { Tag } from '~/types/tags'
import type { Dataset, DatasetQueryResponse } from '~/types/analytics'
import type { BudgetSummaryResponse } from '~/types/budgets'
import type { GoalSummaryResponse } from '~/types/goals'
import type { SpendingPaceResponse } from '~/types/spending'

useHead({ title: 'Home | Finances' })

const authStore = useAuthStore()
const { fetchAccounts } = useAccountsApi()
const { fetchTransactions, setSplits, clearSplits, updateNote } =
  useTransactionsApi()
const { fetchTags, createTag } = useTagsApi()
const { fetchDatasets, queryDataset, fetchAnalyticsStatus, fetchSpendingPace } =
  useAnalyticsApi()
const { fetchBudgetSummary } = useBudgetsApi()
const { fetchGoalSummary } = useGoalsApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Data
const accounts = ref<Account[]>([])
const recentTransactions = ref<Transaction[]>([])
const tags = ref<Tag[]>([])
const monthlyTrends = ref<DatasetQueryResponse | null>(null)
const dailySpendingByTag = ref<DatasetQueryResponse | null>(null)
const budgetSummary = ref<BudgetSummaryResponse | null>(null)
const goalSummary = ref<GoalSummaryResponse | null>(null)
const netWorthHistory = ref<DatasetQueryResponse | null>(null)
const spendingPace = ref<SpendingPaceResponse | null>(null)

// Detail modal state
const detailModalTransaction = ref<Transaction | null>(null)
const showDetailModal = computed(() => detailModalTransaction.value !== null)

// Loading states
const loadingAccounts = ref(true)
const loadingTransactions = ref(true)
const loadingAnalytics = ref(true)
const loadingBudgets = ref(true)
const loadingGoals = ref(true)
const loadingSpendingPace = ref(true)

// Error states
const errorAccounts = ref('')
const errorTransactions = ref('')
const analyticsAvailable = ref(false)

// Dataset IDs (looked up on mount)
const monthlyTrendsDatasetId = ref<string | null>(null)
const dailySpendingDatasetId = ref<string | null>(null)
const netWorthDatasetId = ref<string | null>(null)

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

// Net worth sparkline data (last 30 days of net worth values)
const netWorthSparkline = computed(() => {
  if (!netWorthHistory.value?.rows?.length) return undefined

  // Extract net_worth values, sorted by date
  const sorted = [...netWorthHistory.value.rows].sort((a, b) =>
    (a.balance_date as string).localeCompare(b.balance_date as string),
  )

  // Take last 30 data points for sparkline
  const recent = sorted.slice(-30)
  return recent.map((row) => row.net_worth as number)
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

// This month's income (from monthly trends)
const thisMonthIncome = computed(() => {
  if (!monthlyTrends.value?.rows?.length) return null
  const total = monthlyTrends.value.rows.reduce(
    (sum, row) => sum + ((row.total_income as number) || 0),
    0,
  )
  return total
})

// Spending pace display: "129% of expected" (ratio as percentage)
const paceDisplayValue = computed(() => {
  if (!spendingPace.value || spendingPace.value.pace_status === 'no_history')
    return '—'
  const ratio = spendingPace.value.pace_ratio
  if (ratio === null) return '—'
  return `${Math.round(ratio * 100)}% of expected`
})

// Spending pace subtitle: "£1,113 expected by day 8"
const paceSubtitle = computed(() => {
  if (!spendingPace.value || spendingPace.value.pace_status === 'no_history')
    return 'no data yet'
  const expected = formatCurrency(Number(spendingPace.value.expected_spending))
  return `${expected} expected by day ${spendingPace.value.days_elapsed}`
})

// Spending pace value colour: green when behind/on_track, amber when ahead
const paceValueColor = computed<'positive' | 'negative' | undefined>(() => {
  if (!spendingPace.value || spendingPace.value.pace_status === 'no_history')
    return undefined
  // Behind or on track = spending less than expected = good (green)
  if (
    spendingPace.value.pace_status === 'behind' ||
    spendingPace.value.pace_status === 'on_track'
  )
    return 'positive'
  // Ahead = spending more than expected = bad (red)
  return 'negative'
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
    const netWorthDs = datasets.find(
      (ds: Dataset) => ds.dataset_name === 'fct_net_worth_history',
    )

    monthlyTrendsDatasetId.value = monthlyTrendsDs?.id || null
    dailySpendingDatasetId.value = dailySpendingDs?.id || null
    netWorthDatasetId.value = netWorthDs?.id || null

    // Query monthly trends for current period
    if (monthlyTrendsDatasetId.value) {
      monthlyTrends.value = await queryDataset(monthlyTrendsDatasetId.value, {
        start_date: currentMonthStart.value,
        end_date: today.value,
      })
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

    // Query net worth history for sparkline (last 90 days to have enough data)
    if (netWorthDatasetId.value) {
      const ninetyDaysAgo = new Date()
      ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90)
      netWorthHistory.value = await queryDataset(netWorthDatasetId.value, {
        start_date: ninetyDaysAgo.toISOString().slice(0, 10),
        end_date: today.value,
      })
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

async function loadBudgetSummary() {
  loadingBudgets.value = true
  try {
    budgetSummary.value = await fetchBudgetSummary()
  } catch (e) {
    console.error('Failed to load budget summary:', e)
  } finally {
    loadingBudgets.value = false
  }
}

async function loadGoalSummary() {
  loadingGoals.value = true
  try {
    goalSummary.value = await fetchGoalSummary()
  } catch (e) {
    console.error('Failed to load goal summary:', e)
  } finally {
    loadingGoals.value = false
  }
}

async function loadSpendingPace() {
  loadingSpendingPace.value = true
  try {
    spendingPace.value = await fetchSpendingPace()
  } catch (e) {
    console.error('Failed to load spending pace:', e)
  } finally {
    loadingSpendingPace.value = false
  }
}

// ---------------------------------------------------------------------------
// Transaction tag handlers
// ---------------------------------------------------------------------------

async function handleAddTag(transactionId: string, tagId: string) {
  try {
    const txn = recentTransactions.value.find((t) => t.id === transactionId)
    if (!txn) return
    // Create a 100% split for the tag
    const response = await setSplits(transactionId, {
      splits: [{ tag_id: tagId, amount: Math.abs(txn.amount) }],
    })
    // Update both splits and tags in local state
    txn.splits = response.splits
    txn.tags = response.splits.map((s) => ({
      id: s.tag_id,
      name: s.tag_name,
      colour: s.tag_colour,
      is_auto: s.is_auto,
      rule_id: s.rule_id,
      rule_name: s.rule_name,
    }))
    // Also update detail modal if open
    if (detailModalTransaction.value?.id === transactionId) {
      detailModalTransaction.value.splits = response.splits
      detailModalTransaction.value.tags = txn.tags
    }
  } catch (e) {
    console.error('Failed to add tag:', e)
  }
}

async function handleRemoveTag(transactionId: string, _tagId: string) {
  try {
    // Clear all splits (removes the tag)
    await clearSplits(transactionId)
    // Update local state
    const txn = recentTransactions.value.find((t) => t.id === transactionId)
    if (txn) {
      txn.splits = []
      txn.tags = []
    }
    // Also update detail modal if open
    if (detailModalTransaction.value?.id === transactionId) {
      detailModalTransaction.value.splits = []
      detailModalTransaction.value.tags = []
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

async function handleUpdateNote(transactionId: string, note: string | null) {
  try {
    const updatedTxn = await updateNote(transactionId, { user_note: note })
    // Update the transaction in our list
    const txn = recentTransactions.value.find((t) => t.id === transactionId)
    if (txn) {
      txn.user_note = updatedTxn.user_note
    }
    // Also update detail modal if open
    if (detailModalTransaction.value?.id === transactionId) {
      detailModalTransaction.value.user_note = updatedTxn.user_note
    }
  } catch (e) {
    console.error('Failed to update note:', e)
  }
}

async function handleUpdateSplits(
  transactionId: string,
  splits: SplitRequest[],
) {
  try {
    const response = await setSplits(transactionId, { splits })
    // Derive tags from splits
    const updatedTags = response.splits.map((s) => ({
      id: s.tag_id,
      name: s.tag_name,
      colour: s.tag_colour,
      is_auto: s.is_auto,
      rule_id: s.rule_id,
      rule_name: s.rule_name,
    }))
    // Update the transaction in our list
    const txn = recentTransactions.value.find((t) => t.id === transactionId)
    if (txn) {
      txn.splits = response.splits
      txn.tags = updatedTags
    }
    // Also update detail modal if open
    if (detailModalTransaction.value?.id === transactionId) {
      detailModalTransaction.value.splits = response.splits
      detailModalTransaction.value.tags = updatedTags
    }
  } catch (e) {
    console.error('Failed to update splits:', e)
  }
}

async function handleClearSplits(transactionId: string) {
  try {
    await clearSplits(transactionId)
    // Update the transaction in our list
    const txn = recentTransactions.value.find((t) => t.id === transactionId)
    if (txn) {
      txn.splits = []
      txn.tags = []
    }
    // Also update detail modal if open
    if (detailModalTransaction.value?.id === transactionId) {
      detailModalTransaction.value.splits = []
      detailModalTransaction.value.tags = []
    }
  } catch (e) {
    console.error('Failed to clear splits:', e)
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
  loadBudgetSummary()
  loadGoalSummary()
  loadSpendingPace()
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
        to="/settings/accounts"
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
      <!-- Net Worth - links to net-worth page with sparkline -->
      <HomeMetricCard
        label="Net Worth"
        :value="formatCurrency(netWorth)"
        :trend="netWorthChangePercent"
        :trend-inverted="true"
        :subtitle="netWorthChangePercent !== null ? 'vs last month' : undefined"
        :loading="loadingAccounts"
        :sparkline-data="netWorthSparkline"
        to="/planning/net-worth"
      />

      <!-- This Month Spending - links to transactions for this month -->
      <HomeMetricCard
        label="Spent This Month"
        :value="
          thisMonthSpending !== null ? formatCurrency(thisMonthSpending) : '—'
        "
        :loading="loadingAnalytics"
        :muted="!analyticsAvailable && !loadingAnalytics"
        :to="transactionsLink"
      />

      <!-- Spending Pace - compares current spending vs 90-day historical average -->
      <HomeMetricCard
        label="Spending Pace"
        :value="paceDisplayValue"
        :subtitle="paceSubtitle"
        :value-color="paceValueColor"
        :loading="loadingSpendingPace"
        :muted="!analyticsAvailable && !loadingSpendingPace"
        :to="transactionsLink"
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

    <!-- Upcoming Bills Widget -->
    <SubscriptionsUpcomingBillsWidget v-if="hasAccounts" :days="7" />

    <!-- Budget, Goals & Cash Flow Widgets -->
    <div v-if="hasAccounts" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <BudgetsBudgetSummaryWidget
        :summary="budgetSummary"
        :loading="loadingBudgets"
      />
      <GoalsProgressWidget :summary="goalSummary" :loading="loadingGoals" />
      <CashflowCashFlowWidget
        :income="thisMonthIncome"
        :spending="thisMonthSpending"
        :loading="loadingAnalytics"
      />
    </div>

    <!-- Budget forecast warnings (auto-hides if no budgets at risk) -->
    <BudgetsBudgetWarningsPanel v-if="hasAccounts" />

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
      @create-tag="(txnId, name) => handleCreateTag(txnId, name)"
      @update-note="(txnId, note) => handleUpdateNote(txnId, note)"
      @update-splits="(txnId, splits) => handleUpdateSplits(txnId, splits)"
      @clear-splits="(txnId) => handleClearSplits(txnId)"
    />
  </div>
</template>
