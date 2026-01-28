<!-- ==========================================================================
BudgetSummaryWidget
Dashboard widget showing budget status summary
============================================================================ -->

<script setup lang="ts">
import type { BudgetSummaryResponse } from '~/types/budgets'

// Props
defineProps<{
  summary: BudgetSummaryResponse | null
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
      <h3 class="text-lg font-semibold">Budgets</h3>
      <NuxtLink to="/budgets" class="text-sm text-primary hover:underline">
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
      v-else-if="!summary || summary.total_budgets === 0"
      class="mt-4 py-6 text-center"
    >
      <p class="text-muted">No budgets set up yet</p>
      <NuxtLink
        to="/budgets"
        class="mt-2 inline-block text-sm text-primary hover:underline"
      >
        Create your first budget
      </NuxtLink>
    </div>

    <!-- Summary content -->
    <div v-else class="mt-4 space-y-4">
      <!-- Spending progress -->
      <div>
        <div class="flex items-baseline justify-between text-sm">
          <span class="text-muted">Monthly spending</span>
          <span class="font-medium">
            {{ formatCurrency(summary.total_spent) }} /
            {{ formatCurrency(summary.total_budgeted) }}
          </span>
        </div>
        <!-- Overall progress bar -->
        <div class="mt-2 h-2 overflow-hidden rounded-full bg-gray-700/50">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="
              summary.total_spent >= summary.total_budgeted
                ? 'bg-red-500'
                : summary.total_spent >= summary.total_budgeted * 0.8
                  ? 'bg-amber-500'
                  : 'bg-emerald-500'
            "
            :style="{
              width: `${Math.min((summary.total_spent / summary.total_budgeted) * 100, 100)}%`,
            }"
          />
        </div>
      </div>

      <!-- Status indicators -->
      <div class="grid grid-cols-3 gap-2 text-center">
        <!-- On track -->
        <div class="bg-emerald-500/10 rounded-lg p-2">
          <p class="text-emerald-400 text-xl font-semibold">
            {{ summary.budgets_on_track }}
          </p>
          <p class="text-xs text-muted">On track</p>
        </div>

        <!-- Warning -->
        <div class="rounded-lg bg-amber-500/10 p-2">
          <p class="text-xl font-semibold text-amber-400">
            {{ summary.budgets_warning }}
          </p>
          <p class="text-xs text-muted">Warning</p>
        </div>

        <!-- Exceeded -->
        <div class="rounded-lg bg-red-500/10 p-2">
          <p class="text-xl font-semibold text-red-400">
            {{ summary.budgets_exceeded }}
          </p>
          <p class="text-xs text-muted">Exceeded</p>
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
