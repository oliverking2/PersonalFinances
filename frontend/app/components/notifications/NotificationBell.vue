<!-- ==========================================================================
NotificationBell
Bell icon with unread count badge, toggles notification dropdown
============================================================================ -->

<script setup lang="ts">
import type { Notification } from '~/types/notifications'

// ---------------------------------------------------------------------------
// API and state
// ---------------------------------------------------------------------------
const {
  fetchNotifications,
  fetchUnreadCount,
  markAsRead,
  markAllAsRead,
  deleteNotification,
} = useNotificationsApi()

// State
const isOpen = ref(false)
const notifications = ref<Notification[]>([])
const unreadCount = ref(0)
const loading = ref(false)
const error = ref('')

// Polling interval ref for cleanup
let pollInterval: ReturnType<typeof setInterval> | null = null

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

// Fetch unread count (lightweight, for badge)
async function loadUnreadCount() {
  try {
    const response = await fetchUnreadCount()
    unreadCount.value = response.unread_count
  } catch (e) {
    // Silently fail - badge will just show 0
    console.error('Failed to fetch unread count:', e)
  }
}

// Fetch full notification list (when dropdown opens)
async function loadNotifications() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetchNotifications({ limit: 20 })
    notifications.value = response.notifications
    unreadCount.value = response.unread_count
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : 'Failed to load notifications'
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function toggleDropdown() {
  isOpen.value = !isOpen.value

  // Load notifications when opening
  if (isOpen.value) {
    loadNotifications()
  }
}

function closeDropdown() {
  isOpen.value = false
}

async function handleMarkRead(id: string) {
  try {
    await markAsRead(id)

    // Update local state
    const notification = notifications.value.find((n) => n.id === id)
    if (notification && !notification.read) {
      notification.read = true
      notification.read_at = new Date().toISOString()
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  } catch (e) {
    console.error('Failed to mark notification as read:', e)
  }
}

async function handleMarkAllRead() {
  try {
    await markAllAsRead()

    // Update local state
    notifications.value.forEach((n) => {
      if (!n.read) {
        n.read = true
        n.read_at = new Date().toISOString()
      }
    })
    unreadCount.value = 0
  } catch (e) {
    console.error('Failed to mark all notifications as read:', e)
  }
}

async function handleDelete(id: string) {
  try {
    await deleteNotification(id)

    // Update local state
    const notification = notifications.value.find((n) => n.id === id)
    if (notification && !notification.read) {
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
    notifications.value = notifications.value.filter((n) => n.id !== id)
  } catch (e) {
    console.error('Failed to delete notification:', e)
  }
}

// ---------------------------------------------------------------------------
// Click outside to close
// ---------------------------------------------------------------------------
const dropdownRef = ref<HTMLElement | null>(null)

function handleClickOutside(event: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    closeDropdown()
  }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  // Initial count fetch
  loadUnreadCount()

  // Poll for new notifications every 60 seconds
  pollInterval = setInterval(loadUnreadCount, 60000)

  // Listen for clicks outside
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  // Cleanup polling
  if (pollInterval) {
    clearInterval(pollInterval)
  }

  // Cleanup click listener
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="dropdownRef" class="relative">
    <!-- Bell button -->
    <button
      type="button"
      class="relative rounded-full p-2 text-muted transition-colors hover:bg-white/10 hover:text-foreground"
      title="Notifications"
      @click.stop="toggleDropdown"
    >
      <!-- Bell icon -->
      <svg
        class="h-5 w-5"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
        />
      </svg>

      <!-- Unread count badge -->
      <!-- Only show if there are unread notifications -->
      <span
        v-if="unreadCount > 0"
        class="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- Dropdown -->
    <NotificationsNotificationDropdown
      v-if="isOpen"
      :notifications="notifications"
      :loading="loading"
      :error="error"
      @mark-read="handleMarkRead"
      @mark-all-read="handleMarkAllRead"
      @delete="handleDelete"
      @close="closeDropdown"
    />
  </div>
</template>
