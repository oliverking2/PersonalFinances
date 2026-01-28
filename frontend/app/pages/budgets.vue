<!-- ==========================================================================
Budgets Page
Manage spending budgets by category
============================================================================ -->

<script setup lang="ts">
import type {
  Budget,
  BudgetWithSpending,
  BudgetSummaryResponse,
  BudgetCreateRequest,
  BudgetUpdateRequest,
} from '~/types/budgets'
import { getStatusLabel } from '~/types/budgets'

useHead({ title: 'Budgets | Finances' })

// API
const {
  fetchBudgets,
  fetchBudget,
  fetchBudgetSummary,
  createBudget,
  updateBudget,
  deleteBudget,
} = useBudgetsApi()
const { fetchTags } = useTagsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const budgets = ref<BudgetWithSpending[]>([])
const summary = ref<BudgetSummaryResponse | null>(null)
const availableTags = ref<Array<{ id: string; name: string; colour: string }>>(
  [],
)
const loading = ref(true)
const error = ref('')

// Modal state
const createModalOpen = ref(false)
const editingBudget = ref<Budget | null>(null)

// Filter
const statusFilter = ref<'all' | 'ok' | 'warning' | 'exceeded'>('all')

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Filter budgets by status
const filteredBudgets = computed(() => {
  if (statusFilter.value === 'all') return budgets.value
  return budgets.value.filter((b) => b.status === statusFilter.value)
})

// Tab counts
const tabCounts = computed(() => ({
  all: budgets.value.length,
  ok: budgets.value.filter((b) => b.status === 'ok').length,
  warning: budgets.value.filter((b) => b.status === 'warning').length,
  exceeded: budgets.value.filter((b) => b.status === 'exceeded').length,
}))

// Tags that don't have budgets yet (for creation)
const tagsWithoutBudgets = computed(() => {
  const budgetTagIds = new Set(budgets.value.map((b) => b.tag_id))
  return availableTags.value.filter((t) => !budgetTagIds.has(t.id))
})

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    // Load budgets, summary, and tags in parallel
    const [budgetsResponse, summaryResponse, tagsResponse] = await Promise.all([
      fetchBudgets(),
      fetchBudgetSummary(),
      fetchTags(),
    ])

    // Fetch spending for each budget
    const budgetsWithSpending = await Promise.all(
      budgetsResponse.budgets.map((b) => fetchBudget(b.id)),
    )

    budgets.value = budgetsWithSpending
    summary.value = summaryResponse
    availableTags.value = tagsResponse.tags.map((t) => ({
      id: t.id,
      name: t.name,
      colour: t.colour ?? '#6b7280', // Default grey if no colour
    }))
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load budgets'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function openCreateModal() {
  editingBudget.value = null
  createModalOpen.value = true
}

function handleEdit(budget: BudgetWithSpending) {
  // Convert to Budget (without spending) for the modal
  editingBudget.value = {
    id: budget.id,
    tag_id: budget.tag_id,
    tag_name: budget.tag_name,
    tag_colour: budget.tag_colour,
    amount: budget.amount,
    currency: budget.currency,
    warning_threshold: budget.warning_threshold,
    enabled: budget.enabled,
    created_at: budget.created_at,
    updated_at: budget.updated_at,
  }
  createModalOpen.value = true
}

async function handleCreate(req: BudgetCreateRequest) {
  try {
    const created = await createBudget(req)
    // Fetch with spending
    const withSpending = await fetchBudget(created.id)
    budgets.value.push(withSpending)
    // Update summary
    const newSummary = await fetchBudgetSummary()
    summary.value = newSummary
    toast.success('Budget created')
    createModalOpen.value = false
  } catch {
    toast.error('Failed to create budget')
  }
}

async function handleUpdate(id: string, req: BudgetUpdateRequest) {
  try {
    await updateBudget(id, req)
    // Refresh with spending
    const updated = await fetchBudget(id)
    const idx = budgets.value.findIndex((b) => b.id === id)
    if (idx >= 0) budgets.value[idx] = updated
    // Update summary
    const newSummary = await fetchBudgetSummary()
    summary.value = newSummary
    toast.success('Budget updated')
    createModalOpen.value = false
    editingBudget.value = null
  } catch {
    toast.error('Failed to update budget')
  }
}

async function handleDelete(budget: BudgetWithSpending) {
  if (!confirm(`Delete budget for ${budget.tag_name}?`)) return

  try {
    await deleteBudget(budget.id)
    budgets.value = budgets.value.filter((b) => b.id !== budget.id)
    // Update summary
    const newSummary = await fetchBudgetSummary()
    summary.value = newSummary
    toast.success('Budget deleted')
  } catch {
    toast.error('Failed to delete budget')
  }
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">Budgets</h1>
        <p class="mt-1 text-muted">Track your spending by category</p>
      </div>
      <button
        type="button"
        class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-background transition-opacity hover:opacity-90"
        :disabled="tagsWithoutBudgets.length === 0"
        @click="openCreateModal"
      >
        + New Budget
      </button>
    </div>

    <!-- Summary cards -->
    <div
      v-if="summary && !loading"
      class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      <!-- Total budgeted -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Total Budgeted</p>
        <p class="mt-1 text-2xl font-bold">
          {{ formatCurrency(summary.total_budgeted) }}
        </p>
      </div>

      <!-- Total spent -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Total Spent</p>
        <p class="mt-1 text-2xl font-bold">
          {{ formatCurrency(summary.total_spent) }}
        </p>
      </div>

      <!-- On track -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">On Track</p>
        <p class="text-emerald-400 mt-1 text-2xl font-bold">
          {{ summary.budgets_on_track }}
        </p>
      </div>

      <!-- Needs attention -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Needs Attention</p>
        <p class="mt-1 text-2xl font-bold text-red-400">
          {{ summary.budgets_warning + summary.budgets_exceeded }}
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
      <!-- Status tabs -->
      <div class="flex rounded-lg border border-border bg-surface p-1">
        <button
          v-for="tab in ['all', 'ok', 'warning', 'exceeded'] as const"
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
      v-else-if="filteredBudgets.length === 0"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p v-if="statusFilter === 'all'" class="text-muted">
        No budgets set up yet. Create a budget to start tracking your spending.
      </p>
      <p v-else class="text-muted">
        No {{ getStatusLabel(statusFilter).toLowerCase() }} budgets.
      </p>
    </div>

    <!-- Budget list -->
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <BudgetsBudgetCard
        v-for="budget in filteredBudgets"
        :key="budget.id"
        :budget="budget"
        @edit="handleEdit(budget)"
        @delete="handleDelete(budget)"
      />
    </div>

    <!-- Create/Edit modal -->
    <BudgetsCreateBudgetModal
      :is-open="createModalOpen"
      :existing-budget="editingBudget ?? undefined"
      :available-tags="tagsWithoutBudgets"
      @close="createModalOpen = false"
      @create="handleCreate"
      @update="handleUpdate"
    />
  </div>
</template>
