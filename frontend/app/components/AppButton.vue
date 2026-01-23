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
  @apply mt-2 w-fit self-center rounded-full bg-primary px-12 py-2 text-white transition-all duration-200 hover:scale-105 hover:bg-primary/80 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary active:scale-95;
}
</style>
