<!-- ==========================================================================
CashFlowForecastChart
Area chart showing projected balance over the next 90 days
with income/expense annotations and runway indicator
============================================================================ -->

<script setup lang="ts">
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'
import type { ForecastDay, ForecastSummary } from '~/types/analytics'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  // Daily forecast data from API
  daily: ForecastDay[]
  // Summary metrics from API
  summary: ForecastSummary
  // Currency for formatting
  currency: string
  // Date of starting balance
  asOfDate: string
  // Label for the forecast range (e.g., "90 days", "1 year")
  rangeLabel?: string
}>()

// ---------------------------------------------------------------------------
// Types for bucketed data
// ---------------------------------------------------------------------------

interface BucketedDataPoint {
  date: Date // Start of the bucket (week or month)
  dateLabel: string // Display label for the bucket
  income: number // Sum of income in bucket
  expenses: number // Sum of expenses in bucket
  balance: number // Ending balance of bucket
  eventCount: number // Sum of events in bucket
}

// ---------------------------------------------------------------------------
// Computed: Bucket mode based on data length
// ---------------------------------------------------------------------------

// Determine bucketing mode based on number of days
const bucketMode = computed<'daily' | 'weekly' | 'monthly'>(() => {
  const days = props.daily.length
  if (days <= 90) return 'daily'
  if (days <= 180) return 'weekly'
  return 'monthly'
})

// Helper to get date key (YYYY-MM-DD) from Date object
function getDateKey(date: Date): string {
  return date.toISOString().slice(0, 10)
}

// Aggregate daily data into weekly buckets
function aggregateByWeek(daily: ForecastDay[]): BucketedDataPoint[] {
  const weekMap = new Map<string, BucketedDataPoint>()

  for (const day of daily) {
    const dayDate = new Date(day.forecast_date)
    // Get Monday of the week (ISO week starts on Monday)
    const mondayOffset = dayDate.getDay() === 0 ? -6 : 1 - dayDate.getDay()
    const weekStart = new Date(dayDate)
    weekStart.setDate(dayDate.getDate() + mondayOffset)
    const weekKey = getDateKey(weekStart)

    if (!weekMap.has(weekKey)) {
      weekMap.set(weekKey, {
        date: weekStart,
        dateLabel: formatWeekLabel(weekStart),
        income: 0,
        expenses: 0,
        balance: 0,
        eventCount: 0,
      })
    }

    const bucket = weekMap.get(weekKey)!
    bucket.income += parseFloat(day.daily_income)
    bucket.expenses += parseFloat(day.daily_expenses)
    bucket.balance = parseFloat(day.projected_balance) // Take last balance
    bucket.eventCount += day.event_count
  }

  return Array.from(weekMap.values()).sort(
    (a, b) => a.date.getTime() - b.date.getTime(),
  )
}

// Aggregate daily data into monthly buckets
function aggregateByMonth(daily: ForecastDay[]): BucketedDataPoint[] {
  const monthMap = new Map<string, BucketedDataPoint>()

  for (const day of daily) {
    const dayDate = new Date(day.forecast_date)
    const monthStart = new Date(dayDate.getFullYear(), dayDate.getMonth(), 1)
    const monthKey = getDateKey(monthStart)

    if (!monthMap.has(monthKey)) {
      monthMap.set(monthKey, {
        date: monthStart,
        dateLabel: formatMonthLabel(monthStart),
        income: 0,
        expenses: 0,
        balance: 0,
        eventCount: 0,
      })
    }

    const bucket = monthMap.get(monthKey)!
    bucket.income += parseFloat(day.daily_income)
    bucket.expenses += parseFloat(day.daily_expenses)
    bucket.balance = parseFloat(day.projected_balance) // Take last balance
    bucket.eventCount += day.event_count
  }

  return Array.from(monthMap.values()).sort(
    (a, b) => a.date.getTime() - b.date.getTime(),
  )
}

function formatWeekLabel(date: Date): string {
  return `Week of ${date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}`
}

function formatMonthLabel(date: Date): string {
  return date.toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })
}

// Get bucketed data based on bucket mode
const bucketedData = computed<BucketedDataPoint[]>(() => {
  if (bucketMode.value === 'daily') {
    // Convert daily data to bucketed format
    return props.daily.map((day) => ({
      date: new Date(day.forecast_date),
      dateLabel: formatDate(day.forecast_date),
      income: parseFloat(day.daily_income),
      expenses: parseFloat(day.daily_expenses),
      balance: parseFloat(day.projected_balance),
      eventCount: day.event_count,
    }))
  }
  if (bucketMode.value === 'weekly') {
    return aggregateByWeek(props.daily)
  }
  return aggregateByMonth(props.daily)
})

// ---------------------------------------------------------------------------
// Computed: Chart data
// ---------------------------------------------------------------------------

// Main projected balance series (uses bucketed data for longer ranges)
const series = computed(() => {
  const balanceData = bucketedData.value.map((point) => ({
    x: point.date.getTime(),
    y: point.balance,
  }))

  return [{ name: 'Projected Balance', data: balanceData }]
})

// Zero line annotation (runway indicator)
const runwayAnnotation = computed(() => {
  const runwayDays = props.summary.runway_days
  if (runwayDays === null) return []

  // Find the date when balance goes negative
  const negativeDay = props.daily.find(
    (d) => parseFloat(d.projected_balance) < 0,
  )
  if (!negativeDay) return []

  return [
    {
      x: new Date(negativeDay.forecast_date).getTime(),
      borderColor: '#ef4444',
      borderWidth: 2,
      label: {
        borderColor: '#ef4444',
        style: {
          color: '#fff',
          background: '#ef4444',
          fontSize: '11px',
          padding: { left: 8, right: 8, top: 4, bottom: 4 },
        },
        text: `Runway: ${runwayDays} days`,
        position: 'top',
        offsetY: -10,
      },
    },
  ]
})

// ---------------------------------------------------------------------------
// Computed: Chart configuration
// ---------------------------------------------------------------------------

const chartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    fontFamily: 'inherit',
    background: 'transparent',
    animations: { enabled: true, speed: 600, easing: 'easeinout' },
    zoom: { enabled: false },
    selection: { enabled: false },
  },
  stroke: {
    curve: 'smooth',
    width: 2,
  },
  colors: ['#10b981'], // Emerald for positive outlook
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.4,
      opacityTo: 0.05,
      stops: [0, 100],
    },
  },
  markers: {
    size: 0,
    hover: { size: 5 },
  },
  dataLabels: {
    enabled: false,
  },
  xaxis: {
    type: 'datetime',
    labels: {
      style: { colors: '#a3a3a3', fontSize: '12px' },
      datetimeFormatter: { day: 'dd MMM', month: "MMM 'yy" },
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: {
    // Start y-axis at zero unless balance goes negative (then show full range)
    min: parseFloat(props.summary.min_balance) >= 0 ? 0 : undefined,
    labels: {
      style: { colors: '#a3a3a3', fontSize: '12px' },
      formatter: (val: number) => formatCompactCurrency(val),
    },
  },
  grid: {
    borderColor: '#2e2e2e',
    strokeDashArray: 4,
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: true } },
  },
  legend: { show: false },
  tooltip: {
    theme: 'dark',
    x: { format: 'dd MMM yyyy' },
    y: {
      formatter: (val: number) => formatCurrency(val),
    },
    custom: ({ dataPointIndex }: { dataPointIndex: number }) => {
      const point = bucketedData.value[dataPointIndex]
      if (!point) return ''

      const income = point.income
      const expenses = point.expenses
      const balance = point.balance

      // Build tooltip HTML - use whole numbers for cleaner display
      let html = `<div class="px-3 py-2 text-sm">`
      html += `<div class="font-semibold">${point.dateLabel}</div>`
      html += `<div class="mt-1">Balance: <span class="font-medium">${formatWholeNumber(balance)}</span></div>`

      if (income > 0 || expenses > 0) {
        if (income > 0) {
          html += `<div class="text-emerald-400">+${formatWholeNumber(income)} income</div>`
        }
        if (expenses > 0) {
          html += `<div class="text-red-400">-${formatWholeNumber(expenses)} expenses</div>`
        }
      }

      // Show bucket mode indicator for non-daily views
      if (bucketMode.value !== 'daily') {
        const modeLabel = bucketMode.value === 'weekly' ? 'Weekly' : 'Monthly'
        html += `<div class="mt-1 text-xs text-gray-400">${modeLabel} aggregate</div>`
      }

      html += `</div>`
      return html
    },
  },
  annotations: {
    // Zero line if there's potential to go negative
    yaxis:
      parseFloat(props.summary.min_balance) < 0
        ? [
            {
              y: 0,
              borderColor: '#ef4444',
              strokeDashArray: 5,
              label: {
                borderColor: 'transparent',
                style: {
                  color: '#ef4444',
                  background: 'transparent',
                  fontSize: '10px',
                },
                text: 'Zero',
                position: 'left',
              },
            },
          ]
        : [],
    xaxis: runwayAnnotation.value,
  },
}))

// ---------------------------------------------------------------------------
// Computed: Summary metrics for display
// ---------------------------------------------------------------------------

const startingBalance = computed(() =>
  parseFloat(props.summary.starting_balance),
)
const endingBalance = computed(() => parseFloat(props.summary.ending_balance))
const netChange = computed(() => parseFloat(props.summary.net_change))
const netChangePercent = computed(() => {
  if (startingBalance.value === 0) return 0
  return (netChange.value / startingBalance.value) * 100
})
const totalIncome = computed(() => parseFloat(props.summary.total_income))
const totalExpenses = computed(() => parseFloat(props.summary.total_expenses))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: props.currency || 'GBP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function formatCompactCurrency(amount: number): string {
  const currency = props.currency || 'GBP'
  const symbol = currency === 'GBP' ? '£' : currency === 'EUR' ? '€' : '$'

  // All values shown as whole numbers for cleaner display
  if (Math.abs(amount) >= 1000000) {
    return `${symbol}${Math.round(amount / 1000000)}M`
  }
  if (Math.abs(amount) >= 1000) {
    return `${symbol}${Math.round(amount / 1000)}K`
  }
  return `${symbol}${Math.round(amount)}`
}

// Format currency as whole numbers (no decimal places)
function formatWholeNumber(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: props.currency || 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.round(amount))
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-6">
    <!-- Header with summary metrics -->
    <div class="mb-4 flex flex-wrap items-start justify-between gap-4">
      <!-- Left: Title and projected balance -->
      <div>
        <h2 class="text-lg font-semibold">
          {{ rangeLabel || '90 days' }} Forecast
        </h2>
        <p class="mt-1 text-sm text-muted">
          Based on recurring patterns and planned transactions
          <!-- Bucket mode indicator -->
          <span v-if="bucketMode !== 'daily'" class="ml-1 text-xs">
            ({{ bucketMode }} view)
          </span>
        </p>
        <p class="mt-2 text-2xl font-bold text-emerald-400">
          {{ formatCurrency(endingBalance) }}
          <span class="text-base font-normal text-muted">projected</span>
        </p>
      </div>

      <!-- Right: Change indicator -->
      <div class="text-right">
        <p class="text-sm text-muted">{{ rangeLabel || '90 days' }} Change</p>
        <p
          :class="[
            'text-lg font-semibold',
            netChange >= 0 ? 'text-emerald-400' : 'text-red-400',
          ]"
        >
          {{ netChange >= 0 ? '+' : '' }}{{ formatCurrency(netChange) }}
          <span class="text-sm font-normal">
            ({{ netChange >= 0 ? '+' : '' }}{{ netChangePercent.toFixed(1) }}%)
          </span>
        </p>
      </div>
    </div>

    <!-- Runway warning banner if applicable -->
    <div
      v-if="summary.runway_days !== null"
      class="mb-4 rounded-lg border border-red-500/50 bg-red-500/10 px-4 py-3"
    >
      <div class="flex items-center gap-2">
        <!-- Warning icon -->
        <svg
          class="h-5 w-5 flex-shrink-0 text-red-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <div>
          <p class="font-medium text-red-400">
            Balance may go negative in {{ summary.runway_days }} days
          </p>
          <p class="text-sm text-red-300/80">
            Review planned expenses or add expected income to extend your runway
          </p>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-if="!daily.length"
      class="flex h-64 items-center justify-center text-muted"
    >
      No forecast data available. Add recurring patterns or planned transactions
      to generate a forecast.
    </div>

    <!-- Chart -->
    <div v-else>
      <ClientOnly>
        <VueApexCharts
          type="area"
          height="350"
          :options="chartOptions"
          :series="series"
        />
      </ClientOnly>
    </div>

    <!-- Income/Expense summary below chart -->
    <div class="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4">
      <!-- Total income -->
      <div class="flex items-center gap-3">
        <div
          class="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20"
        >
          <!-- Arrow up icon -->
          <svg
            class="h-5 w-5 text-emerald-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M5 10l7-7m0 0l7 7m-7-7v18"
            />
          </svg>
        </div>
        <div>
          <p class="text-sm text-muted">Total Income</p>
          <p class="text-lg font-semibold text-emerald-400">
            +{{ formatCurrency(totalIncome) }}
          </p>
        </div>
      </div>

      <!-- Total expenses -->
      <div class="flex items-center gap-3">
        <div
          class="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/20"
        >
          <!-- Arrow down icon -->
          <svg
            class="h-5 w-5 text-red-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 14l-7 7m0 0l-7-7m7 7V3"
            />
          </svg>
        </div>
        <div>
          <p class="text-sm text-muted">Total Expenses</p>
          <p class="text-lg font-semibold text-red-400">
            -{{ formatCurrency(totalExpenses) }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
