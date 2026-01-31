<!-- ==========================================================================
RecurringPatternCreateModal
Modal for manually creating a new recurring pattern
============================================================================ -->

<script setup lang="ts">
import type {
  RecurringFrequency,
  RecurringDirection,
  RecurringPatternCreateRequest,
} from '~/types/recurring'

// Props
defineProps<{
  open: boolean
}>()

// Emits
const emit = defineEmits<{
  close: []
  create: [request: RecurringPatternCreateRequest]
}>()

// ---------------------------------------------------------------------------
// Form State
// ---------------------------------------------------------------------------

const name = ref('')
const expectedAmountStr = ref('')
const frequency = ref<RecurringFrequency>('monthly')
const direction = ref<RecurringDirection>('expense')
const merchantContains = ref('')
const notes = ref('')
const saving = ref(false)

// Frequency options for the dropdown
const frequencyOptions = [
  { value: 'weekly', label: 'Weekly' },
  { value: 'fortnightly', label: 'Fortnightly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'annual', label: 'Annual' },
]

// ---------------------------------------------------------------------------
// Form Validation
// ---------------------------------------------------------------------------

const isValid = computed(() => {
  const amount = parseFloat(expectedAmountStr.value)
  return name.value.trim().length > 0 && amount > 0
})

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

function resetForm() {
  name.value = ''
  expectedAmountStr.value = ''
  frequency.value = 'monthly'
  direction.value = 'expense'
  merchantContains.value = ''
  notes.value = ''
  saving.value = false
}

function handleClose() {
  resetForm()
  emit('close')
}

function handleCreate() {
  if (!isValid.value) return

  saving.value = true

  const request: RecurringPatternCreateRequest = {
    name: name.value.trim(),
    expected_amount: parseFloat(expectedAmountStr.value),
    frequency: frequency.value,
    direction: direction.value,
  }

  // Only include optional fields if they have values
  if (merchantContains.value.trim()) {
    request.merchant_contains = merchantContains.value.trim()
  }
  if (notes.value.trim()) {
    request.notes = notes.value.trim()
  }

  emit('create', request)
  // Parent will call handleClose after successful creation
}

// Reset form when modal closes
watch(
  () => open,
  (isOpen) => {
    if (!isOpen) {
      resetForm()
    }
  },
)
</script>

<template>
  <!-- Modal backdrop -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        @click.self="handleClose"
      >
        <!-- Modal content -->
        <div
          class="flex max-h-[85vh] w-full max-w-lg flex-col rounded-lg border border-border bg-surface shadow-xl"
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between border-b border-border px-6 py-4"
          >
            <h2 class="text-lg font-semibold">Create Pattern</h2>
            <button
              type="button"
              class="text-muted hover:text-foreground"
              @click="handleClose"
            >
              <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
                />
              </svg>
            </button>
          </div>

          <!-- Body - scrollable -->
          <div class="flex-1 overflow-y-auto p-6">
            <div class="space-y-4">
              <!-- Name field (required) -->
              <div>
                <label class="mb-1 block text-sm font-medium">Name *</label>
                <AppInput
                  v-model="name"
                  placeholder="e.g., Netflix, Spotify, Rent"
                />
              </div>

              <!-- Expected amount (required) -->
              <div>
                <label class="mb-1 block text-sm font-medium"
                  >Expected Amount *</label
                >
                <div class="flex items-center gap-2">
                  <span class="text-muted">£</span>
                  <AppInput
                    v-model="expectedAmountStr"
                    type="number"
                    class="flex-1"
                    placeholder="0.00"
                  />
                </div>
              </div>

              <!-- Frequency dropdown -->
              <div>
                <label class="mb-1 block text-sm font-medium">Frequency</label>
                <AppSelect
                  v-model="frequency"
                  :options="frequencyOptions"
                  placeholder="Select frequency"
                />
              </div>

              <!-- Direction toggle (expense/income) -->
              <div>
                <label class="mb-1 block text-sm font-medium">Type</label>
                <div class="flex rounded-lg border border-border bg-onyx p-1">
                  <button
                    type="button"
                    class="flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors"
                    :class="
                      direction === 'expense'
                        ? 'bg-red-500/20 text-red-400'
                        : 'text-muted hover:text-foreground'
                    "
                    @click="direction = 'expense'"
                  >
                    Expense
                  </button>
                  <button
                    type="button"
                    class="flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors"
                    :class="
                      direction === 'income'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'text-muted hover:text-foreground'
                    "
                    @click="direction = 'income'"
                  >
                    Income
                  </button>
                </div>
              </div>

              <!-- Merchant contains (optional) -->
              <div>
                <label class="mb-1 block text-sm font-medium"
                  >Merchant Contains</label
                >
                <AppInput
                  v-model="merchantContains"
                  placeholder="e.g., netflix, spotify"
                />
                <p class="mt-1 text-xs text-muted">
                  Text to match in transaction merchant name (optional, case
                  insensitive)
                </p>
              </div>

              <!-- Notes (optional) -->
              <div>
                <label class="mb-1 block text-sm font-medium">Notes</label>
                <textarea
                  v-model="notes"
                  rows="2"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Add any notes..."
                />
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="flex items-center justify-end gap-3 border-t border-border px-6 py-4"
          >
            <button
              type="button"
              class="rounded-lg bg-gray-700/50 px-4 py-2 text-sm font-medium text-gray-300 transition-colors hover:bg-gray-700"
              @click="handleClose"
            >
              Cancel
            </button>
            <button
              type="button"
              :disabled="!isValid || saving"
              class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
              @click="handleCreate"
            >
              {{ saving ? 'Creating...' : 'Create Pattern' }}
            </button>
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
