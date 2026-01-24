<!-- ==========================================================================
StatusIndicator
Badge component showing connection/account status with appropriate colours
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props
// status: The current status to display
// ---------------------------------------------------------------------------
const props = defineProps<{
  status: 'active' | 'expired' | 'pending' | 'error'
}>()

// ---------------------------------------------------------------------------
// Status configuration
// Maps status to display label and colour class
// ---------------------------------------------------------------------------
const statusConfig = computed(() => {
  switch (props.status) {
    case 'active':
      return { label: 'Connected', colorClass: 'text-positive bg-positive/10' }
    case 'expired':
      return { label: 'Expired', colorClass: 'text-negative bg-negative/10' }
    case 'pending':
      return { label: 'Pending', colorClass: 'text-warning bg-warning/10' }
    case 'error':
      return { label: 'Error', colorClass: 'text-negative bg-negative/10' }
    default:
      return { label: 'Unknown', colorClass: 'text-muted bg-muted/10' }
  }
})
</script>

<template>
  <!-- Badge with rounded corners and subtle background -->
  <span
    class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
    :class="statusConfig.colorClass"
  >
    {{ statusConfig.label }}
  </span>
</template>
