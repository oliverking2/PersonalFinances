<!-- ==========================================================================
Login Page
Public page for user authentication via username/password
============================================================================ -->

<script setup lang="ts">
// Mark as public so auth middleware doesn't redirect to itself
definePageMeta({
  layout: false, // No default layout - standalone page
  public: true, // Skip auth middleware
})

const authStore = useAuthStore()

// ---------------------------------------------------------------------------
// Form state
// ref() creates reactive variables that auto-update the UI when changed
// v-model in template binds these to inputs (two-way binding)
// ---------------------------------------------------------------------------
const username = ref('')
const password = ref('')
const errorMessage = ref<string | null>(null)

// ---------------------------------------------------------------------------
// Form submission
// @submit.prevent calls this function and prevents page reload
// Browser handles basic validation via HTML5 attributes (required, etc.)
// ---------------------------------------------------------------------------
async function handleSubmit() {
  errorMessage.value = null

  try {
    await authStore.login(username.value, password.value)
    await navigateTo('/dashboard')
  } catch {
    errorMessage.value = 'Login failed. Please check your credentials.'

    // Auto-dismiss error after 3 seconds
    setTimeout(() => {
      errorMessage.value = null
    }, 3000)
  }
}
</script>

<template>
  <!-- Full-screen container with gradient background -->
  <!-- min-h-screen: at least viewport height -->
  <!-- flex items-center justify-center: center the card both ways -->
  <!-- px-4: padding on mobile to prevent edge-to-edge card -->
  <div
    class="flex min-h-screen flex-col items-center justify-center bg-background px-4"
  >
    <!-- Decorative background blobs (visual depth, no interaction) -->
    <!-- absolute: positioned relative to parent, blur-3xl: heavy blur effect -->
    <!-- hidden sm:block: hide on mobile to reduce visual noise -->
    <div
      class="absolute -left-20 top-20 hidden h-72 w-72 rounded-full bg-emerald opacity-20 blur-3xl sm:block"
    />
    <div
      class="absolute -right-20 bottom-20 hidden h-96 w-96 rounded-full bg-sage opacity-10 blur-3xl sm:block"
    />

    <!-- Login card -->
    <!-- relative: for absolute positioned error message -->
    <!-- w-full max-w-sm: responsive width with max constraint -->
    <div
      class="relative w-full max-w-sm rounded-xl border border-border bg-surface p-6 shadow-xl sm:p-8"
    >
      <!-- Error message (slides in/out) -->
      <Transition name="fade">
        <div
          v-if="errorMessage"
          class="absolute inset-x-2 top-2 rounded-md bg-negative/90 p-3 text-center text-sm font-medium text-white"
        >
          {{ errorMessage }}
        </div>
      </Transition>

      <!-- App title -->
      <h1
        class="pb-4 text-center font-display text-2xl font-bold text-foreground sm:text-3xl"
      >
        Personal Finances
      </h1>

      <!-- Login form -->
      <form class="flex flex-col gap-4 pt-6" @submit.prevent="handleSubmit">
        <AppInput
          v-model="username"
          type="text"
          placeholder="Username"
          required
        />
        <AppInput
          v-model="password"
          type="password"
          placeholder="Password"
          required
        />
        <AppButton type="submit" class="mt-2">Login</AppButton>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* Fade transition for error message */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
