<template>
  <div>
    <UPageHeader
      title="Connections"
      description="Manage your bank connections"
    />

    <UCard class="mt-6">
      <UTable
        :columns="columns"
        :rows="connections?.connections ?? []"
        :loading="pending"
      >
        <template #status-data="{ row }">
          <UBadge
            :color="getStatusColor(row.status)"
            variant="subtle"
          >
            {{ row.status }}
          </UBadge>
        </template>

        <template #expired-data="{ row }">
          <UBadge
            :color="row.expired ? 'error' : 'success'"
            variant="subtle"
          >
            {{ row.expired ? 'Expired' : 'Active' }}
          </UBadge>
        </template>

        <template #created-data="{ row }">
          {{ formatDate(row.created) }}
        </template>
      </UTable>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { ConnectionListResponse } from '~/composables/useApi'

const api = useApi()

const { data: connections, pending } = await useAsyncData('connections', () =>
  api.get<ConnectionListResponse>('/api/connections')
)

const columns = [
  { key: 'friendly_name', label: 'Name' },
  { key: 'institution_id', label: 'Institution' },
  { key: 'status', label: 'Status' },
  { key: 'account_count', label: 'Accounts' },
  { key: 'expired', label: 'Active' },
  { key: 'created', label: 'Created' },
]

function getStatusColor(status: string): string {
  switch (status) {
    case 'LN': return 'success'
    case 'CR': return 'info'
    case 'EX': return 'error'
    default: return 'neutral'
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString()
}
</script>
