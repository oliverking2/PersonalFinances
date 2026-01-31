<!-- ==========================================================================
Recurring Patterns Page
Manage recurring expenses (subscriptions, bills) and income (salary, transfers)
============================================================================ -->

<script setup lang="ts">
import type {
  Subscription,
  RecurringStatus,
  RecurringDirection,
  SubscriptionSummary,
} from '~/types/subscriptions'
import { getStatusLabel } from '~/types/subscriptions'

useHead({ title: 'Recurring Patterns | Finances' })

// API
const {
  fetchSubscriptions,
  fetchSubscriptionSummary,
  confirmSubscription,
  dismissSubscription,
  pauseSubscription,
  updateSubscription,
} = useSubscriptionsApi()

const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const subscriptions = ref<Subscription[]>([])
const summary = ref<SubscriptionSummary | null>(null)
const loading = ref(true)
const error = ref('')

// Filters
const statusFilter = ref<RecurringStatus | 'all'>('all')
const directionFilter = ref<RecurringDirection | 'all'>('all')
const sortBy = ref<'amount' | 'name' | 'next'>('amount')

// Edit modal state
const editModalOpen = ref(false)
const editingSubscription = ref<Subscription | null>(null)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Filter subscriptions by status and direction
const filteredSubscriptions = computed(() => {
  let result = [...subscriptions.value]

  // Direction filter
  if (directionFilter.value !== 'all') {
    result = result.filter((s) => s.direction === directionFilter.value)
  }

  // Status filter
  if (statusFilter.value === 'all') {
    // "All" excludes dismissed subscriptions
    result = result.filter((s) => s.status !== 'dismissed')
  } else {
    result = result.filter((s) => s.status === statusFilter.value)
  }

  // Sort
  result.sort((a, b) => {
    switch (sortBy.value) {
      case 'amount':
        return Math.abs(b.expected_amount) - Math.abs(a.expected_amount)
      case 'name':
        return a.display_name.localeCompare(b.display_name)
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
  let filtered = subscriptions.value
  if (directionFilter.value !== 'all') {
    filtered = filtered.filter((s) => s.direction === directionFilter.value)
  }

  return {
    all: filtered.filter((s) => s.status !== 'dismissed').length,
    confirmed: filtered.filter(
      (s) => s.status === 'confirmed' || s.status === 'manual',
    ).length,
    detected: filtered.filter((s) => s.status === 'detected').length,
    paused: filtered.filter((s) => s.status === 'paused').length,
    dismissed: filtered.filter((s) => s.status === 'dismissed').length,
  }
})

// Direction counts
const directionCounts = computed(() => ({
  all: subscriptions.value.filter((s) => s.status !== 'dismissed').length,
  expense: subscriptions.value.filter(
    (s) => s.direction === 'expense' && s.status !== 'dismissed',
  ).length,
  income: subscriptions.value.filter(
    (s) => s.direction === 'income' && s.status !== 'dismissed',
  ).length,
}))

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    // Include dismissed subscriptions so user can restore them
    const [subsResponse, summaryResponse] = await Promise.all([
      fetchSubscriptions({ include_dismissed: true }),
      fetchSubscriptionSummary(),
    ])
    subscriptions.value = subsResponse.subscriptions
    summary.value = summaryResponse
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : 'Failed to load subscriptions'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

async function handleConfirm(subscription: Subscription) {
  try {
    const updated = await confirmSubscription(subscription.id)
    // Update in list
    const idx = subscriptions.value.findIndex((s) => s.id === subscription.id)
    if (idx >= 0) subscriptions.value[idx] = updated
    toast.success(`Confirmed: ${subscription.display_name}`)
  } catch {
    toast.error('Failed to confirm subscription')
  }
}

async function handleDismiss(subscription: Subscription) {
  try {
    await dismissSubscription(subscription.id)
    // Update status in list (keep it so user can restore later)
    const idx = subscriptions.value.findIndex((s) => s.id === subscription.id)
    if (idx >= 0) {
      subscriptions.value[idx] = { ...subscription, status: 'dismissed' }
    }
    toast.success(`Dismissed: ${subscription.display_name}`)
  } catch {
    toast.error('Failed to dismiss subscription')
  }
}

async function handlePause(subscription: Subscription) {
  try {
    const updated = await pauseSubscription(subscription.id)
    // Update in list
    const idx = subscriptions.value.findIndex((s) => s.id === subscription.id)
    if (idx >= 0) subscriptions.value[idx] = updated
    toast.success(`Paused: ${subscription.display_name}`)
  } catch {
    toast.error('Failed to pause subscription')
  }
}

async function handleRestore(subscription: Subscription) {
  try {
    // Restore by confirming the subscription
    const updated = await confirmSubscription(subscription.id)
    // Update in list
    const idx = subscriptions.value.findIndex((s) => s.id === subscription.id)
    if (idx >= 0) subscriptions.value[idx] = updated
    toast.success(`Restored: ${subscription.display_name}`)
  } catch {
    toast.error('Failed to restore subscription')
  }
}

function handleEdit(subscription: Subscription) {
  editingSubscription.value = subscription
  editModalOpen.value = true
}

interface SubscriptionUpdates {
  display_name?: string
  notes?: string
  expected_amount?: number
}

async function handleSaveEdit(updates: SubscriptionUpdates) {
  if (!editingSubscription.value) return

  try {
    const updated = await updateSubscription(
      editingSubscription.value.id,
      updates,
    )
    // Update in list
    const idx = subscriptions.value.findIndex(
      (s) => s.id === editingSubscription.value?.id,
    )
    if (idx >= 0) subscriptions.value[idx] = updated
    toast.success('Subscription updated')
    editModalOpen.value = false
    editingSubscription.value = null
  } catch {
    toast.error('Failed to update subscription')
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
    <div>
      <h1 class="text-2xl font-bold sm:text-3xl">Recurring Patterns</h1>
      <p class="mt-1 text-muted">Manage recurring expenses and income</p>
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
        <p class="text-emerald-400 mt-1 text-2xl font-bold">
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

      <!-- Confirmed -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Confirmed</p>
        <p class="mt-1 text-2xl font-bold text-primary">
          {{ summary.confirmed_count }}
        </p>
      </div>

      <!-- Needs review -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Needs Review</p>
        <p class="mt-1 text-2xl font-bold text-warning">
          {{ summary.detected_count }}
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
            'confirmed',
            'detected',
            'paused',
            'dismissed',
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
      v-else-if="filteredSubscriptions.length === 0"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p v-if="statusFilter === 'all'" class="text-muted">
        No recurring patterns detected yet. Keep using your accounts and
        patterns will be detected automatically.
      </p>
      <p v-else class="text-muted">
        No {{ getStatusLabel(statusFilter).toLowerCase() }} subscriptions.
      </p>
    </div>

    <!-- Subscription list -->
    <div v-else class="space-y-4">
      <SubscriptionsSubscriptionCard
        v-for="sub in filteredSubscriptions"
        :key="sub.id"
        :subscription="sub"
        @confirm="handleConfirm(sub)"
        @dismiss="handleDismiss(sub)"
        @pause="handlePause(sub)"
        @restore="handleRestore(sub)"
        @edit="handleEdit(sub)"
      />
    </div>

    <!-- Edit modal -->
    <SubscriptionsSubscriptionEditModal
      v-if="editingSubscription"
      :subscription="editingSubscription"
      :open="editModalOpen"
      @close="editModalOpen = false"
      @save="handleSaveEdit"
    />
  </div>
</template>
