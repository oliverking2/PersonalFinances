<!-- ==========================================================================
PeriodFilter
Dropdown for selecting time period and styled toggle for comparison mode
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
defineProps<{
  periodLabel: string
}>()

const period = defineModel<
  'this_month' | 'last_month' | 'last_30_days' | 'last_90_days' | 'this_year'
>('period', { required: true })
const compare = defineModel<boolean>('compare', { required: true })

// ---------------------------------------------------------------------------
// Period options
// ---------------------------------------------------------------------------
const periodOptions = [
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: 'last_30_days', label: 'Last 30 Days' },
  { value: 'last_90_days', label: 'Last 90 Days' },
  { value: 'this_year', label: 'This Year' },
]
</script>

<template>
  <div
    class="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-surface p-4"
  >
    <!-- Period dropdown -->
    <div class="flex items-center gap-2">
      <label class="text-sm font-medium text-muted">Period:</label>
      <div class="w-40">
        <AppSelect v-model="period" :options="periodOptions" />
      </div>
    </div>

    <!-- Comparison toggle (styled switch) -->
    <button
      type="button"
      class="flex items-center gap-3"
      @click="compare = !compare"
    >
      <!-- Toggle switch track -->
      <span
        class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
        :class="compare ? 'bg-primary' : 'bg-border'"
      >
        <!-- Toggle switch thumb -->
        <span
          class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
          :class="compare ? 'translate-x-5' : 'translate-x-0'"
        />
      </span>
      <span class="text-sm text-foreground">Compare to previous period</span>
    </button>
  </div>
</template>
