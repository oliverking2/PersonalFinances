<!-- ==========================================================================
AppButton
Reusable button component with consistent styling
============================================================================ -->

<script setup lang="ts">
defineProps<{
  type?: 'submit' | 'button' | 'reset'
}>()
</script>

<template>
  <button :type="type">
    <slot />
  </button>
</template>

<style scoped>
button {
  /* Layout: centered pill shape */
  @apply w-fit self-center rounded-full px-8 py-2 sm:px-12;

  /* Typography */
  @apply font-sans text-sm font-semibold sm:text-base;

  /* Colours: emerald primary with white text */
  @apply border-none bg-primary text-white outline-none;

  /* Smooth transitions for interactive states */
  @apply transition-all duration-200;

  /* Hover: darken and lift slightly */
  @apply hover:scale-105 hover:bg-primary-hover hover:shadow-lg;

  /* Focus: visible ring for keyboard navigation (accessibility) */
  @apply focus:ring-2 focus:ring-sage focus:ring-offset-2 focus:ring-offset-surface;

  /* Active/click: press down effect */
  @apply active:scale-95;
}
</style>
