<!-- ==========================================================================
Goals Page
Manage savings goals
============================================================================ -->

<script setup lang="ts">
import type {
  Goal,
  GoalSummaryResponse,
  GoalCreateRequest,
  GoalUpdateRequest,
  GoalStatus,
} from '~/types/goals'
import { getStatusLabel } from '~/types/goals'

useHead({ title: 'Savings Goals | Finances' })

// API
const {
  fetchGoals,
  fetchGoalSummary,
  createGoal,
  updateGoal,
  deleteGoal,
  contributeToGoal,
  completeGoal,
  pauseGoal,
  resumeGoal,
  cancelGoal,
} = useGoalsApi()
const { fetchAccounts } = useAccountsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const goals = ref<Goal[]>([])
const summary = ref<GoalSummaryResponse | null>(null)
const accounts = ref<Array<{ id: string; name: string }>>([])
const loading = ref(true)
const error = ref('')

// Modal state
const createModalOpen = ref(false)
const editingGoal = ref<Goal | null>(null)

// Contribute modal
const contributeModalOpen = ref(false)
const contributingGoal = ref<Goal | null>(null)
const contributeAmount = ref(0)

// Filter
const statusFilter = ref<'all' | GoalStatus>('all')

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Filter goals by status
const filteredGoals = computed(() => {
  if (statusFilter.value === 'all') {
    // "All" shows active and paused
    return goals.value.filter((g) => ['active', 'paused'].includes(g.status))
  }
  return goals.value.filter((g) => g.status === statusFilter.value)
})

// Tab counts
const tabCounts = computed(() => ({
  all: goals.value.filter((g) => ['active', 'paused'].includes(g.status))
    .length,
  active: goals.value.filter((g) => g.status === 'active').length,
  paused: goals.value.filter((g) => g.status === 'paused').length,
  completed: goals.value.filter((g) => g.status === 'completed').length,
  cancelled: goals.value.filter((g) => g.status === 'cancelled').length,
}))

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [goalsResponse, summaryResponse, accountsResponse] =
      await Promise.all([
        fetchGoals(true), // Include inactive
        fetchGoalSummary(),
        fetchAccounts(),
      ])
    goals.value = goalsResponse.goals
    summary.value = summaryResponse
    // Map accounts to the format expected by the modal
    accounts.value = accountsResponse.accounts.map((a) => ({
      id: a.id,
      name: a.display_name ?? a.name ?? a.id,
    }))
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load goals'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function openCreateModal() {
  editingGoal.value = null
  createModalOpen.value = true
}

function handleEdit(goal: Goal) {
  editingGoal.value = goal
  createModalOpen.value = true
}

async function handleCreate(req: GoalCreateRequest) {
  try {
    const created = await createGoal(req)
    goals.value.push(created)
    // Update summary
    const newSummary = await fetchGoalSummary()
    summary.value = newSummary
    toast.success('Goal created')
    createModalOpen.value = false
  } catch {
    toast.error('Failed to create goal')
  }
}

async function handleUpdate(id: string, req: GoalUpdateRequest) {
  try {
    const updated = await updateGoal(id, req)
    const idx = goals.value.findIndex((g) => g.id === id)
    if (idx >= 0) goals.value[idx] = updated
    // Update summary
    const newSummary = await fetchGoalSummary()
    summary.value = newSummary
    toast.success('Goal updated')
    createModalOpen.value = false
    editingGoal.value = null
  } catch {
    toast.error('Failed to update goal')
  }
}

async function handleDelete(goal: Goal) {
  if (!confirm(`Delete goal "${goal.name}"?`)) return

  try {
    await deleteGoal(goal.id)
    goals.value = goals.value.filter((g) => g.id !== goal.id)
    // Update summary
    const newSummary = await fetchGoalSummary()
    summary.value = newSummary
    toast.success('Goal deleted')
  } catch {
    toast.error('Failed to delete goal')
  }
}

function openContributeModal(goal: Goal) {
  contributingGoal.value = goal
  contributeAmount.value = 0
  contributeModalOpen.value = true
}

async function handleContribute() {
  if (!contributingGoal.value || contributeAmount.value <= 0) return

  try {
    const updated = await contributeToGoal(contributingGoal.value.id, {
      amount: contributeAmount.value,
    })
    const idx = goals.value.findIndex((g) => g.id === updated.id)
    if (idx >= 0) goals.value[idx] = updated
    // Update summary
    const newSummary = await fetchGoalSummary()
    summary.value = newSummary
    toast.success(
      `Added £${contributeAmount.value} to ${contributingGoal.value.name}`,
    )
    contributeModalOpen.value = false
    contributingGoal.value = null
  } catch {
    toast.error('Failed to add contribution')
  }
}

async function handleComplete(goal: Goal) {
  try {
    const updated = await completeGoal(goal.id)
    const idx = goals.value.findIndex((g) => g.id === goal.id)
    if (idx >= 0) goals.value[idx] = updated
    const newSummary = await fetchGoalSummary()
    summary.value = newSummary
    toast.success(`Completed: ${goal.name}`)
  } catch {
    toast.error('Failed to complete goal')
  }
}

async function handlePause(goal: Goal) {
  try {
    const updated = await pauseGoal(goal.id)
    const idx = goals.value.findIndex((g) => g.id === goal.id)
    if (idx >= 0) goals.value[idx] = updated
    const newSummary = await fetchGoalSummary()
    summary.value = newSummary
    toast.success(`Paused: ${goal.name}`)
  } catch {
    toast.error('Failed to pause goal')
  }
}

async function handleResume(goal: Goal) {
  try {
    const updated = await resumeGoal(goal.id)
    const idx = goals.value.findIndex((g) => g.id === goal.id)
    if (idx >= 0) goals.value[idx] = updated
    const newSummary = await fetchGoalSummary()
    summary.value = newSummary
    toast.success(`Resumed: ${goal.name}`)
  } catch {
    toast.error('Failed to resume goal')
  }
}

async function handleCancel(goal: Goal) {
  if (!confirm(`Cancel goal "${goal.name}"?`)) return

  try {
    const updated = await cancelGoal(goal.id)
    const idx = goals.value.findIndex((g) => g.id === goal.id)
    if (idx >= 0) goals.value[idx] = updated
    const newSummary = await fetchGoalSummary()
    summary.value = newSummary
    toast.success(`Cancelled: ${goal.name}`)
  } catch {
    toast.error('Failed to cancel goal')
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
        <h1 class="text-2xl font-bold sm:text-3xl">Savings Goals</h1>
        <p class="mt-1 text-muted">
          Track your progress towards financial goals
        </p>
      </div>
      <button
        type="button"
        class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
        @click="openCreateModal"
      >
        + New Goal
      </button>
    </div>

    <!-- Summary cards -->
    <div
      v-if="summary && !loading"
      class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      <!-- Total saved -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Total Saved</p>
        <p class="mt-1 text-2xl font-bold">
          {{ formatCurrency(summary.total_saved) }}
        </p>
      </div>

      <!-- Target -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Total Target</p>
        <p class="mt-1 text-2xl font-bold">
          {{ formatCurrency(summary.total_target) }}
        </p>
      </div>

      <!-- Active goals -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Active Goals</p>
        <p class="mt-1 text-2xl font-bold text-emerald-400">
          {{ summary.active_goals }}
        </p>
      </div>

      <!-- Completed -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Completed</p>
        <p class="mt-1 text-2xl font-bold text-sky-400">
          {{ summary.completed_goals }}
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
          v-for="tab in [
            'all',
            'active',
            'paused',
            'completed',
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
          <div class="h-16 w-16 animate-pulse rounded-full bg-border" />
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="filteredGoals.length === 0"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p v-if="statusFilter === 'all'" class="text-muted">
        No savings goals yet. Create a goal to start tracking your progress.
      </p>
      <p v-else class="text-muted">
        No {{ getStatusLabel(statusFilter).toLowerCase() }} goals.
      </p>
    </div>

    <!-- Goals list -->
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <GoalsGoalCard
        v-for="goal in filteredGoals"
        :key="goal.id"
        :goal="goal"
        @contribute="openContributeModal(goal)"
        @complete="handleComplete(goal)"
        @pause="handlePause(goal)"
        @resume="handleResume(goal)"
        @cancel="handleCancel(goal)"
        @edit="handleEdit(goal)"
        @delete="handleDelete(goal)"
      />
    </div>

    <!-- Create/Edit modal -->
    <GoalsCreateGoalModal
      :is-open="createModalOpen"
      :existing-goal="editingGoal ?? undefined"
      :available-accounts="accounts"
      @close="createModalOpen = false"
      @create="handleCreate"
      @update="handleUpdate"
    />

    <!-- Contribute modal -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-opacity duration-200"
        enter-from-class="opacity-0"
        leave-active-class="transition-opacity duration-200"
        leave-to-class="opacity-0"
      >
        <div
          v-if="contributeModalOpen && contributingGoal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          @click.self="contributeModalOpen = false"
        >
          <div
            class="w-full max-w-sm rounded-xl border border-border bg-surface p-6 shadow-xl"
          >
            <h2 class="text-xl font-semibold">Add Funds</h2>
            <p class="mt-1 text-sm text-muted">{{ contributingGoal.name }}</p>

            <form class="mt-4" @submit.prevent="handleContribute">
              <div>
                <label class="block text-sm font-medium text-muted"
                  >Amount</label
                >
                <div class="relative mt-1">
                  <span
                    class="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                    >£</span
                  >
                  <input
                    v-model.number="contributeAmount"
                    type="number"
                    min="0"
                    step="10"
                    class="w-full rounded-lg border border-border bg-background py-2 pl-8 pr-3 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="0"
                    autofocus
                  />
                </div>
              </div>

              <div class="mt-6 flex justify-end gap-2">
                <button
                  type="button"
                  class="rounded-lg bg-gray-700/50 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700"
                  @click="contributeModalOpen = false"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  :disabled="contributeAmount <= 0"
                  class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
                >
                  Add Funds
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
