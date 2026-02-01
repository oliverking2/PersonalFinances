<!-- ==========================================================================
GoalsProgressWidget
Dashboard widget showing savings goals summary
============================================================================ -->

<script setup lang="ts">
import type { GoalSummaryResponse } from '~/types/goals'

// Props
defineProps<{
  summary: GoalSummaryResponse | null
  loading?: boolean
}>()

// Format currency
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
  <div class="widget">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">Savings Goals</h3>
      <NuxtLink
        to="/planning/goals"
        class="text-sm text-primary hover:underline"
      >
        View all
      </NuxtLink>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="mt-4 flex items-center justify-center py-8">
      <div
        class="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"
      />
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!summary || summary.total_goals === 0"
      class="mt-4 py-6 text-center"
    >
      <p class="text-muted">No savings goals set up yet</p>
      <NuxtLink
        to="/planning/goals"
        class="mt-2 inline-block text-sm text-primary hover:underline"
      >
        Create your first goal
      </NuxtLink>
    </div>

    <!-- Summary content -->
    <div v-else class="mt-4 space-y-4">
      <!-- Overall progress -->
      <div class="flex items-center gap-4">
        <!-- Progress ring -->
        <GoalsProgressRing
          :percentage="summary.overall_progress"
          :size="64"
          :stroke-width="5"
        />

        <!-- Progress details -->
        <div class="flex-1">
          <p class="text-lg font-semibold">
            {{ formatCurrency(summary.total_saved) }}
          </p>
          <p class="text-sm text-muted">
            of {{ formatCurrency(summary.total_target) }} total
          </p>
        </div>
      </div>

      <!-- Goal counts -->
      <div class="grid grid-cols-3 gap-2 text-center">
        <!-- Active -->
        <div class="bg-emerald-500/10 rounded-lg p-2">
          <p class="text-emerald-400 text-xl font-semibold">
            {{ summary.active_goals }}
          </p>
          <p class="text-xs text-muted">Active</p>
        </div>

        <!-- Completed -->
        <div class="rounded-lg bg-sky-500/10 p-2">
          <p class="text-xl font-semibold text-sky-400">
            {{ summary.completed_goals }}
          </p>
          <p class="text-xs text-muted">Completed</p>
        </div>

        <!-- Total -->
        <div class="rounded-lg bg-gray-500/10 p-2">
          <p class="text-xl font-semibold text-gray-400">
            {{ summary.total_goals }}
          </p>
          <p class="text-xs text-muted">Total</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.widget {
  @apply rounded-xl border border-border bg-surface p-4;
}
</style>
