<!-- ==========================================================================
TransactionFilters
Filter controls for searching and filtering transactions
============================================================================ -->

<script setup lang="ts">
import type { Account } from '~/types/accounts'
import type { TransactionQueryParams } from '~/types/transactions'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  accounts: Account[]
  connectionNames: Record<string, string>
  modelValue: TransactionQueryParams
}>()

const emit = defineEmits<{
  'update:modelValue': [value: TransactionQueryParams]
}>()

// ---------------------------------------------------------------------------
// Local State
// Debounced search to avoid excessive API calls while typing
// ---------------------------------------------------------------------------

const localSearch = ref(props.modelValue.search || '')
let searchTimeout: ReturnType<typeof setTimeout> | null = null

// Watch for external changes to search
watch(
  () => props.modelValue.search,
  (newValue) => {
    if (newValue !== localSearch.value) {
      localSearch.value = newValue || ''
    }
  },
)

// Debounce search input (300ms delay)
function handleSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    updateFilters({ search: localSearch.value || undefined })
  }, 300)
}

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Check if any filters are active (for showing clear button)
const hasActiveFilters = computed(() => {
  const f = props.modelValue
  return !!(
    f.account_id ||
    f.start_date ||
    f.end_date ||
    f.min_amount !== undefined ||
    f.max_amount !== undefined ||
    f.search
  )
})

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

// Update filters and emit new value
function updateFilters(updates: Partial<TransactionQueryParams>) {
  emit('update:modelValue', {
    ...props.modelValue,
    ...updates,
    page: 1, // Reset to first page when filters change
  })
}

// Handle account dropdown change
function handleAccountChange(event: Event) {
  const select = event.target as HTMLSelectElement
  updateFilters({ account_id: select.value || undefined })
}

// Handle date range changes
function handleStartDateChange(event: Event) {
  const input = event.target as HTMLInputElement
  updateFilters({ start_date: input.value || undefined })
}

function handleEndDateChange(event: Event) {
  const input = event.target as HTMLInputElement
  updateFilters({ end_date: input.value || undefined })
}

// Handle amount range changes
function handleMinAmountChange(event: Event) {
  const input = event.target as HTMLInputElement
  const value = input.value ? parseFloat(input.value) : undefined
  updateFilters({ min_amount: value })
}

function handleMaxAmountChange(event: Event) {
  const input = event.target as HTMLInputElement
  const value = input.value ? parseFloat(input.value) : undefined
  updateFilters({ max_amount: value })
}

// Clear all filters
function clearFilters() {
  localSearch.value = ''
  emit('update:modelValue', { page: 1, page_size: props.modelValue.page_size })
}

// Get display name for an account: "Connection Name - Account Name"
function getAccountDisplayName(account: Account): string {
  const connectionName = props.connectionNames[account.connection_id]
  const accountName = account.display_name || account.name || 'Unnamed Account'

  // If we have a connection name, show "Connection - Account"
  if (connectionName) {
    return `${connectionName} - ${accountName}`
  }
  return accountName
}
</script>

<template>
  <div class="space-y-4">
    <!-- Search input - full width on top -->
    <div class="relative">
      <!-- Search icon -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        class="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted"
      >
        <path
          fill-rule="evenodd"
          d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z"
          clip-rule="evenodd"
        />
      </svg>
      <input
        v-model="localSearch"
        type="text"
        placeholder="Search transactions..."
        class="w-full rounded-lg border border-border bg-surface py-2 pl-10 pr-4 text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        @input="handleSearchInput"
      />
    </div>

    <!-- Filter row - wraps on smaller screens -->
    <div class="flex flex-wrap items-end gap-3">
      <!-- Account filter -->
      <div class="min-w-[150px] flex-1">
        <label class="mb-1 block text-sm text-muted">Account</label>
        <select
          :value="modelValue.account_id || ''"
          class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          @change="handleAccountChange"
        >
          <option value="">All accounts</option>
          <option
            v-for="account in accounts"
            :key="account.id"
            :value="account.id"
          >
            {{ getAccountDisplayName(account) }}
          </option>
        </select>
      </div>

      <!-- Date range -->
      <div class="min-w-[130px]">
        <label class="mb-1 block text-sm text-muted">From</label>
        <input
          type="date"
          :value="modelValue.start_date || ''"
          class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          @change="handleStartDateChange"
        />
      </div>

      <div class="min-w-[130px]">
        <label class="mb-1 block text-sm text-muted">To</label>
        <input
          type="date"
          :value="modelValue.end_date || ''"
          class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          @change="handleEndDateChange"
        />
      </div>

      <!-- Amount range -->
      <div class="min-w-[100px]">
        <label class="mb-1 block text-sm text-muted">Min amount</label>
        <input
          type="number"
          step="0.01"
          placeholder="0.00"
          :value="modelValue.min_amount ?? ''"
          class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          @change="handleMinAmountChange"
        />
      </div>

      <div class="min-w-[100px]">
        <label class="mb-1 block text-sm text-muted">Max amount</label>
        <input
          type="number"
          step="0.01"
          placeholder="0.00"
          :value="modelValue.max_amount ?? ''"
          class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          @change="handleMaxAmountChange"
        />
      </div>

      <!-- Clear button - only shown when filters are active -->
      <button
        v-if="hasActiveFilters"
        type="button"
        class="rounded-lg border border-border px-3 py-2 text-sm text-muted transition-colors hover:bg-border hover:text-foreground"
        @click="clearFilters"
      >
        Clear
      </button>
    </div>
  </div>
</template>
