<!-- ==========================================================================
JobStatusBadge
Small badge showing job status with appropriate colour and optional spinner
============================================================================ -->

<script setup lang="ts">
import type { JobStatus } from '~/types/jobs'

const props = defineProps<{
  status: JobStatus
}>()

// Map status to display configuration
const statusConfig = computed(() => {
  switch (props.status) {
    case 'pending':
      return {
        label: 'Pending',
        // Grey background, muted text
        classes: 'bg-border text-muted',
        showSpinner: false,
      }
    case 'running':
      return {
        label: 'Running',
        // Blue background for active state
        classes: 'bg-blue-500/20 text-blue-400',
        showSpinner: true,
      }
    case 'completed':
      return {
        label: 'Completed',
        // Green for success
        classes: 'bg-emerald-500/20 text-emerald-400',
        showSpinner: false,
      }
    case 'failed':
      return {
        label: 'Failed',
        // Red for errors
        classes: 'bg-red-500/20 text-red-400',
        showSpinner: false,
      }
    default:
      return {
        label: props.status,
        classes: 'bg-border text-muted',
        showSpinner: false,
      }
  }
})
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
      statusConfig.classes,
    ]"
  >
    <!-- Spinner for running state -->
    <svg
      v-if="statusConfig.showSpinner"
      class="h-3 w-3 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>

    <!-- Checkmark for completed -->
    <svg
      v-else-if="status === 'completed'"
      class="h-3 w-3"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M5 13l4 4L19 7"
      />
    </svg>

    <!-- X mark for failed -->
    <svg
      v-else-if="status === 'failed'"
      class="h-3 w-3"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>

    {{ statusConfig.label }}
  </span>
</template>
