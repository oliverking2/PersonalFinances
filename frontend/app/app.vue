<template>
  <UApp>
    <UContainer class="min-h-screen">
      <UHeader>
        <template #title>
          <span class="font-bold">Personal Finances</span>
        </template>

        <template #center>
          <UHorizontalNavigation :links="navLinks" />
        </template>
      </UHeader>

      <UMain class="py-6">
        <NuxtPage />
      </UMain>
    </UContainer>
  </UApp>
</template>

<script setup lang="ts">
const navLinks = [
  { label: 'Dashboard', to: '/' },
  { label: 'Accounts', to: '/accounts' },
  { label: 'Transactions', to: '/transactions' },
  { label: 'Connections', to: '/connections' },
]
</script>
