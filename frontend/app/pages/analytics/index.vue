<!-- ==========================================================================
Analytics Page
Charts and visualisations for spending patterns with period filtering
============================================================================ -->

<script setup lang="ts">
import type { Dataset, DatasetQueryResponse } from '~/types/analytics'

useHead({ title: 'Analytics | Finances' })

const toast = useToastStore()
const { fetchDatasets, queryDataset, fetchAnalyticsStatus, triggerRefresh } =
  useAnalyticsApi()
const { fetchJobs, fetchJob } = useAccountsApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Raw data from API
const dailySpendingByTag = ref<DatasetQueryResponse | null>(null)
const previousPeriodDailySpending = ref<DatasetQueryResponse | null>(null)
const monthlyTrends = ref<DatasetQueryResponse | null>(null)
const previousMonthTrends = ref<DatasetQueryResponse | null>(null)

// Dataset IDs (looked up on mount)
const dailySpendingDatasetId = ref<string | null>(null)
const monthlyTrendsDatasetId = ref<string | null>(null)

// Loading states
const loading = ref(true)
const refreshing = ref(false)

// Error states
const error = ref('')
const analyticsAvailable = ref(false)

// Period filter state
const selectedPeriod = ref<
  'this_month' | 'last_month' | 'last_30_days' | 'last_90_days' | 'this_year'
>('this_month')
const compareEnabled = ref(false)

// ---------------------------------------------------------------------------
// Computed: Date ranges based on selected period
// ---------------------------------------------------------------------------

// Calculate date range for the selected period
const periodDateRange = computed(() => {
  const now = new Date()
  let startDate: Date
  let endDate: Date = now

  switch (selectedPeriod.value) {
    case 'this_month':
      startDate = new Date(now.getFullYear(), now.getMonth(), 1)
      break
    case 'last_month':
      startDate = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      endDate = new Date(now.getFullYear(), now.getMonth(), 0) // Last day of prev month
      break
    case 'last_30_days':
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      break
    case 'last_90_days':
      startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
      break
    case 'this_year':
      startDate = new Date(now.getFullYear(), 0, 1)
      break
    default:
      startDate = new Date(now.getFullYear(), now.getMonth(), 1)
  }

  return {
    start_date: startDate.toISOString().slice(0, 10),
    end_date: endDate.toISOString().slice(0, 10),
  }
})

// Calculate the previous period (same length, immediately before)
const previousPeriodDateRange = computed(() => {
  const now = new Date()

  switch (selectedPeriod.value) {
    case 'this_month': {
      // Previous month, same day range (for fair comparison)
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const lastDayOfPrevMonth = new Date(
        now.getFullYear(),
        now.getMonth(),
        0,
      ).getDate()
      const day = Math.min(now.getDate(), lastDayOfPrevMonth)
      const end = new Date(now.getFullYear(), now.getMonth() - 1, day)
      return {
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
      }
    }
    case 'last_month': {
      // Month before last
      const start = new Date(now.getFullYear(), now.getMonth() - 2, 1)
      const end = new Date(now.getFullYear(), now.getMonth() - 1, 0)
      return {
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
      }
    }
    case 'last_30_days': {
      // 30 days before the current 30-day period
      const start = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000)
      const end = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000 - 1)
      return {
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
      }
    }
    case 'last_90_days': {
      // 90 days before the current 90-day period
      const start = new Date(now.getTime() - 180 * 24 * 60 * 60 * 1000)
      const end = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000 - 1)
      return {
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
      }
    }
    case 'this_year': {
      // Previous year
      const start = new Date(now.getFullYear() - 1, 0, 1)
      const end = new Date(now.getFullYear() - 1, 11, 31)
      return {
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
      }
    }
    default:
      return periodDateRange.value
  }
})

// Human-readable period label for display
const periodLabel = computed(() => {
  switch (selectedPeriod.value) {
    case 'this_month':
      return 'This Month'
    case 'last_month':
      return 'Last Month'
    case 'last_30_days':
      return 'Last 30 Days'
    case 'last_90_days':
      return 'Last 90 Days'
    case 'this_year':
      return 'This Year'
    default:
      return 'This Month'
  }
})

// ---------------------------------------------------------------------------
// Computed: Aggregated data for charts
// ---------------------------------------------------------------------------

// Aggregate spending by tag for bar/donut charts
const spendingByCategory = computed(() => {
  if (!dailySpendingByTag.value?.rows?.length) return []

  const byTag = new Map<
    string,
    { name: string; total: number; colour: string }
  >()

  for (const row of dailySpendingByTag.value.rows) {
    const rawTagName = row.tag_name as string | null | undefined
    // Skip "No Spending" rows (date spine gap-fill rows with zero spending)
    if (rawTagName === 'No Spending') continue

    const tagName = rawTagName || 'Untagged'
    const spending = (row.total_spending as number) || 0
    const colour = rawTagName
      ? (row.tag_colour as string) || '#10b981'
      : '#6b7280'

    const existing = byTag.get(tagName)
    if (existing) {
      existing.total += spending
    } else {
      byTag.set(tagName, { name: tagName, total: spending, colour })
    }
  }

  // Sort by total descending
  return Array.from(byTag.values()).sort((a, b) => b.total - a.total)
})

// Previous period spending by category (for comparison)
const previousSpendingByCategory = computed(() => {
  if (!previousPeriodDailySpending.value?.rows?.length) return []

  const byTag = new Map<
    string,
    { name: string; total: number; colour: string }
  >()

  for (const row of previousPeriodDailySpending.value.rows) {
    const rawTagName = row.tag_name as string | null | undefined
    // Skip "No Spending" rows (date spine gap-fill rows with zero spending)
    if (rawTagName === 'No Spending') continue

    const tagName = rawTagName || 'Untagged'
    const spending = (row.total_spending as number) || 0
    const colour = rawTagName
      ? (row.tag_colour as string) || '#10b981'
      : '#6b7280'

    const existing = byTag.get(tagName)
    if (existing) {
      existing.total += spending
    } else {
      byTag.set(tagName, { name: tagName, total: spending, colour })
    }
  }

  return Array.from(byTag.values()).sort((a, b) => b.total - a.total)
})

// Aggregate daily spending for line chart
const dailySpending = computed(() => {
  if (!dailySpendingByTag.value?.rows?.length) return []

  const byDate = new Map<string, number>()

  for (const row of dailySpendingByTag.value.rows) {
    const date = row.spending_date as string
    const spending = (row.total_spending as number) || 0

    const existing = byDate.get(date)
    if (existing !== undefined) {
      byDate.set(date, existing + spending)
    } else {
      byDate.set(date, spending)
    }
  }

  // Sort by date ascending
  return Array.from(byDate.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, total]) => ({ date, total }))
})

// Previous period daily spending (for comparison line)
const previousDailySpending = computed(() => {
  if (!previousPeriodDailySpending.value?.rows?.length) return []

  const byDate = new Map<string, number>()

  for (const row of previousPeriodDailySpending.value.rows) {
    const date = row.spending_date as string
    const spending = (row.total_spending as number) || 0

    const existing = byDate.get(date)
    if (existing !== undefined) {
      byDate.set(date, existing + spending)
    } else {
      byDate.set(date, spending)
    }
  }

  return Array.from(byDate.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, total]) => ({ date, total }))
})

// ---------------------------------------------------------------------------
// Computed: Summary statistics
// ---------------------------------------------------------------------------

const totalSpending = computed(() => {
  return spendingByCategory.value.reduce((sum, cat) => sum + cat.total, 0)
})

const previousTotalSpending = computed(() => {
  return previousSpendingByCategory.value.reduce(
    (sum, cat) => sum + cat.total,
    0,
  )
})

const spendingChangePercent = computed(() => {
  if (previousTotalSpending.value === 0) return null
  return (
    ((totalSpending.value - previousTotalSpending.value) /
      previousTotalSpending.value) *
    100
  )
})

const transactionCount = computed(() => {
  if (!monthlyTrends.value?.rows?.length) return null
  return monthlyTrends.value.rows.reduce(
    (sum, row) => sum + ((row.total_transactions as number) || 0),
    0,
  )
})

const daysInPeriod = computed(() => {
  const start = new Date(periodDateRange.value.start_date)
  const end = new Date(periodDateRange.value.end_date)
  const diff = end.getTime() - start.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24)) + 1
})

const avgPerDay = computed(() => {
  if (daysInPeriod.value === 0) return 0
  return totalSpending.value / daysInPeriod.value
})

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

async function loadAnalytics() {
  loading.value = true
  error.value = ''

  try {
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

    const dailySpendingDs = datasets.find(
      (ds: Dataset) => ds.dataset_name === 'fct_daily_spending_by_tag',
    )
    const monthlyTrendsDs = datasets.find(
      (ds: Dataset) => ds.dataset_name === 'fct_monthly_trends',
    )

    dailySpendingDatasetId.value = dailySpendingDs?.id || null
    monthlyTrendsDatasetId.value = monthlyTrendsDs?.id || null

    // Fetch data for current period
    await fetchPeriodData()
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : 'Failed to load analytics data'
    analyticsAvailable.value = false
  } finally {
    loading.value = false
  }
}

async function fetchPeriodData() {
  if (!dailySpendingDatasetId.value) return

  const queries: Promise<DatasetQueryResponse>[] = []

  // Current period - daily spending by tag
  queries.push(
    queryDataset(dailySpendingDatasetId.value, {
      start_date: periodDateRange.value.start_date,
      end_date: periodDateRange.value.end_date,
    }),
  )

  // Previous period (for comparison)
  queries.push(
    queryDataset(dailySpendingDatasetId.value, {
      start_date: previousPeriodDateRange.value.start_date,
      end_date: previousPeriodDateRange.value.end_date,
    }),
  )

  // Monthly trends for current period
  if (monthlyTrendsDatasetId.value) {
    queries.push(
      queryDataset(monthlyTrendsDatasetId.value, {
        start_date: periodDateRange.value.start_date,
        end_date: periodDateRange.value.end_date,
      }),
    )
    queries.push(
      queryDataset(monthlyTrendsDatasetId.value, {
        start_date: previousPeriodDateRange.value.start_date,
        end_date: previousPeriodDateRange.value.end_date,
      }),
    )
  }

  const results = await Promise.all(queries)

  dailySpendingByTag.value = results[0] ?? null
  previousPeriodDailySpending.value = results[1] ?? null
  monthlyTrends.value = results[2] ?? null
  previousMonthTrends.value = results[3] ?? null
}

// Re-fetch when period changes
watch([selectedPeriod], async () => {
  if (analyticsAvailable.value && dailySpendingDatasetId.value) {
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
// Refresh handler
// ---------------------------------------------------------------------------

async function handleRefresh() {
  if (refreshing.value) return

  refreshing.value = true
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
      const refreshResponse = await triggerRefresh()

      // Check if Dagster is unavailable
      if (refreshResponse.status === 'failed') {
        toast.error(
          refreshResponse.message || 'Failed to start analytics refresh',
        )
        return
      }

      await pollJobStatus(refreshResponse.job_id)
    }

    // Reload data
    await loadAnalytics()
    toast.success('Analytics refreshed successfully')
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Failed to refresh data'
    error.value = message
    toast.error(message)
  } finally {
    refreshing.value = false
  }
}

async function pollJobStatus(jobId: string) {
  const maxAttempts = 60 // 5 minutes max
  let attempts = 0

  while (attempts < maxAttempts) {
    const job = await fetchJob(jobId)

    if (job.status === 'completed') {
      return
    }

    if (job.status === 'failed') {
      throw new Error('Refresh job failed')
    }

    // Wait 5 seconds before next poll
    await new Promise((resolve) => setTimeout(resolve, 5000))
    attempts++
  }

  throw new Error('Refresh timed out')
}

// ---------------------------------------------------------------------------
// Navigation handlers
// ---------------------------------------------------------------------------

// Navigate to transactions page filtered by tag/category
function handleCategoryClick(categoryName: string) {
  // Build query params for the transactions page
  const params = new URLSearchParams()

  // Add date range from current period
  params.set('start_date', periodDateRange.value.start_date)
  params.set('end_date', periodDateRange.value.end_date)

  // Add tag filter (use the category name to find the tag)
  // Note: "Untagged" is a special case - we'd filter for transactions without tags
  if (categoryName !== 'Untagged') {
    params.set('tag', categoryName)
  } else {
    params.set('untagged', 'true')
  }

  navigateTo(`/transactions?${params.toString()}`)
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  loadAnalytics()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page header with refresh button -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">Analytics</h1>
        <p class="mt-1 text-muted">Spending patterns and trends</p>
      </div>
      <!-- Action buttons -->
      <div class="flex items-center gap-2">
        <!-- Datasets link -->
        <NuxtLink
          to="/analytics/datasets"
          class="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-gray-700/50"
        >
          <!-- Download/export icon -->
          <svg
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
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          Datasets
        </NuxtLink>

        <!-- Refresh button -->
        <AppButton :disabled="refreshing || loading" @click="handleRefresh">
          <span v-if="refreshing" class="flex items-center gap-2">
            <!-- Spinner icon -->
            <svg
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
            Refreshing...
          </span>
          <span v-else class="flex items-center gap-2">
            <!-- Refresh icon -->
            <svg
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
            Refresh
          </span>
        </AppButton>
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
        Analytics data is being prepared. Click Refresh to trigger a data build.
      </p>
    </div>

    <!-- Main content (when analytics available) -->
    <template v-if="analyticsAvailable || loading">
      <!-- Period filter controls -->
      <AnalyticsPeriodFilter
        v-model:period="selectedPeriod"
        v-model:compare="compareEnabled"
        :period-label="periodLabel"
      />

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-6">
        <!-- Skeleton for bar chart -->
        <div class="rounded-lg border border-border bg-surface p-6">
          <div class="mb-4 h-6 w-48 animate-pulse rounded bg-border" />
          <div class="space-y-3">
            <div v-for="i in 5" :key="i" class="flex items-center gap-4">
              <div class="h-4 w-24 animate-pulse rounded bg-border" />
              <div
                class="h-6 animate-pulse rounded bg-border"
                :style="{ width: `${(6 - i) * 15}%` }"
              />
            </div>
          </div>
        </div>

        <!-- Skeleton for line chart -->
        <div class="rounded-lg border border-border bg-surface p-6">
          <div class="mb-4 h-6 w-48 animate-pulse rounded bg-border" />
          <div class="h-64 animate-pulse rounded bg-border" />
        </div>
      </div>

      <!-- Charts (when loaded) -->
      <template v-else>
        <!-- Spending by Category (horizontal bar) -->
        <AnalyticsSpendingByCategory
          :data="spendingByCategory"
          :previous-data="compareEnabled ? previousSpendingByCategory : []"
          :compare-enabled="compareEnabled"
          :total="totalSpending"
          @click-category="handleCategoryClick"
        />

        <!-- Daily Spending Trend (line chart) -->
        <AnalyticsDailySpendingTrend
          :data="dailySpending"
          :previous-data="compareEnabled ? previousDailySpending : []"
          :compare-enabled="compareEnabled"
          :period-label="periodLabel"
        />

        <!-- Bottom row: Donut chart + Summary -->
        <div class="grid gap-6 lg:grid-cols-2">
          <!-- Category Breakdown (donut) -->
          <AnalyticsCategoryBreakdown
            :data="spendingByCategory"
            :total="totalSpending"
          />

          <!-- Summary stats -->
          <AnalyticsSpendingSummary
            :total="totalSpending"
            :previous-total="compareEnabled ? previousTotalSpending : null"
            :change-percent="compareEnabled ? spendingChangePercent : null"
            :transaction-count="transactionCount"
            :avg-per-day="avgPerDay"
            :period-label="periodLabel"
          />
        </div>

        <!-- Spending Table -->
        <AnalyticsSpendingTable :data="dailySpendingByTag?.rows || []" />
      </template>
    </template>
  </div>
</template>
