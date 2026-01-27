<!-- ==========================================================================
TransactionDetailModal
Modal showing full transaction details with tag management
Opens from the "details" button on TransactionRow
============================================================================ -->

<script setup lang="ts">
import type { Transaction, SplitRequest } from '~/types/transactions'
import type { Tag } from '~/types/tags'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
  transaction: Transaction | null
  accountName?: string // Display name of the account (optional)
  availableTags: Tag[] // All user's tags for the selector
}>()

const emit = defineEmits<{
  close: []
  'create-tag': [transactionId: string, name: string]
  'update-note': [transactionId: string, note: string | null]
  'update-splits': [transactionId: string, splits: SplitRequest[]]
  'clear-splits': [transactionId: string]
}>()

// ---------------------------------------------------------------------------
// Local State
// ---------------------------------------------------------------------------

const showTagSelector = ref(false)

// Note editing state
const isEditingNote = ref(false)
const editedNote = ref('')

// Split editing state (always in edit mode, no toggle needed)
const editedSplits = ref<{ tag_id: string; amount: number }[]>([])

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Display name: prefer merchant_name, fall back to description
const displayName = computed(() => {
  if (!props.transaction) return ''
  return (
    props.transaction.merchant_name ||
    props.transaction.description ||
    'Unknown Transaction'
  )
})

// Format booking date for display (e.g., "Mon 20 Jan 2026")
const formattedBookingDate = computed(() => {
  if (!props.transaction?.booking_date) return 'Unknown'
  const date = new Date(props.transaction.booking_date + 'T00:00:00')
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date)
})

// Format value date for display (only shown if different from booking date)
const formattedValueDate = computed(() => {
  if (!props.transaction?.value_date) return null
  if (props.transaction.value_date === props.transaction.booking_date)
    return null
  const date = new Date(props.transaction.value_date + 'T00:00:00')
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date)
})

// Format amount with currency symbol and +/- prefix
const formattedAmount = computed(() => {
  if (!props.transaction) return ''
  const { amount, currency } = props.transaction
  const formatted = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: currency,
  }).format(Math.abs(amount))
  return amount >= 0 ? `+${formatted}` : `-${formatted}`
})

// Amount colour: green for income (positive), default for expenses (negative)
const amountColorClass = computed(() => {
  if (!props.transaction) return ''
  return props.transaction.amount >= 0 ? 'text-positive' : 'text-foreground'
})

// Check if transaction has splits
const hasSplits = computed(() => {
  return (props.transaction?.splits?.length ?? 0) > 0
})

// Check if multiple splits exist (vs single tag at 100%)
// Used to determine if we show auto-tag indicator (only for single tags)
const isSplitMode = computed(() => {
  const splits = props.transaction?.splits ?? []
  // Split mode if: has multiple splits, or single split not at 100%
  if (splits.length > 1) return true
  const firstSplit = splits[0]
  if (firstSplit) {
    const txnAmount = Math.abs(props.transaction?.amount ?? 0)
    // Not 100% if differs by more than 1 cent
    if (Math.abs(firstSplit.amount - txnAmount) > 0.01) return true
  }
  return false
})

// Get the single tag (when in simple mode)
const singleTag = computed(() => {
  if (isSplitMode.value) return null
  const splits = props.transaction?.splits ?? []
  const firstSplit = splits[0]
  if (firstSplit) {
    return {
      id: firstSplit.tag_id,
      name: firstSplit.tag_name,
      colour: firstSplit.tag_colour,
      is_auto: firstSplit.is_auto,
      rule_id: firstSplit.rule_id,
      rule_name: firstSplit.rule_name,
    }
  }
  return null
})

// Format currency amount
function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  }).format(amount)
}

// Total amount for splits validation
const transactionAbsAmount = computed(() => {
  return Math.abs(props.transaction?.amount ?? 0)
})

// Sum of current edited splits
const editedSplitsTotal = computed(() => {
  return editedSplits.value.reduce((sum, s) => sum + (s.amount || 0), 0)
})

// Remaining amount to allocate
const remainingAmount = computed(() => {
  return (
    Math.round((transactionAbsAmount.value - editedSplitsTotal.value) * 100) /
    100
  )
})

// Check if splits are valid (sum equals transaction amount)
const splitsValid = computed(() => {
  if (editedSplits.value.length === 0) return false
  return Math.abs(remainingAmount.value) < 0.02 // Allow small rounding error
})

// Available tags for split selection (exclude already used)
const availableTagsForSplits = computed(() => {
  const usedTagIds = new Set(editedSplits.value.map((s) => s.tag_id))
  return props.availableTags.filter(
    (t) => !t.is_hidden && !usedTagIds.has(t.id),
  )
})

// Tag options for AppSelect (including currently selected if not in available)
function getTagOptionsForSplit(currentTagId: string) {
  const options = availableTagsForSplits.value.map((t) => ({
    value: t.id,
    label: t.name,
  }))

  // Include currently selected tag if not in available list
  if (
    currentTagId &&
    !availableTagsForSplits.value.find((t) => t.id === currentTagId)
  ) {
    const currentTag = props.availableTags.find((t) => t.id === currentTagId)
    if (currentTag) {
      options.unshift({ value: currentTag.id, label: currentTag.name })
    }
  }

  return options
}

// Get percentage for a split amount
function getSplitPercentage(amount: number): number {
  if (transactionAbsAmount.value === 0) return 0
  return Math.round((amount / transactionAbsAmount.value) * 100)
}

// Get tag colour for a split (used for visual indicator)
function getTagColour(tagId: string): string {
  if (!tagId) return 'transparent'
  const tag = props.availableTags.find((t) => t.id === tagId)
  return tag?.colour || 'transparent'
}

// Update split amount from percentage slider
function updateSplitFromPercentage(index: number, percentage: number) {
  const split = editedSplits.value[index]
  if (!split) return
  split.amount =
    Math.round((percentage / 100) * transactionAbsAmount.value * 100) / 100
}

// Currency symbol for display
const currencySymbol = computed(() => {
  const currency = props.transaction?.currency || 'GBP'
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  })
    .format(0)
    .replace(/[\d.,]/g, '')
    .trim()
})

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function handleClose() {
  showTagSelector.value = false
  isEditingNote.value = false
  editedNote.value = ''
  editedSplits.value = []
  emit('close')
}

// ---------------------------------------------------------------------------
// Note Actions
// ---------------------------------------------------------------------------

function startEditingNote() {
  editedNote.value = props.transaction?.user_note || ''
  isEditingNote.value = true
}

function cancelEditingNote() {
  isEditingNote.value = false
  editedNote.value = ''
}

function saveNote() {
  if (!props.transaction) return
  const note = editedNote.value.trim() || null
  emit('update-note', props.transaction.id, note)
  isEditingNote.value = false
}

// ---------------------------------------------------------------------------
// Split Actions
// ---------------------------------------------------------------------------

function addSplit() {
  editedSplits.value.push({ tag_id: '', amount: 0 })
}

function removeSplit(index: number) {
  editedSplits.value.splice(index, 1)
}

function saveSplits() {
  if (!props.transaction || !splitsValid.value) return

  const splits: SplitRequest[] = editedSplits.value
    .filter((s) => s.tag_id && s.amount > 0)
    .map((s) => ({ tag_id: s.tag_id, amount: s.amount }))

  emit('update-splits', props.transaction.id, splits)
  // Note: The parent will update the transaction, and the watch on props.show
  // won't re-initialize since show doesn't change. The parent should update
  // the transaction prop which will trigger re-render with new values.
}

function handleClearSplits() {
  if (!props.transaction) return
  emit('clear-splits', props.transaction.id)
  // Reset to empty state with one slot at 100%
  editedSplits.value = [{ tag_id: '', amount: transactionAbsAmount.value }]
}

// Close selector when clicking outside
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.tag-selector-container')) {
    showTagSelector.value = false
  }
}

// Set up click outside listener and initialize splits when modal is shown
watch(
  () => props.show,
  (isOpen) => {
    if (isOpen) {
      document.addEventListener('click', handleClickOutside)
      // Always initialize split editor when opening modal
      initializeSplits()
    } else {
      document.removeEventListener('click', handleClickOutside)
      showTagSelector.value = false
    }
  },
)

// Initialize splits from transaction data (always show split editor)
function initializeSplits() {
  if (props.transaction?.splits?.length) {
    // Populate from existing splits
    editedSplits.value = props.transaction.splits.map((s) => ({
      tag_id: s.tag_id,
      amount: s.amount,
    }))
  } else {
    // No splits - start with one empty slot at 100%
    editedSplits.value = [{ tag_id: '', amount: transactionAbsAmount.value }]
  }
}

// Re-initialize when transaction changes (e.g., after save updates the data)
watch(
  () => props.transaction,
  () => {
    if (props.show && props.transaction) {
      initializeSplits()
    }
  },
)

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <!-- Modal backdrop -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="show && transaction"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        @click.self="handleClose"
      >
        <!-- Modal content (scrollable with max height) -->
        <div
          class="flex max-h-[80vh] w-full max-w-md flex-col rounded-lg border border-border bg-surface"
        >
          <!-- Fixed header -->
          <div class="flex items-start justify-between gap-4 p-6 pb-0">
            <div class="min-w-0 flex-1">
              <!-- Merchant/Description as main title -->
              <h2 class="truncate text-lg font-semibold text-foreground">
                {{ displayName }}
              </h2>
              <!-- Category badge (if present) -->
              <span
                v-if="transaction.category"
                class="mt-1 inline-block rounded-full bg-onyx px-2 py-0.5 text-xs text-muted"
              >
                {{ transaction.category }}
              </span>
            </div>
            <!-- Close button -->
            <button
              type="button"
              class="flex-shrink-0 rounded p-1 text-muted transition-colors hover:bg-border hover:text-foreground"
              @click="handleClose"
            >
              <!-- X icon -->
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                class="h-5 w-5"
              >
                <path
                  d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
                />
              </svg>
            </button>
          </div>

          <!-- Scrollable content -->
          <div class="overflow-y-auto p-6 pt-4">
            <!-- Details table -->
            <div
              class="mb-6 divide-y divide-border rounded-lg border border-border"
            >
              <!-- Booking Date -->
              <div class="flex justify-between px-4 py-3">
                <span class="text-sm text-muted">Booking Date</span>
                <span class="text-sm font-medium text-foreground">
                  {{ formattedBookingDate }}
                </span>
              </div>

              <!-- Value Date (only shown if different from booking date) -->
              <div
                v-if="formattedValueDate"
                class="flex justify-between px-4 py-3"
              >
                <span class="text-sm text-muted">Value Date</span>
                <span class="text-sm font-medium text-foreground">
                  {{ formattedValueDate }}
                </span>
              </div>

              <!-- Amount -->
              <div class="flex justify-between px-4 py-3">
                <span class="text-sm text-muted">Amount</span>
                <span class="text-sm font-medium" :class="amountColorClass">
                  {{ formattedAmount }}
                </span>
              </div>

              <!-- Account -->
              <div class="flex justify-between px-4 py-3">
                <span class="text-sm text-muted">Account</span>
                <span class="text-sm font-medium text-foreground">
                  {{ accountName }}
                </span>
              </div>

              <!-- Full Description (if different from merchant name) -->
              <div
                v-if="transaction.merchant_name && transaction.description"
                class="px-4 py-3"
              >
                <span class="mb-1 block text-sm text-muted">Description</span>
                <span class="block text-sm text-foreground">
                  {{ transaction.description }}
                </span>
              </div>
            </div>

            <!-- Tag(s) / Splits section (always shows split editor) -->
            <div class="tag-selector-container relative">
              <span class="mb-2 block text-sm text-muted">Tag(s)</span>

              <!-- Auto-tag indicator (shown above editor if applicable) -->
              <div
                v-if="singleTag?.is_auto"
                class="mb-3 rounded-lg bg-onyx px-3 py-2 text-xs text-muted"
              >
                Auto-tagged by
                <NuxtLink
                  v-if="singleTag.rule_id"
                  to="/settings/rules"
                  class="text-primary hover:underline"
                  @click="handleClose"
                >
                  {{ singleTag.rule_name || 'rule' }}
                </NuxtLink>
                <span v-else>rule</span>
              </div>

              <!-- Split editor (always visible) -->
              <div class="space-y-3">
                <!-- Split rows -->
                <div class="space-y-3">
                  <div
                    v-for="(split, index) in editedSplits"
                    :key="index"
                    class="rounded-lg border border-border p-3"
                    :style="{
                      borderLeftWidth: '4px',
                      borderLeftColor: getTagColour(split.tag_id),
                    }"
                  >
                    <!-- Row 1: Tag selector + remove button -->
                    <div class="mb-3 flex items-center gap-2">
                      <div class="flex-1">
                        <AppSelect
                          v-model="split.tag_id"
                          :options="getTagOptionsForSplit(split.tag_id)"
                          placeholder="Select tag..."
                        />
                      </div>
                      <button
                        type="button"
                        class="rounded p-1.5 text-muted hover:bg-border hover:text-foreground"
                        @click="removeSplit(index)"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                          class="h-4 w-4"
                        >
                          <path
                            d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
                          />
                        </svg>
                      </button>
                    </div>

                    <!-- Row 2: Percentage slider + editable inputs -->
                    <div class="flex items-center gap-3">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="5"
                        :value="getSplitPercentage(split.amount)"
                        class="split-slider flex-1"
                        @input="
                          updateSplitFromPercentage(
                            index,
                            Number(($event.target as HTMLInputElement).value),
                          )
                        "
                      />
                      <div class="flex items-center gap-1">
                        <input
                          type="number"
                          min="0"
                          max="100"
                          :value="getSplitPercentage(split.amount)"
                          class="percent-input"
                          @change="
                            updateSplitFromPercentage(
                              index,
                              Math.min(
                                100,
                                Math.max(
                                  0,
                                  Number(
                                    ($event.target as HTMLInputElement).value,
                                  ),
                                ),
                              ),
                            )
                          "
                        />
                        <span class="text-sm text-muted">%</span>
                      </div>
                      <span
                        class="w-20 text-right text-sm font-medium text-foreground"
                      >
                        {{ currencySymbol }}{{ split.amount.toFixed(2) }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Add split button -->
                <button
                  type="button"
                  class="flex w-full items-center justify-center gap-1 rounded-lg border border-dashed border-gray-600 py-2 text-sm text-muted hover:border-primary hover:text-primary"
                  @click="addSplit"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    class="h-4 w-4"
                  >
                    <path
                      d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
                    />
                  </svg>
                  Add split
                </button>

                <!-- Remaining amount -->
                <div class="flex justify-between text-sm">
                  <span class="text-muted">Remaining:</span>
                  <span
                    :class="
                      remainingAmount === 0 ? 'text-positive' : 'text-negative'
                    "
                  >
                    {{ formatCurrency(remainingAmount, transaction.currency) }}
                  </span>
                </div>

                <!-- Actions -->
                <div class="flex gap-2">
                  <button
                    type="button"
                    class="flex-1 rounded-lg border border-border px-3 py-2 text-sm text-muted hover:bg-border"
                    @click="initializeSplits"
                  >
                    Reset
                  </button>
                  <button
                    v-if="hasSplits"
                    type="button"
                    class="rounded-lg border border-negative px-3 py-2 text-sm text-negative hover:bg-negative/10"
                    @click="handleClearSplits"
                  >
                    Clear
                  </button>
                  <button
                    type="button"
                    class="flex-1 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                    :disabled="!splitsValid"
                    @click="saveSplits"
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>

            <!-- Note section -->
            <div class="mt-6">
              <div class="mb-2 flex items-center justify-between">
                <span class="text-sm text-muted">Note</span>
                <button
                  v-if="!isEditingNote"
                  type="button"
                  class="text-xs text-primary hover:underline"
                  @click="startEditingNote"
                >
                  {{ transaction.user_note ? 'Edit' : 'Add' }}
                </button>
              </div>

              <!-- View mode -->
              <p
                v-if="!isEditingNote && transaction.user_note"
                class="text-sm text-foreground"
              >
                {{ transaction.user_note }}
              </p>
              <p v-else-if="!isEditingNote" class="text-sm italic text-muted">
                No note
              </p>

              <!-- Edit mode -->
              <div v-if="isEditingNote" class="space-y-2">
                <textarea
                  v-model="editedNote"
                  rows="3"
                  maxlength="512"
                  class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted"
                  placeholder="Add a note about this transaction..."
                />
                <div class="flex gap-2">
                  <button
                    type="button"
                    class="flex-1 rounded-lg border border-border px-3 py-2 text-sm text-muted hover:bg-border"
                    @click="cancelEditingNote"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    class="flex-1 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white"
                    @click="saveNote"
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* Fade transition for modal backdrop */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Tag with auto-tag info */
.tag-with-info {
  @apply flex flex-col items-start gap-0.5;
}

.auto-tag-indicator {
  @apply text-xs text-muted;
}

.rule-link {
  @apply text-primary hover:underline;
}

/* Split percentage slider */
.split-slider {
  @apply h-2 cursor-pointer appearance-none rounded-full bg-gray-700;
}

.split-slider::-webkit-slider-thumb {
  @apply h-4 w-4 cursor-pointer appearance-none rounded-full bg-primary;
  @apply transition-transform hover:scale-110;
}

.split-slider::-moz-range-thumb {
  @apply h-4 w-4 cursor-pointer appearance-none rounded-full border-0 bg-primary;
  @apply transition-transform hover:scale-110;
}

.split-slider:focus {
  @apply outline-none;
}

.split-slider:focus::-webkit-slider-thumb {
  @apply ring-2 ring-primary/50;
}

/* Editable percentage input */
.percent-input {
  @apply w-12 rounded border border-border bg-surface px-1 py-0.5;
  @apply text-right text-sm text-foreground;
  @apply focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/50;
  /* Hide number spinners */
  -moz-appearance: textfield;
}

.percent-input::-webkit-outer-spin-button,
.percent-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
