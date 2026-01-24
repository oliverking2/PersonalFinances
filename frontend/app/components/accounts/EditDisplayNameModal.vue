<!-- ==========================================================================
EditDisplayNameModal
Modal for editing account or connection display names
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
  entityType: 'account' | 'connection'
  entityId: string
  currentName: string
}>()

const emit = defineEmits<{
  close: []
  save: [id: string, newName: string]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const newName = ref('')
const saving = ref(false)
const error = ref('')

// Reset state when modal opens
watch(
  () => props.show,
  (isOpen) => {
    if (isOpen) {
      newName.value = props.currentName
      error.value = ''
    }
  },
)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const title = computed(() => {
  return props.entityType === 'account'
    ? 'Edit Account Name'
    : 'Edit Connection Name'
})

const placeholder = computed(() => {
  return props.entityType === 'account'
    ? 'Enter display name'
    : 'Enter friendly name'
})

// Validation: name must be non-empty and different from current
const isValid = computed(() => {
  const trimmed = newName.value.trim()
  return trimmed.length > 0 && trimmed !== props.currentName
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
    emit('save', props.entityId, newName.value.trim())
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to save'
    saving.value = false
  }
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
            <h2 class="text-lg font-semibold text-foreground">{{ title }}</h2>
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
            <!-- Name input -->
            <div class="mb-4">
              <label class="mb-2 block text-sm font-medium text-muted">
                {{
                  entityType === 'account' ? 'Display Name' : 'Friendly Name'
                }}
              </label>
              <AppInput
                v-model="newName"
                :placeholder="placeholder"
                :required="true"
              />
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
                {{ saving ? 'Saving...' : 'Save' }}
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
