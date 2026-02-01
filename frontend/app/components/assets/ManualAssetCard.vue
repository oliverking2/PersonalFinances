<!-- ==========================================================================
ManualAssetCard
Card component for displaying a single manual asset or liability
Includes a mini sparkline showing value history
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
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  asset: ManualAsset
}>()

// ---------------------------------------------------------------------------
// Emits
// ---------------------------------------------------------------------------
const emit = defineEmits<{
  view: [asset: ManualAsset]
  edit: [asset: ManualAsset]
  updateValue: [asset: ManualAsset]
  delete: [asset: ManualAsset]
}>()

// Dropdown state for actions menu
const showDropdown = ref(false)

// ---------------------------------------------------------------------------
// Fetch history for sparkline
// ---------------------------------------------------------------------------
const { fetchValueHistory } = useManualAssetsApi()
const history = ref<ValueSnapshot[]>([])

onMounted(async () => {
  try {
    const response = await fetchValueHistory(props.asset.id, 20)
    history.value = response.snapshots
  } catch {
    // Silently fail - sparkline is optional
  }
})

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Colour classes based on whether it's an asset or liability
const colourClass = computed(() => getAssetColour(props.asset.is_liability))
const bgColourClass = computed(() => getAssetBgColour(props.asset.is_liability))

// Badge text
const badgeText = computed(() =>
  props.asset.is_liability ? 'Liability' : 'Asset',
)

// Sparkline chart data - need at least 2 points
const hasSparkline = computed(() => history.value.length >= 2)

const sparklineSeries = computed(() => {
  if (!hasSparkline.value) return []

  // Sort by date ascending
  const sorted = [...history.value].sort(
    (a, b) =>
      new Date(a.captured_at).getTime() - new Date(b.captured_at).getTime(),
  )

  return [
    {
      name: 'Value',
      data: sorted.map((snap) => snap.value),
    },
  ]
})

// Determine if trend is up or down
const trendUp = computed(() => {
  if (history.value.length < 2) return null
  const sorted = [...history.value].sort(
    (a, b) =>
      new Date(a.captured_at).getTime() - new Date(b.captured_at).getTime(),
  )
  const first = sorted[0]!.value
  const last = sorted[sorted.length - 1]!.value
  return last >= first
})

const sparklineColour = computed(() => {
  if (trendUp.value === null) return '#10b981'
  // For liabilities, down is good (paying off debt)
  if (props.asset.is_liability) {
    return trendUp.value ? '#f43f5e' : '#10b981'
  }
  // For assets, up is good
  return trendUp.value ? '#10b981' : '#f43f5e'
})

const sparklineOptions = computed<ApexOptions>(() => ({
  chart: {
    type: 'line',
    sparkline: { enabled: true },
    animations: { enabled: false },
  },
  stroke: {
    curve: 'smooth',
    width: 2,
  },
  colors: [sparklineColour.value],
  tooltip: { enabled: false },
  dataLabels: { enabled: false },
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number | string): string {
  const value = typeof amount === 'string' ? parseFloat(amount) : amount
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: props.asset.currency || 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7)
    return weeks === 1 ? '1 week ago' : `${weeks} weeks ago`
  }
  if (diffDays < 365) {
    const months = Math.floor(diffDays / 30)
    return months === 1 ? '1 month ago' : `${months} months ago`
  }
  return formatDate(dateStr)
}
</script>

<template>
  <div
    class="cursor-pointer rounded-lg border border-border bg-surface p-4 transition-colors hover:border-primary/50"
    :class="{ 'opacity-60': !asset.is_active }"
    @click="emit('view', asset)"
  >
    <!-- Header: Name, type badge, and actions menu -->
    <div class="mb-3 flex items-start justify-between">
      <div class="flex-1">
        <!-- Asset name -->
        <h3 class="font-medium">{{ asset.name }}</h3>
        <!-- Type and liability badge -->
        <div class="mt-1 flex flex-wrap items-center gap-2">
          <span class="text-sm text-muted">{{ asset.display_type }}</span>
          <span
            class="rounded-full px-2 py-0.5 text-xs font-medium"
            :class="[colourClass, bgColourClass]"
          >
            {{ badgeText }}
          </span>
        </div>
      </div>

      <!-- Actions dropdown -->
      <div class="relative" @click.stop>
        <button
          class="rounded p-1 text-muted transition-colors hover:bg-white/10 hover:text-foreground"
          @click="showDropdown = !showDropdown"
        >
          <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"
            />
          </svg>
        </button>
        <div
          v-if="showDropdown"
          class="absolute right-0 top-full z-10 mt-1 w-36 rounded-lg border border-border bg-surface py-1 shadow-lg"
          @click="showDropdown = false"
        >
          <button
            class="w-full px-3 py-1.5 text-left text-sm text-muted hover:bg-white/5 hover:text-foreground"
            @click="emit('edit', asset)"
          >
            Edit Details
          </button>
          <button
            class="w-full px-3 py-1.5 text-left text-sm text-muted hover:bg-white/5 hover:text-foreground"
            @click="emit('updateValue', asset)"
          >
            Update Value
          </button>
          <button
            class="w-full px-3 py-1.5 text-left text-sm text-red-400 hover:bg-white/5"
            @click="emit('delete', asset)"
          >
            Delete
          </button>
        </div>
      </div>
    </div>

    <!-- Current value and sparkline row -->
    <div class="mb-3 flex items-end justify-between gap-4">
      <p class="text-2xl font-bold" :class="colourClass">
        <span v-if="asset.is_liability">-</span
        >{{ formatCurrency(asset.current_value) }}
      </p>
      <!-- Sparkline chart -->
      <div v-if="hasSparkline" class="h-10 w-20 flex-shrink-0">
        <ClientOnly>
          <VueApexCharts
            type="line"
            height="40"
            width="80"
            :options="sparklineOptions"
            :series="sparklineSeries"
          />
        </ClientOnly>
      </div>
    </div>

    <!-- Details row: Interest rate (if applicable) and last updated -->
    <div class="flex items-center justify-between text-sm">
      <div v-if="asset.interest_rate" class="text-muted">
        {{ formatInterestRate(asset.interest_rate) }}
      </div>
      <div v-else class="text-muted" />

      <div class="text-muted">
        Updated {{ formatRelativeDate(asset.value_updated_at) }}
      </div>
    </div>

    <!-- Quick update value button -->
    <div class="mt-3 border-t border-border pt-3" @click.stop>
      <button
        class="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm text-muted transition-colors hover:border-primary hover:text-foreground"
        @click="emit('updateValue', asset)"
      >
        <svg
          class="h-4 w-4"
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
        Update Value
      </button>
    </div>

    <!-- Notes (if any) -->
    <div v-if="asset.notes" class="mt-3 text-xs italic text-muted">
      {{ asset.notes }}
    </div>
  </div>
</template>
