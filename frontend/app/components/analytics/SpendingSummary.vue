<!-- ==========================================================================
SpendingSummary
Stats card showing total spending, change vs previous period, and averages
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
defineProps<{
  total: number
  previousTotal: number | null
  changePercent: number | null
  transactionCount: number | null
  avgPerDay: number
  periodLabel: string
}>()

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-6">
    <!-- Section header -->
    <h2 class="mb-4 text-lg font-semibold">Summary</h2>

    <!-- Stats list -->
    <div class="space-y-4">
      <!-- Total Spent -->
      <div class="flex items-center justify-between">
        <span class="text-muted">Total Spent</span>
        <span class="text-xl font-semibold">{{ formatCurrency(total) }}</span>
      </div>

      <!-- vs Previous Period (only show when comparison enabled) -->
      <div
        v-if="changePercent !== null && previousTotal !== null"
        class="flex items-center justify-between"
      >
        <span class="text-muted">vs Previous Period</span>
        <span
          class="flex items-center gap-1 font-medium"
          :class="
            changePercent >= 0
              ? 'text-negative' // Red for spending more
              : 'text-positive' // Green for spending less
          "
        >
          <!-- Arrow icon -->
          <svg
            v-if="changePercent !== 0"
            class="h-4 w-4"
            :class="changePercent >= 0 ? '' : 'rotate-180'"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
              clip-rule="evenodd"
            />
          </svg>
          {{ changePercent >= 0 ? '+' : '' }}{{ changePercent.toFixed(1) }}%
        </span>
      </div>

      <!-- Transaction Count -->
      <div class="flex items-center justify-between">
        <span class="text-muted">Transactions</span>
        <span class="font-medium">
          {{ transactionCount !== null ? transactionCount : '—' }}
        </span>
      </div>

      <!-- Average Per Day -->
      <div class="flex items-center justify-between">
        <span class="text-muted">Avg per day</span>
        <span class="font-medium">{{ formatCurrency(avgPerDay) }}</span>
      </div>
    </div>
  </div>
</template>
