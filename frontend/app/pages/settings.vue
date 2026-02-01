<!-- ==========================================================================
Settings Page
Tabbed container for configuration: Accounts, Tags, Rules, Profile
============================================================================ -->

<script setup lang="ts">
const route = useRoute()

// ---------------------------------------------------------------------------
// Tab configuration
// ---------------------------------------------------------------------------
const tabs = [
  { to: '/settings/accounts', label: 'Accounts' },
  { to: '/settings/jobs', label: 'Jobs' },
  { to: '/settings/tags', label: 'Tags' },
  { to: '/settings/rules', label: 'Rules' },
  { to: '/settings/profile', label: 'Profile' },
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
