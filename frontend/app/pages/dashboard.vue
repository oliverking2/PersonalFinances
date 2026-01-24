<!-- ==========================================================================
Dashboard Page
Main authenticated view - will show accounts, transactions, etc.
============================================================================ -->

<script setup lang="ts">
const authStore = useAuthStore()
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold sm:text-3xl">Dashboard</h1>
      <p class="mt-1 text-muted">
        Welcome back,
        {{ authStore.user?.first_name || authStore.user?.username }}
      </p>
    </div>

    <!-- Placeholder cards - will be replaced with actual content -->
    <!-- grid: responsive grid layout -->
    <!-- gap-4: consistent spacing between cards -->
    <!-- sm:grid-cols-2 lg:grid-cols-3: more columns on larger screens -->
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <!-- Accounts card - links to /accounts page -->
      <NuxtLink
        to="/accounts"
        class="group block rounded-lg border border-border bg-surface p-6 transition-colors hover:border-primary/50"
      >
        <h2 class="font-semibold text-sage group-hover:text-primary">
          Accounts
        </h2>
        <p class="mt-2 text-sm text-muted">
          Manage your connected bank accounts.
        </p>
      </NuxtLink>

      <!-- Transactions card - links to /transactions page -->
      <NuxtLink
        to="/transactions"
        class="group block rounded-lg border border-border bg-surface p-6 transition-colors hover:border-primary/50"
      >
        <h2 class="font-semibold text-sage group-hover:text-primary">
          Transactions
        </h2>
        <p class="mt-2 text-sm text-muted">
          View and search your transaction history.
        </p>
      </NuxtLink>

      <!-- Summary card placeholder -->
      <div class="rounded-lg border border-border bg-surface p-6">
        <h2 class="font-semibold text-sage">Summary</h2>
        <p class="mt-2 text-sm text-muted">
          Spending insights and totals will appear here.
        </p>
      </div>
    </div>
  </div>
</template>
