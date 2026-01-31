<!-- ==========================================================================
BalanceHistoryChart
Line chart showing account balance history over time
Supports multiple accounts with different coloured lines
============================================================================ -->

<script setup lang="ts">
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  // Balance data: array of rows from fct_daily_balance_history
  // Each row has: account_id, account_name, balance_date, balance_amount, etc.
  data: Array<{
    account_id: string
    account_name: string
    balance_date: string
    balance_amount: number
    balance_currency: string
    total_value?: number | null
    daily_change: number
  }>
  // Optional: show total_value instead of balance_amount (for investment accounts)
  showTotalValue?: boolean
}>()

// ---------------------------------------------------------------------------
// Computed: Group data by account for multi-line chart
// ---------------------------------------------------------------------------

// Get unique accounts and assign colours
const accountColours = computed(() => {
  // Emerald-based palette for multiple accounts
  const palette = [
    '#10b981', // emerald-500
    '#3b82f6', // blue-500
    '#f59e0b', // amber-500
    '#ef4444', // red-500
    '#8b5cf6', // violet-500
    '#ec4899', // pink-500
    '#14b8a6', // teal-500
    '#6366f1', // indigo-500
  ]

  const accounts = [...new Set(props.data.map((row) => row.account_id))]
  const colourMap = new Map<string, string>()

  accounts.forEach((accountId, index) => {
    const colour = palette[index % palette.length] ?? '#10b981'
    colourMap.set(accountId, colour)
  })

  return colourMap
})

// Group data by account for series
const series = computed(() => {
  // Group rows by account_id
  const accountGroups = new Map<
    string,
    { name: string; data: Array<{ x: number; y: number }> }
  >()

  for (const row of props.data) {
    const valueToUse =
      props.showTotalValue && row.total_value != null
        ? row.total_value
        : row.balance_amount

    if (!accountGroups.has(row.account_id)) {
      accountGroups.set(row.account_id, {
        name: row.account_name,
        data: [],
      })
    }

    accountGroups.get(row.account_id)!.data.push({
      x: new Date(row.balance_date).getTime(),
      y: Math.round(valueToUse * 100) / 100,
    })
  }

  // Sort each account's data by date
  for (const group of accountGroups.values()) {
    group.data.sort((a, b) => a.x - b.x)
  }

  return Array.from(accountGroups.values())
})

// Get colours in same order as series
const colours = computed(() => {
  const accounts = [...new Set(props.data.map((row) => row.account_id))]
  return accounts.map(
    (accountId) => accountColours.value.get(accountId) || '#10b981',
  )
})

// ---------------------------------------------------------------------------
// Computed: Chart configuration
// ---------------------------------------------------------------------------

const chartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: 'line',
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
  colors: colours.value,
  markers: { size: 0, hover: { size: 5 } },
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
  legend: {
    show: series.value.length > 1,
    position: 'top',
    horizontalAlign: 'right',
    labels: { colors: '#e5e5e5' },
    markers: { size: 8, shape: 'circle' },
  },
  tooltip: {
    theme: 'dark',
    x: { format: 'dd MMM yyyy' },
    y: { formatter: (val: number) => formatCurrency(val) },
  },
}))

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

function formatCompactCurrency(amount: number): string {
  // Use compact notation for y-axis labels (e.g., 10K, 1.5M)
  if (Math.abs(amount) >= 1000000) {
    return `£${(amount / 1000000).toFixed(1)}M`
  }
  if (Math.abs(amount) >= 1000) {
    return `£${(amount / 1000).toFixed(0)}K`
  }
  return `£${amount.toFixed(0)}`
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-6">
    <!-- Section header -->
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold">
        {{ showTotalValue ? 'Portfolio Value Over Time' : 'Balance History' }}
      </h2>
    </div>

    <!-- Empty state -->
    <div
      v-if="!data.length"
      class="flex h-64 items-center justify-center text-muted"
    >
      No balance history available yet. Trigger a sync to capture balance
      snapshots.
    </div>

    <!-- Chart -->
    <div v-else>
      <ClientOnly>
        <VueApexCharts
          type="line"
          height="350"
          :options="chartOptions"
          :series="series"
        />
      </ClientOnly>
    </div>
  </div>
</template>
