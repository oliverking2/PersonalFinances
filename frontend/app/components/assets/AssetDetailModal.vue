<!-- ==========================================================================
AssetDetailModal
Modal showing detailed asset information with value history chart
============================================================================ -->

<script setup lang="ts">
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'
import type { ManualAsset, ValueSnapshot } from '~/types/manual-assets'
import {
  getAssetColour,
  getAssetBgColour,
  formatInterestRate,
} from '~/types/manual-assets'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
  asset: ManualAsset | null
}>()

const emit = defineEmits<{
  close: []
  updateValue: [asset: ManualAsset]
  edit: [asset: ManualAsset]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const { fetchValueHistory } = useManualAssetsApi()
const history = ref<ValueSnapshot[]>([])
const loadingHistory = ref(false)
const historyError = ref('')

// ---------------------------------------------------------------------------
// Watch for asset changes to load history
// ---------------------------------------------------------------------------
watch(
  () => props.asset,
  async (asset) => {
    if (asset && props.show) {
      await loadHistory(asset.id)
    }
  },
  { immediate: true },
)

watch(
  () => props.show,
  async (show) => {
    if (show && props.asset) {
      await loadHistory(props.asset.id)
    }
  },
)

async function loadHistory(assetId: string) {
  loadingHistory.value = true
  historyError.value = ''
  try {
    const response = await fetchValueHistory(assetId, 100)
    history.value = response.snapshots
  } catch (e) {
    historyError.value =
      e instanceof Error ? e.message : 'Failed to load history'
  } finally {
    loadingHistory.value = false
  }
}

// ---------------------------------------------------------------------------
// Computed: Chart data
// ---------------------------------------------------------------------------
const series = computed(() => {
  if (!history.value.length) return []

  // Sort by date ascending for the chart
  const sorted = [...history.value].sort(
    (a, b) =>
      new Date(a.captured_at).getTime() - new Date(b.captured_at).getTime(),
  )

  return [
    {
      name: 'Value',
      data: sorted.map((snap) => ({
        x: new Date(snap.captured_at).getTime(),
        y: Math.round(snap.value * 100) / 100,
      })),
    },
  ]
})

const chartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    fontFamily: 'inherit',
    background: 'transparent',
    animations: { enabled: true, speed: 600, easing: 'easeinout' },
    zoom: { enabled: false },
  },
  stroke: {
    curve: 'smooth',
    width: 2,
  },
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.4,
      opacityTo: 0.1,
      stops: [0, 100],
    },
  },
  colors: [props.asset?.is_liability ? '#f43f5e' : '#10b981'],
  markers: { size: 4, hover: { size: 6 } },
  dataLabels: { enabled: false },
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
    min: 0,
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
  tooltip: {
    theme: 'dark',
    x: { format: 'dd MMM yyyy HH:mm' },
    y: { formatter: (val: number) => formatCurrency(val) },
  },
}))

// ---------------------------------------------------------------------------
// Computed: Display helpers
// ---------------------------------------------------------------------------
const colourClass = computed(() =>
  props.asset ? getAssetColour(props.asset.is_liability) : '',
)
const bgColourClass = computed(() =>
  props.asset ? getAssetBgColour(props.asset.is_liability) : '',
)
const badgeText = computed(() =>
  props.asset?.is_liability ? 'Liability' : 'Asset',
)

// Calculate value change if we have history
const valueChange = computed(() => {
  if (history.value.length < 2) return null
  const sorted = [...history.value].sort(
    (a, b) =>
      new Date(a.captured_at).getTime() - new Date(b.captured_at).getTime(),
  )
  const oldest = sorted[0]!
  const newest = sorted[sorted.length - 1]!
  const change = newest.value - oldest.value
  const percentChange = oldest.value !== 0 ? (change / oldest.value) * 100 : 0
  return { change, percentChange }
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: props.asset?.currency || 'GBP',
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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <!-- Modal backdrop -->
  <Teleport to="body">
    <div
      v-if="show && asset"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      @click.self="emit('close')"
    >
      <!-- Modal content -->
      <div
        class="w-full max-w-2xl overflow-hidden rounded-xl border border-border bg-surface shadow-xl"
      >
        <!-- Header -->
        <div
          class="flex items-start justify-between border-b border-border p-6"
        >
          <div>
            <h2 class="text-xl font-bold">{{ asset.name }}</h2>
            <div class="mt-1 flex items-center gap-2">
              <span class="text-sm text-muted">{{ asset.display_type }}</span>
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="[colourClass, bgColourClass]"
              >
                {{ badgeText }}
              </span>
            </div>
          </div>
          <button
            type="button"
            class="rounded-lg p-2 text-muted transition-colors hover:bg-white/10 hover:text-foreground"
            @click="emit('close')"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Body -->
        <div class="max-h-[60vh] overflow-y-auto p-6">
          <!-- Current value and change -->
          <div class="mb-6 flex items-end justify-between">
            <div>
              <p class="text-sm text-muted">Current Value</p>
              <p class="text-3xl font-bold" :class="colourClass">
                <span v-if="asset.is_liability">-</span
                >{{ formatCurrency(asset.current_value) }}
              </p>
            </div>
            <div v-if="valueChange" class="text-right">
              <p class="text-sm text-muted">Total Change</p>
              <p
                class="text-lg font-semibold"
                :class="
                  valueChange.change >= 0 ? 'text-emerald-400' : 'text-rose-400'
                "
              >
                {{ valueChange.change >= 0 ? '+' : ''
                }}{{ formatCurrency(valueChange.change) }}
                <span class="text-sm">
                  ({{ valueChange.percentChange >= 0 ? '+' : ''
                  }}{{ valueChange.percentChange.toFixed(1) }}%)
                </span>
              </p>
            </div>
          </div>

          <!-- Value history chart -->
          <div class="mb-6 rounded-lg border border-border bg-background p-4">
            <h3 class="mb-4 font-semibold">Value History</h3>

            <!-- Loading state -->
            <div
              v-if="loadingHistory"
              class="flex h-48 items-center justify-center"
            >
              <div
                class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
              />
            </div>

            <!-- Error state -->
            <div
              v-else-if="historyError"
              class="flex h-48 items-center justify-center text-muted"
            >
              {{ historyError }}
            </div>

            <!-- Empty state -->
            <div
              v-else-if="history.length < 2"
              class="flex h-48 items-center justify-center text-center text-muted"
            >
              <p>
                Not enough data points yet.<br />
                Update the value a few times to see the history chart.
              </p>
            </div>

            <!-- Chart -->
            <div v-else>
              <ClientOnly>
                <VueApexCharts
                  type="area"
                  height="200"
                  :options="chartOptions"
                  :series="series"
                />
              </ClientOnly>
            </div>
          </div>

          <!-- Details section -->
          <div class="grid gap-4 sm:grid-cols-2">
            <!-- Interest rate -->
            <div
              v-if="asset.interest_rate"
              class="rounded-lg border border-border bg-background p-3"
            >
              <p class="text-sm text-muted">Interest Rate</p>
              <p class="font-medium">
                {{ formatInterestRate(asset.interest_rate) }}
              </p>
            </div>

            <!-- Acquisition info -->
            <div
              v-if="asset.acquisition_date || asset.acquisition_value"
              class="rounded-lg border border-border bg-background p-3"
            >
              <p class="text-sm text-muted">Acquired</p>
              <p class="font-medium">
                <span v-if="asset.acquisition_value">{{
                  formatCurrency(asset.acquisition_value)
                }}</span>
                <span v-if="asset.acquisition_value && asset.acquisition_date">
                  on
                </span>
                <span v-if="asset.acquisition_date">{{
                  formatDate(asset.acquisition_date)
                }}</span>
              </p>
            </div>

            <!-- Last updated -->
            <div class="rounded-lg border border-border bg-background p-3">
              <p class="text-sm text-muted">Last Updated</p>
              <p class="font-medium">
                {{ formatDateTime(asset.value_updated_at) }}
              </p>
            </div>

            <!-- Created -->
            <div class="rounded-lg border border-border bg-background p-3">
              <p class="text-sm text-muted">Created</p>
              <p class="font-medium">{{ formatDate(asset.created_at) }}</p>
            </div>
          </div>

          <!-- Notes -->
          <div
            v-if="asset.notes"
            class="mt-4 rounded-lg border border-border bg-background p-3"
          >
            <p class="text-sm text-muted">Notes</p>
            <p class="mt-1 whitespace-pre-wrap">{{ asset.notes }}</p>
          </div>

          <!-- Recent history list -->
          <div v-if="history.length > 0" class="mt-6">
            <h3 class="mb-3 font-semibold">Recent Updates</h3>
            <div class="space-y-2">
              <div
                v-for="snap in history.slice(0, 5)"
                :key="snap.id"
                class="flex items-center justify-between rounded-lg border border-border bg-background p-3"
              >
                <div>
                  <p class="font-medium">{{ formatCurrency(snap.value) }}</p>
                  <p v-if="snap.notes" class="text-sm text-muted">
                    {{ snap.notes }}
                  </p>
                </div>
                <p class="text-sm text-muted">
                  {{ formatDateTime(snap.captured_at) }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer actions -->
        <div class="flex justify-end gap-3 border-t border-border p-4">
          <button
            type="button"
            class="rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted transition-colors hover:bg-white/5 hover:text-foreground"
            @click="emit('edit', asset)"
          >
            Edit Details
          </button>
          <button
            type="button"
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
            @click="emit('updateValue', asset)"
          >
            Update Value
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
