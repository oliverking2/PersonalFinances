// =============================================================================
// Toast Store
// Manages toast notification state for user feedback messages
// =============================================================================

import { defineStore } from 'pinia'

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export type ToastType = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
}

// =============================================================================
// Store Definition
// =============================================================================

export const useToastStore = defineStore('toast', () => {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  // Active toasts to display
  const toasts = ref<Toast[]>([])

  // Auto-incrementing ID for unique toast identification
  let nextId = 1

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  // Add a toast with auto-dismiss after duration (default 5 seconds)
  function addToast(type: ToastType, message: string, duration = 5000) {
    const id = nextId++
    toasts.value.push({ id, type, message })

    // Auto-dismiss after duration
    setTimeout(() => {
      removeToast(id)
    }, duration)

    return id
  }

  // Remove a specific toast by ID
  function removeToast(id: number) {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  // Convenience methods for each toast type
  function success(message: string, duration?: number) {
    return addToast('success', message, duration)
  }

  function error(message: string, duration?: number) {
    return addToast('error', message, duration)
  }

  function info(message: string, duration?: number) {
    return addToast('info', message, duration)
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // State
    toasts,

    // Actions
    addToast,
    removeToast,
    success,
    error,
    info,
  }
})
