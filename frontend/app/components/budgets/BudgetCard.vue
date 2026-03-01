<!-- ==========================================================================
BudgetCard
Displays a single budget with progress bar and spending info
============================================================================ -->

<script setup lang="ts">
import type { BudgetWithSpending } from '~/types/budgets'
import {
  getStatusLabel,
  getStatusColour,
  getStatusBgColour,
  getPeriodLabel,
} from '~/types/budgets'

// Props
const props = defineProps<{
  budget: BudgetWithSpending
  // YYYY-MM-DD reference date; if absent, defaults to today (current period)
  referenceDate?: string
}>()

// Emits
const emit = defineEmits<{
  edit: []
  delete: []
}>()

// Compute the period start/end dates for the transactions link.
// Mirrors the backend get_period_date_range() logic so the link filters
// to exactly the same window the budget spending is calculated over.
const transactionsUrl = computed(() => {
  const ref = props.referenceDate
    ? new Date(props.referenceDate + 'T00:00:00')
    : new Date()

  const fmt = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  let start: string
  let end: string

  if (props.budget.period === 'weekly') {
    // ISO week: Monday → Sunday
    const daysFromMonday = ref.getDay() === 0 ? 6 : ref.getDay() - 1
    const monday = new Date(ref)
    monday.setDate(ref.getDate() - daysFromMonday)
    const sunday = new Date(monday)
    sunday.setDate(monday.getDate() + 6)
    start = fmt(monday)
    end = fmt(sunday)
  } else if (props.budget.period === 'quarterly') {
    const quarter = Math.floor(ref.getMonth() / 3)
    start = fmt(new Date(ref.getFullYear(), quarter * 3, 1))
    end = fmt(new Date(ref.getFullYear(), quarter * 3 + 3, 0))
  } else if (props.budget.period === 'annual') {
    start = `${ref.getFullYear()}-01-01`
    end = `${ref.getFullYear()}-12-31`
  } else {
    // Monthly (default)
    start = fmt(new Date(ref.getFullYear(), ref.getMonth(), 1))
    end = fmt(new Date(ref.getFullYear(), ref.getMonth() + 1, 0))
  }

  const tag = encodeURIComponent(props.budget.tag_name)
  return `/transactions?tag=${tag}&start_date=${start}&end_date=${end}`
})

// Format currency
function formatCurrency(amount: number, currency: string = 'GBP'): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(amount))
}
</script>

<template>
  <div class="budget-card">
    <!-- Header: tag name + status badge -->
    <div class="flex items-start justify-between gap-4">
      <!-- Left: tag colour dot, name, and period -->
      <div class="flex items-center gap-2">
        <!-- Tag colour indicator -->
        <span
          class="h-3 w-3 flex-shrink-0 rounded-full"
          :style="{ backgroundColor: budget.tag_colour }"
        />
        <h3 class="text-lg font-semibold">{{ budget.tag_name }}</h3>
        <!-- Period badge -->
        <span class="rounded bg-border px-1.5 py-0.5 text-xs text-muted">
          {{ getPeriodLabel(budget.period) }}
        </span>
      </div>

      <!-- Right: status badge -->
      <span
        class="flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium"
        :class="[
          getStatusBgColour(budget.status),
          getStatusColour(budget.status),
        ]"
      >
        {{ getStatusLabel(budget.status) }}
      </span>
    </div>

    <!-- Progress bar -->
    <div class="mt-3">
      <BudgetsBudgetProgressBar
        :percentage="Number(budget.percentage_used)"
        :status="budget.status"
        :show-label="true"
      />
    </div>

    <!-- Spending info -->
    <div class="mt-2 flex items-center justify-between text-sm">
      <span class="text-muted">
        {{ formatCurrency(budget.spent_amount, budget.currency) }} spent
      </span>
      <span class="text-muted">
        of {{ formatCurrency(budget.amount, budget.currency) }}
      </span>
    </div>

    <!-- Remaining / over budget -->
    <div class="mt-1 text-right text-sm">
      <template v-if="budget.remaining_amount >= 0">
        <span class="text-emerald-400">
          {{ formatCurrency(budget.remaining_amount, budget.currency) }}
          remaining
        </span>
      </template>
      <template v-else>
        <span class="text-red-400">
          {{
            formatCurrency(Math.abs(budget.remaining_amount), budget.currency)
          }}
          over budget
        </span>
      </template>
    </div>

    <!-- Actions -->
    <div class="mt-4 flex items-center justify-between">
      <!-- View transactions link — filtered to the budget's period -->
      <NuxtLink :to="transactionsUrl" class="action-btn action-btn-ghost">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M6 4.75A.75.75 0 016.75 4h10.5a.75.75 0 010 1.5H6.75A.75.75 0 016 4.75zM6 10a.75.75 0 01.75-.75h10.5a.75.75 0 010 1.5H6.75A.75.75 0 016 10zm0 5.25a.75.75 0 01.75-.75h10.5a.75.75 0 010 1.5H6.75a.75.75 0 01-.75-.75zM1.99 4.75a1 1 0 011-1h.01a1 1 0 010 2h-.01a1 1 0 01-1-1zm1 5.25a1 1 0 100 2h.01a1 1 0 100-2h-.01zm0 5.25a1 1 0 100 2h.01a1 1 0 100-2h-.01z"
            clip-rule="evenodd"
          />
        </svg>
        Transactions
      </NuxtLink>

      <!-- Edit/Delete buttons -->
      <div class="flex items-center gap-2">
        <!-- Edit button -->
        <button
          type="button"
          class="action-btn action-btn-ghost"
          @click="emit('edit')"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path
              d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z"
            />
          </svg>
          Edit
        </button>

        <!-- Delete button -->
        <button
          type="button"
          class="action-btn action-btn-danger"
          @click="emit('delete')"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.budget-card {
  @apply rounded-lg border border-border bg-surface p-4;
}

.action-btn {
  @apply inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium;
  @apply transition-colors;
}

.action-btn-ghost {
  @apply bg-transparent text-muted hover:bg-gray-700/50 hover:text-foreground;
}

.action-btn-danger {
  @apply bg-transparent text-muted hover:bg-negative/20 hover:text-negative;
}
</style>
