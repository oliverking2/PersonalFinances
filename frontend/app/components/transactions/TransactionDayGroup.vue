<!-- ==========================================================================
TransactionDayGroup
Displays a group of transactions for a single day with a sticky header
============================================================================ -->

<script setup lang="ts">
import type { TransactionDayGroup } from '~/types/transactions'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  group: TransactionDayGroup
  accountNames: Record<string, string> // Map of account_id to display name
}>()

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Format day total with currency symbol and +/- prefix
const formattedDayTotal = computed(() => {
  const total = props.group.dayTotal
  // Assume GBP for now - could be derived from transactions
  const formatted = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(Math.abs(total))

  return total >= 0 ? `+${formatted}` : `-${formatted}`
})

// Day total colour: green for net positive, default for net negative
const totalColorClass = computed(() => {
  return props.group.dayTotal >= 0 ? 'text-positive' : 'text-muted'
})
</script>

<template>
  <div class="mb-4">
    <!-- Sticky day header -->
    <!-- sticky: sticks to top when scrolling -->
    <!-- top-0: stick at top of scroll container -->
    <!-- z-10: ensure header stays above transaction rows -->
    <!-- bg-background: solid background to hide content scrolling beneath -->
    <div
      class="sticky top-0 z-10 flex items-center justify-between bg-background px-4 py-2"
    >
      <!-- Date display (Today, Yesterday, or formatted date) -->
      <h3 class="text-sm font-semibold text-foreground">
        {{ group.dateDisplay }}
      </h3>

      <!-- Day total -->
      <span class="text-sm font-medium" :class="totalColorClass">
        {{ formattedDayTotal }}
      </span>
    </div>

    <!-- Transaction list -->
    <div class="rounded-lg border border-border bg-surface">
      <TransactionsTransactionRow
        v-for="transaction in group.transactions"
        :key="transaction.id"
        :transaction="transaction"
        :account-name="accountNames[transaction.account_id]"
      />
    </div>
  </div>
</template>
