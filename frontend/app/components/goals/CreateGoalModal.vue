<!-- ==========================================================================
CreateGoalModal
Modal dialog for creating or editing a savings goal
============================================================================ -->

<script setup lang="ts">
import type {
  Goal,
  GoalCreateRequest,
  GoalTrackingMode,
  GoalUpdateRequest,
} from '~/types/goals'
import {
  getTrackingModeLabel,
  getTrackingModeDescription,
  requiresAccount,
} from '~/types/goals'

// Props
const props = defineProps<{
  isOpen: boolean
  existingGoal?: Goal // If provided, we're editing
  availableAccounts?: Array<{ id: string; name: string }> // Optional accounts to link
}>()

// Emits
const emit = defineEmits<{
  close: []
  create: [req: GoalCreateRequest]
  update: [id: string, req: GoalUpdateRequest]
}>()

// Form state
const name = ref('')
const targetAmount = ref(0)
const currentAmount = ref(0)
const deadline = ref('') // YYYY-MM-DD
const accountId = ref('')
const trackingMode = ref<GoalTrackingMode>('manual')
const targetBalance = ref(0)
const notes = ref('')

// Is editing mode
const isEditing = computed(() => !!props.existingGoal)

// Tracking mode options for the select dropdown
const trackingModeOptions = [
  { value: 'manual', label: getTrackingModeLabel('manual') },
  { value: 'balance', label: getTrackingModeLabel('balance') },
  { value: 'delta', label: getTrackingModeLabel('delta') },
  { value: 'target_balance', label: getTrackingModeLabel('target_balance') },
]

// Account options for the select dropdown
const accountOptions = computed(() => {
  const options =
    props.availableAccounts?.map((a) => ({
      value: a.id,
      label: a.name,
    })) ?? []

  // Add "no account" option if account is not required
  if (!accountRequired.value) {
    return [{ value: '', label: "Don't link to an account" }, ...options]
  }
  return options
})

// Show/hide fields based on tracking mode
const showCurrentAmount = computed(() => trackingMode.value === 'manual')
const showAccountSelector = computed(() => requiresAccount(trackingMode.value))
const showTargetBalance = computed(
  () => trackingMode.value === 'target_balance',
)
// Hide Target Amount for target_balance mode (target_balance field serves that purpose)
const showTargetAmount = computed(() => trackingMode.value !== 'target_balance')
const accountRequired = computed(() => requiresAccount(trackingMode.value))

// Get description for currently selected tracking mode
const trackingModeHelp = computed(() =>
  getTrackingModeDescription(trackingMode.value),
)

// Modal title
const modalTitle = computed(() =>
  isEditing.value ? 'Edit Goal' : 'Create Goal',
)

// Reset form when modal opens
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      if (props.existingGoal) {
        // Editing: populate form with existing values
        name.value = props.existingGoal.name
        targetAmount.value = props.existingGoal.target_amount
        currentAmount.value = props.existingGoal.current_amount
        deadline.value = props.existingGoal.deadline
          ? (props.existingGoal.deadline.split('T')[0] ?? '') // Extract YYYY-MM-DD
          : ''
        accountId.value = props.existingGoal.account_id ?? ''
        trackingMode.value = props.existingGoal.tracking_mode ?? 'manual'
        targetBalance.value = props.existingGoal.target_balance ?? 0
        notes.value = props.existingGoal.notes ?? ''
      } else {
        // Creating: reset to defaults
        name.value = ''
        targetAmount.value = 0
        currentAmount.value = 0
        deadline.value = ''
        accountId.value = ''
        trackingMode.value = 'manual'
        targetBalance.value = 0
        notes.value = ''
      }
    }
  },
)

// Auto-select first account when switching to a mode that requires an account
watch(trackingMode, (newMode) => {
  if (
    requiresAccount(newMode) &&
    !accountId.value &&
    props.availableAccounts?.length
  ) {
    accountId.value = props.availableAccounts[0]?.id ?? ''
  }
})

// Handle form submission
function handleSubmit() {
  if (isEditing.value && props.existingGoal) {
    const req: GoalUpdateRequest = {
      name: name.value,
      target_amount: targetAmount.value,
      current_amount: currentAmount.value,
    }

    // Handle deadline (clear if empty, set if provided)
    if (!deadline.value && props.existingGoal.deadline) {
      req.clear_deadline = true
    } else if (deadline.value) {
      req.deadline = deadline.value
    }

    // Handle account (clear if empty, set if provided)
    if (!accountId.value && props.existingGoal.account_id) {
      req.clear_account = true
    } else if (accountId.value) {
      req.account_id = accountId.value
    }

    // Handle notes (clear if empty, set if provided)
    if (!notes.value && props.existingGoal.notes) {
      req.clear_notes = true
    } else if (notes.value) {
      req.notes = notes.value
    }

    emit('update', props.existingGoal.id, req)
  } else {
    const req: GoalCreateRequest = {
      name: name.value,
      // For target_balance mode, use target_balance as target_amount
      target_amount:
        trackingMode.value === 'target_balance'
          ? targetBalance.value
          : targetAmount.value,
      tracking_mode: trackingMode.value,
    }

    // Only include current_amount for manual mode
    if (trackingMode.value === 'manual' && currentAmount.value > 0) {
      req.current_amount = currentAmount.value
    }

    // Include account for modes that require it
    if (accountId.value) req.account_id = accountId.value

    // Include target_balance for target_balance mode
    if (trackingMode.value === 'target_balance' && targetBalance.value > 0) {
      req.target_balance = targetBalance.value
    }

    if (deadline.value) req.deadline = deadline.value
    if (notes.value) req.notes = notes.value

    emit('create', req)
  }
}

// Validation
const isValid = computed(() => {
  if (!name.value.trim()) return false

  // target_balance mode uses targetBalance instead of targetAmount
  if (trackingMode.value === 'target_balance') {
    if (targetBalance.value <= 0) return false
  } else {
    if (targetAmount.value <= 0) return false
  }

  if (trackingMode.value === 'manual' && currentAmount.value < 0) return false

  // Non-manual modes require an account
  if (requiresAccount(trackingMode.value) && !accountId.value) return false

  return true
})
</script>

<template>
  <!-- Modal backdrop -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-200"
      leave-to-class="opacity-0"
    >
      <div v-if="isOpen" class="modal-backdrop" @click.self="emit('close')">
        <!-- Modal content -->
        <div class="modal-content">
          <!-- Header -->
          <div
            class="flex items-center justify-between border-b border-border pb-4"
          >
            <h2 class="text-xl font-semibold">{{ modalTitle }}</h2>
            <button
              type="button"
              class="rounded-lg p-1 text-muted hover:bg-gray-700/50 hover:text-foreground"
              @click="emit('close')"
            >
              <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
                />
              </svg>
            </button>
          </div>

          <!-- Form -->
          <form class="mt-4 space-y-4" @submit.prevent="handleSubmit">
            <!-- Name -->
            <div>
              <label class="block text-sm font-medium text-muted"
                >Goal Name</label
              >
              <input
                v-model="name"
                type="text"
                maxlength="100"
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="e.g. Emergency Fund"
              />
            </div>

            <!-- Tracking mode (only show when creating, not editing) -->
            <div v-if="!isEditing">
              <label class="block text-sm font-medium text-muted"
                >Tracking Mode</label
              >
              <AppSelect
                v-model="trackingMode"
                :options="trackingModeOptions"
                class="mt-1"
              />
              <p class="mt-1 text-xs text-muted">
                {{ trackingModeHelp }}
              </p>
            </div>

            <!-- Account selector (required for non-manual modes) -->
            <div
              v-if="
                showAccountSelector &&
                availableAccounts &&
                availableAccounts.length > 0
              "
            >
              <label class="block text-sm font-medium text-muted">
                Linked Account
                <span v-if="accountRequired" class="text-red-400">*</span>
              </label>
              <AppSelect
                v-model="accountId"
                :options="accountOptions"
                :placeholder="accountRequired ? 'Select an account' : undefined"
                class="mt-1"
              />
              <p class="mt-1 text-xs text-muted">
                Account balance will be used to track progress
              </p>
            </div>

            <!-- Warning if no accounts available but mode requires one -->
            <div
              v-if="
                showAccountSelector &&
                (!availableAccounts || availableAccounts.length === 0)
              "
              class="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-400"
            >
              This tracking mode requires a linked account. Please connect a
              bank account first.
            </div>

            <!-- Target amount (hidden for target_balance mode) -->
            <div v-if="showTargetAmount">
              <label class="block text-sm font-medium text-muted"
                >Target Amount</label
              >
              <div class="relative mt-1">
                <span
                  class="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                  >£</span
                >
                <input
                  v-model.number="targetAmount"
                  type="number"
                  min="0"
                  step="100"
                  class="w-full rounded-lg border border-border bg-background py-2 pl-8 pr-3 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="0"
                />
              </div>
            </div>

            <!-- Target balance (for target_balance mode) -->
            <div v-if="showTargetBalance">
              <label class="block text-sm font-medium text-muted">
                Target Account Balance
                <span class="text-red-400">*</span>
              </label>
              <div class="relative mt-1">
                <span
                  class="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                  >£</span
                >
                <input
                  v-model.number="targetBalance"
                  type="number"
                  min="0"
                  step="100"
                  class="w-full rounded-lg border border-border bg-background py-2 pl-8 pr-3 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="0"
                />
              </div>
              <p class="mt-1 text-xs text-muted">
                Goal completes when account balance reaches this amount
              </p>
            </div>

            <!-- Current amount (only for manual mode) -->
            <div v-if="showCurrentAmount">
              <label class="block text-sm font-medium text-muted"
                >Current Saved</label
              >
              <div class="relative mt-1">
                <span
                  class="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                  >£</span
                >
                <input
                  v-model.number="currentAmount"
                  type="number"
                  min="0"
                  step="10"
                  class="w-full rounded-lg border border-border bg-background py-2 pl-8 pr-3 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="0"
                />
              </div>
              <p class="mt-1 text-xs text-muted">
                How much you've already saved towards this goal
              </p>
            </div>

            <!-- Deadline -->
            <div>
              <label class="block text-sm font-medium text-muted"
                >Target Date (optional)</label
              >
              <input
                v-model="deadline"
                type="date"
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <!-- Notes -->
            <div>
              <label class="block text-sm font-medium text-muted"
                >Notes (optional)</label
              >
              <textarea
                v-model="notes"
                rows="2"
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="Add any notes about this goal..."
              />
            </div>

            <!-- Actions -->
            <div class="flex justify-end gap-2 pt-4">
              <button
                type="button"
                class="rounded-lg bg-gray-700/50 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700"
                @click="emit('close')"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="!isValid"
                class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
              >
                {{ isEditing ? 'Save Changes' : 'Create Goal' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  @apply fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4;
}

.modal-content {
  @apply flex max-h-[80vh] w-full max-w-md flex-col rounded-xl border border-border bg-surface p-6 shadow-xl;
  /* Allow form to scroll if content overflows */
  & form {
    @apply overflow-y-auto;
  }
}
</style>
