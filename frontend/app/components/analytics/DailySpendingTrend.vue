<!-- ==========================================================================
DailySpendingTrend
Line chart showing daily spending totals over time
Clean display without zoom/toolbar controls
============================================================================ -->

<script setup lang="ts">
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  data: { date: string; total: number }[]
  previousData: { date: string; total: number }[]
  compareEnabled: boolean
  periodLabel: string
}>()

// ---------------------------------------------------------------------------
// Computed: Chart configuration
// ---------------------------------------------------------------------------

// Current period series (round to 2 decimal places to avoid floating point errors)
const currentSeries = computed(() => {
  return props.data.map((item) => ({
    x: new Date(item.date).getTime(),
    y: Math.round(item.total * 100) / 100,
  }))
})

// Previous period series (offset dates to align with current)
const previousSeries = computed(() => {
  if (!props.compareEnabled || !props.previousData.length) return []

  // Calculate offset: difference between first date of current and previous
  const currentStart = props.data[0]?.date
    ? new Date(props.data[0].date).getTime()
    : 0
  const previousStart = props.previousData[0]?.date
    ? new Date(props.previousData[0].date).getTime()
    : 0
  const offset = currentStart - previousStart

  return props.previousData.map((item) => ({
    x: new Date(item.date).getTime() + offset,
    y: Math.round(item.total * 100) / 100,
  }))
})

const series = computed(() => {
  const result = [
    {
      name: 'Current Period',
      data: currentSeries.value,
    },
  ]

  if (props.compareEnabled && previousSeries.value.length) {
    result.push({
      name: 'Previous Period',
      data: previousSeries.value,
    })
  }

  return result
})

// Chart options
const chartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    fontFamily: 'inherit',
    background: 'transparent',
    animations: {
      enabled: true,
      speed: 600,
      easing: 'easeinout',
    },
    zoom: { enabled: false },
    selection: { enabled: false },
  },
  stroke: {
    curve: 'smooth',
    width: props.compareEnabled ? [2, 2] : [2],
    dashArray: props.compareEnabled ? [0, 5] : [0], // Dashed line for previous
  },
  colors: props.compareEnabled ? ['#10b981', '#6b7280'] : ['#10b981'],
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
    hover: {
      size: 6,
    },
  },
  xaxis: {
    type: 'datetime',
    labels: {
      style: {
        colors: '#a3a3a3',
        fontSize: '12px',
      },
      datetimeFormatter: {
        day: 'dd MMM',
        month: "MMM 'yy",
      },
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: {
    labels: {
      style: {
        colors: '#a3a3a3',
        fontSize: '12px',
      },
      formatter: function (val: number) {
        if (val === undefined || val === null) return ''
        return formatCurrency(val, false) // No decimals for axis labels
      },
    },
  },
  grid: {
    borderColor: '#2e2e2e',
    strokeDashArray: 4,
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: true } },
  },
  legend: {
    show: props.compareEnabled,
    position: 'top',
    horizontalAlign: 'right',
    labels: {
      colors: '#e5e5e5',
    },
  },
  tooltip: {
    theme: 'dark',
    x: {
      format: 'dd MMM yyyy',
    },
    y: {
      formatter: (val: number) => formatCurrency(val),
    },
  },
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number, includeDecimals = true): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: includeDecimals ? 2 : 0,
    maximumFractionDigits: includeDecimals ? 2 : 0,
  }).format(amount)
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-6">
    <!-- Section header -->
    <h2 class="mb-4 text-lg font-semibold">Daily Spending Trend</h2>

    <!-- Empty state -->
    <div
      v-if="!data.length"
      class="flex h-64 items-center justify-center text-muted"
    >
      No spending data for this period
    </div>

    <!-- Chart -->
    <div v-else>
      <ClientOnly>
        <VueApexCharts
          type="area"
          height="300"
          :options="chartOptions"
          :series="series"
        />
      </ClientOnly>
    </div>
  </div>
</template>
