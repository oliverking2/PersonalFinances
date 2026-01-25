<!-- ==========================================================================
CategoryBreakdown
Donut chart showing spending distribution by category
Uses ApexCharts with center label showing total
============================================================================ -->

<script setup lang="ts">
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  data: { name: string; total: number; colour: string }[]
  total: number
}>()

// ---------------------------------------------------------------------------
// Computed: Chart configuration
// ---------------------------------------------------------------------------

const series = computed(() => props.data.map((item) => item.total))
const labels = computed(() => props.data.map((item) => item.name))
const colours = computed(() => props.data.map((item) => item.colour))

const chartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: 'donut',
    toolbar: { show: false },
    fontFamily: 'inherit',
    background: 'transparent',
    animations: {
      enabled: true,
      speed: 500,
    },
  },
  labels: labels.value,
  colors: colours.value,
  plotOptions: {
    pie: {
      donut: {
        size: '70%',
        labels: {
          show: true,
          name: {
            show: true,
            fontSize: '14px',
            fontWeight: 500,
            color: '#a3a3a3',
            offsetY: -10,
          },
          value: {
            show: true,
            fontSize: '24px',
            fontWeight: 600,
            color: '#e5e5e5',
            offsetY: 5,
            formatter: (val: string) => formatCurrency(Number(val)),
          },
          total: {
            show: true,
            showAlways: true,
            label: 'Total',
            fontSize: '14px',
            fontWeight: 500,
            color: '#a3a3a3',
            formatter: () => formatCurrency(props.total),
          },
        },
      },
    },
  },
  legend: {
    position: 'right',
    labels: {
      colors: '#e5e5e5',
    },
    markers: {
      offsetX: -4,
    },
    itemMargin: {
      vertical: 4,
    },
    formatter: (seriesName: string, opts: { seriesIndex: number }) => {
      const value = props.data[opts.seriesIndex]?.total || 0
      const percent =
        props.total > 0 ? ((value / props.total) * 100).toFixed(0) : 0
      return `${seriesName} (${percent}%)`
    },
  },
  dataLabels: {
    enabled: false,
  },
  stroke: {
    show: true,
    width: 2,
    colors: ['#1e1e1e'],
  },
  tooltip: {
    theme: 'dark',
    y: {
      formatter: (val: number) => formatCurrency(val),
    },
  },
  responsive: [
    {
      breakpoint: 640,
      options: {
        legend: {
          position: 'bottom',
        },
      },
    },
  ],
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
    <h2 class="mb-4 text-lg font-semibold">Category Breakdown</h2>

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
          type="donut"
          height="300"
          :options="chartOptions"
          :series="series"
        />
      </ClientOnly>
    </div>
  </div>
</template>
