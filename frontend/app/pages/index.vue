<template>
  <div>
    <UPageHeader
      title="Dashboard"
      description="Overview of your personal finances"
    />

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
      <UCard>
        <template #header>
          <h3 class="font-semibold">Active Accounts</h3>
        </template>
        <p class="text-3xl font-bold">{{ accountCount }}</p>
      </UCard>

      <UCard>
        <template #header>
          <h3 class="font-semibold">Bank Connections</h3>
        </template>
        <p class="text-3xl font-bold">{{ connectionCount }}</p>
      </UCard>

      <UCard>
        <template #header>
          <h3 class="font-semibold">Last Sync</h3>
        </template>
        <p class="text-lg">Coming soon</p>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AccountListResponse, ConnectionListResponse } from '~/composables/useApi'

const api = useApi()

const { data: accounts } = await useAsyncData('accounts', () =>
  api.get<AccountListResponse>('/api/accounts').catch(() => ({ accounts: [], total: 0 }))
)

const { data: connections } = await useAsyncData('connections', () =>
  api.get<ConnectionListResponse>('/api/connections').catch(() => ({ connections: [], total: 0 }))
)

const accountCount = computed(() => accounts.value?.total ?? 0)
const connectionCount = computed(() => connections.value?.total ?? 0)
</script>
