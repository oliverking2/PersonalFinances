<!-- ==========================================================================
Default Layout
Used by all authenticated pages - provides header, footer, and content area
============================================================================ -->

<script setup lang="ts">
const authStore = useAuthStore()
const route = useRoute()

// ---------------------------------------------------------------------------
// Navigation links
// ---------------------------------------------------------------------------
const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/accounts', label: 'Accounts' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/subscriptions', label: 'Subscriptions' },
  { to: '/settings/tags', label: 'Settings' },
]

// Check if a nav link is active
// Home (/) only matches exactly, others match if route starts with the path
function isActiveLink(to: string): boolean {
  if (to === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(to)
}

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
    <!-- z-[100]: always above page content (dropdowns, popovers, sticky headers) -->
    <header class="sticky top-0 z-[100] border-b border-border bg-surface">
      <!-- px-4 sm:px-6: more padding on larger screens -->
      <nav class="flex items-center justify-between px-4 py-3 sm:px-6">
        <!-- Left side: App name + nav links -->
        <div class="flex items-center gap-6">
          <!-- App name - clickable to go home -->
          <NuxtLink to="/" class="font-display text-xl font-bold sm:text-2xl">
            Personal Finances
          </NuxtLink>

          <!-- Navigation links -->
          <!-- gap-1: tight spacing, each link has its own padding -->
          <div class="hidden items-center gap-1 sm:flex">
            <NuxtLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
              :class="
                isActiveLink(link.to)
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted hover:bg-white/5 hover:text-foreground'
              "
            >
              {{ link.label }}
            </NuxtLink>
          </div>
        </div>

        <!-- Right side: User info and logout -->
        <div class="flex items-center gap-4">
          <!-- Show user's name on larger screens -->
          <span
            v-if="authStore.displayName"
            class="hidden text-muted md:inline"
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
