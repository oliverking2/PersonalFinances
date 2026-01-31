<!-- ==========================================================================
NotificationItem
Displays a single notification with icon, message, and actions
============================================================================ -->

<script setup lang="ts">
import type {
  Notification,
  ExportNotificationMetadata,
} from '~/types/notifications'
import {
  getNotificationTypeColour,
  getNotificationTypeBgColour,
  formatNotificationTime,
  isErrorNotification,
  isWarningNotification,
} from '~/types/notifications'

const props = defineProps<{
  notification: Notification
}>()

const emit = defineEmits<{
  markRead: [id: string]
  delete: [id: string]
}>()

// Determine icon based on notification type
const iconPath = computed(() => {
  const type = props.notification.notification_type

  // Warning icon (triangle with exclamation)
  if (isWarningNotification(type)) {
    return 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z'
  }

  // Error icon (circle with exclamation)
  if (isErrorNotification(type)) {
    return 'M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z'
  }

  // Success icon (check circle)
  return 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
})

// ---------------------------------------------------------------------------
// Action configuration based on notification type
// ---------------------------------------------------------------------------

interface NotificationAction {
  label: string
  href?: string // For navigation links
  download?: string // For download links (opens in new tab with download)
}

const action = computed<NotificationAction | null>(() => {
  const type = props.notification.notification_type
  const metadata = props.notification.metadata

  switch (type) {
    case 'export_complete': {
      const exportMeta = metadata as unknown as ExportNotificationMetadata
      if (exportMeta.download_url) {
        return {
          label: 'Download',
          download: exportMeta.download_url,
        }
      }
      return null
    }

    case 'export_failed':
      // Link back to datasets page to retry
      return {
        label: 'View Datasets',
        href: '/insights/analytics/datasets',
      }

    case 'budget_warning':
    case 'budget_exceeded':
      return {
        label: 'View Budgets',
        href: '/planning/budgets',
      }

    case 'sync_complete':
    case 'sync_failed':
      return {
        label: 'View Accounts',
        href: '/settings/accounts',
      }

    default:
      return null
  }
})

function handleMarkRead() {
  emit('markRead', props.notification.id)
}

function handleDelete() {
  emit('delete', props.notification.id)
}
</script>

<template>
  <div
    class="group flex items-start gap-3 rounded-lg p-3 transition-colors"
    :class="[
      notification.read
        ? 'bg-transparent opacity-60'
        : 'bg-white/5 hover:bg-white/10',
    ]"
  >
    <!-- Icon with coloured background -->
    <div
      class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
      :class="getNotificationTypeBgColour(notification.notification_type)"
    >
      <svg
        class="h-4 w-4"
        :class="getNotificationTypeColour(notification.notification_type)"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" :d="iconPath" />
      </svg>
    </div>

    <!-- Content -->
    <div class="min-w-0 flex-1">
      <!-- Title -->
      <p
        class="text-sm font-medium"
        :class="notification.read ? 'text-muted' : 'text-foreground'"
      >
        {{ notification.title }}
      </p>

      <!-- Message -->
      <p class="mt-0.5 text-sm text-muted">
        {{ notification.message }}
      </p>

      <!-- Action button (type-specific) -->
      <div v-if="action" class="mt-2">
        <!-- Download link (opens in new tab) -->
        <a
          v-if="action.download"
          :href="action.download"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 rounded bg-primary/20 px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/30"
          @click.stop
        >
          <!-- Download icon -->
          <svg
            class="h-3 w-3"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
            />
          </svg>
          {{ action.label }}
        </a>

        <!-- Navigation link -->
        <NuxtLink
          v-else-if="action.href"
          :to="action.href"
          class="inline-flex items-center gap-1 rounded bg-white/10 px-2 py-1 text-xs font-medium text-muted transition-colors hover:bg-white/20 hover:text-foreground"
          @click.stop
        >
          {{ action.label }}
          <!-- Arrow icon -->
          <svg
            class="h-3 w-3"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
            />
          </svg>
        </NuxtLink>
      </div>

      <!-- Timestamp -->
      <p class="mt-1 text-xs text-muted/70">
        {{ formatNotificationTime(notification.created_at) }}
      </p>
    </div>

    <!-- Actions (visible on hover or when unread) -->
    <div
      class="flex shrink-0 items-center gap-1"
      :class="notification.read ? 'opacity-0 group-hover:opacity-100' : ''"
    >
      <!-- Mark as read button (only show if unread) -->
      <button
        v-if="!notification.read"
        type="button"
        title="Mark as read"
        class="rounded p-1 text-muted transition-colors hover:bg-white/10 hover:text-foreground"
        @click.stop="handleMarkRead"
      >
        <svg
          class="h-4 w-4"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M4.5 12.75l6 6 9-13.5"
          />
        </svg>
      </button>

      <!-- Delete button -->
      <button
        type="button"
        title="Delete notification"
        class="rounded p-1 text-muted transition-colors hover:bg-red-500/20 hover:text-red-400"
        @click.stop="handleDelete"
      >
        <svg
          class="h-4 w-4"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  </div>
</template>
