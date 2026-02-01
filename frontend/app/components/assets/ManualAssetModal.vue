<!-- ==========================================================================
ManualAssetModal
Modal for creating and editing manual assets/liabilities
============================================================================ -->

<script setup lang="ts">
import type {
  ManualAsset,
  ManualAssetType,
  ManualAssetCreateRequest,
} from '~/types/manual-assets'
import {
  getAssetTypeLabel,
  getDefaultIsLiability,
  getAssetTypesByCategory,
} from '~/types/manual-assets'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  show: boolean
  asset?: ManualAsset | null // If provided, we're editing; otherwise creating
}>()

// ---------------------------------------------------------------------------
// Emits
// ---------------------------------------------------------------------------
const emit = defineEmits<{
  close: []
  save: [data: ManualAssetCreateRequest, isEdit: boolean]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const name = ref('')
const assetType = ref<ManualAssetType>('other_asset')
const customType = ref('')
const currentValue = ref<number | null>(null)
const isLiability = ref(false)
const currency = ref('GBP')
const notes = ref('')
const interestRate = ref<number | null>(null)
const acquisitionDate = ref('')
const acquisitionValue = ref<number | null>(null)

// Get asset types grouped by category for the dropdown
const { assets: assetTypes, liabilities: liabilityTypes } =
  getAssetTypesByCategory()
const allTypes = [...liabilityTypes, ...assetTypes]

// Build options for AppSelect
const typeOptions = computed(() =>
  allTypes.map((type) => ({
    value: type,
    label: getAssetTypeLabel(type),
  })),
)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------
const isEditing = computed(() => !!props.asset)

const modalTitle = computed(() =>
  isEditing.value ? 'Edit Asset' : 'Add Asset or Liability',
)

const isValid = computed(() => {
  return (
    name.value.trim().length > 0 &&
    currentValue.value !== null &&
    currentValue.value >= 0
  )
})

// Show interest rate field for loan types
const showInterestRate = computed(() => {
  return ['student_loan', 'mortgage', 'other_liability'].includes(
    assetType.value,
  )
})

// ---------------------------------------------------------------------------
// Watchers
// ---------------------------------------------------------------------------

// Update is_liability when asset type changes (only in create mode)
watch(assetType, (newType) => {
  if (!isEditing.value) {
    isLiability.value = getDefaultIsLiability(newType)
  }
})

// Populate form when editing or reset when creating
watch(
  () => props.show,
  (show) => {
    if (show && props.asset) {
      // Editing mode - populate fields
      name.value = props.asset.name
      assetType.value = props.asset.asset_type
      customType.value = props.asset.custom_type || ''
      currentValue.value = Number(props.asset.current_value)
      isLiability.value = props.asset.is_liability
      currency.value = props.asset.currency
      notes.value = props.asset.notes || ''
      interestRate.value = props.asset.interest_rate
        ? Number(props.asset.interest_rate)
        : null
      acquisitionDate.value = props.asset.acquisition_date
        ? props.asset.acquisition_date.slice(0, 10)
        : ''
      acquisitionValue.value = props.asset.acquisition_value
        ? Number(props.asset.acquisition_value)
        : null
    } else if (show) {
      // Create mode - reset to defaults
      name.value = ''
      assetType.value = 'other_asset'
      customType.value = ''
      currentValue.value = null
      isLiability.value = false
      currency.value = 'GBP'
      notes.value = ''
      interestRate.value = null
      acquisitionDate.value = ''
      acquisitionValue.value = null
    }
  },
)

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

function handleSubmit() {
  if (!isValid.value) return

  const data: ManualAssetCreateRequest = {
    name: name.value.trim(),
    asset_type: assetType.value,
    current_value: currentValue.value!,
    is_liability: isLiability.value,
    currency: currency.value,
  }

  if (customType.value.trim()) {
    data.custom_type = customType.value.trim()
  }

  if (notes.value.trim()) {
    data.notes = notes.value.trim()
  }

  if (interestRate.value !== null && showInterestRate.value) {
    data.interest_rate = interestRate.value
  }

  if (acquisitionDate.value) {
    data.acquisition_date = acquisitionDate.value
  }

  if (acquisitionValue.value !== null) {
    data.acquisition_value = acquisitionValue.value
  }

  emit('save', data, isEditing.value)
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
        class="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-lg border border-border bg-surface p-6"
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
            <label class="mb-1 block text-sm font-medium text-muted">
              Name
            </label>
            <AppInput
              v-model="name"
              placeholder="e.g., Main Residence, Student Loan"
              required
            />
          </div>

          <!-- Asset Type -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Type
            </label>
            <AppSelect
              v-model="assetType"
              :options="typeOptions"
              :disabled="isEditing"
            />
            <p v-if="isEditing" class="mt-1 text-xs text-muted">
              Type cannot be changed after creation
            </p>
          </div>

          <!-- Custom Type (optional) -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Custom Label (optional)
            </label>
            <AppInput
              v-model="customType"
              placeholder="e.g., My Honda Civic, Plan 2 Loan"
            />
            <p class="mt-1 text-xs text-muted">
              Override the default type label with a more specific name
            </p>
          </div>

          <!-- Current Value -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Current Value ({{ currency }})
            </label>
            <AppInput
              v-model="currentValue"
              type="number"
              placeholder="50000"
              :min="0"
              :step="0.01"
              required
            />
          </div>

          <!-- Is Liability override -->
          <div class="flex items-center gap-3">
            <input
              id="is-liability"
              v-model="isLiability"
              type="checkbox"
              class="h-4 w-4 rounded border-border bg-background text-primary focus:ring-primary"
            />
            <label for="is-liability" class="text-sm">
              This is a liability (counts against net worth)
            </label>
          </div>

          <!-- Interest Rate (for loans) -->
          <div v-if="showInterestRate">
            <label class="mb-1 block text-sm font-medium text-muted">
              Interest Rate (% APR)
            </label>
            <AppInput
              v-model="interestRate"
              type="number"
              placeholder="5.5"
              :min="0"
              :max="100"
              :step="0.01"
            />
          </div>

          <!-- Acquisition Date (optional) -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Acquisition Date (optional)
            </label>
            <input
              v-model="acquisitionDate"
              type="date"
              class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none"
            />
          </div>

          <!-- Acquisition Value (optional) -->
          <div>
            <label class="mb-1 block text-sm font-medium text-muted">
              Original Purchase Price (optional)
            </label>
            <AppInput
              v-model="acquisitionValue"
              type="number"
              placeholder="45000"
              :min="0"
              :step="0.01"
            />
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
              placeholder="Any additional details about this asset..."
            />
          </div>

          <!-- Actions -->
          <div class="flex justify-end gap-3 pt-2">
            <AppButton type="button" variant="secondary" @click="handleClose">
              Cancel
            </AppButton>
            <AppButton type="submit" :disabled="!isValid">
              {{ isEditing ? 'Save Changes' : 'Add Asset' }}
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
