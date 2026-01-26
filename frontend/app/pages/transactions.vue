<!-- ==========================================================================
Transactions Page
Main page for viewing and filtering transactions
Displays transactions grouped by day with infinite scroll
Uses client-side filtering for instant response (no API round-trips)
============================================================================ -->

<script setup lang="ts">
import type { Account, Connection } from '~/types/accounts'
import type { Tag } from '~/types/tags'
import type {
  Transaction,
  TransactionDayGroup,
  TransactionQueryParams,
  SplitRequest,
} from '~/types/transactions'
import { useToastStore } from '~/stores/toast'

useHead({ title: 'Transactions | Finances' })

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const route = useRoute()
const router = useRouter()
const { fetchTransactions, setSplits, clearSplits, updateNote } =
  useTransactionsApi()
const { fetchAccounts, fetchConnections } = useAccountsApi()
const { fetchTags, createTag } = useTagsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// All loaded transactions (accumulated via infinite scroll)
const allTransactions = ref<Transaction[]>([])
const accounts = ref<Account[]>([])
const connections = ref<Connection[]>([])
const tags = ref<Tag[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 50

// Client-side filters (applied locally, no API calls)
const filters = ref<TransactionQueryParams>({
  page: 1,
  page_size: pageSize,
})

// Loading states
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')

// Infinite scroll sentinel element ref
const sentinelRef = ref<HTMLDivElement | null>(null)

// Selection state for bulk operations
const selectedTransactionIds = ref<Set<string>>(new Set())
const showBulkTagSelector = ref(false)

// Detail modal state
const showDetailModal = ref(false)
const selectedDetailTransaction = ref<Transaction | null>(null)

// ---------------------------------------------------------------------------
// Computed - Client-side filtering
// ---------------------------------------------------------------------------

// Apply filters to loaded transactions (instant, no API call)
const filteredTransactions = computed((): Transaction[] => {
  let result = allTransactions.value

  // Filter by accounts
  if (filters.value.account_ids && filters.value.account_ids.length > 0) {
    const accountIdSet = new Set(filters.value.account_ids)
    result = result.filter((t) => accountIdSet.has(t.account_id))
  }

  // Filter by tags (OR logic - transaction has ANY of the selected tags)
  // Special handling for "__untagged__" to filter for transactions without tags
  if (filters.value.tag_ids && filters.value.tag_ids.length > 0) {
    const tagIdSet = new Set(filters.value.tag_ids)
    const includeUntagged = tagIdSet.has('__untagged__')

    result = result.filter((t) => {
      // Check if transaction has no tags and we want untagged
      if (includeUntagged && (!t.tags || t.tags.length === 0)) {
        return true
      }
      // Check if transaction has any of the selected tags
      return t.tags.some((tag) => tagIdSet.has(tag.id))
    })
  }

  // Filter by date range
  if (filters.value.start_date) {
    result = result.filter(
      (t) => t.booking_date && t.booking_date >= filters.value.start_date!,
    )
  }
  if (filters.value.end_date) {
    result = result.filter(
      (t) => t.booking_date && t.booking_date <= filters.value.end_date!,
    )
  }

  // Filter by amount range
  if (filters.value.min_amount !== undefined) {
    result = result.filter((t) => t.amount >= filters.value.min_amount!)
  }
  if (filters.value.max_amount !== undefined) {
    result = result.filter((t) => t.amount <= filters.value.max_amount!)
  }

  // Filter by search (case-insensitive, searches description and merchant)
  if (filters.value.search) {
    const searchLower = filters.value.search.toLowerCase()
    result = result.filter(
      (t) =>
        t.description?.toLowerCase().includes(searchLower) ||
        t.merchant_name?.toLowerCase().includes(searchLower),
    )
  }

  return result
})

// Check if there are more transactions to load from server
const hasMore = computed(() => allTransactions.value.length < total.value)

// Map of connection_id to friendly_name for building account display strings
const connectionNames = computed((): Record<string, string> => {
  const names: Record<string, string> = {}
  for (const connection of connections.value) {
    names[connection.id] = connection.friendly_name
  }
  return names
})

// Map of account_id to display name for showing in transaction rows
const accountNames = computed((): Record<string, string> => {
  const names: Record<string, string> = {}
  for (const account of accounts.value) {
    names[account.id] =
      account.display_name || account.name || 'Unknown Account'
  }
  return names
})

// Group filtered transactions by booking_date for display
const dayGroups = computed((): TransactionDayGroup[] => {
  const groups: Record<string, Transaction[]> = {}

  for (const txn of filteredTransactions.value) {
    const date = txn.booking_date || 'unknown'
    const existing = groups[date]
    if (existing) {
      existing.push(txn)
    } else {
      groups[date] = [txn]
    }
  }

  // Convert to array and sort by date descending
  const sortedDates = Object.keys(groups).sort((a, b) => b.localeCompare(a))

  return sortedDates.map((date) => {
    const dayTransactions = groups[date]!
    const dayTotal = dayTransactions.reduce((sum, t) => sum + t.amount, 0)

    return {
      date,
      dateDisplay: formatDateDisplay(date),
      transactions: dayTransactions,
      dayTotal,
    }
  })
})

// Check if there are no filtered transactions (after loading)
const isEmpty = computed(
  () =>
    !loading.value && !error.value && filteredTransactions.value.length === 0,
)

// Check if filters are active (for empty state messaging)
const hasActiveFilters = computed(() => {
  const f = filters.value
  return (
    (f.account_ids && f.account_ids.length > 0) ||
    (f.tag_ids && f.tag_ids.length > 0) ||
    f.start_date ||
    f.end_date ||
    f.min_amount !== undefined ||
    f.max_amount !== undefined ||
    f.search
  )
})

// Number of selected transactions
const selectedCount = computed(() => selectedTransactionIds.value.size)

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

// Format date for display: "Today", "Yesterday", or "Mon 20 Jan"
function formatDateDisplay(dateStr: string): string {
  if (dateStr === 'unknown') return 'Unknown Date'

  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  // Reset times for comparison
  const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const todayOnly = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  )
  const yesterdayOnly = new Date(
    yesterday.getFullYear(),
    yesterday.getMonth(),
    yesterday.getDate(),
  )

  if (dateOnly.getTime() === todayOnly.getTime()) {
    return 'Today'
  }
  if (dateOnly.getTime() === yesterdayOnly.getTime()) {
    return 'Yesterday'
  }

  // Format as "Mon 20 Jan"
  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

// Find transaction by ID in our local state
function findTransaction(transactionId: string): Transaction | undefined {
  return allTransactions.value.find((t) => t.id === transactionId)
}

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

// Load initial data (transactions, accounts, connections, tags)
async function loadData() {
  loading.value = true
  error.value = ''

  try {
    // Fetch all data in parallel (no filters on initial load - get everything)
    const [txnResponse, accountsResponse, connectionsResponse, tagsResponse] =
      await Promise.all([
        fetchTransactions({ page: 1, page_size: pageSize }),
        fetchAccounts(),
        fetchConnections(),
        fetchTags(),
      ])

    allTransactions.value = txnResponse.transactions
    total.value = txnResponse.total
    currentPage.value = 1
    accounts.value = accountsResponse.accounts
    connections.value = connectionsResponse.connections
    tags.value = tagsResponse.tags
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load transactions'
  } finally {
    loading.value = false
  }
}

// Load more transactions (infinite scroll - no filters, just pagination)
async function loadMore() {
  if (loadingMore.value || !hasMore.value) return

  loadingMore.value = true

  try {
    const nextPage = currentPage.value + 1
    const response = await fetchTransactions({
      page: nextPage,
      page_size: pageSize,
    })

    // Append new transactions
    allTransactions.value = [...allTransactions.value, ...response.transactions]
    currentPage.value = nextPage
    total.value = response.total
  } catch (e) {
    console.error('Failed to load more transactions:', e)
  } finally {
    loadingMore.value = false
  }
}

// Flag to prevent infinite loops when syncing URL ↔ filters
const isUpdatingFromUrl = ref(false)

// Handle filter changes - update local state and sync to URL
function handleFiltersChange(newFilters: TransactionQueryParams) {
  filters.value = { ...newFilters }
  // Clear selection when filters change
  selectedTransactionIds.value.clear()
  selectedTransactionIds.value = new Set(selectedTransactionIds.value)

  // Sync filters to URL (unless we're updating from URL change)
  if (!isUpdatingFromUrl.value) {
    syncFiltersToUrl()
  }
}

// Build URL query params from current filters
function syncFiltersToUrl() {
  const query: Record<string, string | string[]> = {}

  // Date range
  if (filters.value.start_date) {
    query.start_date = filters.value.start_date
  }
  if (filters.value.end_date) {
    query.end_date = filters.value.end_date
  }

  // Tags - convert IDs back to names for readable URLs
  if (filters.value.tag_ids && filters.value.tag_ids.length > 0) {
    const tagNames: string[] = []
    for (const tagId of filters.value.tag_ids) {
      if (tagId === '__untagged__') {
        query.untagged = 'true'
      } else {
        const tag = tags.value.find((t) => t.id === tagId)
        if (tag) {
          tagNames.push(tag.name)
        }
      }
    }
    if (tagNames.length > 0) {
      query.tags = tagNames
    }
  }

  // Accounts
  if (filters.value.account_ids && filters.value.account_ids.length > 0) {
    query.accounts = filters.value.account_ids
  }

  // Value range
  if (filters.value.min_amount !== undefined) {
    query.min = String(filters.value.min_amount)
  }
  if (filters.value.max_amount !== undefined) {
    query.max = String(filters.value.max_amount)
  }

  // Search
  if (filters.value.search) {
    query.search = filters.value.search
  }

  // Replace URL without adding to history for minor filter tweaks
  router.replace({ query })
}

// ---------------------------------------------------------------------------
// Tag Operations (single tag per transaction, via splits)
// ---------------------------------------------------------------------------

// Set a single tag on a transaction (creates 100% split)
async function handleAddTag(transactionId: string, tagId: string) {
  try {
    const txn = findTransaction(transactionId)
    if (!txn) return

    // Create a 100% split for this tag
    const response = await setSplits(transactionId, {
      splits: [{ tag_id: tagId, amount: Math.abs(txn.amount) }],
    })

    // Update local state (unified model: tags derived from splits)
    txn.splits = response.splits
    txn.tags = response.splits.map((s) => ({
      id: s.tag_id,
      name: s.tag_name,
      colour: s.tag_colour,
      is_auto: s.is_auto,
      rule_id: s.rule_id,
      rule_name: s.rule_name,
    }))
  } catch {
    toast.error('Failed to set tag')
  }
}

async function handleRemoveTag(transactionId: string, _tagId: string) {
  try {
    // In unified model, removing tag clears all splits
    await clearSplits(transactionId)

    const txn = findTransaction(transactionId)
    if (txn) {
      txn.splits = []
      txn.tags = []
    }
  } catch {
    toast.error('Failed to remove tag')
  }
}

// Create a new tag and set it on the transaction (creates 100% split)
async function handleCreateTag(transactionId: string, name: string) {
  try {
    // Create the tag
    const newTag = await createTag({ name })
    tags.value.push(newTag)
    tags.value.sort((a, b) => a.name.localeCompare(b.name))

    const txn = findTransaction(transactionId)
    if (!txn) return

    // Create a 100% split for this tag
    const response = await setSplits(transactionId, {
      splits: [{ tag_id: newTag.id, amount: Math.abs(txn.amount) }],
    })

    // Update local state
    txn.splits = response.splits
    // Also update tags (derived from splits in unified model)
    txn.tags = response.splits.map((s) => ({
      id: s.tag_id,
      name: s.tag_name,
      colour: s.tag_colour,
      is_auto: s.is_auto,
      rule_id: s.rule_id,
      rule_name: s.rule_name,
    }))

    toast.success(`Tag "${name}" created`)
  } catch {
    toast.error('Failed to create tag')
  }
}

// ---------------------------------------------------------------------------
// Selection Operations
// ---------------------------------------------------------------------------

function toggleSelection(transactionId: string) {
  if (selectedTransactionIds.value.has(transactionId)) {
    selectedTransactionIds.value.delete(transactionId)
  } else {
    selectedTransactionIds.value.add(transactionId)
  }
  // Force reactivity
  selectedTransactionIds.value = new Set(selectedTransactionIds.value)
}

function clearSelection() {
  selectedTransactionIds.value.clear()
  selectedTransactionIds.value = new Set(selectedTransactionIds.value)
  showBulkTagSelector.value = false
}

function selectAll() {
  // Select all currently filtered transactions
  const allIds = filteredTransactions.value.map((t) => t.id)
  selectedTransactionIds.value = new Set(allIds)
}

function toggleBulkTagSelector() {
  showBulkTagSelector.value = !showBulkTagSelector.value
}

// Apply a tag to all selected transactions (creates 100% split)
async function handleBulkAddTag(tagId: string) {
  const selectedIds = Array.from(selectedTransactionIds.value)
  if (selectedIds.length === 0) return

  showBulkTagSelector.value = false

  // Tag each selected transaction via splits
  const results = await Promise.allSettled(
    selectedIds.map(async (transactionId) => {
      const txn = findTransaction(transactionId)
      if (!txn) return

      // Create a 100% split for this tag
      const response = await setSplits(transactionId, {
        splits: [{ tag_id: tagId, amount: Math.abs(txn.amount) }],
      })

      // Update local state
      txn.splits = response.splits
      txn.tags = response.splits.map((s) => ({
        id: s.tag_id,
        name: s.tag_name,
        colour: s.tag_colour,
        is_auto: s.is_auto,
        rule_id: s.rule_id,
        rule_name: s.rule_name,
      }))
    }),
  )

  // Count successes and failures
  const successes = results.filter((r) => r.status === 'fulfilled').length
  const failures = results.filter((r) => r.status === 'rejected').length

  if (failures === 0) {
    toast.success(
      `Tagged ${successes} transaction${successes !== 1 ? 's' : ''}`,
    )
  } else {
    toast.error(`Tagged ${successes}, failed ${failures}`)
  }

  clearSelection()
}

// Create a new tag and apply it to all selected transactions (creates 100% split)
async function handleBulkCreateTag(name: string) {
  const selectedIds = Array.from(selectedTransactionIds.value)
  if (selectedIds.length === 0) return

  showBulkTagSelector.value = false

  try {
    // Create the tag first
    const newTag = await createTag({ name })
    tags.value.push(newTag)
    tags.value.sort((a, b) => a.name.localeCompare(b.name))

    // Apply to all selected transactions via splits
    const results = await Promise.allSettled(
      selectedIds.map(async (transactionId) => {
        const txn = findTransaction(transactionId)
        if (!txn) return

        // Create a 100% split for this tag
        const response = await setSplits(transactionId, {
          splits: [{ tag_id: newTag.id, amount: Math.abs(txn.amount) }],
        })

        // Update local state
        txn.splits = response.splits
        txn.tags = response.splits.map((s) => ({
          id: s.tag_id,
          name: s.tag_name,
          colour: s.tag_colour,
          is_auto: s.is_auto,
          rule_id: s.rule_id,
          rule_name: s.rule_name,
        }))
      }),
    )

    const successes = results.filter((r) => r.status === 'fulfilled').length
    toast.success(
      `Created "${name}" and tagged ${successes} transaction${successes !== 1 ? 's' : ''}`,
    )
  } catch {
    toast.error('Failed to create tag')
  }

  clearSelection()
}

// Remove tags from all selected transactions (clears splits)
async function handleBulkUntag() {
  const selectedIds = Array.from(selectedTransactionIds.value)
  if (selectedIds.length === 0) return

  showBulkTagSelector.value = false

  // Clear splits from each selected transaction
  const results = await Promise.allSettled(
    selectedIds.map(async (transactionId) => {
      await clearSplits(transactionId)

      const txn = findTransaction(transactionId)
      if (txn) {
        txn.splits = []
        txn.tags = []
      }
    }),
  )

  const successes = results.filter((r) => r.status === 'fulfilled').length
  toast.success(
    `Untagged ${successes} transaction${successes !== 1 ? 's' : ''}`,
  )

  clearSelection()
}

// Close bulk tag selector when clicking outside
function handleBulkTagClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.bulk-tag-container')) {
    showBulkTagSelector.value = false
  }
}

// ---------------------------------------------------------------------------
// Detail Modal Operations
// ---------------------------------------------------------------------------

function handleOpenDetail(transactionId: string) {
  const txn = findTransaction(transactionId)
  if (txn) {
    selectedDetailTransaction.value = txn
    showDetailModal.value = true
  }
}

function handleCloseDetail() {
  showDetailModal.value = false
  selectedDetailTransaction.value = null
}

// Tag operations from within the detail modal
async function handleDetailCreateTag(transactionId: string, name: string) {
  await handleCreateTag(transactionId, name)
  // Update the selected transaction ref to reflect the change
  selectedDetailTransaction.value = findTransaction(transactionId) || null
}

// Note operations from detail modal
async function handleDetailUpdateNote(
  transactionId: string,
  note: string | null,
) {
  try {
    const updatedTxn = await updateNote(transactionId, { user_note: note })
    // Update local state
    const txn = findTransaction(transactionId)
    if (txn) {
      txn.user_note = updatedTxn.user_note
    }
    selectedDetailTransaction.value = findTransaction(transactionId) || null
    toast.success(note ? 'Note saved' : 'Note removed')
  } catch {
    toast.error('Failed to update note')
  }
}

// Split operations from detail modal
async function handleDetailUpdateSplits(
  transactionId: string,
  splits: SplitRequest[],
) {
  try {
    const response = await setSplits(transactionId, { splits })
    // Update local state (unified model: tags are derived from splits)
    const txn = findTransaction(transactionId)
    if (txn) {
      txn.splits = response.splits
      txn.tags = response.splits.map((s) => ({
        id: s.tag_id,
        name: s.tag_name,
        colour: s.tag_colour,
        is_auto: s.is_auto,
        rule_id: s.rule_id,
        rule_name: s.rule_name,
      }))
    }
    selectedDetailTransaction.value = findTransaction(transactionId) || null
    toast.success('Tag saved')
  } catch {
    toast.error('Failed to save tag')
  }
}

async function handleDetailClearSplits(transactionId: string) {
  try {
    await clearSplits(transactionId)
    // Update local state (unified model: tags are derived from splits)
    const txn = findTransaction(transactionId)
    if (txn) {
      txn.splits = []
      txn.tags = []
    }
    selectedDetailTransaction.value = findTransaction(transactionId) || null
    toast.success('Tag removed')
  } catch {
    toast.error('Failed to remove tag')
  }
}

// ---------------------------------------------------------------------------
// Infinite Scroll (IntersectionObserver)
// ---------------------------------------------------------------------------

let observer: IntersectionObserver | null = null

function setupIntersectionObserver() {
  if (!sentinelRef.value) return

  // Disconnect existing observer
  if (observer) {
    observer.disconnect()
  }

  // Create new observer
  // rootMargin: load early when sentinel is 100px from viewport
  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      if (entry?.isIntersecting && hasMore.value && !loadingMore.value) {
        loadMore()
      }
    },
    {
      rootMargin: '100px',
    },
  )

  observer.observe(sentinelRef.value)
}

// Watch for sentinel ref changes
watch(sentinelRef, () => {
  setupIntersectionObserver()
})

// Cleanup on unmount
onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
  document.removeEventListener('click', handleBulkTagClickOutside)
})

// Apply filters from URL query parameters
function applyQueryParams() {
  isUpdatingFromUrl.value = true

  const query = route.query

  // Reset filters to defaults first
  const newFilters: TransactionQueryParams = {
    page: 1,
    page_size: pageSize,
  }

  // Date range filters
  if (query.start_date && typeof query.start_date === 'string') {
    newFilters.start_date = query.start_date
  }
  if (query.end_date && typeof query.end_date === 'string') {
    newFilters.end_date = query.end_date
  }

  // Tag filters - support both single 'tag' param and multiple 'tags' param
  const tagIds: string[] = []

  // Single tag param (legacy/simple)
  if (query.tag && typeof query.tag === 'string') {
    const tagName = query.tag
    const matchingTag = tags.value.find(
      (t) => t.name.toLowerCase() === tagName.toLowerCase(),
    )
    if (matchingTag) {
      tagIds.push(matchingTag.id)
    }
  }

  // Multiple tags param
  if (query.tags) {
    const tagNames = Array.isArray(query.tags) ? query.tags : [query.tags]
    for (const tagName of tagNames) {
      if (typeof tagName === 'string') {
        const matchingTag = tags.value.find(
          (t) => t.name.toLowerCase() === tagName.toLowerCase(),
        )
        if (matchingTag) {
          tagIds.push(matchingTag.id)
        }
      }
    }
  }

  // Untagged filter
  if (query.untagged === 'true') {
    tagIds.push('__untagged__')
  }

  if (tagIds.length > 0) {
    newFilters.tag_ids = tagIds
  }

  // Account filters
  if (query.accounts) {
    const accountIds = Array.isArray(query.accounts)
      ? query.accounts
      : [query.accounts]
    newFilters.account_ids = accountIds.filter(
      (id): id is string => typeof id === 'string',
    )
  }

  // Value range
  if (query.min && typeof query.min === 'string') {
    const minVal = parseFloat(query.min)
    if (!isNaN(minVal)) {
      newFilters.min_amount = minVal
    }
  }
  if (query.max && typeof query.max === 'string') {
    const maxVal = parseFloat(query.max)
    if (!isNaN(maxVal)) {
      newFilters.max_amount = maxVal
    }
  }

  // Search
  if (query.search && typeof query.search === 'string') {
    newFilters.search = query.search
  }

  filters.value = newFilters

  // Clear selection when filters change from URL
  selectedTransactionIds.value.clear()
  selectedTransactionIds.value = new Set(selectedTransactionIds.value)

  isUpdatingFromUrl.value = false
}

// Watch for route query changes (back/forward navigation)
watch(
  () => route.query,
  () => {
    // Only apply if we have tags loaded (to match tag names to IDs)
    if (tags.value.length > 0) {
      applyQueryParams()
    }
  },
)

// Load data and set up listeners on mount
onMounted(async () => {
  await loadData()
  // Apply query params after data is loaded (so we have tags to match against)
  applyQueryParams()
  document.addEventListener('click', handleBulkTagClickOutside)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold sm:text-3xl">Transactions</h1>
      <p class="mt-1 text-muted">View and search your transaction history</p>
    </div>

    <!-- Filters (client-side, no API calls) -->
    <TransactionsTransactionFilters
      :accounts="accounts"
      :tags="tags"
      :connection-names="connectionNames"
      :model-value="filters"
      @update:model-value="handleFiltersChange"
    />

    <!-- Loading state (initial load) -->
    <div v-if="loading" class="py-12 text-center text-muted">
      Loading transactions...
    </div>

    <!-- Error state -->
    <div
      v-else-if="error"
      class="rounded-lg border border-negative/50 bg-negative/10 px-6 py-4 text-negative"
    >
      {{ error }}
      <button
        type="button"
        class="ml-2 underline hover:no-underline"
        @click="loadData"
      >
        Retry
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="isEmpty"
      class="rounded-lg border border-border bg-surface px-6 py-12 text-center"
    >
      <!-- Receipt icon -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="1.5"
        stroke="currentColor"
        class="mx-auto h-12 w-12 text-muted"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M9 14.25l6-6m4.5-3.493V21.75l-3.75-1.5-3.75 1.5-3.75-1.5-3.75 1.5V4.757c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0c1.1.128 1.907 1.077 1.907 2.185ZM9.75 9h.008v.008H9.75V9Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm4.125 4.5h.008v.008h-.008V13.5Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
        />
      </svg>
      <h3 class="mt-4 font-semibold text-foreground">
        {{
          hasActiveFilters ? 'No matching transactions' : 'No transactions yet'
        }}
      </h3>
      <p class="mt-1 text-sm text-muted">
        {{
          hasActiveFilters
            ? "Try adjusting your filters to find what you're looking for."
            : 'Transactions will appear here once your accounts start syncing.'
        }}
      </p>
      <!-- Hint about loading more if filters active but no matches -->
      <p v-if="hasActiveFilters && hasMore" class="mt-2 text-xs text-muted">
        Scroll down to load more transactions from the server.
      </p>
    </div>

    <!-- Transaction list grouped by day -->
    <div v-else>
      <!-- Selection actions bar -->
      <div class="mb-3 flex items-center justify-between">
        <span class="text-sm text-muted">
          {{ filteredTransactions.length }} transactions
        </span>
        <button
          type="button"
          class="text-sm text-primary hover:underline"
          @click="selectAll"
        >
          Select all
        </button>
      </div>

      <TransactionsTransactionDayGroup
        v-for="group in dayGroups"
        :key="group.date"
        :group="group"
        :account-names="accountNames"
        :available-tags="tags"
        :selected-transaction-ids="selectedTransactionIds"
        @toggle-select="toggleSelection"
        @add-tag="handleAddTag"
        @remove-tag="handleRemoveTag"
        @create-tag="handleCreateTag"
        @open-detail="handleOpenDetail"
      />

      <!-- Infinite scroll sentinel -->
      <!-- This invisible element triggers loading more when scrolled into view -->
      <div v-if="hasMore" ref="sentinelRef" class="flex justify-center py-4">
        <span v-if="loadingMore" class="text-muted">Loading more...</span>
      </div>

      <!-- End of list indicator -->
      <div v-else class="py-4 text-center text-sm text-muted">
        Showing {{ filteredTransactions.length }} of
        {{ allTransactions.length }} transactions
      </div>
    </div>

    <!-- Floating selection toolbar (fixed at bottom of screen) -->
    <!-- Transition: slides up when items selected, slides down when cleared -->
    <Transition name="slide-up">
      <div
        v-if="selectedCount > 0"
        class="bulk-tag-container fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-4 rounded-full border border-primary/50 bg-surface px-6 py-3 shadow-lg"
      >
        <span class="text-sm font-medium text-foreground">
          {{ selectedCount }} selected
        </span>

        <!-- Bulk tag button with dropdown -->
        <div class="relative">
          <button
            type="button"
            class="rounded-full bg-primary px-4 py-1.5 text-sm font-medium text-background transition-colors hover:bg-primary/80"
            @click="toggleBulkTagSelector"
          >
            Tag
          </button>

          <!-- Tag selector dropdown (opens upward from floating bar) -->
          <div
            v-if="showBulkTagSelector"
            class="absolute bottom-full left-0 z-50 mb-2"
            @click.stop
          >
            <TagsTagSelector
              :available-tags="tags"
              :selected-tag-ids="[]"
              @select="handleBulkAddTag"
              @create="handleBulkCreateTag"
            />
          </div>
        </div>

        <!-- Untag button -->
        <button
          type="button"
          class="rounded-full border border-gray-600 px-4 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-gray-700"
          @click="handleBulkUntag"
        >
          Untag
        </button>

        <button
          type="button"
          class="text-sm text-muted hover:text-foreground"
          @click="clearSelection"
        >
          Clear
        </button>
      </div>
    </Transition>

    <!-- Transaction detail modal -->
    <TransactionsTransactionDetailModal
      :show="showDetailModal"
      :transaction="selectedDetailTransaction"
      :account-name="
        selectedDetailTransaction
          ? accountNames[selectedDetailTransaction.account_id] || 'Unknown'
          : ''
      "
      :available-tags="tags"
      @close="handleCloseDetail"
      @create-tag="handleDetailCreateTag"
      @update-note="handleDetailUpdateNote"
      @update-splits="handleDetailUpdateSplits"
      @clear-splits="handleDetailClearSplits"
    />
  </div>
</template>

<style scoped>
/* Slide up animation for floating toolbar */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.2s ease-out;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translate(-50%, 100%);
}
</style>
