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
      <!-- Accounts card placeholder -->
      <div class="rounded-lg border border-border bg-surface p-6">
        <h2 class="font-semibold text-sage">Accounts</h2>
        <p class="mt-2 text-sm text-muted">
          Your connected bank accounts will appear here.
        </p>
      </div>

      <!-- Transactions card placeholder -->
      <div class="rounded-lg border border-border bg-surface p-6">
        <h2 class="font-semibold text-sage">Recent Transactions</h2>
        <p class="mt-2 text-sm text-muted">
          Your recent transactions will appear here.
        </p>
      </div>

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
