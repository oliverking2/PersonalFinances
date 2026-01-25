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

      <!-- Settings button -->
      <button
        type="button"
        class="rounded p-1.5 text-muted transition-colors hover:bg-border hover:text-foreground"
        title="Account settings"
        @click="handleEdit"
      >
        <!-- Cog icon (heroicons/mini) -->
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          class="h-4 w-4"
        >
          <path
            fill-rule="evenodd"
            d="M7.84 1.804A1 1 0 0 1 8.82 1h2.36a1 1 0 0 1 .98.804l.331 1.652a6.993 6.993 0 0 1 1.929 1.115l1.598-.54a1 1 0 0 1 1.186.447l1.18 2.044a1 1 0 0 1-.205 1.251l-1.267 1.113a7.047 7.047 0 0 1 0 2.228l1.267 1.113a1 1 0 0 1 .206 1.25l-1.18 2.045a1 1 0 0 1-1.187.447l-1.598-.54a6.993 6.993 0 0 1-1.929 1.115l-.33 1.652a1 1 0 0 1-.98.804H8.82a1 1 0 0 1-.98-.804l-.331-1.652a6.993 6.993 0 0 1-1.929-1.115l-1.598.54a1 1 0 0 1-1.186-.447l-1.18-2.044a1 1 0 0 1 .205-1.251l1.267-1.114a7.05 7.05 0 0 1 0-2.227L1.821 7.773a1 1 0 0 1-.206-1.25l1.18-2.045a1 1 0 0 1 1.187-.447l1.598.54A6.992 6.992 0 0 1 7.51 3.456l.33-1.652ZM10 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
    </div>
  </div>
</template>
