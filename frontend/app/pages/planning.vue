<!-- ==========================================================================
Planning Page
Tabbed container for financial planning features: Net Worth, Forecast, Budgets, Goals
============================================================================ -->

<script setup lang="ts">
const route = useRoute()

// ---------------------------------------------------------------------------
// Tab configuration
// ---------------------------------------------------------------------------
const tabs = [
  { to: '/planning/net-worth', label: 'Net Worth', icon: 'chart-line' },
  { to: '/planning/forecast', label: 'Forecast', icon: 'calendar' },
  { to: '/planning/recurring', label: 'Recurring', icon: 'repeat' },
  { to: '/planning/budgets', label: 'Budgets', icon: 'wallet' },
  { to: '/planning/goals', label: 'Goals', icon: 'target' },
]

// Check if a tab is active
function isActiveTab(to: string): boolean {
  return route.path === to || route.path.startsWith(to + '/')
}
</script>

<template>
  <div class="space-y-6">
    <!-- Tab navigation -->
    <div class="border-b border-border">
      <nav class="-mb-px flex gap-6">
        <NuxtLink
          v-for="tab in tabs"
          :key="tab.to"
          :to="tab.to"
          class="border-b-2 px-1 py-3 text-sm font-medium transition-colors"
          :class="
            isActiveTab(tab.to)
              ? 'border-primary text-primary'
              : 'border-transparent text-muted hover:border-border hover:text-foreground'
          "
        >
          {{ tab.label }}
        </NuxtLink>
      </nav>
    </div>

    <!-- Tab content (nested route) -->
    <NuxtPage />
  </div>
</template>
