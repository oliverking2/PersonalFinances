<!-- ==========================================================================
FilterDropdown
Reusable dropdown for filtering (tags, accounts, etc.)
Supports both multi-select (default) and single-select modes.
Multi-select shows checkboxes; single-select shows checkmarks and auto-closes.
Uses Teleport to render dropdown panel at body level to avoid clipping in modals.
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
export interface FilterOption {
  id: string
  label: string
  colour?: string | null // Optional colour for visual indicator
}

const props = defineProps<{
  label: string // Label shown above the dropdown
  placeholder: string // Placeholder when nothing selected
  options: FilterOption[]
  selectedIds: string[] // Currently selected option IDs
  multiSelect?: boolean // Allow multiple selections (default: true)
  searchable?: boolean // Show search input (default: true)
  manageLink?: string // Optional link to management page
  manageLinkText?: string // Text for manage link (default: "Manage")
}>()

const emit = defineEmits<{
  'update:selectedIds': [ids: string[]]
}>()

// ---------------------------------------------------------------------------
// Local State
// ---------------------------------------------------------------------------

const isOpen = ref(false)
const searchQuery = ref('')
const triggerRef = ref<HTMLButtonElement | null>(null)
const panelRef = ref<HTMLDivElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)

// Panel positioning
const panelStyle = ref({
  top: '0px',
  left: '0px',
  width: '0px',
})

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Filter options by search query
const filteredOptions = computed(() => {
  if (!searchQuery.value) return props.options
  const query = searchQuery.value.toLowerCase()
  return props.options.filter((opt) => opt.label.toLowerCase().includes(query))
})

// Get selected options for display
const selectedOptions = computed(() => {
  return props.options.filter((opt) => props.selectedIds.includes(opt.id))
})

// Display text when dropdown is closed
const displayText = computed(() => {
  if (selectedOptions.value.length === 0) return props.placeholder
  if (selectedOptions.value.length === 1) return selectedOptions.value[0]!.label
  return `${selectedOptions.value.length} selected`
})

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

function updatePanelPosition() {
  if (!triggerRef.value) return

  const rect = triggerRef.value.getBoundingClientRect()
  panelStyle.value = {
    top: `${rect.bottom + window.scrollY + 4}px`,
    left: `${rect.left + window.scrollX}px`,
    width: `${rect.width}px`,
  }
}

function toggleDropdown() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    searchQuery.value = ''
    updatePanelPosition()
    // Auto-focus the search input when dropdown opens
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  }
}

function isSelected(id: string): boolean {
  return props.selectedIds.includes(id)
}

function toggleOption(id: string) {
  const multiSelect = props.multiSelect !== false // Default to true

  if (isSelected(id)) {
    // Deselect
    emit(
      'update:selectedIds',
      props.selectedIds.filter((selectedId) => selectedId !== id),
    )
  } else {
    // Select
    if (multiSelect) {
      emit('update:selectedIds', [...props.selectedIds, id])
    } else {
      // Single select - replace selection
      emit('update:selectedIds', [id])
      isOpen.value = false
    }
  }
}

function clearSelection() {
  emit('update:selectedIds', [])
}

// Close dropdown when clicking outside (check both trigger and panel)
function handleClickOutside(event: MouseEvent) {
  const target = event.target as Node
  const clickedTrigger = triggerRef.value?.contains(target)
  const clickedPanel = panelRef.value?.contains(target)

  if (!clickedTrigger && !clickedPanel) {
    isOpen.value = false
  }
}

// Update position on scroll/resize when open
function handleScrollOrResize() {
  if (isOpen.value) {
    updatePanelPosition()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('scroll', handleScrollOrResize, true)
  window.addEventListener('resize', handleScrollOrResize)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('scroll', handleScrollOrResize, true)
  window.removeEventListener('resize', handleScrollOrResize)
})
</script>

<template>
  <div class="relative">
    <!-- Label row with optional manage link -->
    <div class="mb-1 flex items-center justify-between">
      <label class="text-sm text-muted">{{ label }}</label>
      <NuxtLink
        v-if="manageLink"
        :to="manageLink"
        class="text-xs text-primary hover:underline"
      >
        {{ manageLinkText || 'Manage' }}
      </NuxtLink>
    </div>

    <!-- Dropdown trigger button -->
    <button
      ref="triggerRef"
      type="button"
      class="flex w-full items-center justify-between rounded-lg border border-border bg-surface px-3 py-2 text-left transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      :class="isOpen ? 'border-primary ring-1 ring-primary' : ''"
      @click="toggleDropdown"
    >
      <!-- Selected chips or placeholder -->
      <div class="flex min-w-0 flex-1 flex-wrap gap-1">
        <template
          v-if="selectedOptions.length > 0 && selectedOptions.length <= 2"
        >
          <!-- Show chips for 1-2 selections -->
          <span
            v-for="opt in selectedOptions"
            :key="opt.id"
            class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs"
            :style="
              opt.colour
                ? { backgroundColor: opt.colour + '20', color: opt.colour }
                : {}
            "
            :class="!opt.colour ? 'bg-gray-700 text-gray-300' : ''"
          >
            <span
              v-if="opt.colour"
              class="h-2 w-2 rounded-full"
              :style="{ backgroundColor: opt.colour }"
            />
            {{ opt.label }}
          </span>
        </template>
        <span
          v-else
          class="truncate"
          :class="selectedOptions.length > 0 ? 'text-foreground' : 'text-muted'"
        >
          {{ displayText }}
        </span>
      </div>

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

    <!-- Dropdown panel - teleported to body to avoid modal clipping -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="fixed z-[60] min-w-[200px] rounded-lg border border-border bg-surface shadow-lg"
        :style="panelStyle"
      >
        <!-- Search input -->
        <div v-if="searchable !== false" class="border-b border-border p-2">
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            placeholder="Search..."
            class="w-full rounded border border-border bg-background px-2 py-1 text-sm text-foreground placeholder:text-muted focus:border-primary focus:outline-none"
            @click.stop
          />
        </div>

        <!-- Options list -->
        <div class="max-h-48 overflow-y-auto p-1">
          <div
            v-if="filteredOptions.length === 0"
            class="px-3 py-2 text-sm text-muted"
          >
            No options found
          </div>

          <button
            v-for="option in filteredOptions"
            :key="option.id"
            type="button"
            class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-onyx"
            @click.stop="toggleOption(option.id)"
          >
            <!-- Checkbox for multi-select mode -->
            <span
              v-if="multiSelect !== false"
              class="flex h-4 w-4 items-center justify-center rounded border"
              :class="
                isSelected(option.id)
                  ? 'border-primary bg-primary'
                  : 'border-gray-600 bg-transparent'
              "
            >
              <svg
                v-if="isSelected(option.id)"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                class="h-3 w-3 text-background"
              >
                <path
                  fill-rule="evenodd"
                  d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                  clip-rule="evenodd"
                />
              </svg>
            </span>

            <!-- Simple checkmark for single-select mode (only shown when selected) -->
            <svg
              v-else-if="isSelected(option.id)"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              class="h-4 w-4 text-primary"
            >
              <path
                fill-rule="evenodd"
                d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                clip-rule="evenodd"
              />
            </svg>
            <!-- Empty spacer for unselected items in single-select to keep alignment -->
            <span v-else class="h-4 w-4" />

            <!-- Colour dot (if present) -->
            <span
              v-if="option.colour"
              class="h-3 w-3 rounded-full"
              :style="{ backgroundColor: option.colour }"
            />

            <!-- Label -->
            <span class="text-foreground">{{ option.label }}</span>
          </button>
        </div>

        <!-- Clear button (when items selected) -->
        <div v-if="selectedIds.length > 0" class="border-t border-border p-2">
          <button
            type="button"
            class="w-full rounded px-2 py-1 text-sm text-muted transition-colors hover:bg-onyx hover:text-foreground"
            @click.stop="clearSelection"
          >
            Clear selection
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>
