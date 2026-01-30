<!-- ==========================================================================
DatasetCard
Card component showing dataset info with export button
============================================================================ -->

<script setup lang="ts">
import type { Dataset } from '~/types/analytics'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

const props = defineProps<{
  dataset: Dataset
}>()

// ---------------------------------------------------------------------------
// Emits
// ---------------------------------------------------------------------------

const emit = defineEmits<{
  export: [dataset: Dataset]
}>()

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Get a user-friendly time grain label
const timeGrainLabel = computed(() => {
  if (!props.dataset.time_grain) return null
  switch (props.dataset.time_grain) {
    case 'day':
      return 'Daily'
    case 'month':
      return 'Monthly'
    case 'week':
      return 'Weekly'
    default:
      return props.dataset.time_grain
  }
})

// Get group badge colour
const groupColor = computed(() => {
  switch (props.dataset.group) {
    case 'facts':
      return 'bg-primary/20 text-primary'
    case 'aggregations':
      return 'bg-sage/20 text-sage'
    case 'dimensions':
      return 'bg-amber-500/20 text-amber-400'
    default:
      return 'bg-gray-500/20 text-gray-400'
  }
})
</script>

<template>
  <!-- Card container with hover effect - flex column for consistent height in grid -->
  <div
    class="flex flex-col rounded-lg border border-border bg-surface p-5 transition-colors hover:border-border/80"
  >
    <!-- Title -->
    <h3 class="text-lg font-semibold">
      {{ dataset.friendly_name }}
    </h3>

    <!-- Description - grows to fill available space -->
    <p v-if="dataset.description" class="mt-1 flex-1 text-sm text-muted">
      {{ dataset.description }}
    </p>
    <div v-else class="flex-1" />

    <!-- Metadata badges -->
    <div class="mt-3 flex flex-wrap gap-2">
      <!-- Group badge -->
      <span
        class="rounded-full px-2.5 py-0.5 text-xs font-medium"
        :class="groupColor"
      >
        {{ dataset.group }}
      </span>

      <!-- Time grain badge (if applicable) -->
      <span
        v-if="timeGrainLabel"
        class="rounded-full bg-gray-500/20 px-2.5 py-0.5 text-xs font-medium text-gray-400"
      >
        {{ timeGrainLabel }}
      </span>
    </div>

    <!-- Export button - full width at bottom -->
    <AppButton class="mt-4 w-full" size="sm" @click="emit('export', dataset)">
      Export
    </AppButton>
  </div>
</template>
