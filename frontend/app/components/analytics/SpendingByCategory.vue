<!-- ==========================================================================
SpendingByCategory
Horizontal bar chart showing spending by tag/category
Bars coloured by tag, click to view transactions
============================================================================ -->

<script setup lang="ts">
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  data: { name: string; total: number; colour: string }[]
  previousData: { name: string; total: number; colour: string }[]
  compareEnabled: boolean
  total: number
}>()

const emit = defineEmits<{
  'click-category': [category: string, period: 'current' | 'previous']
}>()

// ---------------------------------------------------------------------------
// Computed: Chart configuration
// ---------------------------------------------------------------------------

// Get all unique category names (current + previous for alignment)
const categories = computed(() => {
  const names = new Set<string>()
  for (const item of props.data) names.add(item.name)
  if (props.compareEnabled) {
    for (const item of props.previousData) names.add(item.name)
  }
  // Sort by current period total descending, fallback to name
  return Array.from(names).sort((a, b) => {
    const aTotal = props.data.find((d) => d.name === a)?.total || 0
    const bTotal = props.data.find((d) => d.name === b)?.total || 0
    return bTotal - aTotal
  })
})

// Build series data aligned to categories
const series = computed(() => {
  const currentSeries = categories.value.map((cat) => {
    const item = props.data.find((d) => d.name === cat)
    return item?.total || 0
  })

  if (props.compareEnabled && props.previousData.length > 0) {
    const previousSeries = categories.value.map((cat) => {
      const item = props.previousData.find((d) => d.name === cat)
      return item?.total || 0
    })
    return [
      { name: 'Current', data: currentSeries },
      { name: 'Previous', data: previousSeries },
    ]
  }

  return [{ name: 'Spending', data: currentSeries }]
})

// Get colours for current period bars (by tag colour)
const colours = computed(() => {
  return categories.value.map((cat) => {
    const item = props.data.find((d) => d.name === cat)
    return item?.colour || '#10b981'
  })
})

// Calculate dynamic tick interval based on max value to prevent label crowding
function calculateTickInterval(maxValue: number): number {
  if (maxValue <= 500) return 100
  if (maxValue <= 2000) return 500
  if (maxValue <= 10000) return 1000
  if (maxValue <= 50000) return 5000
  return 10000
}

// Calculate max x-axis value - consider ALL series and round to dynamic interval
const xAxisMax = computed(() => {
  // Get max from ALL series (current + previous if comparing)
  const allData = series.value.flatMap((s) => s.data)
  if (!allData.length) return undefined

  const maxValue = Math.max(...allData)
  if (maxValue === 0) return 100

  // Add 15% buffer then round up to next tick interval
  const tickInterval = calculateTickInterval(maxValue)
  const withBuffer = maxValue * 1.15
  return Math.ceil(withBuffer / tickInterval) * tickInterval
})

// Calculate tick amount to prevent label crowding
const tickAmount = computed(() => {
  if (!xAxisMax.value) return undefined
  const maxValue = Math.max(...series.value.flatMap((s) => s.data), 0)
  const tickInterval = calculateTickInterval(maxValue)
  return Math.min(8, Math.ceil(xAxisMax.value / tickInterval))
})

// Chart options
const chartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: 'bar',
    toolbar: { show: false },
    fontFamily: 'inherit',
    background: 'transparent',
    animations: {
      enabled: true,
      speed: 500,
      animateGradually: { enabled: true, delay: 100 },
    },
    events: {
      dataPointSelection: (
        _event: unknown,
        _chart: unknown,
        config: { dataPointIndex: number; seriesIndex: number },
      ) => {
        const categoryName = categories.value[config.dataPointIndex]
        if (categoryName) {
          // seriesIndex 0 = current period, 1 = previous period
          const period =
            props.compareEnabled && config.seriesIndex === 1
              ? 'previous'
              : 'current'
          emit('click-category', categoryName, period)
        }
      },
    },
    selection: { enabled: false },
    zoom: { enabled: false },
  },
  states: {
    hover: {
      filter: { type: 'darken', value: 0.9 },
    },
    active: {
      filter: { type: 'darken', value: 0.85 },
    },
  },
  plotOptions: {
    bar: {
      horizontal: true,
      borderRadius: 4,
      barHeight: props.compareEnabled ? '70%' : '60%',
      // distributed: true means each bar gets its own colour from the colors array
      distributed: !props.compareEnabled,
      dataLabels: {
        position: 'top', // Places labels at end of bar for horizontal charts
      },
    },
  },
  // Use tag colours - distributed mode applies colors per bar when not comparing
  colors: props.compareEnabled
    ? [
        // Current period uses tag colours via function
        ({ dataPointIndex }: { dataPointIndex: number }) =>
          colours.value[dataPointIndex] || '#10b981',
        '#4b5563', // Grey for previous period
      ]
    : colours.value,
  dataLabels: {
    enabled: true,
    formatter: (val: number) => formatCurrency(val),
    textAnchor: 'start',
    style: {
      fontSize: '12px',
      fontWeight: 500,
      colors: ['#e5e5e5'],
    },
    offsetX: 8,
    dropShadow: { enabled: false },
  },
  xaxis: {
    categories: categories.value,
    labels: {
      style: {
        colors: '#a3a3a3',
        fontSize: '12px',
      },
      formatter: (val: string) => formatCurrency(Number(val)),
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
    min: 0,
    // Dynamic max and tick amount based on data scale
    max: xAxisMax.value,
    tickAmount: tickAmount.value,
  },
  yaxis: {
    labels: {
      style: {
        colors: '#a3a3a3',
        fontSize: '13px',
      },
    },
  },
  grid: {
    borderColor: '#2e2e2e',
    strokeDashArray: 4,
    xaxis: { lines: { show: true } },
    yaxis: { lines: { show: false } },
    padding: { right: 80 }, // Extra space for data labels
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
    y: {
      formatter: (val: number) => formatCurrency(val),
    },
  },
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-6">
    <!-- Section header -->
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold">Spending by Category</h2>
      <span class="text-xs text-muted">Click a bar to view transactions</span>
    </div>

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
          type="bar"
          :height="Math.max(200, categories.length * 50)"
          :options="chartOptions"
          :series="series"
        />
      </ClientOnly>
    </div>
  </div>
</template>
