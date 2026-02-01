<!-- ==========================================================================
Net Worth Page
Net worth history, account breakdown, and milestone tracking
============================================================================ -->

<script setup lang="ts">
import type { Dataset, DatasetQueryResponse } from '~/types/analytics'
import type { Milestone, MilestoneCreateRequest } from '~/types/milestones'

useHead({ title: 'Net Worth | Finances' })

const toast = useToastStore()
const { fetchDatasets, queryDataset, fetchAnalyticsStatus } = useAnalyticsApi()
const {
  fetchMilestones,
  createMilestone,
  updateMilestone,
  deleteMilestone,
  achieveMilestone,
} = useMilestonesApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Raw data from API
const netWorthHistory = ref<DatasetQueryResponse | null>(null)
const balanceHistory = ref<DatasetQueryResponse | null>(null)
const milestones = ref<Milestone[]>([])

// Dataset IDs (looked up on mount)
const netWorthDatasetId = ref<string | null>(null)
const balanceHistoryDatasetId = ref<string | null>(null)

// Loading states
const loading = ref(true)
const error = ref('')
const analyticsAvailable = ref(false)

// Milestone modal state
const showMilestoneModal = ref(false)
const editingMilestone = ref<Milestone | null>(null)
const showDeleteConfirm = ref(false)
const deletingMilestone = ref<Milestone | null>(null)

// Period filter state
const selectedPeriod = ref<
  'last_30_days' | 'last_90_days' | 'last_6_months' | 'last_year' | 'all_time'
>('last_90_days')

// ---------------------------------------------------------------------------
// Computed: Date ranges based on selected period
// ---------------------------------------------------------------------------

const periodDateRange = computed(() => {
  const now = new Date()
  let startDate: Date

  switch (selectedPeriod.value) {
    case 'last_30_days':
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      break
    case 'last_90_days':
      startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
      break
    case 'last_6_months':
      startDate = new Date(now.getTime() - 180 * 24 * 60 * 60 * 1000)
      break
    case 'last_year':
      startDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000)
      break
    case 'all_time':
      startDate = new Date(2020, 0, 1) // Far back enough
      break
    default:
      startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
  }

  return {
    start_date: startDate.toISOString().slice(0, 10),
    end_date: now.toISOString().slice(0, 10),
  }
})

const periodOptions = [
  { value: 'last_30_days', label: '30 Days' },
  { value: 'last_90_days', label: '90 Days' },
  { value: 'last_6_months', label: '6 Months' },
  { value: 'last_year', label: '1 Year' },
  { value: 'all_time', label: 'All Time' },
]

// ---------------------------------------------------------------------------
// Computed: Processed data for charts
// ---------------------------------------------------------------------------

// Net worth chart data
const netWorthChartData = computed(() => {
  if (!netWorthHistory.value?.rows?.length) return []

  return netWorthHistory.value.rows.map((row) => ({
    balance_date: row.balance_date as string,
    net_worth: row.net_worth as number,
    daily_change: (row.daily_change as number) || 0,
    rolling_7d_avg: row.rolling_7d_avg as number | null | undefined,
    currency: (row.currency as string) || 'GBP',
  }))
})

// Account breakdown from balance history
const accountBreakdown = computed(() => {
  if (!balanceHistory.value?.rows?.length) return []

  // Get latest balance for each account
  const latestByAccount = new Map<
    string,
    {
      account_id: string
      account_name: string
      account_type: string
      balance_amount: number
      total_value: number | null
      currency: string
      balance_date: string
    }
  >()

  for (const row of balanceHistory.value.rows) {
    const accountId = row.account_id as string
    const existing = latestByAccount.get(accountId)
    const rowDate = row.balance_date as string

    if (!existing || rowDate > existing.balance_date) {
      latestByAccount.set(accountId, {
        account_id: accountId,
        account_name: row.account_name as string,
        account_type: row.account_type as string,
        balance_amount: row.balance_amount as number,
        total_value: row.total_value as number | null,
        currency: (row.balance_currency as string) || 'GBP',
        balance_date: rowDate,
      })
    }
  }

  // Sort by value descending
  return Array.from(latestByAccount.values()).sort((a, b) => {
    const aValue =
      a.account_type === 'trading' && a.total_value
        ? a.total_value
        : a.balance_amount
    const bValue =
      b.account_type === 'trading' && b.total_value
        ? b.total_value
        : b.balance_amount
    return bValue - aValue
  })
})

// Total net worth from latest data point
const currentNetWorth = computed(() => {
  if (!netWorthChartData.value.length) return 0
  return (
    netWorthChartData.value[netWorthChartData.value.length - 1]?.net_worth ?? 0
  )
})

// Period change metrics
const periodMetrics = computed(() => {
  if (netWorthChartData.value.length < 2) {
    return { change: 0, percentChange: 0, startValue: 0 }
  }

  const startValue = netWorthChartData.value[0]?.net_worth ?? 0
  const endValue =
    netWorthChartData.value[netWorthChartData.value.length - 1]?.net_worth ?? 0
  const change = endValue - startValue
  const percentChange = startValue !== 0 ? (change / startValue) * 100 : 0

  return { change, percentChange, startValue }
})

// Transform milestones for chart display (only pending milestones)
const chartMilestones = computed(() => {
  return milestones.value
    .filter((m) => !m.achieved)
    .map((m) => ({
      name: m.name,
      target_amount: parseFloat(m.target_amount),
      target_date: m.target_date,
    }))
})

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    // Fetch milestones (independent of analytics)
    try {
      const milestonesResponse = await fetchMilestones()
      milestones.value = milestonesResponse.milestones
    } catch {
      // Milestones are optional, don't fail page load
      milestones.value = []
    }

    // Check if analytics is available
    const status = await fetchAnalyticsStatus()
    analyticsAvailable.value =
      status.duckdb_available && status.manifest_available

    if (!analyticsAvailable.value) {
      loading.value = false
      return
    }

    // Look up dataset IDs
    const datasetsResponse = await fetchDatasets()
    const datasets = datasetsResponse.datasets

    const netWorthDs = datasets.find(
      (ds: Dataset) => ds.dataset_name === 'fct_net_worth_history',
    )
    const balanceHistoryDs = datasets.find(
      (ds: Dataset) => ds.dataset_name === 'fct_daily_balance_history',
    )

    netWorthDatasetId.value = netWorthDs?.id || null
    balanceHistoryDatasetId.value = balanceHistoryDs?.id || null

    // Fetch data for current period
    await fetchPeriodData()
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : 'Failed to load net worth data'
    analyticsAvailable.value = false
  } finally {
    loading.value = false
  }
}

async function fetchPeriodData() {
  const queries: Promise<DatasetQueryResponse>[] = []

  // Net worth history
  if (netWorthDatasetId.value) {
    queries.push(
      queryDataset(netWorthDatasetId.value, {
        start_date: periodDateRange.value.start_date,
        end_date: periodDateRange.value.end_date,
        limit: 10000,
      }),
    )
  }

  // Balance history for account breakdown
  if (balanceHistoryDatasetId.value) {
    queries.push(
      queryDataset(balanceHistoryDatasetId.value, {
        start_date: periodDateRange.value.start_date,
        end_date: periodDateRange.value.end_date,
        limit: 10000,
      }),
    )
  }

  const results = await Promise.all(queries)

  netWorthHistory.value = results[0] ?? null
  balanceHistory.value = results[1] ?? null
}

// Re-fetch when period changes
watch([selectedPeriod], async () => {
  if (analyticsAvailable.value && netWorthDatasetId.value) {
    loading.value = true
    try {
      await fetchPeriodData()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load data'
    } finally {
      loading.value = false
    }
  }
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function getAccountValue(account: {
  account_type: string
  total_value: number | null
  balance_amount: number
}): number {
  return account.account_type === 'trading' && account.total_value
    ? account.total_value
    : account.balance_amount
}

// ---------------------------------------------------------------------------
// Milestone handlers
// ---------------------------------------------------------------------------

function openCreateMilestone() {
  editingMilestone.value = null
  showMilestoneModal.value = true
}

function openEditMilestone(milestone: Milestone) {
  editingMilestone.value = milestone
  showMilestoneModal.value = true
}

function closeMilestoneModal() {
  showMilestoneModal.value = false
  editingMilestone.value = null
}

async function handleSaveMilestone(data: MilestoneCreateRequest) {
  try {
    if (editingMilestone.value) {
      // Update existing
      const updated = await updateMilestone(editingMilestone.value.id, data)
      const idx = milestones.value.findIndex(
        (m) => m.id === editingMilestone.value!.id,
      )
      if (idx !== -1) {
        milestones.value[idx] = updated
      }
      toast.success('Milestone updated')
    } else {
      // Create new
      const created = await createMilestone(data)
      milestones.value.push(created)
      toast.success('Milestone created')
    }
    closeMilestoneModal()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Failed to save milestone')
  }
}

function confirmDeleteMilestone(milestone: Milestone) {
  deletingMilestone.value = milestone
  showDeleteConfirm.value = true
}

async function handleDeleteMilestone() {
  if (!deletingMilestone.value) return

  try {
    await deleteMilestone(deletingMilestone.value.id)
    milestones.value = milestones.value.filter(
      (m) => m.id !== deletingMilestone.value!.id,
    )
    toast.success('Milestone deleted')
    showDeleteConfirm.value = false
    deletingMilestone.value = null
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Failed to delete milestone')
  }
}

async function handleAchieveMilestone(milestone: Milestone) {
  try {
    const updated = await achieveMilestone(milestone.id)
    const idx = milestones.value.findIndex((m) => m.id === milestone.id)
    if (idx !== -1) {
      milestones.value[idx] = updated
    }
    toast.success('Milestone achieved!')
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Failed to mark as achieved')
  }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div
      class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">Net Worth</h1>
        <p class="mt-1 text-muted">Track your total wealth over time</p>
      </div>
      <!-- Period selector -->
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-sm text-muted">Period:</span>
        <div class="flex flex-wrap rounded-lg border border-border bg-surface">
          <button
            v-for="option in periodOptions"
            :key="option.value"
            :class="[
              'px-2 py-1 text-sm transition-colors sm:px-3 sm:py-1.5',
              selectedPeriod === option.value
                ? 'bg-emerald-600 text-white'
                : 'text-muted hover:text-foreground',
            ]"
            @click="selectedPeriod = option.value as typeof selectedPeriod"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="rounded-lg border border-negative/50 bg-negative/10 p-4 text-negative"
    >
      {{ error }}
    </div>

    <!-- Analytics unavailable state -->
    <div
      v-if="!loading && !analyticsAvailable"
      class="rounded-lg border border-warning/50 bg-warning/10 p-8 text-center"
    >
      <p class="text-warning">
        Net worth data is being prepared. Go to Analytics and click Refresh to
        build data.
      </p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-6">
      <div class="rounded-lg border border-border bg-surface p-6">
        <div class="mb-4 h-6 w-32 animate-pulse rounded bg-border" />
        <div class="h-80 animate-pulse rounded bg-border" />
      </div>
    </div>

    <!-- Main content -->
    <template v-else-if="analyticsAvailable">
      <!-- Net Worth Chart -->
      <AnalyticsNetWorthChart
        :data="netWorthChartData"
        :milestones="chartMilestones"
        :show-rolling-avg="true"
      />

      <!-- Account Breakdown -->
      <div class="rounded-lg border border-border bg-surface p-6">
        <h2 class="mb-4 text-lg font-semibold">Account Breakdown</h2>

        <div
          v-if="!accountBreakdown.length"
          class="py-8 text-center text-muted"
        >
          No account data available
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="account in accountBreakdown"
            :key="account.account_id"
            class="flex items-center justify-between rounded-lg border border-border/50 bg-background p-4"
          >
            <div class="flex items-center gap-3">
              <!-- Account type icon -->
              <div
                :class="[
                  'flex h-10 w-10 items-center justify-center rounded-full',
                  account.account_type === 'trading'
                    ? 'bg-violet-500/20 text-violet-400'
                    : 'bg-emerald-500/20 text-emerald-400',
                ]"
              >
                <!-- Bank icon for bank accounts -->
                <svg
                  v-if="account.account_type !== 'trading'"
                  class="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M3 6l9-4 9 4v2H3V6zM3 10h18v10a2 2 0 01-2 2H5a2 2 0 01-2-2V10zm4 4v4m4-4v4m4-4v4"
                  />
                </svg>
                <!-- Chart icon for trading accounts -->
                <svg
                  v-else
                  class="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                  />
                </svg>
              </div>
              <div>
                <p class="font-medium">{{ account.account_name }}</p>
                <p class="text-sm capitalize text-muted">
                  {{ account.account_type }}
                </p>
              </div>
            </div>
            <div class="text-right">
              <p class="text-lg font-semibold">
                {{ formatCurrency(getAccountValue(account)) }}
              </p>
              <p v-if="currentNetWorth > 0" class="text-sm text-muted">
                {{
                  ((getAccountValue(account) / currentNetWorth) * 100).toFixed(
                    1,
                  )
                }}% of total
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Period Summary -->
      <div class="grid gap-4 md:grid-cols-3">
        <div class="rounded-lg border border-border bg-surface p-4">
          <p class="text-sm text-muted">Starting Value</p>
          <p class="text-xl font-semibold">
            {{ formatCurrency(periodMetrics.startValue) }}
          </p>
        </div>
        <div class="rounded-lg border border-border bg-surface p-4">
          <p class="text-sm text-muted">Period Change</p>
          <p
            :class="[
              'text-xl font-semibold',
              periodMetrics.change >= 0 ? 'text-emerald-400' : 'text-red-400',
            ]"
          >
            {{ periodMetrics.change >= 0 ? '+' : ''
            }}{{ formatCurrency(periodMetrics.change) }}
          </p>
        </div>
        <div class="rounded-lg border border-border bg-surface p-4">
          <p class="text-sm text-muted">Percentage Change</p>
          <p
            :class="[
              'text-xl font-semibold',
              periodMetrics.percentChange >= 0
                ? 'text-emerald-400'
                : 'text-red-400',
            ]"
          >
            {{ periodMetrics.percentChange >= 0 ? '+' : ''
            }}{{ periodMetrics.percentChange.toFixed(2) }}%
          </p>
        </div>
      </div>

      <!-- Milestones Section -->
      <div class="rounded-lg border border-border bg-surface p-6">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-semibold">Milestones</h2>
          <AppButton @click="openCreateMilestone">Add Milestone</AppButton>
        </div>

        <div v-if="!milestones.length" class="py-8 text-center text-muted">
          No milestones set. Create one to track your progress towards financial
          goals.
        </div>

        <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MilestonesMilestoneCard
            v-for="milestone in milestones"
            :key="milestone.id"
            :milestone="milestone"
            :current-net-worth="currentNetWorth"
            @edit="openEditMilestone"
            @achieve="handleAchieveMilestone"
            @delete="confirmDeleteMilestone"
          />
        </div>
      </div>
    </template>

    <!-- Milestone Modal -->
    <MilestonesMilestoneModal
      :show="showMilestoneModal"
      :milestone="editingMilestone"
      @close="closeMilestoneModal"
      @save="handleSaveMilestone"
    />

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="showDeleteConfirm"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        @click.self="showDeleteConfirm = false"
      >
        <div
          class="w-full max-w-sm rounded-lg border border-border bg-surface p-6"
        >
          <h3 class="mb-2 text-lg font-bold">Delete Milestone</h3>
          <p class="mb-4 text-muted">
            Are you sure you want to delete "{{ deletingMilestone?.name }}"?
            This action cannot be undone.
          </p>
          <div class="flex justify-end gap-3">
            <AppButton variant="secondary" @click="showDeleteConfirm = false">
              Cancel
            </AppButton>
            <AppButton variant="danger" @click="handleDeleteMilestone">
              Delete
            </AppButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
