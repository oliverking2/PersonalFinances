<!-- ==========================================================================
TagSelector
Dropdown/popover for selecting tags to add to a transaction
============================================================================ -->

<script setup lang="ts">
import type { Tag } from '~/types/tags'

// Props
const props = defineProps<{
  availableTags: Tag[] // All user's tags
  selectedTagIds: string[] // Currently selected tag IDs
  loading?: boolean
}>()

// Emit events
const emit = defineEmits<{
  select: [tagId: string]
  deselect: [tagId: string]
  create: [name: string]
}>()

// Constants
const MAX_TAG_LENGTH = 30

// Local state
const searchQuery = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

// Compute dynamic width based on longest tag name
// Base: padding (24px) + colour dot (12px + 8px gap) + checkbox (16px + 8px gap) + buffer (16px) = ~84px
// Character width: ~7px per char at text-sm
const selectorWidth = computed(() => {
  const longestTag = props.availableTags.reduce(
    (max, tag) => Math.max(max, tag.name.length),
    0,
  )
  // Min width 140px, max width 280px
  const charWidth = 7
  const baseWidth = 84
  const calculatedWidth = baseWidth + longestTag * charWidth
  return Math.min(Math.max(calculatedWidth, 140), 280)
})

// Filter tags based on search
const filteredTags = computed(() => {
  if (!searchQuery.value.trim()) {
    return props.availableTags
  }
  const query = searchQuery.value.toLowerCase()
  return props.availableTags.filter((tag) =>
    tag.name.toLowerCase().includes(query),
  )
})

// Check if we should show "Create new tag" option
const showCreateOption = computed(() => {
  const trimmed = searchQuery.value.trim()
  if (!trimmed) return false
  // Only show if no exact match exists
  return !props.availableTags.some(
    (tag) => tag.name.toLowerCase() === trimmed.toLowerCase(),
  )
})

// Check if a tag is selected
function isSelected(tagId: string): boolean {
  return props.selectedTagIds.includes(tagId)
}

// Toggle tag selection
function toggleTag(tag: Tag) {
  if (isSelected(tag.id)) {
    emit('deselect', tag.id)
  } else {
    emit('select', tag.id)
  }
}

// Create new tag
function handleCreate() {
  const trimmed = searchQuery.value.trim()
  if (trimmed) {
    emit('create', trimmed)
    searchQuery.value = ''
  }
}

// Handle keyboard input
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && showCreateOption.value) {
    event.preventDefault()
    handleCreate()
  }
}

// Focus input on mount
onMounted(() => {
  inputRef.value?.focus()
})
</script>

<template>
  <div class="tag-selector" :style="{ width: `${selectorWidth}px` }">
    <!-- Search input -->
    <div class="search-container">
      <input
        ref="inputRef"
        v-model="searchQuery"
        type="text"
        placeholder="Search or create..."
        class="search-input"
        :maxlength="MAX_TAG_LENGTH"
        @keydown="handleKeydown"
      />
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading">Loading tags...</div>

    <!-- Tag list -->
    <div v-else class="tag-list">
      <!-- Create new option -->
      <button
        v-if="showCreateOption"
        type="button"
        class="tag-option create-option"
        @click="handleCreate"
      >
        <span class="create-icon">+</span>
        Create "{{ searchQuery.trim() }}"
      </button>

      <!-- Existing tags -->
      <button
        v-for="tag in filteredTags"
        :key="tag.id"
        type="button"
        class="tag-option"
        :class="{ selected: isSelected(tag.id) }"
        @click="toggleTag(tag)"
      >
        <!-- Colour indicator -->
        <span
          v-if="tag.colour"
          class="colour-dot"
          :style="{ backgroundColor: tag.colour }"
        />
        <span v-else class="colour-dot neutral" />

        <!-- Tag name -->
        <span class="tag-name">{{ tag.name }}</span>

        <!-- Checkbox indicator -->
        <span class="checkbox">
          <span v-if="isSelected(tag.id)" class="check">✓</span>
        </span>
      </button>

      <!-- Empty state -->
      <div v-if="filteredTags.length === 0 && !showCreateOption" class="empty">
        No tags found
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-selector {
  /* Container - width set dynamically via inline style */
  @apply flex flex-col overflow-hidden rounded-lg bg-surface shadow-lg;
  @apply border border-gray-700;
}

.search-container {
  /* Padding around input */
  @apply border-b border-gray-700 p-2;
}

.search-input {
  /* Full width input */
  @apply w-full rounded-md bg-gray-800 px-3 py-2;
  @apply text-sm text-foreground placeholder-gray-500;
  @apply border border-gray-700 outline-none;
  @apply focus:border-primary focus:ring-1 focus:ring-primary;
}

.tag-list {
  /* Scrollable list */
  @apply max-h-60 overflow-y-auto;
}

.tag-option {
  /* Button reset */
  @apply w-full border-none bg-transparent text-left;

  /* Layout */
  @apply flex items-center gap-2 px-3 py-2;

  /* Typography */
  @apply text-sm text-foreground;

  /* Hover state */
  @apply cursor-pointer hover:bg-gray-800;

  /* Selected state */
  &.selected {
    @apply bg-gray-800/50;
  }
}

.create-option {
  /* Slightly different style for create */
  @apply border-b border-gray-700 text-primary;
}

.create-icon {
  /* Plus icon */
  @apply flex h-4 w-4 items-center justify-center rounded-full bg-primary text-xs text-white;
}

.colour-dot {
  /* Small colour indicator */
  @apply h-3 w-3 flex-shrink-0 rounded-full;

  &.neutral {
    @apply bg-gray-600;
  }
}

.tag-name {
  /* Name takes remaining space */
  @apply flex-1 truncate;
}

.checkbox {
  /* Checkbox area */
  @apply flex h-4 w-4 items-center justify-center rounded border border-gray-600;
  @apply text-xs text-primary;
}

.check {
  /* Checkmark */
  @apply font-bold;
}

.loading,
.empty {
  /* Center text states */
  @apply px-3 py-4 text-center text-sm text-muted;
}
</style>
