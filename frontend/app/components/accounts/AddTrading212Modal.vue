<!-- ==========================================================================
AddTrading212Modal
Modal for adding a Trading 212 connection via API key
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
  created: []
}>()

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const { addT212Connection, ApiError } = useTrading212Api()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Form fields
const apiKey = ref('')
const friendlyName = ref('')

// UI state
const creating = ref(false)
const error = ref('')

// Password visibility toggle for API key field
const showApiKey = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Validation: both fields must be filled
const isValid = computed(() => {
  return apiKey.value.trim().length > 0 && friendlyName.value.trim().length > 0
})

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

// Reset form when modal opens
watch(
  () => props.show,
  (isOpen) => {
    if (isOpen) {
      apiKey.value = ''
      friendlyName.value = ''
      error.value = ''
      showApiKey.value = false
    }
  },
)

function handleClose() {
  if (!creating.value) {
    emit('close')
  }
}

async function handleCreate() {
  if (!isValid.value || creating.value) return

  creating.value = true
  error.value = ''

  try {
    await addT212Connection({
      api_key: apiKey.value.trim(),
      friendly_name: friendlyName.value.trim(),
    })

    emit('created')
    emit('close')
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 400) {
        error.value =
          'Invalid API key. Please check your API key and try again.'
      } else if (e.status === 502) {
        error.value =
          'Could not connect to Trading 212. Please try again later.'
      } else {
        error.value = e.message || 'Failed to add connection'
      }
    } else {
      error.value = e instanceof Error ? e.message : 'Failed to add connection'
    }
  } finally {
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
              Add Trading 212 Account
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

          <!-- Info box explaining API key -->
          <div class="mb-4 rounded-lg bg-onyx p-3 text-sm text-muted">
            <p>
              To connect your Trading 212 account, you need to generate an API
              key from the Trading 212 app.
            </p>
            <ol class="mt-2 list-inside list-decimal space-y-1">
              <li>Open the Trading 212 mobile app</li>
              <li>Go to Settings → API</li>
              <li>Generate a new API key</li>
              <li>Paste it below</li>
            </ol>
          </div>

          <!-- Form -->
          <form @submit.prevent="handleCreate">
            <!-- API Key input (with visibility toggle) -->
            <div class="mb-4">
              <label class="mb-2 block text-sm font-medium text-muted">
                API Key
              </label>
              <div class="relative">
                <AppInput
                  v-model="apiKey"
                  :type="showApiKey ? 'text' : 'password'"
                  placeholder="Enter your Trading 212 API key"
                  :required="true"
                  class="pr-10"
                />
                <!-- Toggle visibility button -->
                <button
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted hover:text-foreground"
                  @click="showApiKey = !showApiKey"
                >
                  <!-- Eye icon (show) -->
                  <svg
                    v-if="!showApiKey"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    class="h-5 w-5"
                  >
                    <path d="M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z" />
                    <path
                      fill-rule="evenodd"
                      d="M.664 10.59a1.651 1.651 0 0 1 0-1.186A10.004 10.004 0 0 1 10 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0 1 10 17c-4.257 0-7.893-2.66-9.336-6.41ZM14 10a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <!-- Eye-slash icon (hide) -->
                  <svg
                    v-else
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    class="h-5 w-5"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M3.28 2.22a.75.75 0 0 0-1.06 1.06l14.5 14.5a.75.75 0 1 0 1.06-1.06l-1.745-1.745a10.029 10.029 0 0 0 3.3-4.38 1.651 1.651 0 0 0 0-1.185A10.004 10.004 0 0 0 9.999 3a9.956 9.956 0 0 0-4.744 1.194L3.28 2.22ZM7.752 6.69l1.092 1.092a2.5 2.5 0 0 1 3.374 3.373l1.091 1.092a4 4 0 0 0-5.557-5.557Z"
                      clip-rule="evenodd"
                    />
                    <path
                      d="m10.748 13.93 2.523 2.523a9.987 9.987 0 0 1-3.27.547c-4.258 0-7.894-2.66-9.337-6.41a1.651 1.651 0 0 1 0-1.186A10.007 10.007 0 0 1 2.839 6.02L6.07 9.252a4 4 0 0 0 4.678 4.678Z"
                    />
                  </svg>
                </button>
              </div>
              <p class="mt-1 text-xs text-muted">
                Your API key is stored securely and encrypted
              </p>
            </div>

            <!-- Friendly name input -->
            <div class="mb-4">
              <label class="mb-2 block text-sm font-medium text-muted">
                Friendly Name
              </label>
              <AppInput
                v-model="friendlyName"
                placeholder="e.g. ISA Account"
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
