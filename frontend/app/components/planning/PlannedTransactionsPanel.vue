<!-- ==========================================================================
Planned Transactions Panel
Manage expected income and expenses that feed into forecasts
============================================================================ -->

<script setup lang="ts">
import type {
  PlannedTransaction,
  PlannedTransactionCreateRequest,
  RecurringFrequency,
  TransactionDirection,
} from '~/types/planned-transactions'
import { getFrequencyLabel } from '~/types/planned-transactions'

// ---------------------------------------------------------------------------
// API & State
// ---------------------------------------------------------------------------

const {
  fetchPlannedTransactions,
  createPlannedTransaction,
  updatePlannedTransaction,
  deletePlannedTransaction,
  togglePlannedTransaction,
} = usePlannedTransactionsApi()

const toast = useToastStore()

// Data
const transactions = ref<PlannedTransaction[]>([])
const loading = ref(true)
const error = ref('')

// Filters
const directionFilter = ref<TransactionDirection | 'all'>('all')

// Modal state
const showModal = ref(false)
const editingTransaction = ref<PlannedTransaction | null>(null)

// Form state
const formData = ref({
  name: '',
  amount: '',
  direction: 'expense' as TransactionDirection,
  frequency: '' as string,
  next_expected_date: '',
  end_date: '',
  notes: '',
})

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Filter transactions by direction
const filteredTransactions = computed(() => {
  if (directionFilter.value === 'all') {
    return transactions.value
  }
  return transactions.value.filter((t) => t.direction === directionFilter.value)
})

// Count by direction for tabs
const counts = computed(() => ({
  all: transactions.value.length,
  income: transactions.value.filter((t) => t.direction === 'income').length,
  expense: transactions.value.filter((t) => t.direction === 'expense').length,
}))

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetchPlannedTransactions()
    transactions.value = response.transactions
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : 'Failed to load planned transactions'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function openCreateModal() {
  editingTransaction.value = null
  formData.value = {
    name: '',
    amount: '',
    direction: 'expense',
    frequency: '',
    next_expected_date: '',
    end_date: '',
    notes: '',
  }
  showModal.value = true
}

function openEditModal(txn: PlannedTransaction) {
  editingTransaction.value = txn
  formData.value = {
    name: txn.name,
    amount: Math.abs(parseFloat(txn.amount)).toString(),
    direction: txn.direction,
    frequency: txn.frequency || '',
    next_expected_date: txn.next_expected_date
      ? (txn.next_expected_date.split('T')[0] ?? '')
      : '',
    end_date: txn.end_date ? (txn.end_date.split('T')[0] ?? '') : '',
    notes: txn.notes || '',
  }
  showModal.value = true
}

async function handleSubmit() {
  const amount = parseFloat(formData.value.amount)
  if (isNaN(amount) || amount <= 0) {
    toast.error('Please enter a valid amount')
    return
  }

  // Sign the amount based on direction
  const signedAmount = formData.value.direction === 'expense' ? -amount : amount

  // Parse frequency as RecurringFrequency or null
  const frequency = formData.value.frequency
    ? (formData.value.frequency as RecurringFrequency)
    : null

  try {
    if (editingTransaction.value) {
      // Update existing
      const updated = await updatePlannedTransaction(
        editingTransaction.value.id,
        {
          name: formData.value.name,
          amount: signedAmount,
          frequency,
          next_expected_date: formData.value.next_expected_date || null,
          end_date: formData.value.end_date || null,
          notes: formData.value.notes || null,
          clear_frequency: !formData.value.frequency,
          clear_end_date: !formData.value.end_date,
          clear_notes: !formData.value.notes,
        },
      )
      // Update in list
      const idx = transactions.value.findIndex(
        (t) => t.id === editingTransaction.value?.id,
      )
      if (idx >= 0) transactions.value[idx] = updated
      toast.success('Transaction updated')
    } else {
      // Create new
      const request: PlannedTransactionCreateRequest = {
        name: formData.value.name,
        amount: signedAmount,
        frequency,
        next_expected_date: formData.value.next_expected_date || null,
        end_date: formData.value.end_date || null,
        notes: formData.value.notes || null,
      }
      const created = await createPlannedTransaction(request)
      transactions.value.push(created)
      toast.success('Transaction created')
    }

    showModal.value = false
  } catch {
    toast.error('Failed to save transaction')
  }
}

async function handleToggle(txn: PlannedTransaction) {
  try {
    const updated = await togglePlannedTransaction(txn.id, !txn.enabled)
    const idx = transactions.value.findIndex((t) => t.id === txn.id)
    if (idx >= 0) transactions.value[idx] = updated
    toast.success(
      updated.enabled ? 'Transaction enabled' : 'Transaction disabled',
    )
  } catch {
    toast.error('Failed to toggle transaction')
  }
}

async function handleDelete(txn: PlannedTransaction) {
  if (!confirm(`Delete "${txn.name}"? This cannot be undone.`)) return

  try {
    await deletePlannedTransaction(txn.id)
    transactions.value = transactions.value.filter((t) => t.id !== txn.id)
    toast.success('Transaction deleted')
  } catch {
    toast.error('Failed to delete transaction')
  }
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

function formatCurrency(amount: string): string {
  const num = parseFloat(amount)
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
  }).format(Math.abs(num))
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Not set'
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface">
    <!-- Header -->
    <div
      class="flex items-center justify-between border-b border-border px-6 py-4"
    >
      <div>
        <h2 class="text-lg font-semibold">Planned Transactions</h2>
        <p class="text-sm text-muted">
          Expected income and expenses for forecasting
        </p>
      </div>
      <AppButton @click="openCreateModal"> Add Planned </AppButton>
    </div>

    <!-- Direction filter tabs -->
    <div class="border-b border-border px-6">
      <div class="flex gap-4 py-2">
        <button
          v-for="dir in ['all', 'income', 'expense'] as const"
          :key="dir"
          type="button"
          class="px-3 py-1.5 text-sm font-medium transition-colors"
          :class="
            directionFilter === dir
              ? dir === 'income'
                ? 'text-emerald-400'
                : dir === 'expense'
                  ? 'text-red-400'
                  : 'text-primary'
              : 'text-muted hover:text-foreground'
          "
          @click="directionFilter = dir"
        >
          {{ dir === 'all' ? 'All' : dir === 'income' ? 'Income' : 'Expenses' }}
          <span class="ml-1 text-xs opacity-60">({{ counts[dir] }})</span>
        </button>
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="m-4 rounded-lg border border-negative/50 bg-negative/10 p-4 text-negative"
    >
      {{ error }}
    </div>

    <!-- Loading state -->
    <div v-else-if="loading" class="space-y-3 p-6">
      <div
        v-for="i in 3"
        :key="i"
        class="h-16 animate-pulse rounded-lg bg-border"
      />
    </div>

    <!-- Empty state -->
    <div
      v-else-if="filteredTransactions.length === 0"
      class="p-8 text-center text-muted"
    >
      <p>No planned transactions yet.</p>
      <p class="mt-1 text-sm">
        Add expected income or expenses to improve your forecast accuracy.
      </p>
    </div>

    <!-- Transaction list -->
    <div v-else class="divide-y divide-border">
      <div
        v-for="txn in filteredTransactions"
        :key="txn.id"
        class="flex items-center gap-4 px-6 py-4 hover:bg-border/10"
        :class="!txn.enabled && 'opacity-50'"
      >
        <!-- Direction indicator -->
        <div
          :class="[
            'flex h-10 w-10 items-center justify-center rounded-full',
            txn.direction === 'income'
              ? 'bg-emerald-500/20 text-emerald-400'
              : 'bg-red-500/20 text-red-400',
          ]"
        >
          <svg
            v-if="txn.direction === 'income'"
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M7 11l5-5m0 0l5 5m-5-5v12"
            />
          </svg>
          <svg
            v-else
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M17 13l-5 5m0 0l-5-5m5 5V6"
            />
          </svg>
        </div>

        <!-- Transaction details -->
        <div class="flex-1">
          <p class="font-medium">{{ txn.name }}</p>
          <p class="text-sm text-muted">
            {{ getFrequencyLabel(txn.frequency) }}
            <span v-if="txn.next_expected_date" class="mx-1">·</span>
            <span v-if="txn.next_expected_date">
              Next: {{ formatDate(txn.next_expected_date) }}
            </span>
          </p>
        </div>

        <!-- Amount -->
        <div
          :class="[
            'text-right font-semibold',
            txn.direction === 'income' ? 'text-emerald-400' : 'text-red-400',
          ]"
        >
          {{ txn.direction === 'income' ? '+' : '-'
          }}{{ formatCurrency(txn.amount) }}
        </div>

        <!-- Actions dropdown -->
        <div class="relative">
          <button
            type="button"
            class="rounded p-1.5 text-muted hover:bg-border hover:text-foreground"
            @click.stop="
              (
                $event.currentTarget as HTMLElement
              ).nextElementSibling?.classList.toggle('hidden')
            "
          >
            <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"
              />
            </svg>
          </button>
          <!-- Dropdown menu -->
          <div
            class="absolute right-0 top-full z-10 mt-1 hidden min-w-[120px] rounded-lg border border-border bg-surface py-1 shadow-lg"
          >
            <button
              type="button"
              class="w-full px-4 py-2 text-left text-sm hover:bg-border/50"
              @click="openEditModal(txn)"
            >
              Edit
            </button>
            <button
              type="button"
              class="w-full px-4 py-2 text-left text-sm hover:bg-border/50"
              @click="handleToggle(txn)"
            >
              {{ txn.enabled ? 'Disable' : 'Enable' }}
            </button>
            <button
              type="button"
              class="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-border/50"
              @click="handleDelete(txn)"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <div
        v-if="showModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showModal = false"
      >
        <div
          class="w-full max-w-md rounded-lg border border-border bg-surface p-6"
        >
          <h3 class="mb-4 text-lg font-semibold">
            {{ editingTransaction ? 'Edit' : 'Add' }} Planned Transaction
          </h3>

          <form class="space-y-4" @submit.prevent="handleSubmit">
            <!-- Name -->
            <div>
              <label class="mb-1 block text-sm font-medium">Name</label>
              <AppInput
                v-model="formData.name"
                placeholder="e.g., Salary, Rent, Bonus"
                required
              />
            </div>

            <!-- Direction -->
            <div>
              <label class="mb-1 block text-sm font-medium">Type</label>
              <div class="flex gap-4">
                <label class="flex items-center gap-2">
                  <input
                    v-model="formData.direction"
                    type="radio"
                    value="income"
                    class="text-emerald-500"
                  />
                  <span class="text-emerald-400">Income</span>
                </label>
                <label class="flex items-center gap-2">
                  <input
                    v-model="formData.direction"
                    type="radio"
                    value="expense"
                    class="text-red-500"
                  />
                  <span class="text-red-400">Expense</span>
                </label>
              </div>
            </div>

            <!-- Amount -->
            <div>
              <label class="mb-1 block text-sm font-medium">Amount</label>
              <AppInput
                v-model="formData.amount"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="0.00"
                required
              />
            </div>

            <!-- Frequency -->
            <div>
              <label class="mb-1 block text-sm font-medium">Frequency</label>
              <AppSelect
                v-model="formData.frequency"
                :options="[
                  { value: '', label: 'One-time' },
                  { value: 'weekly', label: 'Weekly' },
                  { value: 'fortnightly', label: 'Fortnightly' },
                  { value: 'monthly', label: 'Monthly' },
                  { value: 'quarterly', label: 'Quarterly' },
                  { value: 'annual', label: 'Annual' },
                ]"
              />
            </div>

            <!-- Next expected date -->
            <div>
              <label class="mb-1 block text-sm font-medium"
                >Next Expected Date</label
              >
              <input
                v-model="formData.next_expected_date"
                type="date"
                class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <!-- End date (for recurring) -->
            <div v-if="formData.frequency">
              <label class="mb-1 block text-sm font-medium"
                >End Date (optional)</label
              >
              <input
                v-model="formData.end_date"
                type="date"
                class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <!-- Notes -->
            <div>
              <label class="mb-1 block text-sm font-medium"
                >Notes (optional)</label
              >
              <textarea
                v-model="formData.notes"
                rows="2"
                class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="Any additional details..."
              />
            </div>

            <!-- Buttons -->
            <div class="flex justify-end gap-3 pt-2">
              <AppButton
                variant="outline"
                type="button"
                @click="showModal = false"
              >
                Cancel
              </AppButton>
              <AppButton type="submit">
                {{ editingTransaction ? 'Save' : 'Create' }}
              </AppButton>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>
