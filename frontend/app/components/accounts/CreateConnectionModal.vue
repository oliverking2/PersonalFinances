<!-- ==========================================================================
CreateConnectionModal
Modal for creating new bank connections
Shows institution selection and friendly name input
============================================================================ -->

<script setup lang="ts">
import type { Institution } from '~/types/accounts'
import type { FilterOption } from '~/components/FilterDropdown.vue'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
  created: [authUrl: string]
}>()

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const { fetchInstitutions, createConnection, ApiError } = useAccountsApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const institutions = ref<Institution[]>([])
const selectedInstitutionId = ref('')
const friendlyName = ref('')
const loading = ref(false)
const creating = ref(false)
const redirecting = ref(false)
const error = ref('')

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Get the selected institution object
const selectedInstitution = computed(() => {
  return institutions.value.find((i) => i.id === selectedInstitutionId.value)
})

// Convert institutions to FilterOption format for the dropdown
const institutionOptions = computed<FilterOption[]>(() => {
  return institutions.value.map((inst) => ({
    id: inst.id,
    label: inst.name,
  }))
})

// FilterDropdown uses arrays, so wrap the single ID in an array
const selectedInstitutionIds = computed(() => {
  return selectedInstitutionId.value ? [selectedInstitutionId.value] : []
})

// Validation: both fields must be filled
const isValid = computed(() => {
  return selectedInstitutionId.value && friendlyName.value.trim().length > 0
})

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

// Load institutions when modal opens
async function loadInstitutions() {
  if (institutions.value.length > 0) return // Already loaded

  loading.value = true
  error.value = ''

  try {
    const response = await fetchInstitutions()
    institutions.value = response.institutions
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load institutions'
  } finally {
    loading.value = false
  }
}

// Watch for modal open to load data and reset form
watch(
  () => props.show,
  async (isOpen) => {
    if (isOpen) {
      selectedInstitutionId.value = ''
      friendlyName.value = ''
      error.value = ''
      redirecting.value = false
      await loadInstitutions()
    }
  },
)

function handleClose() {
  if (!creating.value && !redirecting.value) {
    emit('close')
  }
}

// Handle institution selection from FilterDropdown (converts array back to single value)
function handleInstitutionSelect(ids: string[]) {
  selectedInstitutionId.value = ids[0] ?? ''
}

async function handleCreate() {
  if (!isValid.value || creating.value) return

  creating.value = true
  error.value = ''

  try {
    const response = await createConnection({
      institution_id: selectedInstitutionId.value,
      friendly_name: friendlyName.value.trim(),
    })

    // Show redirecting state before navigating
    creating.value = false
    redirecting.value = true

    // Small delay so user sees the message
    await new Promise((resolve) => setTimeout(resolve, 500))

    emit('created', response.link)
  } catch (e) {
    // Handle 501 Not Implemented - feature coming soon
    if (e instanceof ApiError && e.status === 501) {
      error.value =
        'Bank connections coming soon! This feature is still being built.'
    } else {
      error.value =
        e instanceof Error ? e.message : 'Failed to create connection'
    }
    creating.value = false
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
            <h2 class="text-lg font-semibold text-foreground">
              Connect Bank Account
            </h2>
            <button
              type="button"
              class="rounded p-1 text-muted transition-colors hover:bg-border hover:text-foreground"
              :disabled="creating"
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

          <!-- Loading state -->
          <div v-if="loading" class="py-8 text-center text-muted">
            Loading banks...
          </div>

          <!-- Redirecting state -->
          <div v-else-if="redirecting" class="py-8 text-center">
            <div
              class="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
            />
            <p class="text-foreground">Redirecting to GoCardless...</p>
            <p class="mt-1 text-sm text-muted">
              You'll be asked to sign in to your bank
            </p>
          </div>

          <!-- Form -->
          <form v-else @submit.prevent="handleCreate">
            <!-- Institution select using FilterDropdown in single-select mode -->
            <div class="mb-4">
              <FilterDropdown
                label="Select Bank"
                placeholder="Choose a bank..."
                :options="institutionOptions"
                :selected-ids="selectedInstitutionIds"
                :multi-select="false"
                :searchable="true"
                @update:selected-ids="handleInstitutionSelect"
              />
            </div>

            <!-- Selected bank preview -->
            <div
              v-if="selectedInstitution"
              class="mb-4 flex items-center gap-3 rounded-lg bg-onyx p-3"
            >
              <img
                v-if="selectedInstitution.logo_url"
                :src="selectedInstitution.logo_url"
                :alt="selectedInstitution.name"
                class="h-8 w-8 object-contain"
              />
              <div
                v-else
                class="flex h-8 w-8 items-center justify-center rounded bg-border text-sm font-bold text-muted"
              >
                {{ selectedInstitution.name.charAt(0) }}
              </div>
              <span class="font-medium text-foreground">
                {{ selectedInstitution.name }}
              </span>
            </div>

            <!-- Friendly name input -->
            <div class="mb-4">
              <label class="mb-2 block text-sm font-medium text-muted">
                Friendly Name
              </label>
              <AppInput
                v-model="friendlyName"
                placeholder="e.g. Personal Banking"
                :required="true"
              />
              <p class="mt-1 text-xs text-muted">
                A name to help you identify this connection
              </p>
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
                :disabled="creating"
                @click="handleClose"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!isValid || creating"
              >
                {{ creating ? 'Connecting...' : 'Connect' }}
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
