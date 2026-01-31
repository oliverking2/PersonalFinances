<!-- ==========================================================================
RecurringBadge
Small badge indicating a transaction is part of a recurring pattern
Shows a repeat icon with optional frequency label
============================================================================ -->

<script setup lang="ts">
import type { RecurringFrequency, RecurringStatus } from '~/types/recurring'
import { getFrequencyShortLabel } from '~/types/recurring'

// Props
const props = defineProps<{
  frequency: RecurringFrequency
  status: RecurringStatus
  showLabel?: boolean // Show frequency text (default: hover only)
}>()

// Compute tooltip text
const tooltipText = computed(() => {
  const freqLabels: Record<RecurringFrequency, string> = {
    weekly: 'Weekly',
    fortnightly: 'Fortnightly',
    monthly: 'Monthly',
    quarterly: 'Quarterly',
    annual: 'Annual',
  }
  const statusLabel =
    props.status === 'pending'
      ? ' (pending)'
      : props.status === 'paused'
        ? ' (paused)'
        : props.status === 'cancelled'
          ? ' (cancelled)'
          : ''
  return `Recurring: ${freqLabels[props.frequency]}${statusLabel}`
})

// Badge colour varies by status
const badgeClass = computed(() => {
  // Active patterns get solid styling
  if (props.status === 'active') {
    return 'bg-primary/20 border-primary/40 text-primary'
  }
  // Pending patterns get muted styling
  if (props.status === 'pending') {
    return 'bg-gray-700/50 border-gray-600 text-gray-400'
  }
  // Paused and cancelled patterns get dimmed styling
  return 'bg-gray-800/50 border-gray-700 text-gray-500'
})
</script>

<template>
  <span class="recurring-badge" :class="badgeClass" :title="tooltipText">
    <!-- Repeat icon -->
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      class="h-3 w-3"
    >
      <path
        fill-rule="evenodd"
        d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
        clip-rule="evenodd"
      />
    </svg>

    <!-- Optional frequency label -->
    <span v-if="showLabel" class="ml-0.5 text-xs">
      {{ getFrequencyShortLabel(frequency) }}
    </span>
  </span>
</template>

<style scoped>
.recurring-badge {
  /* Layout: inline flex with gap */
  @apply inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5;

  /* Border */
  @apply border;

  /* Typography */
  @apply text-xs font-medium;

  /* Cursor for tooltip */
  @apply cursor-help;
}
</style>
