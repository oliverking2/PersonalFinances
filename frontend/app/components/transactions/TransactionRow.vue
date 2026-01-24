<!-- ==========================================================================
TransactionRow
Displays a single transaction with merchant/description and amount
============================================================================ -->

<script setup lang="ts">
import type { Transaction } from '~/types/transactions'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  transaction: Transaction
  accountName?: string // Display name of the account this transaction belongs to
}>()

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Display name: prefer merchant_name, fall back to description
const displayName = computed(() => {
  return (
    props.transaction.merchant_name ||
    props.transaction.description ||
    'Unknown Transaction'
  )
})

// Secondary line: show description if merchant is displayed, otherwise category
const secondaryText = computed(() => {
  if (props.transaction.merchant_name && props.transaction.description) {
    return props.transaction.description
  }
  return props.transaction.category || null
})

// Build the metadata line (account name + secondary text)
const metadataText = computed(() => {
  const parts: string[] = []
  if (props.accountName) {
    parts.push(props.accountName)
  }
  if (secondaryText.value) {
    parts.push(secondaryText.value)
  }
  return parts.join(' · ')
})

// Format amount with currency symbol and +/- prefix
const formattedAmount = computed(() => {
  const { amount, currency } = props.transaction
  const formatted = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: currency,
  }).format(Math.abs(amount))

  // Add +/- prefix for clarity
  return amount >= 0 ? `+${formatted}` : `-${formatted}`
})

// Amount colour: green for income (positive), default for expenses (negative)
const amountColorClass = computed(() => {
  return props.transaction.amount >= 0 ? 'text-positive' : 'text-foreground'
})
</script>

<template>
  <!-- Transaction row with subtle hover effect -->
  <div
    class="flex items-center justify-between rounded-lg px-4 py-3 transition-colors hover:bg-onyx/50"
  >
    <!-- Left side: merchant/description -->
    <div class="min-w-0 flex-1">
      <p class="truncate font-medium text-foreground">{{ displayName }}</p>
      <p v-if="metadataText" class="truncate text-sm text-muted">
        {{ metadataText }}
      </p>
    </div>

    <!-- Right side: amount -->
    <div class="ml-4 flex-shrink-0">
      <span class="font-medium" :class="amountColorClass">
        {{ formattedAmount }}
      </span>
    </div>
  </div>
</template>
