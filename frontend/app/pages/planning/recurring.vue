<!-- ==========================================================================
Recurring Patterns Page
Manage recurring expenses (subscriptions, bills) and income (salary, transfers)
============================================================================ -->

<script setup lang="ts">
import type {
  RecurringPattern,
  RecurringPatternCreateRequest,
  RecurringStatus,
  RecurringDirection,
  RecurringFrequency,
  RecurringSummary,
} from '~/types/recurring'
import { getStatusLabel } from '~/types/recurring'

useHead({ title: 'Recurring Patterns | Finances' })

// API
const {
  fetchPatterns,
  fetchSummary,
  acceptPattern,
  deletePattern,
  pausePattern,
  resumePattern,
  updatePattern,
  createPattern,
} = useRecurringApi()

const { fetchTags } = useTagsApi()

const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const patterns = ref<RecurringPattern[]>([])
const summary = ref<RecurringSummary | null>(null)
const loading = ref(true)
const error = ref('')

// Tags for budget linking
const tags = ref<Array<{ id: string; name: string; colour: string }>>([])

// Filters - default tab is now 'pending' to highlight items needing review
const statusFilter = ref<RecurringStatus | 'all'>('all')
const directionFilter = ref<RecurringDirection | 'all'>('all')
const sortBy = ref<'amount' | 'name' | 'next'>('amount')

// Edit modal state
const editModalOpen = ref(false)
const editingPattern = ref<RecurringPattern | null>(null)

// Create modal state
const createModalOpen = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Filter patterns by status and direction
const filteredPatterns = computed(() => {
  let result = [...patterns.value]

  // Direction filter
  if (directionFilter.value !== 'all') {
    result = result.filter((p) => p.direction === directionFilter.value)
  }

  // Status filter
  if (statusFilter.value === 'all') {
    // "All" excludes cancelled patterns
    result = result.filter((p) => p.status !== 'cancelled')
  } else {
    result = result.filter((p) => p.status === statusFilter.value)
  }

  // Sort
  result.sort((a, b) => {
    switch (sortBy.value) {
      case 'amount':
        return Math.abs(b.expected_amount) - Math.abs(a.expected_amount)
      case 'name':
        return a.name.localeCompare(b.name)
      case 'next':
        if (!a.next_expected_date) return 1
        if (!b.next_expected_date) return -1
        return a.next_expected_date.localeCompare(b.next_expected_date)
      default:
        return 0
    }
  })

  return result
})

// Tab counts (respects direction filter)
const tabCounts = computed(() => {
  // First filter by direction if set
  let filtered = patterns.value
  if (directionFilter.value !== 'all') {
    filtered = filtered.filter((p) => p.direction === directionFilter.value)
  }

  return {
    all: filtered.filter((p) => p.status !== 'cancelled').length,
    pending: filtered.filter((p) => p.status === 'pending').length,
    active: filtered.filter((p) => p.status === 'active').length,
    paused: filtered.filter((p) => p.status === 'paused').length,
    cancelled: filtered.filter((p) => p.status === 'cancelled').length,
  }
})

// Direction counts
const directionCounts = computed(() => ({
  all: patterns.value.filter((p) => p.status !== 'cancelled').length,
  expense: patterns.value.filter(
    (p) => p.direction === 'expense' && p.status !== 'cancelled',
  ).length,
  income: patterns.value.filter(
    (p) => p.direction === 'income' && p.status !== 'cancelled',
  ).length,
}))

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [patternsResponse, summaryResponse, tagsResponse] = await Promise.all(
      [fetchPatterns(), fetchSummary(), fetchTags()],
    )
    patterns.value = patternsResponse.patterns
    summary.value = summaryResponse
    // Filter to only visible tags for the selector (exclude hidden, require colour)
    tags.value = tagsResponse.tags
      .filter((t) => !t.is_hidden && t.colour)
      .map((t) => ({ id: t.id, name: t.name, colour: t.colour as string }))
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : 'Failed to load recurring patterns'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

// Accept a pending pattern (detected → active)
async function handleAccept(pattern: RecurringPattern) {
  try {
    const updated = await acceptPattern(pattern.id)
    // Update in list
    const idx = patterns.value.findIndex((p) => p.id === pattern.id)
    if (idx >= 0) patterns.value[idx] = updated
    toast.success(`Accepted: ${pattern.name}`)
    summary.value = await fetchSummary()
  } catch {
    toast.error('Failed to accept pattern')
  }
}

// Dismiss (delete) a pattern - can be re-detected later
async function handleDismiss(pattern: RecurringPattern) {
  try {
    await deletePattern(pattern.id)
    // Remove from list
    patterns.value = patterns.value.filter((p) => p.id !== pattern.id)
    toast.success(`Dismissed: ${pattern.name}`)
    summary.value = await fetchSummary()
  } catch {
    toast.error('Failed to dismiss pattern')
  }
}

// Pause an active pattern
async function handlePause(pattern: RecurringPattern) {
  try {
    const updated = await pausePattern(pattern.id)
    // Update in list
    const idx = patterns.value.findIndex((p) => p.id === pattern.id)
    if (idx >= 0) patterns.value[idx] = updated
    toast.success(`Paused: ${pattern.name}`)
    summary.value = await fetchSummary()
  } catch {
    toast.error('Failed to pause pattern')
  }
}

// Resume a paused pattern
async function handleResume(pattern: RecurringPattern) {
  try {
    const updated = await resumePattern(pattern.id)
    // Update in list
    const idx = patterns.value.findIndex((p) => p.id === pattern.id)
    if (idx >= 0) patterns.value[idx] = updated
    toast.success(`Resumed: ${pattern.name}`)
    summary.value = await fetchSummary()
  } catch {
    toast.error('Failed to resume pattern')
  }
}

function handleEdit(pattern: RecurringPattern) {
  editingPattern.value = pattern
  editModalOpen.value = true
}

interface PatternUpdates {
  name?: string
  notes?: string
  expected_amount?: number
  frequency?: RecurringFrequency
}

async function handleSaveEdit(updates: PatternUpdates) {
  if (!editingPattern.value) return

  try {
    const updated = await updatePattern(editingPattern.value.id, updates)
    // Update in list
    const idx = patterns.value.findIndex(
      (p) => p.id === editingPattern.value?.id,
    )
    if (idx >= 0) patterns.value[idx] = updated
    toast.success('Pattern updated')
    editModalOpen.value = false
    editingPattern.value = null
    summary.value = await fetchSummary()
  } catch {
    toast.error('Failed to update pattern')
  }
}

// Create a new pattern manually
async function handleCreate(request: RecurringPatternCreateRequest) {
  try {
    const created = await createPattern(request)
    // Add to list
    patterns.value.push(created)
    toast.success(`Created: ${created.name}`)
    createModalOpen.value = false
    summary.value = await fetchSummary()
  } catch {
    toast.error('Failed to create pattern')
  }
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
  }).format(Math.abs(amount))
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">Recurring Patterns</h1>
        <p class="mt-1 text-muted">Manage recurring expenses and income</p>
      </div>
      <!-- Create Pattern button -->
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
        @click="createModalOpen = true"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
          />
        </svg>
        Create Pattern
      </button>
    </div>

    <!-- Summary cards -->
    <div
      v-if="summary && !loading"
      class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5"
    >
      <!-- Monthly expenses -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Monthly Expenses</p>
        <p class="mt-1 text-2xl font-bold text-red-400">
          {{ formatCurrency(summary.monthly_expenses || 0) }}
        </p>
        <p class="text-xs text-muted">
          {{ summary.expense_count || 0 }} patterns
        </p>
      </div>

      <!-- Monthly income -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Monthly Income</p>
        <p class="mt-1 text-2xl font-bold text-emerald-400">
          {{ formatCurrency(summary.monthly_income || 0) }}
        </p>
        <p class="text-xs text-muted">
          {{ summary.income_count || 0 }} patterns
        </p>
      </div>

      <!-- Net monthly -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Net Monthly</p>
        <p
          :class="[
            'mt-1 text-2xl font-bold',
            summary.monthly_total >= 0 ? 'text-emerald-400' : 'text-red-400',
          ]"
        >
          {{ summary.monthly_total >= 0 ? '+' : ''
          }}{{ formatCurrency(summary.monthly_total) }}
        </p>
      </div>

      <!-- Active -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Active</p>
        <p class="mt-1 text-2xl font-bold text-primary">
          {{ summary.active_count }}
        </p>
      </div>

      <!-- Pending review -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Pending Review</p>
        <p class="mt-1 text-2xl font-bold text-warning">
          {{ summary.pending_count }}
        </p>
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="rounded-lg border border-negative/50 bg-negative/10 p-4 text-negative"
    >
      {{ error }}
    </div>

    <!-- Filters row -->
    <div class="flex flex-wrap items-center gap-4">
      <!-- Direction tabs (Expenses / Income) -->
      <div class="flex rounded-lg border border-border bg-surface p-1">
        <button
          v-for="dir in ['all', 'expense', 'income'] as const"
          :key="dir"
          type="button"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="[
            directionFilter === dir
              ? dir === 'income'
                ? 'bg-emerald-500/20 text-emerald-400'
                : dir === 'expense'
                  ? 'bg-red-500/20 text-red-400'
                  : 'bg-primary/20 text-primary'
              : 'text-muted hover:text-foreground',
          ]"
          @click="directionFilter = dir"
        >
          {{
            dir === 'all' ? 'All' : dir === 'expense' ? 'Expenses' : 'Income'
          }}
          <span class="ml-1 text-xs opacity-60">
            ({{ directionCounts[dir] }})
          </span>
        </button>
      </div>

      <!-- Status tabs -->
      <div class="flex rounded-lg border border-border bg-surface p-1">
        <button
          v-for="tab in [
            'all',
            'pending',
            'active',
            'paused',
            'cancelled',
          ] as const"
          :key="tab"
          type="button"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="
            statusFilter === tab
              ? 'bg-primary/20 text-primary'
              : 'text-muted hover:text-foreground'
          "
          @click="statusFilter = tab"
        >
          {{ tab === 'all' ? 'All' : getStatusLabel(tab) }}
          <span class="ml-1 text-xs opacity-60"> ({{ tabCounts[tab] }}) </span>
        </button>
      </div>

      <!-- Spacer -->
      <div class="flex-1" />

      <!-- Sort dropdown -->
      <div class="flex items-center gap-2">
        <span class="text-sm text-muted">Sort by:</span>
        <AppSelect
          v-model="sortBy"
          :options="[
            { value: 'amount', label: 'Amount' },
            { value: 'name', label: 'Name' },
            { value: 'next', label: 'Next Due' },
          ]"
          class="w-32"
        />
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="space-y-4">
      <div
        v-for="i in 3"
        :key="i"
        class="rounded-lg border border-border bg-surface p-4"
      >
        <div class="flex items-start justify-between">
          <div class="space-y-2">
            <div class="h-5 w-40 animate-pulse rounded bg-border" />
            <div class="h-4 w-24 animate-pulse rounded bg-border" />
          </div>
          <div class="h-6 w-20 animate-pulse rounded bg-border" />
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="filteredPatterns.length === 0"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p v-if="statusFilter === 'all'" class="text-muted">
        No recurring patterns detected yet. Keep using your accounts and
        patterns will be detected automatically.
      </p>
      <p v-else class="text-muted">
        No {{ getStatusLabel(statusFilter).toLowerCase() }} patterns.
      </p>
    </div>

    <!-- Pattern list -->
    <div v-else class="space-y-4">
      <SubscriptionsRecurringPatternCard
        v-for="pattern in filteredPatterns"
        :key="pattern.id"
        :pattern="pattern"
        @accept="handleAccept(pattern)"
        @dismiss="handleDismiss(pattern)"
        @pause="handlePause(pattern)"
        @resume="handleResume(pattern)"
        @edit="handleEdit(pattern)"
      />
    </div>

    <!-- Edit modal -->
    <SubscriptionsRecurringPatternEditModal
      v-if="editingPattern"
      :pattern="editingPattern"
      :open="editModalOpen"
      :available-tags="tags"
      @close="editModalOpen = false"
      @save="handleSaveEdit"
    />

    <!-- Create modal -->
    <SubscriptionsRecurringPatternCreateModal
      :open="createModalOpen"
      :available-tags="tags"
      @close="createModalOpen = false"
      @create="handleCreate"
    />
  </div>
</template>
