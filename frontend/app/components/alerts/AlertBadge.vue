<!-- ==========================================================================
AlertBadge
Small badge showing pending alert count (for header/nav)
============================================================================ -->

<script setup lang="ts">
// Props
defineProps<{
  count: number
}>()
</script>

<template>
  <!-- Only show when there are pending alerts -->
  <div v-if="count > 0" class="alert-badge">
    {{ count > 99 ? '99+' : count }}
  </div>
</template>

<style scoped>
.alert-badge {
  @apply absolute -right-1 -top-1 flex h-5 min-w-[1.25rem] items-center justify-center;
  @apply rounded-full bg-red-500 px-1 text-xs font-bold text-white;
}
</style>
