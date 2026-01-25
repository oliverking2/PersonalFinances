<!-- ==========================================================================
TransactionDetailModal
Modal showing full transaction details with tag management
Opens from the "details" button on TransactionRow
============================================================================ -->

<script setup lang="ts">
import type { Transaction } from '~/types/transactions'
import type { Tag } from '~/types/tags'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
  transaction: Transaction | null
  accountName: string // Display name of the account this transaction belongs to
  availableTags: Tag[] // All user's tags for the selector
}>()

const emit = defineEmits<{
  close: []
  'add-tag': [transactionId: string, tagId: string]
  'remove-tag': [transactionId: string, tagId: string]
  'create-tag': [transactionId: string, name: string]
}>()

// ---------------------------------------------------------------------------
// Local State
// ---------------------------------------------------------------------------

const showTagSelector = ref(false)

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

// Get tag IDs for selector
const selectedTagIds = computed(() => {
  return props.transaction?.tags?.map((t) => t.id) || []
})

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function handleClose() {
  showTagSelector.value = false
  emit('close')
}

function toggleTagSelector(event: MouseEvent) {
  event.stopPropagation()
  showTagSelector.value = !showTagSelector.value
}

function handleTagSelect(tagId: string) {
  if (props.transaction) {
    emit('add-tag', props.transaction.id, tagId)
  }
  showTagSelector.value = false // Close after selecting (single tag only)
}

function handleTagDeselect(tagId: string) {
  if (props.transaction) {
    emit('remove-tag', props.transaction.id, tagId)
  }
}

function handleTagCreate(name: string) {
  if (props.transaction) {
    emit('create-tag', props.transaction.id, name)
  }
  showTagSelector.value = false
}

function handleRemoveTag(tagId: string) {
  if (props.transaction) {
    emit('remove-tag', props.transaction.id, tagId)
  }
}

// Close selector when clicking outside
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.tag-selector-container')) {
    showTagSelector.value = false
  }
}

// Set up click outside listener when modal is shown
watch(
  () => props.show,
  (isOpen) => {
    if (isOpen) {
      document.addEventListener('click', handleClickOutside)
    } else {
      document.removeEventListener('click', handleClickOutside)
      showTagSelector.value = false
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
        <!-- Modal content -->
        <div
          class="w-full max-w-md rounded-lg border border-border bg-surface p-6"
        >
          <!-- Header -->
          <div class="mb-4 flex items-start justify-between gap-4">
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

          <!-- Tags section -->
          <div class="tag-selector-container relative">
            <span class="mb-2 block text-sm text-muted">Tags</span>
            <div class="flex flex-wrap items-center gap-2">
              <!-- Existing tags -->
              <TagsTagChip
                v-for="tag in transaction.tags"
                :key="tag.id"
                :name="tag.name"
                :colour="tag.colour"
                removable
                @remove="handleRemoveTag(tag.id)"
              />

              <!-- Add tag button (only show if no tag yet - single tag only) -->
              <button
                v-if="!transaction.tags || transaction.tags.length === 0"
                type="button"
                class="flex items-center gap-1 rounded-full border border-dashed border-gray-600 px-3 py-1 text-sm text-muted transition-colors hover:border-primary hover:text-primary"
                @click="toggleTagSelector"
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
                Add tag
              </button>

              <!-- Tag selector popover -->
              <div
                v-if="showTagSelector && availableTags"
                class="absolute left-0 top-full z-10 mt-1"
                @click.stop
              >
                <TagsTagSelector
                  :available-tags="availableTags"
                  :selected-tag-ids="selectedTagIds"
                  @select="handleTagSelect"
                  @deselect="handleTagDeselect"
                  @create="handleTagCreate"
                />
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
</style>
