<!-- ==========================================================================
DateFilterDropdown
Dropdown for date range filtering with preset options and custom date inputs
Presets: This month, Last 30 days, This year, Custom
When Custom is selected, shows From/To date inputs within the dropdown
============================================================================ -->

<script setup lang="ts">
import {
  type DatePreset,
  DATE_PRESET_OPTIONS,
  useDatePresets,
} from '~/composables/useDatePresets'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------

const props = defineProps<{
  startDate?: string // ISO date string (YYYY-MM-DD)
  endDate?: string // ISO date string (YYYY-MM-DD)
}>()

const emit = defineEmits<{
  'update:startDate': [date: string | undefined]
  'update:endDate': [date: string | undefined]
  // Emitted when selecting a preset - both dates at once to avoid race condition
  'update:dateRange': [
    startDate: string | undefined,
    endDate: string | undefined,
  ]
}>()

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------

const { getPresetDateRange, detectPreset, formatDateRangeDisplay } =
  useDatePresets()

// ---------------------------------------------------------------------------
// Local State
// ---------------------------------------------------------------------------

const isOpen = ref(false)
const dropdownRef = ref<HTMLDivElement | null>(null)
// Track when user explicitly selects "Custom" (needed because detectPreset
// returns 'all_time' when no dates are set, but we want to show date inputs)
const showCustomInputs = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Detect which preset matches current dates
const detectedPreset = computed<DatePreset>(() => {
  return detectPreset(props.startDate, props.endDate)
})

// The visually selected preset - accounts for explicit "Custom" selection
const selectedPreset = computed<DatePreset>(() => {
  // If user explicitly clicked Custom, show that as selected
  if (showCustomInputs.value) {
    return 'custom'
  }
  return detectedPreset.value
})

// Check if any dates are set
const hasValue = computed(() => {
  return !!(props.startDate || props.endDate)
})

// Display text when dropdown is closed
const displayText = computed(() => {
  const preset = selectedPreset.value

  // For all_time or custom without dates, show "All dates"
  if (preset === 'all_time') {
    return 'All dates'
  }

  if (preset !== 'custom') {
    // Show preset label
    const option = DATE_PRESET_OPTIONS.find((o) => o.value === preset)
    return option?.label || 'All dates'
  }

  // Custom dates - show formatted range
  const rangeText = formatDateRangeDisplay(props.startDate, props.endDate)
  return rangeText ? `Custom: ${rangeText}` : 'Custom'
})

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

function toggleDropdown() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    // When opening, show custom inputs if there are custom dates set
    showCustomInputs.value = detectedPreset.value === 'custom'
  }
}

function selectPreset(preset: DatePreset) {
  if (preset === 'custom') {
    // Don't close dropdown - user needs to enter dates
    // Show the custom date inputs
    showCustomInputs.value = true
    return
  }

  // Hide custom inputs when selecting a preset
  showCustomInputs.value = false

  // Get dates for this preset and emit both at once (avoids race condition)
  const { start_date, end_date } = getPresetDateRange(preset)
  emit('update:dateRange', start_date, end_date)
  isOpen.value = false
}

function handleStartDateChange(event: Event) {
  const input = event.target as HTMLInputElement
  emit('update:startDate', input.value || undefined)
}

function handleEndDateChange(event: Event) {
  const input = event.target as HTMLInputElement
  emit('update:endDate', input.value || undefined)
}

function clearDates() {
  showCustomInputs.value = false
  emit('update:dateRange', undefined, undefined)
  isOpen.value = false
}

// Close dropdown when clicking outside
function handleClickOutside(event: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="dropdownRef" class="relative">
    <!-- Label -->
    <label class="mb-1 block text-sm text-muted">Date</label>

    <!-- Dropdown trigger button -->
    <button
      type="button"
      class="flex w-full items-center justify-between rounded-lg border border-border bg-surface px-3 py-2 text-left transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      :class="isOpen ? 'border-primary ring-1 ring-primary' : ''"
      @click="toggleDropdown"
    >
      <span :class="hasValue ? 'text-foreground' : 'text-muted'">
        {{ displayText }}
      </span>

      <!-- Chevron icon -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        class="ml-2 h-5 w-5 flex-shrink-0 text-muted transition-transform"
        :class="isOpen ? 'rotate-180' : ''"
      >
        <path
          fill-rule="evenodd"
          d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
          clip-rule="evenodd"
        />
      </svg>
    </button>

    <!-- Dropdown panel -->
    <div
      v-if="isOpen"
      class="absolute left-0 top-full z-30 mt-1 w-full min-w-[220px] rounded-lg border border-border bg-surface shadow-lg"
    >
      <!-- Preset options (radio-style) -->
      <div class="p-1">
        <button
          v-for="option in DATE_PRESET_OPTIONS"
          :key="option.value"
          type="button"
          class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-onyx"
          @click.stop="selectPreset(option.value)"
        >
          <!-- Radio indicator -->
          <span
            class="flex h-4 w-4 items-center justify-center rounded-full border"
            :class="
              selectedPreset === option.value
                ? 'border-primary'
                : 'border-gray-600'
            "
          >
            <span
              v-if="selectedPreset === option.value"
              class="h-2 w-2 rounded-full bg-primary"
            />
          </span>

          <!-- Label -->
          <span class="text-foreground">{{ option.label }}</span>
        </button>
      </div>

      <!-- Custom date inputs (shown when Custom is selected or dates don't match a preset) -->
      <div
        v-if="showCustomInputs || selectedPreset === 'custom'"
        class="border-t border-border p-3"
      >
        <div class="space-y-2">
          <!-- From date -->
          <div>
            <label class="mb-1 block text-xs text-muted">From</label>
            <input
              type="date"
              :value="startDate || ''"
              class="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              @change="handleStartDateChange"
              @click.stop
            />
          </div>

          <!-- To date -->
          <div>
            <label class="mb-1 block text-xs text-muted">To</label>
            <input
              type="date"
              :value="endDate || ''"
              class="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              @change="handleEndDateChange"
              @click.stop
            />
          </div>
        </div>
      </div>

      <!-- Clear button (when dates are set) -->
      <div v-if="hasValue" class="border-t border-border p-2">
        <button
          type="button"
          class="w-full rounded px-2 py-1 text-sm text-muted transition-colors hover:bg-onyx hover:text-foreground"
          @click.stop="clearDates"
        >
          Clear dates
        </button>
      </div>
    </div>
  </div>
</template>
