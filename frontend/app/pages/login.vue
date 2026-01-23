<script setup lang="ts">
const username = ref('')
const password = ref('')

function handleSubmit() {
  console.log('Username:', username.value)
  console.log('Password:', password.value)
}
</script>

<template>
  <div
    class="login-page flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900"
  >
    <!-- Background blobs -->
    <div
      class="absolute -left-20 top-20 h-72 w-72 rounded-full bg-blue-500 opacity-20 blur-3xl"
    />
    <div
      class="absolute -right-20 bottom-20 h-96 w-96 rounded-full bg-primary opacity-10 blur-3xl"
    />

    <div
      class="logo-card rounded-xl border border-border bg-surface p-8 shadow-xl"
    >
      <h1 class="pb-4 text-center font-sans text-3xl font-bold">
        <span class="block">Personal Finances</span>
        <span class="block">App</span>
      </h1>
      <form class="flex flex-col gap-4 pt-6" @submit.prevent="handleSubmit">
        <input v-model="username" type="text" placeholder="Username" />
        <input v-model="password" type="password" placeholder="Password" />
        <AppButton type="submit">Login</AppButton>
      </form>
    </div>
  </div>
</template>
