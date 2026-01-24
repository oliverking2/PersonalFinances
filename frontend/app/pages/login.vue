<script setup lang="ts">
// ============================================================================
// Login Page
// Handles user authentication via username/password form
// ============================================================================

// ----------------------------------------------------------------------------
// Reactive State
// ref() creates reactive variables that update the UI when changed
// v-model in the template binds these to the input fields (two-way binding)
// ----------------------------------------------------------------------------
import { useAuthStore } from '~/stores/auth'

const username = ref('')
const password = ref('')
const errorMessage = ref<string | null>(null)
const authStore = useAuthStore()

// ----------------------------------------------------------------------------
// Form Submission
// @submit.prevent in template calls this and prevents page reload
// Browser handles validation via HTML5 attributes (required, minlength, maxlength)
// ----------------------------------------------------------------------------
async function handleSubmit() {
  errorMessage.value = null
  try {
    await authStore.login(username.value, password.value)
    await navigateTo('/')
  } catch (error) {
    errorMessage.value = 'Login failed'
    console.log(error)

    setTimeout(() => {
      errorMessage.value = null
    }, 3000)
  }
}
</script>

<template>
  <!-- Full-screen container with dark gradient background -->
  <div
    class="login-page flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900"
  >
    <!-- Decorative background blobs (purely visual, no interaction) -->
    <div
      class="absolute -left-20 top-20 h-72 w-72 rounded-full bg-blue-500 opacity-20 blur-3xl"
    />
    <div
      class="absolute -right-20 bottom-20 h-96 w-96 rounded-full bg-primary opacity-10 blur-3xl"
    />

    <!-- Login card - centered on page -->
    <div
      class="login-card relative rounded-xl border border-border bg-surface p-8 shadow-xl"
    >
      <!-- Error message -->
      <Transition name="fade">
        <div
          v-if="errorMessage"
          class="absolute left-2 right-2 top-2 rounded-md bg-red-600/90 p-3 text-center font-bold text-white"
        >
          {{ errorMessage }}
        </div></Transition
      >
      <!-- App title -->
      <h1 class="pb-4 text-center font-sans text-3xl font-bold">
        <span class="block">Personal Finances</span>
        <span class="block">App</span>
      </h1>

      <!-- Login form -->
      <!-- @submit.prevent: calls handleSubmit() and prevents default form submission -->
      <form class="flex flex-col gap-4 pt-6" @submit.prevent="handleSubmit">
        <!-- HTML5 validation: required, minlength, maxlength -->
        <input v-model="username" type="text" placeholder="Username" required />
        <input
          v-model="password"
          type="password"
          placeholder="Password"
          required
        />
        <AppButton type="submit">Login</AppButton>
      </form>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
