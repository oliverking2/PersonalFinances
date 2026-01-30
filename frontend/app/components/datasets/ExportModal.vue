<!-- ==========================================================================
ExportModal
Modal for configuring and executing dataset exports
Shows export form, progress state, and download button when complete
============================================================================ -->

<script setup lang="ts">
import type {
  Dataset,
  EnumFilterValue,
  ExportStatusResponse,
  NumericFilterValue,
} from '~/types/analytics'
import type { Account } from '~/types/accounts'
import type { Tag } from '~/types/tags'
import type { FilterOption } from '~/components/FilterDropdown.vue'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

const props = defineProps<{
  isOpen: boolean
  dataset: Dataset | null
  accounts: Account[]
  tags: Tag[]
}>()

// ---------------------------------------------------------------------------
// Emits
// ---------------------------------------------------------------------------

const emit = defineEmits<{
  close: []
}>()

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

const { createExport, getExportStatus } = useExportsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// Form State
// ---------------------------------------------------------------------------

const format = ref<'csv' | 'parquet'>('csv')
const startDate = ref('')
const endDate = ref('')
const selectedAccountIds = ref<string[]>([])
const selectedTagIds = ref<string[]>([])

// Dynamic filter state - keyed by filter name
// Enum filters: selected values (multi-select)
const enumFilterSelections = ref<Record<string, string[]>>({})
// Numeric filters: min/max values
const numericFilterValues = ref<Record<string, { min: string; max: string }>>(
  {},
)

// ---------------------------------------------------------------------------
// Filter Options
// ---------------------------------------------------------------------------

// Convert accounts to filter options
const accountOptions = computed<FilterOption[]>(() =>
  props.accounts.map((account) => ({
    id: account.id,
    label: account.display_name ?? account.name ?? 'Unknown Account',
  })),
)

// Convert tags to filter options
const tagOptions = computed<FilterOption[]>(() =>
  props.tags.map((tag) => ({
    id: tag.id,
    label: tag.name,
    colour: tag.colour,
  })),
)

// Convert enum filter options to FilterOption format
// Returns a map of filter name -> FilterOption[]
const enumFilterOptions = computed(() => {
  const result: Record<string, FilterOption[]> = {}
  for (const filter of props.dataset?.filters.enum_filters ?? []) {
    result[filter.name] = filter.options.map((opt) => ({
      id: opt,
      label: opt,
    }))
  }
  return result
})

// ---------------------------------------------------------------------------
// Export State
// ---------------------------------------------------------------------------

type ExportState = 'form' | 'running' | 'completed' | 'failed'
const exportState = ref<ExportState>('form')
const currentJobId = ref<string | null>(null)
const exportResult = ref<ExportStatusResponse | null>(null)
const errorMessage = ref('')

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Format label for display
const formatLabel = computed(() => (format.value === 'csv' ? 'CSV' : 'Parquet'))

// File size formatted
const fileSizeFormatted = computed(() => {
  if (!exportResult.value?.file_size_bytes) return null
  const bytes = exportResult.value.file_size_bytes
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
})

// ---------------------------------------------------------------------------
// Reset form when modal opens
// ---------------------------------------------------------------------------

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      // Reset to form state
      exportState.value = 'form'
      currentJobId.value = null
      exportResult.value = null
      errorMessage.value = ''

      // Reset form fields
      format.value = 'csv'
      startDate.value = ''
      endDate.value = ''
      selectedAccountIds.value = []
      selectedTagIds.value = []

      // Initialize dynamic filter state based on dataset filters
      const enumFilters = props.dataset?.filters.enum_filters ?? []
      const numericFilters = props.dataset?.filters.numeric_filters ?? []

      // Initialize empty arrays for each enum filter
      enumFilterSelections.value = Object.fromEntries(
        enumFilters.map((f) => [f.name, []]),
      )

      // Initialize empty min/max for each numeric filter
      numericFilterValues.value = Object.fromEntries(
        numericFilters.map((f) => [f.name, { min: '', max: '' }]),
      )
    }
  },
)

// ---------------------------------------------------------------------------
// Export Handler
// ---------------------------------------------------------------------------

async function handleStartExport() {
  if (!props.dataset) return

  try {
    exportState.value = 'running'
    errorMessage.value = ''

    // Build enum filters (only include filters with selected values)
    const enumFilters: EnumFilterValue[] = Object.entries(
      enumFilterSelections.value,
    )
      .filter(([, values]) => values.length > 0)
      .map(([column, values]) => ({ column, values }))

    // Build numeric filters (only include filters with min or max set)
    const numericFilters: NumericFilterValue[] = Object.entries(
      numericFilterValues.value,
    )
      .filter(([, { min, max }]) => min !== '' || max !== '')
      .map(([column, { min, max }]) => ({
        column,
        min: min !== '' ? Number(min) : undefined,
        max: max !== '' ? Number(max) : undefined,
      }))

    // Create export job
    const response = await createExport({
      dataset_id: props.dataset.id,
      format: format.value,
      start_date: startDate.value || undefined,
      end_date: endDate.value || undefined,
      account_ids:
        selectedAccountIds.value.length > 0
          ? selectedAccountIds.value
          : undefined,
      tag_ids:
        selectedTagIds.value.length > 0 ? selectedTagIds.value : undefined,
      enum_filters: enumFilters.length > 0 ? enumFilters : undefined,
      numeric_filters: numericFilters.length > 0 ? numericFilters : undefined,
    })

    // Check if creation failed
    if (response.status === 'failed') {
      exportState.value = 'failed'
      errorMessage.value = response.message || 'Failed to create export job'
      return
    }

    currentJobId.value = response.job_id

    // Start polling for status
    await pollExportStatus(response.job_id)
  } catch (e) {
    exportState.value = 'failed'
    errorMessage.value = e instanceof Error ? e.message : 'Export failed'
    toast.error(errorMessage.value)
  }
}

// ---------------------------------------------------------------------------
// Status Polling
// ---------------------------------------------------------------------------

async function pollExportStatus(jobId: string) {
  const maxAttempts = 120 // 10 minutes max (5s intervals)
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      const status = await getExportStatus(jobId)

      if (status.status === 'completed') {
        exportResult.value = status
        exportState.value = 'completed'
        return
      }

      if (status.status === 'failed') {
        exportState.value = 'failed'
        errorMessage.value = status.error_message || 'Export failed'
        return
      }

      // Still running - wait and try again
      await new Promise((resolve) => setTimeout(resolve, 5000))
      attempts++
    } catch {
      // Continue polling on transient errors
      attempts++
      await new Promise((resolve) => setTimeout(resolve, 5000))
    }
  }

  // Timeout
  exportState.value = 'failed'
  errorMessage.value = 'Export timed out'
}

// ---------------------------------------------------------------------------
// Download Handler
// ---------------------------------------------------------------------------

function handleDownload() {
  if (exportResult.value?.download_url) {
    window.open(exportResult.value.download_url, '_blank')
  }
}

// ---------------------------------------------------------------------------
// Numeric Filter Helper
// ---------------------------------------------------------------------------

function updateNumericFilter(
  filterName: string,
  field: 'min' | 'max',
  event: Event,
) {
  const value = (event.target as HTMLInputElement).value
  if (!numericFilterValues.value[filterName]) {
    numericFilterValues.value[filterName] = { min: '', max: '' }
  }
  numericFilterValues.value[filterName][field] = value
}

// ---------------------------------------------------------------------------
// Close Handler
// ---------------------------------------------------------------------------

function handleClose() {
  emit('close')
}
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
      <div v-if="isOpen" class="modal-backdrop" @click.self="handleClose">
        <!-- Modal content -->
        <div class="modal-content">
          <!-- Header -->
          <div
            class="flex items-center justify-between border-b border-border pb-4"
          >
            <h2 class="text-xl font-semibold">
              Export: {{ dataset?.friendly_name }}
            </h2>
            <button
              type="button"
              class="rounded-lg p-1 text-muted hover:bg-gray-700/50 hover:text-foreground"
              @click="handleClose"
            >
              <!-- Close icon -->
              <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
                />
              </svg>
            </button>
          </div>

          <!-- Form state -->
          <!-- pb-2 gives room for button scale effect without causing scrollbars -->
          <div v-if="exportState === 'form'" class="mt-4 space-y-4 pb-2">
            <!-- Format selector -->
            <div>
              <label class="block text-sm font-medium text-muted">Format</label>
              <div class="mt-2 flex gap-3">
                <!-- CSV option -->
                <label class="flex cursor-pointer items-center gap-2">
                  <input
                    v-model="format"
                    type="radio"
                    value="csv"
                    class="h-4 w-4 accent-primary"
                  />
                  <span>CSV</span>
                </label>

                <!-- Parquet option -->
                <label class="flex cursor-pointer items-center gap-2">
                  <input
                    v-model="format"
                    type="radio"
                    value="parquet"
                    class="h-4 w-4 accent-primary"
                  />
                  <span>Parquet</span>
                </label>
              </div>
            </div>

            <!-- Date range - only show if dataset supports date filtering -->
            <div
              v-if="dataset?.filters.date_column"
              class="grid grid-cols-2 gap-4"
            >
              <div>
                <label class="block text-sm font-medium text-muted"
                  >Start Date</label
                >
                <input
                  v-model="startDate"
                  type="date"
                  class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-muted"
                  >End Date</label
                >
                <input
                  v-model="endDate"
                  type="date"
                  class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <!-- Account filter - only show if dataset supports account filtering -->
            <FilterDropdown
              v-if="
                dataset?.filters.account_id_column && accountOptions.length > 0
              "
              v-model:selected-ids="selectedAccountIds"
              label="Accounts"
              placeholder="All accounts"
              :options="accountOptions"
            />

            <!-- Tag filter - only show if dataset supports tag filtering -->
            <FilterDropdown
              v-if="dataset?.filters.tag_id_column && tagOptions.length > 0"
              v-model:selected-ids="selectedTagIds"
              label="Tags"
              placeholder="All tags"
              :options="tagOptions"
            />

            <!-- Dynamic enum filters -->
            <FilterDropdown
              v-for="filter in dataset?.filters.enum_filters ?? []"
              :key="filter.name"
              :selected-ids="enumFilterSelections[filter.name] ?? []"
              :label="filter.label"
              :placeholder="`All ${filter.label.toLowerCase()}`"
              :options="enumFilterOptions[filter.name] ?? []"
              @update:selected-ids="enumFilterSelections[filter.name] = $event"
            />

            <!-- Dynamic numeric filters (min/max range) -->
            <div
              v-for="filter in dataset?.filters.numeric_filters ?? []"
              :key="filter.name"
              class="space-y-1"
            >
              <label class="block text-sm font-medium text-muted">{{
                filter.label
              }}</label>
              <div class="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  placeholder="Min"
                  :value="numericFilterValues[filter.name]?.min ?? ''"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground placeholder:text-muted/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  @input="updateNumericFilter(filter.name, 'min', $event)"
                />
                <input
                  type="number"
                  placeholder="Max"
                  :value="numericFilterValues[filter.name]?.max ?? ''"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground placeholder:text-muted/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  @input="updateNumericFilter(filter.name, 'max', $event)"
                />
              </div>
            </div>

            <!-- Actions - pr-4 gives room for button scale effect -->
            <div class="flex justify-end gap-2 pr-4 pt-4">
              <button
                type="button"
                class="rounded-lg bg-gray-700/50 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700"
                @click="handleClose"
              >
                Cancel
              </button>
              <AppButton @click="handleStartExport"> Start Export </AppButton>
            </div>
          </div>

          <!-- Running state -->
          <div
            v-else-if="exportState === 'running'"
            class="flex flex-col items-center py-12"
          >
            <!-- Spinner -->
            <svg
              class="h-12 w-12 animate-spin text-primary"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>

            <p class="mt-4 text-lg font-medium">Export in progress...</p>
            <p class="mt-2 text-sm text-muted">
              We'll notify you via Telegram when ready
            </p>

            <!-- Close button (user can close and check later) -->
            <button
              type="button"
              class="mt-6 rounded-lg bg-gray-700/50 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700"
              @click="handleClose"
            >
              Close
            </button>
          </div>

          <!-- Completed state -->
          <div
            v-else-if="exportState === 'completed'"
            class="flex flex-col items-center py-8"
          >
            <!-- Success icon -->
            <div
              class="flex h-16 w-16 items-center justify-center rounded-full bg-positive/20"
            >
              <svg
                class="h-8 w-8 text-positive"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>

            <p class="mt-4 text-lg font-medium">Export Complete!</p>

            <!-- Export details -->
            <div class="mt-4 text-center text-sm text-muted">
              <p>
                {{ exportResult?.row_count?.toLocaleString() }} rows
                <span v-if="fileSizeFormatted"> • {{ fileSizeFormatted }}</span>
              </p>
            </div>

            <!-- Download button -->
            <AppButton class="mt-6" @click="handleDownload">
              Download {{ formatLabel }}
            </AppButton>

            <p class="mt-3 text-xs text-muted">Link expires in 1 hour</p>

            <!-- Close button -->
            <button
              type="button"
              class="mt-4 text-sm text-muted hover:text-foreground"
              @click="handleClose"
            >
              Close
            </button>
          </div>

          <!-- Failed state -->
          <div
            v-else-if="exportState === 'failed'"
            class="flex flex-col items-center py-8"
          >
            <!-- Error icon -->
            <div
              class="flex h-16 w-16 items-center justify-center rounded-full bg-negative/20"
            >
              <svg
                class="h-8 w-8 text-negative"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>

            <p class="mt-4 text-lg font-medium">Export Failed</p>
            <p class="mt-2 text-sm text-negative">{{ errorMessage }}</p>

            <!-- Retry button -->
            <div class="mt-6 flex gap-2">
              <button
                type="button"
                class="rounded-lg bg-gray-700/50 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700"
                @click="handleClose"
              >
                Close
              </button>
              <AppButton @click="exportState = 'form'"> Try Again </AppButton>
            </div>
          </div>
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
  @apply flex max-h-[85vh] w-full max-w-lg flex-col rounded-xl border border-border bg-surface p-6 shadow-xl;

  /* Clip horizontal overflow from button scale effects */
  @apply overflow-x-hidden;

  /* Allow form to scroll if content overflows */
  & > div {
    @apply overflow-y-auto;
  }
}
</style>
