<!-- ==========================================================================
Default Layout
Used by all authenticated pages - provides header, footer, and content area
============================================================================ -->

<script setup lang="ts">
const authStore = useAuthStore()

// ---------------------------------------------------------------------------
// Logout handler
// Optimistic: redirect immediately, API call in background
// The slow backend token lookup shouldn't block the user
// ---------------------------------------------------------------------------
function logout() {
  // Fire and forget - don't wait for the slow API call
  authStore.logout().catch(() => {
    // Ignore errors - user is logged out locally regardless
    // Worst case: orphaned token expires on its own
  })

  // Redirect immediately for instant feedback
  navigateTo('/login')
}
</script>

<template>
  <!-- Full page container with dark background -->
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <!-- Header -->
    <!-- sticky top-0: stays at top when scrolling -->
    <!-- z-10: above page content for proper layering -->
    <header class="sticky top-0 z-10 border-b border-border bg-surface">
      <!-- px-4 sm:px-6: more padding on larger screens -->
      <nav class="flex items-center justify-between px-4 py-3 sm:px-6">
        <!-- App name - clickable to go home -->
        <NuxtLink
          to="/dashboard"
          class="font-display text-xl font-bold sm:text-2xl"
        >
          Personal Finances
        </NuxtLink>

        <!-- User info and logout -->
        <div class="flex items-center gap-4">
          <!-- Show user's name on larger screens -->
          <span
            v-if="authStore.displayName"
            class="hidden text-muted sm:inline"
          >
            {{ authStore.displayName }}
          </span>
          <AppButton type="button" @click="logout">Logout</AppButton>
        </div>
      </nav>
    </header>

    <!-- Main content area -->
    <!-- flex-1: takes remaining vertical space -->
    <!-- p-4 sm:p-6: responsive padding -->
    <main class="flex-1 p-4 sm:p-6">
      <slot />
    </main>

    <!-- Footer -->
    <footer
      class="border-t border-border px-4 py-4 text-center text-sm text-muted sm:px-6"
    >
      Personal Finances App
    </footer>
  </div>
</template>
