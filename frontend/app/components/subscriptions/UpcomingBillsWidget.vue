<!-- ==========================================================================
UpcomingBillsWidget
Shows upcoming bills/subscriptions for the next N days on the home page
============================================================================ -->

<script setup lang="ts">
import type { UpcomingBill, UpcomingBillsResponse } from '~/types/subscriptions'
import { getFrequencyLabel } from '~/types/subscriptions'

// Props
const props = withDefaults(
  defineProps<{
    days?: number // Number of days to look ahead (default 7)
  }>(),
  {
    days: 7,
  },
)

// API
const { fetchUpcomingBills } = useSubscriptionsApi()

// State
const upcomingBills = ref<UpcomingBill[]>([])
const totalExpected = ref(0)
const dateRange = ref<{ start: string; end: string } | null>(null)
const loading = ref(true)
const error = ref('')

// Load upcoming bills on mount
onMounted(loadUpcomingBills)

async function loadUpcomingBills() {
  loading.value = true
  error.value = ''
  try {
    const response: UpcomingBillsResponse = await fetchUpcomingBills(props.days)
    upcomingBills.value = response.upcoming
    totalExpected.value = response.total_expected
    dateRange.value = response.date_range
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : 'Failed to load upcoming bills'
  } finally {
    loading.value = false
  }
}

// Format currency
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
  }).format(Math.abs(amount))
}

// Format relative date (e.g., "Today", "Tomorrow", "Mon 28")
function formatRelativeDate(dateStr: string, daysUntil: number): string {
  if (daysUntil === 0) return 'Today'
  if (daysUntil === 1) return 'Tomorrow'

  const date = new Date(dateStr)
  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
  })
}

// Computed: show widget only if there are upcoming bills
const hasUpcomingBills = computed(() => upcomingBills.value.length > 0)
</script>

<template>
  <!-- Only show widget if there are upcoming bills or loading -->
  <div
    v-if="loading || hasUpcomingBills || error"
    class="upcoming-bills-widget"
  >
    <!-- Header -->
    <div
      class="flex items-center justify-between border-b border-border px-4 py-3"
    >
      <div class="flex items-center gap-2">
        <!-- Calendar icon -->
        <svg
          class="h-5 w-5 text-primary"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M5.75 2a.75.75 0 01.75.75V4h7V2.75a.75.75 0 011.5 0V4h.25A2.75 2.75 0 0118 6.75v8.5A2.75 2.75 0 0115.25 18H4.75A2.75 2.75 0 012 15.25v-8.5A2.75 2.75 0 014.75 4H5V2.75A.75.75 0 015.75 2zm-1 5.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25v-6.5c0-.69-.56-1.25-1.25-1.25H4.75z"
            clip-rule="evenodd"
          />
        </svg>
        <h3 class="font-semibold">Upcoming Bills</h3>
      </div>
      <span class="text-sm text-muted">Next {{ days }} days</span>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="space-y-2 p-4">
      <div v-for="i in 3" :key="i" class="flex items-center justify-between">
        <div class="space-y-1">
          <div class="h-4 w-24 animate-pulse rounded bg-border" />
          <div class="h-3 w-16 animate-pulse rounded bg-border" />
        </div>
        <div class="h-5 w-14 animate-pulse rounded bg-border" />
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="p-4 text-sm text-negative">
      {{ error }}
    </div>

    <!-- No upcoming bills (widget hidden in this case, but keep for edge cases) -->
    <div
      v-else-if="!hasUpcomingBills"
      class="p-4 text-center text-sm text-muted"
    >
      No upcoming bills in the next {{ days }} days
    </div>

    <!-- Bills list -->
    <div v-else class="divide-y divide-border">
      <div
        v-for="bill in upcomingBills"
        :key="bill.id"
        class="flex items-center justify-between px-4 py-3 transition-colors hover:bg-onyx/30"
      >
        <!-- Left: date + name -->
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <!-- Date badge -->
            <span
              class="flex-shrink-0 rounded px-1.5 py-0.5 text-xs font-medium"
              :class="
                bill.days_until === 0
                  ? 'bg-warning/20 text-warning'
                  : bill.days_until === 1
                    ? 'bg-primary/20 text-primary'
                    : 'bg-gray-700 text-gray-300'
              "
            >
              {{ formatRelativeDate(bill.next_expected_date, bill.days_until) }}
            </span>

            <!-- Name -->
            <span class="truncate font-medium">{{ bill.display_name }}</span>

            <!-- Detected badge (for unconfirmed) with tooltip -->
            <span
              v-if="bill.status === 'detected'"
              class="group relative flex-shrink-0 cursor-help rounded bg-gray-700/50 px-1 py-0.5 text-xs text-gray-400"
            >
              ?
              <!-- Tooltip -->
              <span
                class="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-48 -translate-x-1/2 rounded-lg bg-graphite p-2 text-xs opacity-0 shadow-lg transition-opacity group-hover:opacity-100"
              >
                <span class="block font-medium text-foreground"
                  >Auto-detected</span
                >
                <span class="block text-muted">
                  Confidence: {{ Math.round(bill.confidence_score * 100) }}%
                </span>
                <span class="block text-muted">
                  Visit Subscriptions to confirm or dismiss
                </span>
                <!-- Arrow -->
                <span
                  class="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-graphite"
                />
              </span>
            </span>
          </div>

          <!-- Frequency label -->
          <p class="mt-0.5 text-sm text-muted">
            {{ getFrequencyLabel(bill.frequency) }}
          </p>
        </div>

        <!-- Right: amount -->
        <span class="flex-shrink-0 font-medium text-foreground">
          -{{ formatCurrency(bill.expected_amount) }}
        </span>
      </div>

      <!-- Footer: total + link -->
      <div class="flex items-center justify-between bg-background/30 px-4 py-3">
        <span class="text-sm text-muted">
          Total expected:
          <span class="font-medium text-foreground"
            >-{{ formatCurrency(totalExpected) }}</span
          >
        </span>
        <NuxtLink
          to="/insights/subscriptions"
          class="text-sm text-primary hover:text-primary-hover"
        >
          View all →
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upcoming-bills-widget {
  @apply rounded-lg border border-border bg-surface;
}
</style>
