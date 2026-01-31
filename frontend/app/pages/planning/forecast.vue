<!-- ==========================================================================
Forecasting Page
90-day cash flow forecast with projected balances and runway analysis
============================================================================ -->

<script setup lang="ts">
import type {
  CashFlowForecastResponse,
  WeeklyForecastResponse,
} from '~/types/analytics'

useHead({ title: 'Forecasting | Finances' })

const { fetchForecast, fetchWeeklyForecast, fetchAnalyticsStatus } =
  useAnalyticsApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Forecast data from API
const forecastData = ref<CashFlowForecastResponse | null>(null)
const weeklyData = ref<WeeklyForecastResponse | null>(null)

// Loading states
const loading = ref(true)
const error = ref('')
const analyticsAvailable = ref(false)

// View toggle: chart vs weekly table
const activeView = ref<'chart' | 'weekly'>('chart')

// Scenario data (when user calculates a what-if scenario)
const scenarioData = ref<CashFlowForecastResponse | null>(null)

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    // Check if analytics is available first
    const status = await fetchAnalyticsStatus()
    analyticsAvailable.value =
      status.duckdb_available && status.manifest_available

    if (!analyticsAvailable.value) {
      loading.value = false
      return
    }

    // Fetch both forecast views in parallel
    const [dailyForecast, weekly] = await Promise.all([
      fetchForecast().catch(() => null),
      fetchWeeklyForecast().catch(() => null),
    ])

    forecastData.value = dailyForecast
    weeklyData.value = weekly
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load forecast'
    analyticsAvailable.value = false
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Computed: Weekly breakdown for display
// ---------------------------------------------------------------------------

const weeklyBreakdown = computed(() => {
  if (!weeklyData.value?.weeks) return []
  return weeklyData.value.weeks.map((week) => ({
    ...week,
    // Parse decimal strings to numbers for display
    total_income_num: parseFloat(week.total_income),
    total_expenses_num: parseFloat(week.total_expenses),
    net_change_num: parseFloat(week.net_change),
    ending_balance_num: parseFloat(week.ending_balance),
  }))
})

// ---------------------------------------------------------------------------
// Computed: Summary cards data
// ---------------------------------------------------------------------------

const summaryCards = computed(() => {
  if (!forecastData.value) return []

  const summary = forecastData.value.summary
  const startBalance = parseFloat(summary.starting_balance)
  const endBalance = parseFloat(summary.ending_balance)
  const netChange = parseFloat(summary.net_change)
  const percentChange =
    startBalance !== 0 ? (netChange / startBalance) * 100 : 0

  return [
    {
      label: 'Current Net Worth',
      value: startBalance,
      type: 'currency' as const,
    },
    {
      label: 'Projected (90 Days)',
      value: endBalance,
      type: 'currency' as const,
    },
    {
      label: 'Expected Change',
      value: netChange,
      type: 'change' as const,
      percent: percentChange,
    },
    {
      label: 'Runway',
      value: summary.runway_days,
      type: 'days' as const,
    },
  ]
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: forecastData.value?.currency || 'GBP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
  })
}

function formatDateRange(start: string, end: string): string {
  return `${formatDate(start)} - ${formatDate(end)}`
}

// Handle scenario calculation from ScenarioBuilder component
function handleScenarioCalculated(scenario: CashFlowForecastResponse | null) {
  scenarioData.value = scenario
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
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">Cash Flow Forecast</h1>
        <p class="mt-1 text-muted">
          90-day projection based on recurring patterns and planned transactions
        </p>
      </div>
      <!-- View toggle buttons -->
      <div
        v-if="forecastData"
        class="flex rounded-lg border border-border bg-surface"
      >
        <button
          :class="[
            'px-4 py-2 text-sm transition-colors',
            activeView === 'chart'
              ? 'bg-emerald-600 text-white'
              : 'text-muted hover:text-foreground',
          ]"
          @click="activeView = 'chart'"
        >
          Chart
        </button>
        <button
          :class="[
            'px-4 py-2 text-sm transition-colors',
            activeView === 'weekly'
              ? 'bg-emerald-600 text-white'
              : 'text-muted hover:text-foreground',
          ]"
          @click="activeView = 'weekly'"
        >
          Weekly
        </button>
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
        Forecast data is being prepared. Go to Analytics and click Refresh to
        build data.
      </p>
    </div>

    <!-- No forecast data state -->
    <div
      v-else-if="!loading && analyticsAvailable && !forecastData"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p class="text-muted">
        No forecast data available. Add recurring patterns or planned
        transactions to generate a forecast.
      </p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-6">
      <!-- Summary cards skeleton -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="i in 4"
          :key="i"
          class="rounded-lg border border-border bg-surface p-4"
        >
          <div class="mb-2 h-4 w-20 animate-pulse rounded bg-border" />
          <div class="h-8 w-32 animate-pulse rounded bg-border" />
        </div>
      </div>
      <!-- Chart skeleton -->
      <div class="rounded-lg border border-border bg-surface p-6">
        <div class="mb-4 h-6 w-40 animate-pulse rounded bg-border" />
        <div class="h-80 animate-pulse rounded bg-border" />
      </div>
    </div>

    <!-- Main content -->
    <template v-else-if="analyticsAvailable && forecastData">
      <!-- Summary cards -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="(card, idx) in summaryCards"
          :key="idx"
          class="rounded-lg border border-border bg-surface p-4"
        >
          <p class="text-sm text-muted">{{ card.label }}</p>
          <!-- Currency value -->
          <template v-if="card.type === 'currency'">
            <p class="mt-1 text-xl font-semibold">
              {{ formatCurrency(card.value as number) }}
            </p>
          </template>
          <!-- Change value with percent -->
          <template v-else-if="card.type === 'change'">
            <p
              :class="[
                'mt-1 text-xl font-semibold',
                (card.value as number) >= 0
                  ? 'text-emerald-400'
                  : 'text-red-400',
              ]"
            >
              {{ (card.value as number) >= 0 ? '+' : ''
              }}{{ formatCurrency(card.value as number) }}
              <span class="text-sm font-normal">
                ({{ (card.value as number) >= 0 ? '+' : ''
                }}{{ (card.percent ?? 0).toFixed(1) }}%)
              </span>
            </p>
          </template>
          <!-- Days value (runway) -->
          <template v-else-if="card.type === 'days'">
            <p
              :class="[
                'mt-1 text-xl font-semibold',
                card.value === null
                  ? 'text-emerald-400'
                  : (card.value as number) > 30
                    ? 'text-warning'
                    : 'text-red-400',
              ]"
            >
              <template v-if="card.value === null">
                <span class="text-emerald-400">Healthy</span>
              </template>
              <template v-else> {{ card.value }} days </template>
            </p>
          </template>
        </div>
      </div>

      <!-- Chart view -->
      <div v-if="activeView === 'chart'">
        <AnalyticsCashFlowForecastChart
          :daily="forecastData.daily"
          :summary="forecastData.summary"
          :currency="forecastData.currency"
          :as-of-date="forecastData.as_of_date"
        />
      </div>

      <!-- Weekly breakdown view -->
      <div
        v-if="activeView === 'weekly'"
        class="rounded-lg border border-border bg-surface"
      >
        <div class="border-b border-border px-6 py-4">
          <h2 class="text-lg font-semibold">Weekly Breakdown</h2>
          <p class="text-sm text-muted">
            Aggregated income and expenses by week
          </p>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-border text-left text-sm text-muted">
                <th class="px-6 py-3 font-medium">Week</th>
                <th class="px-6 py-3 text-right font-medium">Income</th>
                <th class="px-6 py-3 text-right font-medium">Expenses</th>
                <th class="px-6 py-3 text-right font-medium">Net</th>
                <th class="px-6 py-3 text-right font-medium">Balance</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="week in weeklyBreakdown"
                :key="week.week_number"
                class="border-b border-border/50 hover:bg-border/10"
              >
                <td class="px-6 py-3">
                  <div class="font-medium">Week {{ week.week_number }}</div>
                  <div class="text-sm text-muted">
                    {{ formatDateRange(week.week_start, week.week_end) }}
                  </div>
                </td>
                <td class="text-emerald-400 px-6 py-3 text-right">
                  +{{ formatCurrency(week.total_income_num) }}
                </td>
                <td class="px-6 py-3 text-right text-red-400">
                  -{{ formatCurrency(week.total_expenses_num) }}
                </td>
                <td
                  :class="[
                    'px-6 py-3 text-right font-medium',
                    week.net_change_num >= 0
                      ? 'text-emerald-400'
                      : 'text-red-400',
                  ]"
                >
                  {{ week.net_change_num >= 0 ? '+' : ''
                  }}{{ formatCurrency(week.net_change_num) }}
                </td>
                <td class="px-6 py-3 text-right font-medium">
                  {{ formatCurrency(week.ending_balance_num) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- What-If Scenario Builder -->
      <AnalyticsScenarioBuilder
        :baseline-forecast="forecastData"
        :currency="forecastData.currency"
        @scenario-calculated="handleScenarioCalculated"
      />

      <!-- Planned Transactions Panel -->
      <PlanningPlannedTransactionsPanel />

      <!-- Data sources info -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <h3 class="font-medium">About this forecast</h3>
        <p class="mt-1 text-sm text-muted">
          This forecast is generated from your recurring patterns (detected
          subscriptions and income) and any planned transactions you've added.
          For more accurate projections, confirm detected patterns on the
          <NuxtLink
            to="/insights/subscriptions"
            class="text-emerald-400 hover:underline"
            >Subscriptions</NuxtLink
          >
          page.
        </p>
      </div>
    </template>
  </div>
</template>
