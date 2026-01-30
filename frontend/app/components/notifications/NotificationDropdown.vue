<!-- ==========================================================================
NotificationDropdown
Dropdown panel showing list of recent notifications
============================================================================ -->

<script setup lang="ts">
import type { Notification } from '~/types/notifications'

defineProps<{
  notifications: Notification[]
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  markRead: [id: string]
  markAllRead: []
  delete: [id: string]
  close: []
}>()

function handleMarkRead(id: string) {
  emit('markRead', id)
}

function handleMarkAllRead() {
  emit('markAllRead')
}

function handleDelete(id: string) {
  emit('delete', id)
}
</script>

<template>
  <!-- Dropdown panel -->
  <!-- Position: anchored to right edge, below the bell icon -->
  <div
    class="absolute right-0 top-full mt-2 w-80 rounded-lg border border-border bg-surface shadow-xl sm:w-96"
  >
    <!-- Header -->
    <div
      class="flex items-center justify-between border-b border-border px-4 py-3"
    >
      <h3 class="font-medium text-foreground">Notifications</h3>

      <!-- Mark all as read button (only show if there are unread notifications) -->
      <button
        v-if="notifications.some((n) => !n.read)"
        type="button"
        class="text-xs text-primary transition-colors hover:text-primary-hover"
        @click="handleMarkAllRead"
      >
        Mark all as read
      </button>
    </div>

    <!-- Content -->
    <div class="max-h-96 overflow-y-auto">
      <!-- Loading state -->
      <div v-if="loading" class="flex items-center justify-center py-8">
        <div
          class="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"
        />
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="px-4 py-8 text-center text-sm text-red-400">
        {{ error }}
      </div>

      <!-- Empty state -->
      <div
        v-else-if="notifications.length === 0"
        class="px-4 py-8 text-center text-sm text-muted"
      >
        No notifications
      </div>

      <!-- Notification list -->
      <div v-else class="divide-y divide-border/50">
        <NotificationsNotificationItem
          v-for="notification in notifications"
          :key="notification.id"
          :notification="notification"
          @mark-read="handleMarkRead"
          @delete="handleDelete"
        />
      </div>
    </div>

    <!-- Footer -->
    <div class="border-t border-border px-4 py-2">
      <button
        type="button"
        class="w-full text-center text-xs text-muted transition-colors hover:text-foreground"
        @click="emit('close')"
      >
        Close
      </button>
    </div>
  </div>
</template>
