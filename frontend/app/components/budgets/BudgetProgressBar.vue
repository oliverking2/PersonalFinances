<!-- ==========================================================================
BudgetProgressBar
Displays a coloured progress bar for budget spending
============================================================================ -->

<script setup lang="ts">
import type { BudgetStatus } from '~/types/budgets'
import { getProgressBarColour } from '~/types/budgets'

// Props
const props = defineProps<{
  percentage: number // 0-100+
  status: BudgetStatus
  showLabel?: boolean // Show percentage label
}>()

// Clamp display percentage to 100 for visual (can still exceed internally)
const displayPercentage = computed(() => Math.min(props.percentage, 100))

// Get the progress bar colour based on status
const barColour = computed(() => getProgressBarColour(props.status))
</script>

<template>
  <!-- Progress bar container -->
  <div class="progress-container">
    <!-- Track (background) -->
    <div class="progress-track">
      <!-- Filled bar -->
      <div
        class="progress-bar"
        :style="{ width: `${displayPercentage}%`, backgroundColor: barColour }"
      />
    </div>

    <!-- Label (optional) -->
    <span v-if="showLabel" class="progress-label">
      {{ Math.round(percentage) }}%
    </span>
  </div>
</template>

<style scoped>
/* Container for the progress bar and optional label */
.progress-container {
  @apply flex items-center gap-2;
}

/* Track is the full-width background */
.progress-track {
  @apply h-2 flex-1 overflow-hidden rounded-full bg-gray-700/50;
}

/* Filled portion of the bar */
.progress-bar {
  @apply h-full rounded-full transition-all duration-300;
}

/* Percentage label */
.progress-label {
  @apply min-w-[3rem] text-right text-sm font-medium text-muted;
}
</style>
