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
}>()

// ---------------------------------------------------------------------------
// Computed: Chart data
// ---------------------------------------------------------------------------

// Main projected balance series
const series = computed(() => {
  const balanceData = props.daily.map((day) => ({
    x: new Date(day.forecast_date).getTime(),
    y: parseFloat(day.projected_balance),
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

// Minimum balance marker
const minBalanceAnnotation = computed(() => {
  if (!props.summary.min_balance_date) return []

  const minDate = new Date(props.summary.min_balance_date).getTime()
  const minBalance = parseFloat(props.summary.min_balance)

  // Only show if minimum is significantly lower than ending balance
  const endBalance = parseFloat(props.summary.ending_balance)
  if (minBalance >= endBalance * 0.95) return []

  return [
    {
      x: minDate,
      y: minBalance,
      marker: {
        size: 6,
        fillColor: '#f59e0b',
        strokeColor: '#f59e0b',
      },
      label: {
        borderColor: '#f59e0b',
        style: {
          color: '#fff',
          background: '#f59e0b',
          fontSize: '10px',
        },
        text: `Min: ${formatCompactCurrency(minBalance)}`,
        offsetY: 0,
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
      const day = props.daily[dataPointIndex]
      if (!day) return ''

      const income = parseFloat(day.daily_income)
      const expenses = parseFloat(day.daily_expenses)
      const balance = parseFloat(day.projected_balance)

      let html = `<div class="px-3 py-2 text-sm">`
      html += `<div class="font-semibold">${formatDate(day.forecast_date)}</div>`
      html += `<div class="mt-1">Balance: <span class="font-medium">${formatCurrency(balance)}</span></div>`

      if (income > 0 || expenses > 0) {
        if (income > 0) {
          html += `<div class="text-emerald-400">+${formatCurrency(income)} income</div>`
        }
        if (expenses > 0) {
          html += `<div class="text-red-400">-${formatCurrency(expenses)} expenses</div>`
        }
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
    points: minBalanceAnnotation.value,
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

  if (Math.abs(amount) >= 1000000) {
    return `${symbol}${(amount / 1000000).toFixed(1)}M`
  }
  if (Math.abs(amount) >= 1000) {
    return `${symbol}${(amount / 1000).toFixed(0)}K`
  }
  return `${symbol}${amount.toFixed(0)}`
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
        <h2 class="text-lg font-semibold">90-Day Forecast</h2>
        <p class="mt-1 text-sm text-muted">
          Based on recurring patterns and planned transactions
        </p>
        <p class="text-emerald-400 mt-2 text-2xl font-bold">
          {{ formatCurrency(endingBalance) }}
          <span class="text-base font-normal text-muted">projected</span>
        </p>
      </div>

      <!-- Right: Change indicator -->
      <div class="text-right">
        <p class="text-sm text-muted">90-Day Change</p>
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
          class="bg-emerald-500/20 flex h-10 w-10 items-center justify-center rounded-full"
        >
          <!-- Arrow up icon -->
          <svg
            class="text-emerald-400 h-5 w-5"
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
          <p class="text-emerald-400 text-lg font-semibold">
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
