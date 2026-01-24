<!-- ==========================================================================
AccountRow
Displays a single bank account with name, IBAN, currency, and edit action
============================================================================ -->

<script setup lang="ts">
import type { Account } from '~/types/accounts'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  account: Account
}>()

const emit = defineEmits<{
  edit: [account: Account]
}>()

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Display name: prefer user-set display_name, fall back to provider name
const displayName = computed(() => {
  return props.account.display_name || props.account.name || 'Unnamed Account'
})

// Masked IBAN: show only last 4 characters for privacy
// e.g. "GB12NAIA12345678901234" -> "...1234"
const maskedIban = computed(() => {
  if (!props.account.iban) return null
  const last4 = props.account.iban.slice(-4)
  return `...${last4}`
})

// Format balance with currency symbol
const formattedBalance = computed(() => {
  if (!props.account.balance) return null

  const { amount, currency } = props.account.balance
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: currency,
  }).format(amount)
})

// Balance colour: positive for credit, negative for debt
const balanceColorClass = computed(() => {
  if (!props.account.balance) return ''
  return props.account.balance.amount >= 0 ? 'text-positive' : 'text-negative'
})

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function handleEdit() {
  emit('edit', props.account)
}
</script>

<template>
  <!-- Account row with hover effect -->
  <div
    class="flex items-center justify-between rounded-lg px-4 py-3 transition-colors hover:bg-onyx/50"
  >
    <!-- Left side: account info -->
    <div class="flex items-center gap-4">
      <!-- Account name and IBAN -->
      <div>
        <p class="font-medium text-foreground">{{ displayName }}</p>
        <p v-if="maskedIban" class="text-sm text-muted">
          IBAN {{ maskedIban }}
        </p>
      </div>
    </div>

    <!-- Right side: balance, currency badge, and edit button -->
    <div class="flex items-center gap-4">
      <!-- Balance (if available) -->
      <span
        v-if="formattedBalance"
        class="font-medium"
        :class="balanceColorClass"
      >
        {{ formattedBalance }}
      </span>

      <!-- Currency badge -->
      <span
        v-if="account.currency"
        class="rounded bg-border px-2 py-0.5 text-xs font-medium text-muted"
      >
        {{ account.currency }}
      </span>

      <!-- Edit button -->
      <button
        type="button"
        class="rounded p-1.5 text-muted transition-colors hover:bg-border hover:text-foreground"
        title="Edit display name"
        @click="handleEdit"
      >
        <!-- Pencil icon (heroicons/mini) -->
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          class="h-4 w-4"
        >
          <path
            d="m5.433 13.917 1.262-3.155A4 4 0 0 1 7.58 9.42l6.92-6.918a2.121 2.121 0 0 1 3 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 0 1-.65-.65Z"
          />
          <path
            d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0 0 10 3H4.75A2.75 2.75 0 0 0 2 5.75v9.5A2.75 2.75 0 0 0 4.75 18h9.5A2.75 2.75 0 0 0 17 15.25V10a.75.75 0 0 0-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5Z"
          />
        </svg>
      </button>
    </div>
  </div>
</template>
