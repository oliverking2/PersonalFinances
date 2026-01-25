<!-- ==========================================================================
AccountSettingsModal
Modal for editing account settings: display name, category, min balance
Shows last synced date as read-only information
============================================================================ -->

<script setup lang="ts">
import type { Account, AccountCategory } from '~/types/accounts'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
  account: Account
}>()

const emit = defineEmits<{
  close: []
  save: [
    id: string,
    settings: {
      display_name: string | null
      category: AccountCategory | null
      min_balance: number | null
      credit_limit: number | null
    },
  ]
}>()

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// Category options with human-readable labels
const categoryOptions: { value: AccountCategory; label: string }[] = [
  { value: 'bank_account', label: 'Savings Account' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'debit_card', label: 'Debit Card' },
  { value: 'investment_account', label: 'Investment Account' },
]

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const displayName = ref('')
const category = ref<AccountCategory | ''>('')
const saving = ref(false)
const error = ref('')

const minBalanceField = useMoneyField({ allowNegative: true })
const creditLimitField = useMoneyField({ allowNegative: false })

// Reset state when modal opens or account changes
// immediate: true ensures this runs when the component mounts (since it's conditionally rendered)
watch(
  () => props.show,
  (isOpen) => {
    if (isOpen) {
      displayName.value = props.account.display_name || ''
      category.value = props.account.category || ''
      minBalanceField.value.value =
        props.account.min_balance !== null
          ? String(props.account.min_balance)
          : ''
      creditLimitField.value.value =
        props.account.credit_limit !== null
          ? String(props.account.credit_limit)
          : ''
      error.value = ''
    }
  },
  { immediate: true },
)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Format the last synced date for display
const formattedLastSyncDate = computed(() => {
  if (!props.account.last_synced_at) return 'Never'

  const date = new Date(props.account.last_synced_at)
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
})

// Check if any values have changed from the original
const hasChanges = computed(() => {
  const originalDisplayName = props.account.display_name || ''
  const originalCategory = props.account.category || ''
  const originalMinBalance =
    props.account.min_balance !== null ? String(props.account.min_balance) : ''
  const originalCreditLimit =
    props.account.credit_limit !== null
      ? String(props.account.credit_limit)
      : ''

  return (
    displayName.value !== originalDisplayName ||
    category.value !== originalCategory ||
    minBalanceField.value.value !== originalMinBalance ||
    creditLimitField.value.value !== originalCreditLimit
  )
})

// Check if current category is credit card (to show credit limit field)
const isCreditCard = computed(() => category.value === 'credit_card')

// Validate min balance is a valid number if provided
const isValidMinBalance = minBalanceField.isValid

// Validate credit limit is a valid number if provided
const isValidCreditLimit = creditLimitField.isValid

// Overall form validity
const isValid = computed(() => {
  return hasChanges.value && isValidMinBalance.value && isValidCreditLimit.value
})

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function handleClose() {
  if (!saving.value) {
    emit('close')
  }
}

async function handleSave() {
  if (!isValid.value || saving.value) return

  saving.value = true
  error.value = ''

  try {
    // Build settings object - convert empty strings to null
    const settings = {
      display_name: displayName.value.trim() || null,
      category: (category.value as AccountCategory) || null,
      min_balance: minBalanceField.value.value
        ? parseFloat(minBalanceField.value.value)
        : null,
      credit_limit: creditLimitField.value.value
        ? parseFloat(creditLimitField.value.value)
        : null,
    }

    emit('save', props.account.id, settings)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to save'
    saving.value = false
  }
}

function useMoneyField(options: { allowNegative: boolean }) {
  const value = ref('')

  function sanitise(v: unknown): void {
    const s = String(v ?? '').replace(/[£,\s]/g, '')
    value.value = s
      .replace(options.allowNegative ? /[^\d.-]/g : /[^\d.]/g, '')
      .replace(/(?!^)-/g, '')
      .replace(/(\..*)\./g, '$1')
  }

  const isValid = computed(() => {
    if (value.value === '') return true
    const n = Number.parseFloat(value.value)
    if (!Number.isFinite(n)) return false
    return !(!options.allowNegative && n < 0)
  })

  return { value, sanitise, isValid }
}

// Clear min balance field
function clearMinBalance() {
  minBalanceField.value.value = ''
}

// Clear credit limit field
function clearCreditLimit() {
  creditLimitField.value.value = ''
}
</script>

<template>
  <!-- Modal backdrop -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="show"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        @click.self="handleClose"
      >
        <!-- Modal content -->
        <div
          class="w-full max-w-md rounded-lg border border-border bg-surface p-6"
        >
          <!-- Header -->
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-foreground">
              Account Settings
            </h2>
            <button
              type="button"
              class="rounded p-1 text-muted transition-colors hover:bg-border hover:text-foreground"
              :disabled="saving"
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

          <!-- Form -->
          <form @submit.prevent="handleSave">
            <!-- Display Name input -->
            <div class="mb-4">
              <label
                for="display-name"
                class="mb-2 block text-sm font-medium text-muted"
              >
                Display Name
              </label>
              <AppInput
                id="display-name"
                v-model="displayName"
                placeholder="Enter display name"
              />
              <p class="mt-1 text-xs text-muted">
                Leave blank to use the provider name
              </p>
            </div>

            <!-- Category dropdown -->
            <div class="mb-4">
              <label
                for="category"
                class="mb-2 block text-sm font-medium text-muted"
              >
                Account Category
              </label>
              <AppSelect
                id="category"
                v-model="category"
                :options="categoryOptions"
                placeholder="Select a category..."
              />
            </div>

            <!-- Credit Limit input (only for credit cards) -->
            <div v-if="isCreditCard" class="mb-4">
              <label
                for="credit-limit"
                class="mb-2 block text-sm font-medium text-muted"
              >
                Credit Limit (non-negative)
              </label>
              <div class="relative">
                <AppInput
                  id="credit-limit"
                  :model-value="creditLimitField.value.value"
                  type="number"
                  step="0.01"
                  placeholder="e.g. 5000.00"
                  prefix="£"
                  :class="{ 'pr-8': creditLimitField.value.value }"
                  @update:model-value="creditLimitField.sanitise"
                />
                <!-- Clear button (shown when there's a value) -->
                <button
                  v-if="creditLimitField.value.value"
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted transition-colors hover:text-foreground"
                  title="Clear"
                  @click="clearCreditLimit"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    class="h-4 w-4"
                  >
                    <path
                      d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
                    />
                  </svg>
                </button>
              </div>
              <p
                v-if="creditLimitField.value.value && !isValidCreditLimit"
                class="mt-1 text-xs text-negative"
              >
                Please enter a valid positive number
              </p>
            </div>

            <!-- Min Balance input -->
            <div class="mb-4">
              <label
                for="min-balance"
                class="mb-2 block text-sm font-medium text-muted"
              >
                Minimum Balance Threshold
              </label>
              <div class="relative">
                <AppInput
                  id="min-balance"
                  :model-value="minBalanceField.value.value"
                  type="number"
                  step="0.01"
                  placeholder="e.g. 500.00"
                  prefix="£"
                  :class="{ 'pr-8': minBalanceField.value.value }"
                  @update:model-value="minBalanceField.sanitise"
                />
                <!-- Clear button (shown when there's a value) -->
                <button
                  v-if="minBalanceField.value.value"
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted transition-colors hover:text-foreground"
                  title="Clear"
                  @click="clearMinBalance"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    class="h-4 w-4"
                  >
                    <path
                      d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
                    />
                  </svg>
                </button>
              </div>
              <p class="mt-1 text-xs text-muted">
                Get notified when balance falls below this amount (coming soon)
              </p>
              <p
                v-if="minBalanceField.value.value && !isValidMinBalance"
                class="mt-1 text-xs text-negative"
              >
                Please enter a valid number
              </p>
            </div>

            <!-- Last Synced (read-only) -->
            <div class="mb-6 rounded-lg bg-onyx/50 px-4 py-3">
              <div class="flex items-center justify-between">
                <span class="text-sm text-muted">Last Synced</span>
                <span class="text-sm font-medium text-foreground">
                  {{ formattedLastSyncDate }}
                </span>
              </div>
            </div>

            <!-- Error message -->
            <p v-if="error" class="mb-4 text-sm text-negative">
              {{ error }}
            </p>

            <!-- Actions -->
            <div class="flex justify-end gap-3">
              <button
                type="button"
                class="rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted transition-colors hover:bg-border hover:text-foreground"
                :disabled="saving"
                @click="handleClose"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!isValid || saving"
              >
                {{ saving ? 'Saving...' : 'Save Changes' }}
              </button>
            </div>
          </form>
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
