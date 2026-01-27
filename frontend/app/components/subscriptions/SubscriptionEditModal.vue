<!-- ==========================================================================
SubscriptionEditModal
Modal for viewing subscription details, transactions, and editing
============================================================================ -->

<script setup lang="ts">
import type {
  Subscription,
  SubscriptionTransaction,
} from '~/types/subscriptions'
import { getFrequencyLabel } from '~/types/subscriptions'

// Props
const props = defineProps<{
  subscription: Subscription
  open: boolean
}>()

// Emits
const emit = defineEmits<{
  close: []
  save: [updates: SubscriptionUpdates]
}>()

// API
const { fetchSubscriptionTransactions } = useSubscriptionsApi()

// Types
interface SubscriptionUpdates {
  display_name?: string
  notes?: string
  expected_amount?: number
}

// Tabs
const activeTab = ref<'details' | 'transactions'>('details')

// Form state - initialise from subscription
const displayName = ref(props.subscription.display_name)
const notes = ref(props.subscription.notes || '')
// Store as string for AppInput compatibility, convert to/from number when needed
const expectedAmountStr = ref(
  Math.abs(props.subscription.expected_amount).toFixed(2),
)
const saving = ref(false)

// Transactions state
const transactions = ref<SubscriptionTransaction[]>([])
const loadingTransactions = ref(false)
const transactionsLoaded = ref(false)

// Watch for subscription changes (when opening for different subscription)
watch(
  () => props.subscription,
  (sub) => {
    displayName.value = sub.display_name
    notes.value = sub.notes || ''
    expectedAmountStr.value = Math.abs(sub.expected_amount).toFixed(2)
    // Reset transactions when subscription changes
    transactions.value = []
    transactionsLoaded.value = false
  },
)

// Load transactions when tab is switched
watch(activeTab, async (tab) => {
  if (tab === 'transactions' && !transactionsLoaded.value) {
    await loadTransactions()
  }
})

// Load transactions
async function loadTransactions() {
  loadingTransactions.value = true
  try {
    const response = await fetchSubscriptionTransactions(props.subscription.id)
    transactions.value = response.transactions
    transactionsLoaded.value = true
  } catch {
    // Silent fail - transactions just won't show
  } finally {
    loadingTransactions.value = false
  }
}

// Handle save
function handleSave() {
  saving.value = true
  const updates: SubscriptionUpdates = {}

  if (displayName.value !== props.subscription.display_name) {
    updates.display_name = displayName.value
  }
  if (notes.value !== (props.subscription.notes || '')) {
    updates.notes = notes.value || undefined
  }
  // Compare expected amount (stored as negative, edited as positive string)
  const newAmount = parseFloat(expectedAmountStr.value) || 0
  if (newAmount !== Math.abs(props.subscription.expected_amount)) {
    // Send as negative since subscriptions are expenses
    updates.expected_amount = -Math.abs(newAmount)
  }

  emit('save', updates)
  saving.value = false
}

// Format currency
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
  }).format(Math.abs(amount))
}

// Format date
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
</script>

<template>
  <!-- Modal backdrop -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        @click.self="emit('close')"
      >
        <!-- Modal content -->
        <div
          class="flex max-h-[85vh] w-full max-w-lg flex-col rounded-lg border border-border bg-surface shadow-xl"
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between border-b border-border px-6 py-4"
          >
            <h2 class="text-lg font-semibold">
              {{ subscription.display_name }}
            </h2>
            <button
              type="button"
              class="text-muted hover:text-foreground"
              @click="emit('close')"
            >
              <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
                />
              </svg>
            </button>
          </div>

          <!-- Tabs -->
          <div class="flex border-b border-border px-6">
            <button
              type="button"
              class="border-b-2 px-4 py-2 text-sm font-medium transition-colors"
              :class="
                activeTab === 'details'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted hover:text-foreground'
              "
              @click="activeTab = 'details'"
            >
              Details
            </button>
            <button
              type="button"
              class="border-b-2 px-4 py-2 text-sm font-medium transition-colors"
              :class="
                activeTab === 'transactions'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted hover:text-foreground'
              "
              @click="activeTab = 'transactions'"
            >
              Transactions ({{ subscription.occurrence_count }})
            </button>
          </div>

          <!-- Body - scrollable -->
          <div class="flex-1 overflow-y-auto p-6">
            <!-- Details Tab -->
            <div v-if="activeTab === 'details'" class="space-y-4">
              <!-- Expected amount (editable) -->
              <div>
                <label class="mb-1 block text-sm font-medium"
                  >Expected Amount</label
                >
                <div class="flex items-center gap-2">
                  <span class="text-muted">£</span>
                  <AppInput
                    v-model="expectedAmountStr"
                    type="number"
                    class="flex-1"
                    placeholder="0.00"
                  />
                  <span class="text-sm text-muted">
                    /
                    {{
                      getFrequencyLabel(subscription.frequency).toLowerCase()
                    }}
                  </span>
                </div>
                <p class="mt-1 text-xs text-muted">
                  Update if the subscription price has changed
                </p>
              </div>

              <!-- Display name -->
              <div>
                <label class="mb-1 block text-sm font-medium"
                  >Display Name</label
                >
                <AppInput
                  v-model="displayName"
                  placeholder="e.g., Netflix, Spotify"
                />
              </div>

              <!-- Notes -->
              <div>
                <label class="mb-1 block text-sm font-medium">Notes</label>
                <textarea
                  v-model="notes"
                  rows="3"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Add any notes..."
                />
              </div>

              <!-- Detection info -->
              <div class="rounded-lg bg-background/50 p-3">
                <p class="mb-2 text-sm font-medium text-muted">
                  Detection Info
                </p>
                <div class="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span class="text-muted">Confidence:</span>
                    <span class="ml-1"
                      >{{
                        Math.round(subscription.confidence_score * 100)
                      }}%</span
                    >
                  </div>
                  <div>
                    <span class="text-muted">Occurrences:</span>
                    <span class="ml-1">{{
                      subscription.occurrence_count
                    }}</span>
                  </div>
                  <div>
                    <span class="text-muted">Last:</span>
                    <span class="ml-1">{{
                      formatDate(subscription.last_occurrence_date)
                    }}</span>
                  </div>
                  <div>
                    <span class="text-muted">Next:</span>
                    <span class="ml-1">{{
                      formatDate(subscription.next_expected_date)
                    }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Transactions Tab -->
            <div v-else-if="activeTab === 'transactions'">
              <!-- Loading -->
              <div v-if="loadingTransactions" class="space-y-3">
                <div
                  v-for="i in 3"
                  :key="i"
                  class="h-12 animate-pulse rounded bg-border"
                />
              </div>

              <!-- No transactions -->
              <div
                v-else-if="transactions.length === 0"
                class="py-8 text-center text-muted"
              >
                No linked transactions found.
              </div>

              <!-- Transaction list -->
              <div v-else class="space-y-2">
                <div
                  v-for="txn in transactions"
                  :key="txn.id"
                  class="flex items-center justify-between rounded-lg border border-border bg-background/50 p-3"
                >
                  <div>
                    <p class="text-sm font-medium">
                      {{ txn.merchant_name || txn.description || 'Unknown' }}
                    </p>
                    <p class="text-xs text-muted">
                      {{ formatDate(txn.booking_date) }}
                    </p>
                  </div>
                  <p class="font-medium text-negative">
                    -{{ formatCurrency(txn.amount) }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="flex items-center justify-end gap-3 border-t border-border px-6 py-4"
          >
            <AppButton variant="secondary" @click="emit('close')">
              Cancel
            </AppButton>
            <AppButton
              v-if="activeTab === 'details'"
              :loading="saving"
              @click="handleSave"
            >
              Save Changes
            </AppButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
