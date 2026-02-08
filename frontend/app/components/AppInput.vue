<!-- ==========================================================================
AppInput
Reusable text input component with consistent styling
Supports both text and number types with proper value handling
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props
// modelValue + emit enable v-model on this component
// Usage: <AppInput v-model="myValue" type="email" placeholder="Email" />
// For numbers: <AppInput v-model="numValue" type="number" :min="0" :step="0.01" />
// ---------------------------------------------------------------------------
const props = defineProps<{
  modelValue: string | number | null
  type?: 'text' | 'password' | 'email' | 'number'
  placeholder?: string
  required?: boolean
  prefix?: string
  autofocus?: boolean
  // Number-specific props (accept string or number since HTML attributes are strings)
  min?: number | string
  max?: number | string
  step?: number | string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
}>()

// Handle input events and emit to parent
// For number types, emit as number (or null if empty)
function onInput(event: Event) {
  const target = event.target as HTMLInputElement
  if (props.type === 'number') {
    // For number inputs, emit number or null if empty
    emit('update:modelValue', target.value === '' ? null : Number(target.value))
  } else {
    emit('update:modelValue', target.value)
  }
}

// Compute the display value for the input
// Numbers need to be converted to string, null shows empty
const displayValue = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined) {
    return ''
  }
  return String(props.modelValue)
})
</script>

<template>
  <div class="input-wrapper">
    <span v-if="prefix" class="input-prefix">{{ prefix }}</span>

    <input
      :type="type ?? 'text'"
      :value="displayValue"
      :placeholder="placeholder"
      :required="required"
      :autofocus="autofocus"
      :min="min"
      :max="max"
      :step="step"
      @input="onInput"
    />
  </div>
</template>

<style scoped>
input {
  /* Layout: full width with padding */
  @apply w-full rounded-lg py-3 pl-8 pr-4;

  /* Colours: dark input with light text */
  @apply border border-border bg-onyx text-foreground;

  /* Placeholder text colour */
  @apply placeholder:text-muted;

  /* Focus state: highlight border */
  @apply focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50;
}

.input-wrapper {
  position: relative;
}

.input-prefix {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  @apply text-muted;
}
</style>
