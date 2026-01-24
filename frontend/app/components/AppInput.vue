<!-- ==========================================================================
AppInput
Reusable text input component with consistent styling
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props
// modelValue + emit enable v-model on this component
// Usage: <AppInput v-model="myValue" type="email" placeholder="Email" />
// ---------------------------------------------------------------------------
defineProps<{
  modelValue: string
  type?: 'text' | 'password' | 'email' | 'number'
  placeholder?: string
  required?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

// Handle input events and emit to parent
function onInput(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <input
    :type="type ?? 'text'"
    :value="modelValue"
    :placeholder="placeholder"
    :required="required"
    @input="onInput"
  />
</template>

<style scoped>
input {
  /* Layout: full width with padding */
  @apply w-full rounded-lg px-4 py-3;

  /* Colours: dark input with light text */
  @apply border border-border bg-onyx text-foreground;

  /* Placeholder text colour */
  @apply placeholder:text-muted;

  /* Focus state: highlight border */
  @apply focus:border-emerald focus:outline-none focus:ring-2 focus:ring-emerald/50;
}
</style>
