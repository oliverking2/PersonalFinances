<!-- ==========================================================================
AppSelect
Reusable dropdown select component with fully styled options
Built with divs/buttons for full styling control (not native <select>)
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  modelValue: string
  options: { value: string; label: string }[]
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const isOpen = ref(false)
const dropdownRef = ref<HTMLDivElement | null>(null)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Get the label for the currently selected value
const selectedLabel = computed(() => {
  const selected = props.options.find((opt) => opt.value === props.modelValue)
  return selected?.label || props.placeholder || 'Select...'
})

// Check if a value is currently selected
const hasSelection = computed(() => {
  return props.options.some((opt) => opt.value === props.modelValue)
})

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

function toggleDropdown() {
  isOpen.value = !isOpen.value
}

function selectOption(value: string) {
  emit('update:modelValue', value)
  isOpen.value = false
}

function clearSelection() {
  emit('update:modelValue', '')
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
    <!-- Dropdown trigger button (styled to match AppInput) -->
    <button
      type="button"
      class="flex w-full items-center justify-between rounded-lg border border-border bg-onyx px-4 py-3 text-left transition-colors focus:border-emerald focus:outline-none focus:ring-2 focus:ring-emerald/50"
      :class="isOpen ? 'border-emerald ring-2 ring-emerald/50' : ''"
      @click="toggleDropdown"
    >
      <!-- Selected value or placeholder -->
      <span :class="hasSelection ? 'text-foreground' : 'text-muted'">
        {{ selectedLabel }}
      </span>

      <!-- Chevron icon -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        class="h-5 w-5 text-muted transition-transform"
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
      class="absolute left-0 top-full z-50 mt-1 w-full rounded-lg border border-border bg-surface shadow-lg"
    >
      <!-- Options list -->
      <div class="max-h-60 overflow-y-auto p-1">
        <!-- Placeholder/clear option -->
        <button
          v-if="placeholder"
          type="button"
          class="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm transition-colors hover:bg-onyx"
          :class="!hasSelection ? 'text-primary' : 'text-muted'"
          @click="clearSelection"
        >
          <!-- Checkmark for selected state -->
          <svg
            v-if="!hasSelection"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            class="h-4 w-4"
          >
            <path
              fill-rule="evenodd"
              d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
              clip-rule="evenodd"
            />
          </svg>
          <span v-else class="h-4 w-4" />
          {{ placeholder }}
        </button>

        <!-- Actual options -->
        <button
          v-for="option in options"
          :key="option.value"
          type="button"
          class="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm transition-colors hover:bg-onyx"
          :class="
            modelValue === option.value ? 'text-primary' : 'text-foreground'
          "
          @click="selectOption(option.value)"
        >
          <!-- Checkmark for selected state -->
          <svg
            v-if="modelValue === option.value"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            class="h-4 w-4"
          >
            <path
              fill-rule="evenodd"
              d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
              clip-rule="evenodd"
            />
          </svg>
          <span v-else class="h-4 w-4" />
          {{ option.label }}
        </button>
      </div>
    </div>
  </div>
</template>
