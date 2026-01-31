<!-- ==========================================================================
MilestoneModal
Modal for creating and editing financial milestones
============================================================================ -->

<script setup lang="ts">
import type { Milestone, MilestoneCreateRequest } from '~/types/milestones'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
  milestone?: Milestone | null // If provided, we're editing; otherwise creating
}>()

// ---------------------------------------------------------------------------
// Emits
// ---------------------------------------------------------------------------
const emit = defineEmits<{
  close: []
  save: [data: MilestoneCreateRequest]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const name = ref('')
const targetAmount = ref<number | null>(null)
const targetDate = ref('')
const colour = ref('#f59e0b')
const notes = ref('')

// Preset colours for quick selection
const presetColours = [
  '#f59e0b', // Amber (default)
  '#10b981', // Emerald
  '#3b82f6', // Blue
  '#8b5cf6', // Violet
  '#ec4899', // Pink
  '#ef4444', // Red
]

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------
const isEditing = computed(() => !!props.milestone)

const modalTitle = computed(() =>
  isEditing.value ? 'Edit Milestone' : 'Create Milestone',
)

const isValid = computed(() => {
  return (
    name.value.trim().length > 0 && targetAmount.value && targetAmount.value > 0
  )
})

// ---------------------------------------------------------------------------
// Watchers
// ---------------------------------------------------------------------------

// Populate form when editing
watch(
  () => props.show,
  (show) => {
    if (show && props.milestone) {
      // Editing mode - populate fields
      name.value = props.milestone.name
      targetAmount.value = parseFloat(props.milestone.target_amount)
      targetDate.value = props.milestone.target_date
        ? props.milestone.target_date.slice(0, 10)
        : ''
      colour.value = props.milestone.colour
      notes.value = props.milestone.notes || ''
    } else if (show) {
      // Create mode - reset to defaults
      name.value = ''
      targetAmount.value = null
      targetDate.value = ''
      colour.value = '#f59e0b'
      notes.value = ''
    }
  },
)

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

function handleSubmit() {
  if (!isValid.value) return

  const data: MilestoneCreateRequest = {
    name: name.value.trim(),
    target_amount: targetAmount.value!,
    colour: colour.value,
  }

  if (targetDate.value) {
    data.target_date = targetDate.value
  }

  if (notes.value.trim()) {
    data.notes = notes.value.trim()
  }

  emit('save', data)
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="handleClose"
    >
      <div
        class="w-full max-w-md rounded-lg border border-border bg-surface p-6"
      >
        <!-- Header -->
        <div class="mb-6 flex items-center justify-between">
          <h2 class="text-xl font-bold">{{ modalTitle }}</h2>
          <button
            class="text-muted transition-colors hover:text-foreground"
            @click="handleClose"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Form -->
        <form class="space-y-4" @submit.prevent="handleSubmit">
          <!-- Name -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted"
              >Name</label
            >
            <AppInput
              v-model="name"
              placeholder="e.g., Emergency Fund, £100k Net Worth"
              required
            />
          </div>

          <!-- Target Amount -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Target Amount (£)
            </label>
            <input
              v-model.number="targetAmount"
              type="number"
              placeholder="50000"
              min="1"
              step="1"
              required
              class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground placeholder:text-muted focus:border-primary focus:outline-none"
            />
          </div>

          <!-- Target Date (optional) -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Target Date (optional)
            </label>
            <input
              v-model="targetDate"
              type="date"
              class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none"
            />
            <p class="mt-1 text-xs text-muted">
              Set a deadline to track days remaining
            </p>
          </div>

          <!-- Colour -->
          <div>
            <label class="mb-2 block text-sm font-medium text-muted"
              >Colour</label
            >
            <div class="flex items-center gap-2">
              <!-- Preset colours -->
              <button
                v-for="c in presetColours"
                :key="c"
                type="button"
                class="h-8 w-8 rounded-full border-2 transition-transform hover:scale-110"
                :class="colour === c ? 'border-white' : 'border-transparent'"
                :style="{ backgroundColor: c }"
                @click="colour = c"
              />
              <!-- Custom colour picker -->
              <input
                v-model="colour"
                type="color"
                class="h-8 w-8 cursor-pointer rounded border-0 bg-transparent"
              />
            </div>
          </div>

          <!-- Notes (optional) -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Notes (optional)
            </label>
            <textarea
              v-model="notes"
              class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground placeholder:text-muted focus:border-primary focus:outline-none"
              rows="2"
              placeholder="Why is this milestone important?"
            />
          </div>

          <!-- Actions -->
          <div class="flex justify-end gap-3 pt-2">
            <AppButton type="button" variant="secondary" @click="handleClose">
              Cancel
            </AppButton>
            <AppButton type="submit" :disabled="!isValid">
              {{ isEditing ? 'Save Changes' : 'Create Milestone' }}
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
