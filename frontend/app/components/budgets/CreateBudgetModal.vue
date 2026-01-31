<!-- ==========================================================================
CreateBudgetModal
Modal dialog for creating or editing a budget
============================================================================ -->

<script setup lang="ts">
import type {
  Budget,
  BudgetCreateRequest,
  BudgetUpdateRequest,
} from '~/types/budgets'

// Props
const props = defineProps<{
  isOpen: boolean
  existingBudget?: Budget // If provided, we're editing
  availableTags: Array<{ id: string; name: string; colour: string }>
}>()

// Emits
const emit = defineEmits<{
  close: []
  create: [req: BudgetCreateRequest]
  update: [id: string, req: BudgetUpdateRequest]
}>()

// Form state
const selectedTagId = ref('')
const amount = ref(0)
const warningThreshold = ref(80) // As percentage (80 = 0.80)
const enabled = ref(true)

// Is editing mode
const isEditing = computed(() => !!props.existingBudget)

// Modal title
const modalTitle = computed(() =>
  isEditing.value ? 'Edit Budget' : 'Create Budget',
)

// Reset form when modal opens
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      if (props.existingBudget) {
        // Editing: populate form with existing values
        selectedTagId.value = props.existingBudget.tag_id
        amount.value = props.existingBudget.amount
        warningThreshold.value = props.existingBudget.warning_threshold * 100
        enabled.value = props.existingBudget.enabled
      } else {
        // Creating: reset to defaults
        selectedTagId.value = props.availableTags[0]?.id ?? ''
        amount.value = 0
        warningThreshold.value = 80
        enabled.value = true
      }
    }
  },
)

// Handle form submission
function handleSubmit() {
  if (isEditing.value && props.existingBudget) {
    emit('update', props.existingBudget.id, {
      amount: amount.value,
      warning_threshold: warningThreshold.value / 100,
      enabled: enabled.value,
    })
  } else {
    emit('create', {
      tag_id: selectedTagId.value,
      amount: amount.value,
      warning_threshold: warningThreshold.value / 100,
    })
  }
}

// Validation
const isValid = computed(() => {
  if (!isEditing.value && !selectedTagId.value) return false
  if (amount.value <= 0) return false
  if (warningThreshold.value < 0 || warningThreshold.value > 100) return false
  return true
})

// Transform tags to AppSelect options format
const tagOptions = computed(() =>
  props.availableTags.map((tag) => ({
    value: tag.id,
    label: tag.name,
  })),
)
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
            <!-- Tag selector (only for new budgets) -->
            <div v-if="!isEditing">
              <label class="mb-1 block text-sm font-medium text-muted"
                >Category</label
              >
              <AppSelect
                v-model="selectedTagId"
                :options="tagOptions"
                placeholder="Select a category..."
              />
            </div>

            <!-- Tag display (for editing) -->
            <div v-else>
              <label class="block text-sm font-medium text-muted"
                >Category</label
              >
              <div class="mt-1 flex items-center gap-2">
                <span
                  class="h-3 w-3 rounded-full"
                  :style="{ backgroundColor: existingBudget?.tag_colour }"
                />
                <span class="text-foreground">{{
                  existingBudget?.tag_name
                }}</span>
              </div>
            </div>

            <!-- Amount -->
            <div>
              <label class="block text-sm font-medium text-muted"
                >Monthly Budget</label
              >
              <div class="relative mt-1">
                <span
                  class="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                  >£</span
                >
                <input
                  v-model.number="amount"
                  type="number"
                  min="0"
                  step="10"
                  class="w-full rounded-lg border border-border bg-background py-2 pl-8 pr-3 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="0"
                />
              </div>
            </div>

            <!-- Warning threshold -->
            <div>
              <label class="block text-sm font-medium text-muted"
                >Warning at ({{ warningThreshold }}%)</label
              >
              <input
                v-model.number="warningThreshold"
                type="range"
                min="50"
                max="95"
                step="5"
                class="mt-2 w-full"
              />
              <p class="mt-1 text-xs text-muted">
                You'll be warned when spending reaches {{ warningThreshold }}%
                of the budget
              </p>
            </div>

            <!-- Enabled toggle (only for editing) -->
            <div v-if="isEditing" class="flex items-center gap-3">
              <input
                id="enabled"
                v-model="enabled"
                type="checkbox"
                class="h-4 w-4 rounded border-border bg-background text-primary focus:ring-primary"
              />
              <label for="enabled" class="text-sm text-foreground"
                >Budget enabled</label
              >
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
                {{ isEditing ? 'Save Changes' : 'Create Budget' }}
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
  @apply w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl;
}
</style>
