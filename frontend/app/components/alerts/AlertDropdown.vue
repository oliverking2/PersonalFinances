<!-- ==========================================================================
AlertDropdown
Dropdown showing recent alerts with quick actions
============================================================================ -->

<script setup lang="ts">
import type { Alert } from '~/types/alerts'
import {
  formatAlertMessage,
  getAlertTypeBgColour,
  getAlertTypeColour,
} from '~/types/alerts'

// Emits
const emit = defineEmits<{
  acknowledge: [id: string]
  acknowledgeAll: []
  close: []
}>()

// Format date as relative
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

// Props (need reference for computed)
const props = defineProps<{
  alerts: Alert[]
  loading?: boolean
}>()

// Pending alerts (not acknowledged)
const pendingAlerts = computed(() =>
  props.alerts.filter((a: Alert) => a.status === 'pending'),
)
</script>

<template>
  <div class="alert-dropdown">
    <!-- Header -->
    <div
      class="flex items-center justify-between border-b border-border px-4 py-3"
    >
      <h3 class="font-semibold">Alerts</h3>
      <button
        v-if="pendingAlerts.length > 0"
        type="button"
        class="text-sm text-primary hover:underline"
        @click="emit('acknowledgeAll')"
      >
        Mark all read
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex items-center justify-center py-8">
      <div
        class="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent"
      />
    </div>

    <!-- Empty state -->
    <div v-else-if="alerts.length === 0" class="px-4 py-8 text-center">
      <svg
        class="mx-auto h-8 w-8 text-muted"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fill-rule="evenodd"
          d="M10 2a6 6 0 00-6 6c0 1.887-.454 3.665-1.257 5.234a.75.75 0 00.515 1.076 32.91 32.91 0 003.256.508 3.5 3.5 0 006.972 0 32.903 32.903 0 003.256-.508.75.75 0 00.515-1.076A11.448 11.448 0 0116 8a6 6 0 00-6-6zM8.05 14.943a33.54 33.54 0 003.9 0 2 2 0 01-3.9 0z"
          clip-rule="evenodd"
        />
      </svg>
      <p class="mt-2 text-sm text-muted">No alerts</p>
    </div>

    <!-- Alert list -->
    <div v-else class="max-h-80 overflow-y-auto">
      <div
        v-for="alert in alerts"
        :key="alert.id"
        class="alert-item"
        :class="{ 'opacity-60': alert.status === 'acknowledged' }"
      >
        <!-- Alert icon -->
        <div
          class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full"
          :class="getAlertTypeBgColour(alert.alert_type)"
        >
          <!-- Warning icon -->
          <svg
            v-if="alert.alert_type === 'budget_warning'"
            class="h-4 w-4"
            :class="getAlertTypeColour(alert.alert_type)"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
              clip-rule="evenodd"
            />
          </svg>
          <!-- Exceeded icon -->
          <svg
            v-else
            class="h-4 w-4"
            :class="getAlertTypeColour(alert.alert_type)"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
              clip-rule="evenodd"
            />
          </svg>
        </div>

        <!-- Alert content -->
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium">{{ formatAlertMessage(alert) }}</p>
          <p class="text-xs text-muted">{{ formatDate(alert.created_at) }}</p>
        </div>

        <!-- Acknowledge button (only for pending) -->
        <button
          v-if="alert.status === 'pending'"
          type="button"
          class="flex-shrink-0 rounded-lg p-1.5 text-muted hover:bg-gray-700/50 hover:text-foreground"
          title="Mark as read"
          @click="emit('acknowledge', alert.id)"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- Footer link -->
    <div v-if="alerts.length > 0" class="border-t border-border px-4 py-3">
      <NuxtLink
        to="/budgets"
        class="block text-center text-sm text-primary hover:underline"
        @click="emit('close')"
      >
        View all budgets
      </NuxtLink>
    </div>
  </div>
</template>

<style scoped>
.alert-dropdown {
  @apply w-80 rounded-xl border border-border bg-surface shadow-xl;
}

.alert-item {
  @apply flex items-start gap-3 px-4 py-3;
  @apply border-b border-border last:border-b-0;
  @apply hover:bg-gray-700/30;
}
</style>
