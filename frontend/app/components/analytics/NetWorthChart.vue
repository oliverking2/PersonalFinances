<!-- ==========================================================================
NetWorthChart
Area chart showing net worth trend over time with milestone markers
============================================================================ -->

<script setup lang="ts">
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  // Net worth data: array of rows from fct_net_worth_history
  data: Array<{
    balance_date: string
    net_worth: number
    daily_change: number
    rolling_7d_avg?: number | null
    currency: string
  }>
  // Optional milestones to show as horizontal lines
  milestones?: Array<{
    name: string
    target_amount: number
    target_date?: string | null
  }>
  // Show rolling average line
  showRollingAvg?: boolean
}>()

// ---------------------------------------------------------------------------
// Computed: Chart data
// ---------------------------------------------------------------------------

const series = computed(() => {
  const result = []

  // Main net worth line
  const netWorthData = props.data.map((item) => ({
    x: new Date(item.balance_date).getTime(),
    y: Math.round(item.net_worth * 100) / 100,
  }))
  result.push({ name: 'Net Worth', data: netWorthData })

  // Rolling average line (optional)
  if (props.showRollingAvg) {
    const avgData = props.data
      .filter((item) => item.rolling_7d_avg != null)
      .map((item) => ({
        x: new Date(item.balance_date).getTime(),
        y: Math.round((item.rolling_7d_avg ?? 0) * 100) / 100,
      }))
    if (avgData.length > 0) {
      result.push({ name: '7-Day Average', data: avgData })
    }
  }

  return result
})

// Calculate milestone annotations
const milestoneAnnotations = computed(() => {
  if (!props.milestones?.length) return []

  return props.milestones.map((milestone) => ({
    y: milestone.target_amount,
    borderColor: '#f59e0b',
    borderWidth: 2,
    strokeDashArray: 5,
    label: {
      borderColor: '#f59e0b',
      style: {
        color: '#fff',
        background: '#f59e0b',
        fontSize: '11px',
        padding: { left: 8, right: 8, top: 4, bottom: 4 },
      },
      text: milestone.name,
      position: 'right',
    },
  }))
})

// ---------------------------------------------------------------------------
// Computed: Summary metrics
// ---------------------------------------------------------------------------

const currentNetWorth = computed(() => {
  if (!props.data.length) return 0
  return props.data[props.data.length - 1]?.net_worth ?? 0
})

const totalChange = computed(() => {
  if (props.data.length < 2) return 0
  const first = props.data[0]?.net_worth ?? 0
  return currentNetWorth.value - first
})

const totalChangePercent = computed(() => {
  if (props.data.length < 2) return 0
  const first = props.data[0]?.net_worth ?? 0
  if (first === 0) return 0
  return ((currentNetWorth.value - first) / first) * 100
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
    width: props.showRollingAvg ? [2, 1] : [2],
    dashArray: props.showRollingAvg ? [0, 5] : [0],
  },
  colors: props.showRollingAvg ? ['#10b981', '#6b7280'] : ['#10b981'],
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.4,
      opacityTo: 0.05,
      stops: [0, 100],
    },
  },
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
    show: props.showRollingAvg,
    position: 'top',
    horizontalAlign: 'right',
    labels: { colors: '#e5e5e5' },
  },
  tooltip: {
    theme: 'dark',
    x: { format: 'dd MMM yyyy' },
    y: { formatter: (val: number) => formatCurrency(val) },
  },
  annotations: {
    yaxis: milestoneAnnotations.value,
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
    <!-- Header with summary metrics -->
    <div class="mb-4 flex items-start justify-between">
      <div>
        <h2 class="text-lg font-semibold">Net Worth</h2>
        <p class="text-emerald-400 mt-1 text-2xl font-bold">
          {{ formatCurrency(currentNetWorth) }}
        </p>
      </div>
      <!-- Change indicator -->
      <div v-if="data.length > 1" class="text-right">
        <p class="text-sm text-muted">Period Change</p>
        <p
          :class="[
            'text-lg font-semibold',
            totalChange >= 0 ? 'text-emerald-400' : 'text-red-400',
          ]"
        >
          {{ totalChange >= 0 ? '+' : '' }}{{ formatCurrency(totalChange) }}
          <span class="text-sm font-normal">
            ({{ totalChange >= 0 ? '+' : ''
            }}{{ totalChangePercent.toFixed(1) }}%)
          </span>
        </p>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-if="!data.length"
      class="flex h-64 items-center justify-center text-muted"
    >
      No net worth history available yet. Trigger a sync to capture balance
      snapshots.
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
  </div>
</template>
