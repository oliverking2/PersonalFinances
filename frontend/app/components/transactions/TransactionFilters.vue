<!-- ==========================================================================
TransactionFilters
Filter controls for searching and filtering transactions
============================================================================ -->

<script setup lang="ts">
import type { Account } from '~/types/accounts'
import type { Tag } from '~/types/tags'
import type { TransactionQueryParams } from '~/types/transactions'
import type { FilterOption } from '~/components/FilterDropdown.vue'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  accounts: Account[]
  tags: Tag[]
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
    (f.account_ids && f.account_ids.length > 0) ||
    (f.tag_ids && f.tag_ids.length > 0) ||
    f.start_date ||
    f.end_date ||
    f.min_amount !== undefined ||
    f.max_amount !== undefined ||
    f.search
  )
})

// Convert accounts to FilterOption format for the dropdown
const accountOptions = computed((): FilterOption[] => {
  return props.accounts.map((account) => ({
    id: account.id,
    label: getAccountDisplayName(account),
  }))
})

// Currently selected account IDs (defaulting to empty array)
const selectedAccountIds = computed(() => props.modelValue.account_ids || [])

// Special ID for "Untagged" filter option
const UNTAGGED_FILTER_ID = '__untagged__'

// Convert tags to FilterOption format for the dropdown
// Adds "Untagged" option at the top to filter for transactions without tags
const tagOptions = computed((): FilterOption[] => {
  const untaggedOption: FilterOption = {
    id: UNTAGGED_FILTER_ID,
    label: 'Untagged',
  }
  const tagsList = props.tags.map((tag) => ({
    id: tag.id,
    label: tag.name,
    colour: tag.colour,
  }))
  return [untaggedOption, ...tagsList]
})

// Currently selected tag IDs (defaulting to empty array)
const selectedTagIds = computed(() => props.modelValue.tag_ids || [])

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

// Handle account selection change (multi-select)
function handleAccountsChange(ids: string[]) {
  updateFilters({ account_ids: ids.length > 0 ? ids : undefined })
}

// Handle tag selection change (multi-select)
function handleTagsChange(ids: string[]) {
  updateFilters({ tag_ids: ids.length > 0 ? ids : undefined })
}

// Handle date range changes (from DateFilterDropdown)
function handleDateRangeChange(
  startDate: string | undefined,
  endDate: string | undefined,
) {
  updateFilters({ start_date: startDate, end_date: endDate })
}

// Individual date changes (for custom mode inputs)
function handleStartDateChange(date: string | undefined) {
  updateFilters({ start_date: date })
}

function handleEndDateChange(date: string | undefined) {
  updateFilters({ end_date: date })
}

// Handle amount range changes (from ValueFilterDropdown)
function handleMinAmountChange(amount: number | undefined) {
  updateFilters({ min_amount: amount })
}

function handleMaxAmountChange(amount: number | undefined) {
  updateFilters({ max_amount: amount })
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
    <div class="flex flex-wrap items-end gap-2 sm:gap-3">
      <!-- Account filter (multi-select dropdown) -->
      <div class="min-w-[140px] flex-1 sm:min-w-[180px]">
        <FilterDropdown
          label="Accounts"
          placeholder="All accounts"
          :options="accountOptions"
          :selected-ids="selectedAccountIds"
          :multi-select="true"
          :searchable="true"
          @update:selected-ids="handleAccountsChange"
        />
      </div>

      <!-- Tag filter (multi-select dropdown) -->
      <div class="min-w-[100px] sm:min-w-[140px]">
        <FilterDropdown
          label="Tags"
          placeholder="All tags"
          :options="tagOptions"
          :selected-ids="selectedTagIds"
          :multi-select="true"
          :searchable="true"
          manage-link="/settings/tags"
          manage-link-text="Manage"
          @update:selected-ids="handleTagsChange"
        />
      </div>

      <!-- Date filter dropdown (presets + custom) -->
      <div class="min-w-[120px] sm:min-w-[160px]">
        <TransactionsDateFilterDropdown
          :start-date="modelValue.start_date"
          :end-date="modelValue.end_date"
          @update:date-range="handleDateRangeChange"
          @update:start-date="handleStartDateChange"
          @update:end-date="handleEndDateChange"
        />
      </div>

      <!-- Value filter dropdown (min/max amount) -->
      <div class="min-w-[100px] sm:min-w-[140px]">
        <TransactionsValueFilterDropdown
          :min-amount="modelValue.min_amount"
          :max-amount="modelValue.max_amount"
          @update:min-amount="handleMinAmountChange"
          @update:max-amount="handleMaxAmountChange"
        />
      </div>

      <!-- Clear button - always visible, disabled when no filters active -->
      <button
        type="button"
        class="mb-px self-end rounded-lg border border-border px-3 py-2 text-sm transition-colors"
        :class="
          hasActiveFilters
            ? 'text-muted hover:bg-border hover:text-foreground'
            : 'cursor-not-allowed text-muted/40'
        "
        :disabled="!hasActiveFilters"
        @click="clearFilters"
      >
        Clear
      </button>
    </div>
  </div>
</template>
