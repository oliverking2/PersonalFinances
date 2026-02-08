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

useHead({ title: 'Login | Finances' })

const authStore = useAuthStore()

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------
const username = ref('')
const password = ref('')
const errorMessage = ref<string | null>(null)
const isShaking = ref(false)

// ---------------------------------------------------------------------------
// Form submission
// ---------------------------------------------------------------------------
async function handleSubmit() {
  errorMessage.value = null

  try {
    await authStore.login(username.value, password.value)
    await navigateTo('/')
  } catch {
    errorMessage.value = 'Invalid username or password'

    // Trigger shake animation on form
    isShaking.value = true
    setTimeout(() => {
      isShaking.value = false
    }, 500)

    // Auto-dismiss error after 5 seconds
    setTimeout(() => {
      errorMessage.value = null
    }, 5000)
  }
}

// Dismiss error when user starts typing
function dismissError() {
  if (errorMessage.value) {
    errorMessage.value = null
  }
}
</script>

<template>
  <!-- Full-screen container -->
  <div
    class="flex min-h-screen flex-col items-center justify-center bg-background px-4"
  >
    <!-- Decorative background blobs -->
    <div
      class="absolute -left-20 top-20 hidden h-72 w-72 rounded-full bg-emerald-500 opacity-20 blur-3xl sm:block"
    />
    <div
      class="absolute -right-20 bottom-20 hidden h-96 w-96 rounded-full bg-sage opacity-10 blur-3xl sm:block"
    />

    <!-- Card wrapper - relative for absolute error positioning -->
    <div class="relative w-full max-w-sm">
      <!-- Error message - absolute so card doesn't move -->
      <Transition name="slide">
        <div
          v-if="errorMessage"
          class="absolute -top-16 left-0 right-0 flex items-center gap-3 rounded-lg border border-negative/30 bg-negative/10 px-4 py-3 backdrop-blur-sm"
        >
          <!-- Error icon (X in circle) -->
          <div
            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-negative/20"
          >
            <svg
              class="h-4 w-4 text-negative"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
          <!-- Error text -->
          <p class="text-sm font-medium text-negative">
            {{ errorMessage }}
          </p>
        </div>
      </Transition>

      <!-- Login card -->
      <div
        class="rounded-xl border border-border bg-surface p-6 shadow-xl sm:p-8"
      >
        <!-- App title -->
        <h1
          class="pb-4 text-center font-display text-2xl font-bold text-foreground sm:text-3xl"
        >
          Personal Finances
        </h1>

        <!-- Login form - shakes on error -->
        <form
          :class="{ shake: isShaking }"
          class="flex flex-col gap-4"
          @submit.prevent="handleSubmit"
        >
          <AppInput
            v-model="username"
            type="text"
            placeholder="Username"
            required
            @input="dismissError"
          />
          <AppInput
            v-model="password"
            type="password"
            placeholder="Password"
            required
            @input="dismissError"
          />
          <AppButton type="submit" class="mt-2">Login</AppButton>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Slide down transition for error message */
.slide-enter-active {
  transition: all 0.3s ease-out;
}
.slide-leave-active {
  transition: all 0.2s ease-in;
}
.slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Shake animation for form on error */
@keyframes shake {
  0%,
  100% {
    transform: translateX(0);
  }
  10%,
  30%,
  50%,
  70%,
  90% {
    transform: translateX(-4px);
  }
  20%,
  40%,
  60%,
  80% {
    transform: translateX(4px);
  }
}
.shake {
  animation: shake 0.5s ease-in-out;
}
</style>
