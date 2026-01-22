<template>
  <div>
    <UPageHeader
      title="Accounts"
      description="Your connected bank accounts"
    />

    <UCard class="mt-6">
      <UTable
        :columns="columns"
        :rows="accounts?.accounts ?? []"
        :loading="pending"
      >
        <template #status-data="{ row }">
          <UBadge
            :color="row.status === 'READY' ? 'success' : 'warning'"
            variant="subtle"
          >
            {{ row.status }}
          </UBadge>
        </template>

        <template #iban-data="{ row }">
          <span class="font-mono text-sm">{{ formatIban(row.iban) }}</span>
        </template>
      </UTable>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { AccountListResponse } from '~/composables/useApi'

const api = useApi()

const { data: accounts, pending } = await useAsyncData('accounts', () =>
  api.get<AccountListResponse>('/api/accounts')
)

const columns = [
  { key: 'display_name', label: 'Name' },
  { key: 'iban', label: 'IBAN' },
  { key: 'currency', label: 'Currency' },
  { key: 'owner_name', label: 'Owner' },
  { key: 'status', label: 'Status' },
]

function formatIban(iban: string | null): string {
  if (!iban) return '-'
  // Format IBAN in groups of 4
  return iban.replace(/(.{4})/g, '$1 ').trim()
}
</script>
