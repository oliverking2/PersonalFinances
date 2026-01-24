<!-- ==========================================================================
AppToast
Global toast notification container - displays stacked toasts in bottom-right
============================================================================ -->

<script setup lang="ts">
import { useToastStore, type Toast } from '~/stores/toast'

const toastStore = useToastStore()

// Icon paths for each toast type (Heroicons)
const icons: Record<Toast['type'], string> = {
  success: 'M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  error:
    'M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z',
  info: 'm11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z',
}
</script>

<template>
  <!-- Toast container: fixed in bottom-right corner, stacked vertically -->
  <Teleport to="body">
    <div
      class="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
      aria-live="polite"
    >
      <TransitionGroup name="toast">
        <div
          v-for="toast in toastStore.toasts"
          :key="toast.id"
          :class="[
            'flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg',
            'min-w-[280px] max-w-[400px]',
            // Background and border colours based on toast type
            toast.type === 'success' && 'border-primary/30 bg-primary/10',
            toast.type === 'error' && 'border-negative/30 bg-negative/10',
            toast.type === 'info' && 'border-sage/30 bg-sage/10',
          ]"
        >
          <!-- Icon -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            :class="[
              'h-5 w-5 flex-shrink-0',
              toast.type === 'success' && 'text-primary',
              toast.type === 'error' && 'text-negative',
              toast.type === 'info' && 'text-sage',
            ]"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              :d="icons[toast.type]"
            />
          </svg>

          <!-- Message -->
          <p
            :class="[
              'flex-1 text-sm',
              toast.type === 'success' && 'text-primary',
              toast.type === 'error' && 'text-negative',
              toast.type === 'info' && 'text-sage',
            ]"
          >
            {{ toast.message }}
          </p>

          <!-- Dismiss button -->
          <button
            type="button"
            class="flex-shrink-0 rounded p-1 text-muted transition-colors hover:bg-border hover:text-foreground"
            @click="toastStore.removeToast(toast.id)"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              class="h-4 w-4"
            >
              <path
                d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
              />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
/* Slide-in from right animation for toasts */
.toast-enter-active {
  transition: all 0.3s ease-out;
}

.toast-leave-active {
  transition: all 0.2s ease-in;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

/* Smooth repositioning when toasts are added/removed */
.toast-move {
  transition: transform 0.3s ease;
}
</style>
