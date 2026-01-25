<!-- ==========================================================================
ValueFilterDropdown
Dropdown for filtering transactions by amount range (min/max)
Shows "All values" when no filter, or range like "£10 - £100"
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------

const props = defineProps<{
  minAmount?: number
  maxAmount?: number
}>()

const emit = defineEmits<{
  'update:minAmount': [amount: number | undefined]
  'update:maxAmount': [amount: number | undefined]
}>()

// ---------------------------------------------------------------------------
// Local State
// ---------------------------------------------------------------------------

const isOpen = ref(false)
const dropdownRef = ref<HTMLDivElement | null>(null)

// Local input values (strings for form binding)
const localMin = ref('')
const localMax = ref('')

// Sync local state with props when they change
watch(
  () => props.minAmount,
  (val) => {
    localMin.value = val !== undefined ? String(val) : ''
  },
  { immediate: true },
)

watch(
  () => props.maxAmount,
  (val) => {
    localMax.value = val !== undefined ? String(val) : ''
  },
  { immediate: true },
)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Check if any amount filter is set
const hasValue = computed(() => {
  return props.minAmount !== undefined || props.maxAmount !== undefined
})

// Format a number as currency for display
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)
}

// Display text when dropdown is closed
const displayText = computed(() => {
  if (!hasValue.value) return 'All values'

  if (props.minAmount !== undefined && props.maxAmount !== undefined) {
    return `${formatCurrency(props.minAmount)} - ${formatCurrency(props.maxAmount)}`
  }

  if (props.minAmount !== undefined) {
    return `Min ${formatCurrency(props.minAmount)}`
  }

  if (props.maxAmount !== undefined) {
    return `Max ${formatCurrency(props.maxAmount)}`
  }

  return 'All values'
})

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

function toggleDropdown() {
  isOpen.value = !isOpen.value
}

function handleMinChange(event: Event) {
  const input = event.target as HTMLInputElement
  const value = input.value ? parseFloat(input.value) : undefined
  emit('update:minAmount', value)
}

function handleMaxChange(event: Event) {
  const input = event.target as HTMLInputElement
  const value = input.value ? parseFloat(input.value) : undefined
  emit('update:maxAmount', value)
}

function clearValues() {
  localMin.value = ''
  localMax.value = ''
  emit('update:minAmount', undefined)
  emit('update:maxAmount', undefined)
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
    <label class="mb-1 block text-sm text-muted">Value</label>

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
      class="absolute left-0 top-full z-30 mt-1 w-full min-w-[200px] rounded-lg border border-border bg-surface shadow-lg"
    >
      <!-- Amount inputs -->
      <div class="space-y-3 p-3">
        <!-- Min amount -->
        <div>
          <label class="mb-1 block text-xs text-muted">Minimum</label>
          <input
            v-model="localMin"
            type="number"
            step="0.01"
            placeholder="0.00"
            class="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            @change="handleMinChange"
            @click.stop
          />
        </div>

        <!-- Max amount -->
        <div>
          <label class="mb-1 block text-xs text-muted">Maximum</label>
          <input
            v-model="localMax"
            type="number"
            step="0.01"
            placeholder="0.00"
            class="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            @change="handleMaxChange"
            @click.stop
          />
        </div>
      </div>

      <!-- Clear button (when values are set) -->
      <div v-if="hasValue" class="border-t border-border p-2">
        <button
          type="button"
          class="w-full rounded px-2 py-1 text-sm text-muted transition-colors hover:bg-onyx hover:text-foreground"
          @click.stop="clearValues"
        >
          Clear values
        </button>
      </div>
    </div>
  </div>
</template>
