<!-- ==========================================================================
ValueUpdateModal
Modal for quickly updating a manual asset's value
============================================================================ -->

<script setup lang="ts">
import type { ManualAsset, ValueUpdateRequest } from '~/types/manual-assets'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
  asset: ManualAsset | null
}>()

// ---------------------------------------------------------------------------
// Emits
// ---------------------------------------------------------------------------
const emit = defineEmits<{
  close: []
  save: [assetId: string, data: ValueUpdateRequest]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const newValue = ref<number | null>(null)
const notes = ref('')

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const currentValue = computed(() => {
  if (!props.asset) return 0
  return Number(props.asset.current_value)
})

const valueDiff = computed(() => {
  if (newValue.value === null) return 0
  return newValue.value - currentValue.value
})

const valueDiffFormatted = computed(() => {
  const diff = valueDiff.value
  const sign = diff >= 0 ? '+' : ''
  return `${sign}${formatCurrency(diff)}`
})

const valueDiffColour = computed(() => {
  if (valueDiff.value > 0) return 'text-emerald-400'
  if (valueDiff.value < 0) return 'text-rose-400'
  return 'text-muted'
})

const isValid = computed(() => {
  return newValue.value !== null && newValue.value >= 0
})

// ---------------------------------------------------------------------------
// Watchers
// ---------------------------------------------------------------------------

// Populate with current value when modal opens
watch(
  () => props.show,
  (show) => {
    if (show && props.asset) {
      newValue.value = Number(props.asset.current_value)
      notes.value = ''
    }
  },
)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: props.asset?.currency || 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

function handleSubmit() {
  if (!isValid.value || !props.asset) return

  const data: ValueUpdateRequest = {
    new_value: newValue.value!,
  }

  if (notes.value.trim()) {
    data.notes = notes.value.trim()
  }

  emit('save', props.asset.id, data)
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show && asset"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="handleClose"
    >
      <div
        class="w-full max-w-md rounded-lg border border-border bg-surface p-6"
      >
        <!-- Header -->
        <div class="mb-6 flex items-center justify-between">
          <h2 class="text-xl font-bold">Update Value</h2>
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

        <!-- Asset info -->
        <div class="mb-4 rounded-lg bg-background p-3">
          <p class="font-medium">{{ asset.name }}</p>
          <p class="text-sm text-muted">{{ asset.display_type }}</p>
        </div>

        <!-- Form -->
        <form class="space-y-4" @submit.prevent="handleSubmit">
          <!-- Current value (read-only) -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Current Value
            </label>
            <p class="text-lg font-semibold">
              {{ formatCurrency(currentValue) }}
            </p>
          </div>

          <!-- New value input -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              New Value ({{ asset.currency }})
            </label>
            <AppInput
              v-model="newValue"
              type="number"
              :placeholder="String(currentValue)"
              :min="0"
              :step="0.01"
              required
              autofocus
            />
          </div>

          <!-- Value change indicator -->
          <div
            v-if="newValue !== null && valueDiff !== 0"
            class="rounded-lg bg-background p-3"
          >
            <p class="text-sm text-muted">Change</p>
            <p class="text-lg font-semibold" :class="valueDiffColour">
              {{ valueDiffFormatted }}
            </p>
          </div>

          <!-- Notes (optional) -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Note (optional)
            </label>
            <AppInput
              v-model="notes"
              placeholder="e.g., Annual revaluation, Loan payment"
            />
            <p class="mt-1 text-xs text-muted">
              Explain why the value changed (saved in history)
            </p>
          </div>

          <!-- Actions -->
          <div class="flex justify-end gap-3 pt-2">
            <AppButton type="button" variant="secondary" @click="handleClose">
              Cancel
            </AppButton>
            <AppButton type="submit" :disabled="!isValid">
              Update Value
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
