<!-- ==========================================================================
TagChip
Display a single tag as a small coloured chip/pill
============================================================================ -->

<script setup lang="ts">
// Props
const props = defineProps<{
  name: string
  colour?: string | null // Hex colour for background
  removable?: boolean // Show remove button
}>()

// Emit events
const emit = defineEmits<{
  remove: []
}>()

// Compute styles based on colour
// If colour is provided, use it with reduced opacity for background
// If no colour, use a neutral background
const chipStyle = computed(() => {
  if (props.colour) {
    return {
      backgroundColor: `${props.colour}20`, // 20 = ~12% opacity in hex
      borderColor: props.colour,
      color: props.colour,
    }
  }
  return {}
})

function handleRemove(event: MouseEvent) {
  event.stopPropagation()
  emit('remove')
}
</script>

<template>
  <span class="tag-chip" :class="{ 'has-colour': colour }" :style="chipStyle">
    <!-- Tag name -->
    <span class="name">{{ name }}</span>

    <!-- Remove button (optional) -->
    <button
      v-if="removable"
      type="button"
      class="remove-btn"
      title="Remove tag"
      @click="handleRemove"
    >
      ×
    </button>
  </span>
</template>

<style scoped>
.tag-chip {
  /* Layout: inline flex pill */
  @apply inline-flex items-center gap-1 rounded-full px-2.5 py-1;

  /* Typography */
  @apply text-sm font-semibold;

  /* Default colours (when no colour prop) */
  @apply border border-gray-600 bg-gray-800 text-gray-300;

  /* When has custom colour, override defaults */
  &.has-colour {
    @apply border;
  }
}

.name {
  /* Truncate long names */
  @apply max-w-32 truncate;
}

.remove-btn {
  /* Reset button styles */
  @apply border-none bg-transparent p-0 leading-none;

  /* Size and shape */
  @apply ml-0.5 flex h-4 w-4 items-center justify-center rounded-full;

  /* Hover: highlight for visibility */
  @apply hover:bg-white/20;

  /* Typography */
  @apply text-sm font-bold text-current;

  /* Cursor */
  @apply cursor-pointer;
}
</style>
