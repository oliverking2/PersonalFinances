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

// Check if account needs configuration (category not set)
const needsConfiguration = computed(() => {
  return !props.account.category
})

// Check if this is a credit card
const isCreditCard = computed(() => {
  return props.account.category === 'credit_card'
})

// Check if credit card is missing credit limit
const creditCardMissingLimit = computed(() => {
  return isCreditCard.value && props.account.credit_limit === null
})

// Balance colour based on account type
// API returns credit card balances as negative (liabilities)
const balanceColorClass = computed(() => {
  if (!props.account.balance) return ''

  const amount = props.account.balance.amount

  if (isCreditCard.value) {
    // For credit cards: balance is negative (liability)
    // £0 owed = green, any debt (negative) = red
    return amount < 0 ? 'text-negative' : 'text-positive'
  }

  // For regular accounts: positive = good, negative = bad
  return amount >= 0 ? 'text-positive' : 'text-negative'
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
      <!-- Warning icon if configuration needed -->
      <div
        v-if="needsConfiguration || creditCardMissingLimit"
        class="flex h-8 w-8 items-center justify-center rounded-full bg-amber-500/20"
        :title="
          needsConfiguration
            ? 'Set account category'
            : 'Set credit limit for accurate balance display'
        "
      >
        <!-- Exclamation icon -->
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          class="h-5 w-5 text-amber-500"
        >
          <path
            fill-rule="evenodd"
            d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
            clip-rule="evenodd"
          />
        </svg>
      </div>

      <!-- Account name and IBAN -->
      <div>
        <p class="font-medium text-foreground">{{ displayName }}</p>
        <p v-if="maskedIban" class="text-sm text-muted">
          IBAN {{ maskedIban }}
        </p>
        <!-- Warning message if needs configuration -->
        <p v-if="needsConfiguration" class="text-xs text-amber-500">
          Set account category
        </p>
        <p v-else-if="creditCardMissingLimit" class="text-xs text-amber-500">
          Set credit limit
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
