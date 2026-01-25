<!-- ==========================================================================
SpendingTable
Data table showing daily spending by tag with sorting
Provides accessible alternative to visual charts
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
defineProps<{
  data: Record<string, unknown>[]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Toggle visibility
const isExpanded = ref(false)

// Sorting
const sortKey = ref<'date' | 'tag' | 'total'>('date')
const sortDirection = ref<'asc' | 'desc'>('desc')

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

function toggleSort(key: 'date' | 'tag' | 'total') {
  if (sortKey.value === key) {
    // Toggle direction
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    // New key, default to desc for total, asc for others
    sortKey.value = key
    sortDirection.value = key === 'total' ? 'desc' : 'asc'
  }
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

// Aggregate data from raw rows
function aggregateRows(rows: Record<string, unknown>[]): {
  date: string
  tag: string
  colour: string
  count: number
  total: number
}[] {
  const byDateTag = new Map<
    string,
    {
      date: string
      tag: string
      colour: string
      count: number
      total: number
    }
  >()

  for (const row of rows) {
    const date = row.spending_date as string
    const rawTag = row.tag_name as string | null | undefined
    const tag = rawTag || 'Untagged'
    const colour = rawTag ? (row.tag_colour as string) || '#10b981' : '#6b7280'
    const spending = (row.total_spending as number) || 0
    const count = (row.total_transactions as number) || 0

    const key = `${date}|${tag}`
    const existing = byDateTag.get(key)

    if (existing) {
      existing.total += spending
      existing.count += count
    } else {
      byDateTag.set(key, { date, tag, colour, count, total: spending })
    }
  }

  return Array.from(byDateTag.values())
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface">
    <!-- Header with toggle -->
    <button
      type="button"
      class="flex w-full items-center justify-between p-4 text-left hover:bg-background/50"
      @click="isExpanded = !isExpanded"
    >
      <h2 class="text-lg font-semibold">Transactions Table</h2>
      <span class="flex items-center gap-2 text-sm text-muted">
        {{ isExpanded ? 'Hide' : 'Show' }}
        <svg
          class="h-5 w-5 transition-transform"
          :class="isExpanded ? 'rotate-180' : ''"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
            clip-rule="evenodd"
          />
        </svg>
      </span>
    </button>

    <!-- Table content (collapsible) -->
    <div v-if="isExpanded" class="border-t border-border">
      <!-- Empty state -->
      <div v-if="!data.length" class="p-6 text-center text-muted">
        No transaction data for this period
      </div>

      <!-- Table -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <!-- Table header with sortable columns -->
          <thead class="bg-background/50">
            <tr>
              <th class="px-4 py-3 text-left">
                <button
                  type="button"
                  class="flex items-center gap-1 font-medium text-muted hover:text-foreground"
                  @click="toggleSort('date')"
                >
                  Date
                  <!-- Sort icon -->
                  <svg
                    class="h-4 w-4"
                    :class="
                      sortKey === 'date' ? 'text-primary' : 'text-muted/50'
                    "
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
                      clip-rule="evenodd"
                      :class="
                        sortKey === 'date' && sortDirection === 'asc'
                          ? 'opacity-100'
                          : 'opacity-30'
                      "
                    />
                  </svg>
                </button>
              </th>
              <th class="px-4 py-3 text-left">
                <button
                  type="button"
                  class="flex items-center gap-1 font-medium text-muted hover:text-foreground"
                  @click="toggleSort('tag')"
                >
                  Tag
                  <svg
                    class="h-4 w-4"
                    :class="
                      sortKey === 'tag' ? 'text-primary' : 'text-muted/50'
                    "
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
                      clip-rule="evenodd"
                      :class="
                        sortKey === 'tag' && sortDirection === 'asc'
                          ? 'opacity-100'
                          : 'opacity-30'
                      "
                    />
                  </svg>
                </button>
              </th>
              <th class="px-4 py-3 text-center font-medium text-muted">
                Count
              </th>
              <th class="px-4 py-3 text-right">
                <button
                  type="button"
                  class="ml-auto flex items-center gap-1 font-medium text-muted hover:text-foreground"
                  @click="toggleSort('total')"
                >
                  Total
                  <svg
                    class="h-4 w-4"
                    :class="
                      sortKey === 'total' ? 'text-primary' : 'text-muted/50'
                    "
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
                      clip-rule="evenodd"
                      :class="
                        sortKey === 'total' && sortDirection === 'desc'
                          ? 'opacity-100'
                          : 'opacity-30'
                      "
                    />
                  </svg>
                </button>
              </th>
            </tr>
          </thead>

          <!-- Table body -->
          <tbody class="divide-y divide-border">
            <tr
              v-for="(row, idx) in aggregateRows(data).sort((a, b) => {
                let comparison = 0
                if (sortKey === 'date')
                  comparison = a.date.localeCompare(b.date)
                else if (sortKey === 'tag')
                  comparison = a.tag.localeCompare(b.tag)
                else comparison = a.total - b.total
                return sortDirection === 'asc' ? comparison : -comparison
              })"
              :key="`${row.date}-${row.tag}-${idx}`"
              class="hover:bg-background/30"
            >
              <td class="px-4 py-3 text-foreground">
                {{ formatDate(row.date) }}
              </td>
              <td class="px-4 py-3">
                <span class="inline-flex items-center gap-2">
                  <!-- Tag colour dot -->
                  <span
                    class="h-2.5 w-2.5 rounded-full"
                    :style="{ backgroundColor: row.colour }"
                  />
                  {{ row.tag }}
                </span>
              </td>
              <td class="px-4 py-3 text-center text-muted">
                {{ row.count }}
              </td>
              <td class="px-4 py-3 text-right font-medium">
                {{ formatCurrency(row.total) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
