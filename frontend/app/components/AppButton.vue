<script setup lang="ts">
defineProps<{
  type?: 'submit' | 'button' | 'reset'
}>()
</script>

<template>
  <button :type="type"><slot /></button>
</template>

<style scoped>
button {
  /* Layout & sizing */
  @apply mt-2 w-fit self-center rounded-full px-12 py-2;

  /* Colors & reset browser defaults */
  @apply border-none bg-primary text-white outline-none;

  /* Smooth transitions for hover/active states */
  @apply transition-all duration-200;

  /* Hover: grow slightly, lighten, add shadow */
  @apply hover:scale-105 hover:bg-primary/80 hover:shadow-lg;

  /* Focus: visible ring for keyboard navigation */
  @apply focus:ring-2 focus:ring-primary;

  /* Active/click: shrink slightly for "press" feedback */
  @apply active:scale-95;
}
</style>
