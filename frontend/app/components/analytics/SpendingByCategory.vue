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
  'click-category': [category: string]
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

// Calculate max x-axis value - round up to next £100 with buffer for labels
const xAxisMax = computed(() => {
  const firstSeries = series.value[0]
  if (!firstSeries || !firstSeries.data || firstSeries.data.length === 0) {
    return undefined
  }
  const maxValue = Math.max(...firstSeries.data)
  // Add 15% buffer then round up to next £100
  const withBuffer = maxValue * 1.15
  return Math.ceil(withBuffer / 100) * 100
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
        config: { dataPointIndex: number },
      ) => {
        const categoryName = categories.value[config.dataPointIndex]
        if (categoryName) {
          emit('click-category', categoryName)
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
        position: 'top',
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
    offsetX: 5,
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
    // Round max up to next £100 with buffer for labels
    max: xAxisMax.value,
    tickAmount: xAxisMax.value ? Math.ceil(xAxisMax.value / 100) : undefined,
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
