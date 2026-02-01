<!-- ==========================================================================
Default Layout
Used by all authenticated pages - provides header, footer, and content area
============================================================================ -->

<script setup lang="ts">
const authStore = useAuthStore()
const route = useRoute()

// ---------------------------------------------------------------------------
// Mobile menu state
// ---------------------------------------------------------------------------
const mobileMenuOpen = ref(false)

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

// ---------------------------------------------------------------------------
// Navigation links - simplified to 5 top-level items
// ---------------------------------------------------------------------------
const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/planning', label: 'Planning' },
  { to: '/insights', label: 'Insights' },
  { to: '/settings', label: 'Settings' },
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
        <!-- Left side: Hamburger (mobile) + App name + nav links -->
        <div class="flex items-center gap-4 sm:gap-6">
          <!-- Hamburger button - visible on mobile only -->
          <button
            type="button"
            class="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-foreground sm:hidden"
            aria-label="Open menu"
            @click="mobileMenuOpen = true"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
              class="h-6 w-6"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
              />
            </svg>
          </button>

          <!-- App name - clickable to go home -->
          <NuxtLink to="/" class="font-display text-xl font-bold sm:text-2xl">
            Personal Finances
          </NuxtLink>

          <!-- Navigation links - desktop only -->
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

        <!-- Right side: User info, notifications, and logout -->
        <div class="flex items-center gap-4">
          <!-- Show user's name on larger screens -->
          <span
            v-if="authStore.displayName"
            class="hidden text-muted md:inline"
          >
            {{ authStore.displayName }}
          </span>

          <!-- Notification bell with dropdown -->
          <NotificationsNotificationBell />

          <AppButton type="button" @click="logout">Logout</AppButton>
        </div>
      </nav>
    </header>

    <!-- Mobile navigation drawer -->
    <!-- Teleport to body to avoid z-index issues -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="mobileMenuOpen"
          class="fixed inset-0 z-[200] bg-black/50 sm:hidden"
          aria-hidden="true"
          @click="closeMobileMenu"
        />
      </Transition>
      <Transition name="slide">
        <nav
          v-if="mobileMenuOpen"
          class="fixed inset-y-0 left-0 z-[201] flex w-64 flex-col bg-surface sm:hidden"
        >
          <!-- Drawer header with close button -->
          <div
            class="flex items-center justify-between border-b border-border px-4 py-3"
          >
            <span class="font-display text-lg font-bold">Menu</span>
            <button
              type="button"
              class="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-foreground"
              aria-label="Close menu"
              @click="closeMobileMenu"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="h-6 w-6"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M6 18 18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <!-- Navigation links -->
          <div class="flex-1 overflow-y-auto px-2 py-4">
            <NuxtLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              class="block rounded-md px-3 py-2.5 text-base font-medium transition-colors"
              :class="
                isActiveLink(link.to)
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted hover:bg-white/5 hover:text-foreground'
              "
              @click="closeMobileMenu"
            >
              {{ link.label }}
            </NuxtLink>
          </div>

          <!-- Logout at bottom -->
          <div class="border-t border-border px-4 py-4">
            <button
              type="button"
              class="w-full rounded-md bg-white/5 px-3 py-2.5 text-base font-medium text-muted transition-colors hover:bg-white/10 hover:text-foreground"
              @click="logout"
            >
              Logout
            </button>
          </div>
        </nav>
      </Transition>
    </Teleport>

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

<style scoped>
/* Fade transition for overlay */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Slide transition for drawer */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}
</style>
