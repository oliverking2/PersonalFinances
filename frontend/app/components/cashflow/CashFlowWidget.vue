<!-- ==========================================================================
CashFlowWidget
Dashboard widget showing income vs expenses for the current month
============================================================================ -->

<script setup lang="ts">
// Props
const props = defineProps<{
  income: number | null
  spending: number | null
  loading?: boolean
}>()

// Net change: income minus spending
const netChange = computed(() => {
  if (props.income === null || props.spending === null) return null
  return props.income - props.spending
})

// Bar widths as percentages (relative to the larger of income/spending)
const maxAmount = computed(() => {
  return Math.max(props.income || 0, props.spending || 0)
})

const incomeBarWidth = computed(() => {
  if (!maxAmount.value || props.income === null || props.income === 0) return 0
  // Minimum 3% so the bar is always visible when there's a value
  return Math.max(3, (props.income / maxAmount.value) * 100)
})

const spendingBarWidth = computed(() => {
  if (!maxAmount.value || props.spending === null || props.spending === 0)
    return 0
  return Math.max(3, (props.spending / maxAmount.value) * 100)
})

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
      <h3 class="text-lg font-semibold">Cash Flow</h3>
      <NuxtLink
        to="/insights/analytics"
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
      v-else-if="income === null && spending === null"
      class="mt-4 py-6 text-center"
    >
      <p class="text-muted">No data yet</p>
    </div>

    <!-- Content -->
    <div v-else class="mt-4 space-y-4">
      <!-- Income bar -->
      <div>
        <div class="flex items-baseline justify-between text-sm">
          <span class="text-muted">Income</span>
          <span class="font-medium text-emerald-400">
            {{ income !== null ? formatCurrency(income) : '—' }}
          </span>
        </div>
        <!-- Bar (green) -->
        <div class="mt-1.5 h-2.5 overflow-hidden rounded-full bg-gray-700/50">
          <div
            class="h-full rounded-full bg-emerald-500 transition-all duration-300"
            :style="{ width: `${incomeBarWidth}%` }"
          />
        </div>
      </div>

      <!-- Expenses bar -->
      <div>
        <div class="flex items-baseline justify-between text-sm">
          <span class="text-muted">Expenses</span>
          <span class="font-medium text-amber-400">
            {{ spending !== null ? formatCurrency(spending) : '—' }}
          </span>
        </div>
        <!-- Bar (amber/red depending on vs income) -->
        <div class="mt-1.5 h-2.5 overflow-hidden rounded-full bg-gray-700/50">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="
              spending !== null && income !== null && spending > income
                ? 'bg-red-500'
                : 'bg-amber-500'
            "
            :style="{ width: `${spendingBarWidth}%` }"
          />
        </div>
      </div>

      <!-- Net change summary -->
      <div class="grid grid-cols-3 gap-2 text-center">
        <!-- Income -->
        <div class="rounded-lg bg-emerald-500/10 p-2">
          <p class="text-xl font-semibold text-emerald-400">
            {{ income !== null ? formatCurrency(income) : '—' }}
          </p>
          <p class="text-xs text-muted">Income</p>
        </div>

        <!-- Expenses -->
        <div class="rounded-lg bg-amber-500/10 p-2">
          <p class="text-xl font-semibold text-amber-400">
            {{ spending !== null ? formatCurrency(spending) : '—' }}
          </p>
          <p class="text-xs text-muted">Expenses</p>
        </div>

        <!-- Net -->
        <div
          class="rounded-lg p-2"
          :class="
            netChange !== null && netChange >= 0
              ? 'bg-emerald-500/10'
              : 'bg-red-500/10'
          "
        >
          <p
            class="text-xl font-semibold"
            :class="
              netChange !== null && netChange >= 0
                ? 'text-emerald-400'
                : 'text-red-400'
            "
          >
            {{
              netChange !== null
                ? `${netChange >= 0 ? '+' : ''}${formatCurrency(netChange)}`
                : '—'
            }}
          </p>
          <p class="text-xs text-muted">Net</p>
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
