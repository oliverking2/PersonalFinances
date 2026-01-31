<!-- ==========================================================================
Forecasting Page
90-day cash flow forecast with projected balances and runway analysis
============================================================================ -->

<script setup lang="ts">
import type {
  CashFlowForecastResponse,
  ForecastEvent,
  ForecastQueryParams,
  WeeklyForecastResponse,
} from '~/types/analytics'

useHead({ title: 'Forecasting | Finances' })

const {
  fetchForecast,
  fetchWeeklyForecast,
  fetchForecastEvents,
  fetchAnalyticsStatus,
} = useAnalyticsApi()

// ---------------------------------------------------------------------------
// Date Range Options
// ---------------------------------------------------------------------------

// Date range presets with label and days
const dateRangeOptions = [
  { label: '30 days', days: 30 },
  { label: '90 days', days: 90 },
  { label: '6 months', days: 180 },
  { label: '1 year', days: 365 },
] as const

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Selected date range (days from today)
const selectedDays = ref(90)

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

// Expanded week rows (week number -> expanded state)
const expandedWeeks = ref<Set<number>>(new Set())

// Events cache (date string -> events)
const eventsCache = ref<Map<string, ForecastEvent[]>>(new Map())

// Loading state for expanded weeks
const loadingWeekEvents = ref<Set<number>>(new Set())

// ---------------------------------------------------------------------------
// Computed: Date range params for API calls
// ---------------------------------------------------------------------------

const dateRangeParams = computed<ForecastQueryParams>(() => {
  const today = new Date()
  const endDate = new Date(today)
  endDate.setDate(endDate.getDate() + selectedDays.value)

  return {
    start_date: today.toISOString().split('T')[0],
    end_date: endDate.toISOString().split('T')[0],
  }
})

// Selected range label for display
const selectedRangeLabel = computed(() => {
  const option = dateRangeOptions.find((o) => o.days === selectedDays.value)
  return option?.label ?? `${selectedDays.value} days`
})

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

    // Fetch both forecast views in parallel with date range params
    const [dailyForecast, weekly] = await Promise.all([
      fetchForecast(dateRangeParams.value).catch(() => null),
      fetchWeeklyForecast(dateRangeParams.value).catch(() => null),
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

// Reload data when date range changes
function handleDateRangeChange(days: number) {
  selectedDays.value = days
  loadData()
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
      label: `Projected (${selectedRangeLabel.value})`,
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
// Weekly table expansion
// ---------------------------------------------------------------------------

// Toggle expansion of a week row
async function toggleWeekExpansion(weekNumber: number) {
  if (expandedWeeks.value.has(weekNumber)) {
    expandedWeeks.value.delete(weekNumber)
    // Force reactivity
    expandedWeeks.value = new Set(expandedWeeks.value)
    return
  }

  // Expand and load events for the week
  expandedWeeks.value.add(weekNumber)
  expandedWeeks.value = new Set(expandedWeeks.value)

  await loadWeekEvents(weekNumber)
}

// Load events for all days in a week
async function loadWeekEvents(weekNumber: number) {
  const week = weeklyBreakdown.value.find((w) => w.week_number === weekNumber)
  if (!week) return

  // Get all dates in the week
  const dates = getDatesInRange(week.week_start, week.week_end)

  // Skip dates that are already cached
  const uncachedDates = dates.filter((d) => !eventsCache.value.has(d))
  if (uncachedDates.length === 0) return

  loadingWeekEvents.value.add(weekNumber)
  loadingWeekEvents.value = new Set(loadingWeekEvents.value)

  try {
    // Fetch events for each uncached date
    const results = await Promise.all(
      uncachedDates.map((date) => fetchForecastEvents(date).catch(() => null)),
    )

    // Cache the results
    for (let i = 0; i < uncachedDates.length; i++) {
      const dateKey = uncachedDates[i]
      const result = results[i]
      if (result && dateKey) {
        eventsCache.value.set(dateKey, result.events)
      }
    }
    eventsCache.value = new Map(eventsCache.value)
  } finally {
    loadingWeekEvents.value.delete(weekNumber)
    loadingWeekEvents.value = new Set(loadingWeekEvents.value)
  }
}

// Get all dates between start and end (inclusive)
function getDatesInRange(start: string, end: string): string[] {
  const dates: string[] = []
  const current = new Date(start)
  const endDate = new Date(end)

  while (current <= endDate) {
    // Get date in YYYY-MM-DD format
    dates.push(current.toISOString().slice(0, 10))
    current.setDate(current.getDate() + 1)
  }

  return dates
}

// Get events for a specific week (from cache)
function getWeekEvents(
  weekNumber: number,
): { date: string; events: ForecastEvent[] }[] {
  const week = weeklyBreakdown.value.find((w) => w.week_number === weekNumber)
  if (!week) return []

  const dates = getDatesInRange(week.week_start, week.week_end)
  const result: { date: string; events: ForecastEvent[] }[] = []

  for (const date of dates) {
    const events = eventsCache.value.get(date) || []
    if (events.length > 0) {
      result.push({ date, events })
    }
  }

  return result
}

// Format frequency for display
function formatFrequency(frequency: string | null): string {
  if (!frequency) return 'One-time'
  return frequency.charAt(0).toUpperCase() + frequency.slice(1)
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
        <h1 class="text-2xl font-bold sm:text-3xl">Cash Flow Forecast</h1>
        <p class="mt-1 text-muted">
          {{ selectedRangeLabel }} projection based on recurring patterns and
          planned transactions
        </p>
      </div>

      <!-- Controls: date range + view toggle + refresh -->
      <div v-if="forecastData" class="flex flex-wrap items-center gap-3">
        <!-- Date range selector -->
        <div class="flex rounded-lg border border-border bg-surface">
          <button
            v-for="option in dateRangeOptions"
            :key="option.days"
            :class="[
              'px-3 py-2 text-sm transition-colors',
              selectedDays === option.days
                ? 'bg-emerald-600 text-white'
                : 'text-muted hover:text-foreground',
            ]"
            @click="handleDateRangeChange(option.days)"
          >
            {{ option.label }}
          </button>
        </div>

        <!-- View toggle buttons -->
        <div class="flex rounded-lg border border-border bg-surface">
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

        <!-- Refresh button -->
        <button
          class="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-muted transition-colors hover:text-foreground"
          :disabled="loading"
          @click="loadData"
        >
          <svg
            :class="['h-4 w-4', loading && 'animate-spin']"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
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
          :range-label="selectedRangeLabel"
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
                <!-- Empty column for expand toggle -->
                <th class="w-10 px-3 py-3" />
                <th class="px-4 py-3 font-medium">Week</th>
                <th class="px-4 py-3 text-right font-medium">Income</th>
                <th class="px-4 py-3 text-right font-medium">Expenses</th>
                <th class="px-4 py-3 text-right font-medium">Net</th>
                <th class="px-4 py-3 text-right font-medium">Balance</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="week in weeklyBreakdown" :key="week.week_number">
                <!-- Main week row -->
                <tr
                  class="cursor-pointer border-b border-border/50 transition-colors hover:bg-border/10"
                  @click="toggleWeekExpansion(week.week_number)"
                >
                  <!-- Expand/collapse toggle -->
                  <td class="px-3 py-3">
                    <button
                      class="flex h-6 w-6 items-center justify-center rounded transition-colors hover:bg-border"
                      :aria-expanded="expandedWeeks.has(week.week_number)"
                    >
                      <!-- Chevron icon - rotates when expanded -->
                      <svg
                        :class="[
                          'h-4 w-4 text-muted transition-transform',
                          expandedWeeks.has(week.week_number)
                            ? 'rotate-90'
                            : '',
                        ]"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </button>
                  </td>
                  <td class="px-4 py-3">
                    <div class="font-medium">Week {{ week.week_number }}</div>
                    <div class="text-sm text-muted">
                      {{ formatDateRange(week.week_start, week.week_end) }}
                    </div>
                  </td>
                  <td class="text-emerald-400 px-4 py-3 text-right">
                    +{{ formatCurrency(week.total_income_num) }}
                  </td>
                  <td class="px-4 py-3 text-right text-red-400">
                    -{{ formatCurrency(week.total_expenses_num) }}
                  </td>
                  <td
                    :class="[
                      'px-4 py-3 text-right font-medium',
                      week.net_change_num >= 0
                        ? 'text-emerald-400'
                        : 'text-red-400',
                    ]"
                  >
                    {{ week.net_change_num >= 0 ? '+' : ''
                    }}{{ formatCurrency(week.net_change_num) }}
                  </td>
                  <td class="px-4 py-3 text-right font-medium">
                    {{ formatCurrency(week.ending_balance_num) }}
                  </td>
                </tr>

                <!-- Expanded events row -->
                <tr v-if="expandedWeeks.has(week.week_number)">
                  <td colspan="6" class="bg-border/5 px-6 py-4">
                    <!-- Loading state -->
                    <div
                      v-if="loadingWeekEvents.has(week.week_number)"
                      class="flex items-center gap-2 text-sm text-muted"
                    >
                      <svg
                        class="h-4 w-4 animate-spin"
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
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      Loading events...
                    </div>

                    <!-- Events list by date -->
                    <div
                      v-else-if="getWeekEvents(week.week_number).length > 0"
                      class="space-y-3"
                    >
                      <div
                        v-for="dayEvents in getWeekEvents(week.week_number)"
                        :key="dayEvents.date"
                      >
                        <!-- Date header -->
                        <div class="mb-1 text-xs font-medium text-muted">
                          {{ formatDate(dayEvents.date) }}
                        </div>
                        <!-- Events for this date -->
                        <div class="space-y-1">
                          <div
                            v-for="(event, idx) in dayEvents.events"
                            :key="`${dayEvents.date}-${idx}`"
                            class="flex items-center justify-between rounded bg-surface px-3 py-2 text-sm"
                          >
                            <div class="flex items-center gap-2">
                              <!-- Source type badge -->
                              <span
                                :class="[
                                  'rounded px-1.5 py-0.5 text-xs',
                                  event.source_type === 'recurring'
                                    ? 'bg-blue-500/20 text-blue-400'
                                    : 'bg-purple-500/20 text-purple-400',
                                ]"
                              >
                                {{
                                  event.source_type === 'recurring'
                                    ? 'Recurring'
                                    : 'Planned'
                                }}
                              </span>
                              <span>{{ event.name }}</span>
                              <!-- Frequency badge -->
                              <span
                                v-if="event.frequency"
                                class="rounded bg-border px-1.5 py-0.5 text-xs text-muted"
                              >
                                {{ formatFrequency(event.frequency) }}
                              </span>
                            </div>
                            <!-- Amount -->
                            <span
                              :class="[
                                'font-medium',
                                parseFloat(event.amount) >= 0
                                  ? 'text-emerald-400'
                                  : 'text-red-400',
                              ]"
                            >
                              {{ parseFloat(event.amount) >= 0 ? '+' : ''
                              }}{{ formatCurrency(parseFloat(event.amount)) }}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- No events state -->
                    <div v-else class="text-sm text-muted">
                      No scheduled events for this week
                    </div>
                  </td>
                </tr>
              </template>
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
            to="/planning/recurring"
            class="text-emerald-400 hover:underline"
            >Recurring</NuxtLink
          >
          page.
        </p>
      </div>
    </template>
  </div>
</template>
