<!-- ==========================================================================
BudgetWarningsPanel
Shows budgets at risk of being exceeded based on forecast projections
============================================================================ -->

<script setup lang="ts">
import type { BudgetForecast } from '~/types/budgets'
import {
  getPeriodLabel,
  getRiskLevelColour,
  getRiskLevelBgColour,
} from '~/types/budgets'

// API
const { fetchBudgetForecasts } = useBudgetsApi()

// State
const forecasts = ref<BudgetForecast[]>([])
const budgetsAtRisk = ref(0)
const loading = ref(true)
const error = ref('')

// Load forecast data on mount
onMounted(loadData)

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetchBudgetForecasts()
    forecasts.value = response.forecasts
    budgetsAtRisk.value = response.budgets_at_risk
  } catch (e) {
    console.error('Failed to load budget forecasts:', e)
    error.value = 'Failed to load budget forecasts'
    forecasts.value = []
    budgetsAtRisk.value = 0
  } finally {
    loading.value = false
  }
}

// Filter to only show at-risk budgets (high or critical risk level)
const atRiskForecasts = computed(() =>
  forecasts.value.filter(
    (f) => f.risk_level === 'high' || f.risk_level === 'critical',
  ),
)

// Format currency
function formatCurrency(amount: number, currency: string = 'GBP'): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

// Format days until exhausted
function formatDaysUntilExhausted(days: number | null): string {
  if (days === null) return 'Unknown'
  if (days <= 0) return 'Already exceeded'
  if (days === 1) return '1 day'
  return `${Math.floor(days)} days`
}

// Get risk label
function getRiskLabel(level: string): string {
  const labels: Record<string, string> = {
    low: 'On Track',
    medium: 'At Risk',
    high: 'Warning',
    critical: 'Critical',
  }
  return labels[level] || level
}

// Build a transactions link filtered by tag and current budget period
function getTransactionsLink(forecast: BudgetForecast): string {
  const now = new Date()
  let startDate: Date

  // Calculate the start of the current budget period
  switch (forecast.period) {
    case 'weekly': {
      // Start of current week (Monday)
      const day = now.getDay()
      const diff = day === 0 ? 6 : day - 1
      startDate = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate() - diff,
      )
      break
    }
    case 'monthly':
      startDate = new Date(now.getFullYear(), now.getMonth(), 1)
      break
    case 'quarterly': {
      const quarterMonth = Math.floor(now.getMonth() / 3) * 3
      startDate = new Date(now.getFullYear(), quarterMonth, 1)
      break
    }
    case 'annual':
      startDate = new Date(now.getFullYear(), 0, 1)
      break
    default:
      startDate = new Date(now.getFullYear(), now.getMonth(), 1)
  }

  const params = new URLSearchParams()
  params.set('tag', forecast.tag_name)
  params.set('start_date', startDate.toISOString().slice(0, 10))
  params.set('end_date', now.toISOString().slice(0, 10))
  return `/transactions?${params.toString()}`
}
</script>

<template>
  <!-- Only show if there are budgets at risk or loading -->
  <div
    v-if="loading || atRiskForecasts.length > 0"
    class="rounded-lg border border-border bg-surface"
  >
    <!-- Header -->
    <div class="border-b border-border px-6 py-4">
      <div class="flex items-center gap-2">
        <!-- Warning icon -->
        <svg
          class="h-5 w-5 text-amber-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <h2 class="text-lg font-semibold">Budget Warnings</h2>
        <span
          v-if="budgetsAtRisk > 0"
          class="rounded-full bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-400"
        >
          {{ budgetsAtRisk }} at risk
        </span>
      </div>
      <p class="mt-1 text-sm text-muted">
        Budgets projected to exceed based on your spending patterns
      </p>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="p-6">
      <div class="flex items-center gap-2 text-sm text-muted">
        <svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        Loading budget forecasts...
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="p-6 text-sm text-negative">
      {{ error }}
    </div>

    <!-- At-risk budgets list -->
    <div v-else-if="atRiskForecasts.length > 0" class="divide-y divide-border">
      <div
        v-for="forecast in atRiskForecasts"
        :key="forecast.budget_id"
        class="flex items-center justify-between px-6 py-4"
      >
        <!-- Left: tag info and status -->
        <div class="flex items-center gap-3">
          <!-- Tag colour indicator -->
          <span
            class="h-3 w-3 flex-shrink-0 rounded-full"
            :style="{ backgroundColor: forecast.tag_colour || '#6b7280' }"
          />
          <div>
            <div class="flex items-center gap-2">
              <span class="font-medium">{{ forecast.tag_name }}</span>
              <!-- Period badge -->
              <span class="rounded bg-border px-1.5 py-0.5 text-xs text-muted">
                {{ getPeriodLabel(forecast.period) }}
              </span>
              <!-- Risk level badge -->
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="[
                  getRiskLevelBgColour(forecast.risk_level),
                  getRiskLevelColour(forecast.risk_level),
                ]"
              >
                {{ getRiskLabel(forecast.risk_level) }}
              </span>
            </div>
            <div class="mt-0.5 text-sm text-muted">
              {{ formatCurrency(forecast.spent_amount, forecast.currency) }} of
              {{ formatCurrency(forecast.budget_amount, forecast.currency) }}
              spent ({{ Number(forecast.percentage_used).toFixed(0) }}%)
            </div>
          </div>
        </div>

        <!-- Right: days until exhausted + transactions link -->
        <div class="flex items-center gap-3">
          <div class="text-right">
            <div
              class="font-medium"
              :class="getRiskLevelColour(forecast.risk_level)"
            >
              {{ formatDaysUntilExhausted(forecast.days_until_exhausted) }}
            </div>
            <div class="text-xs text-muted">
              {{ forecast.days_remaining }} days left in period
            </div>
          </div>

          <!-- Transactions link (matches BudgetCard action-btn style) -->
          <NuxtLink :to="getTransactionsLink(forecast)" class="action-btn">
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M6 4.75A.75.75 0 016.75 4h10.5a.75.75 0 010 1.5H6.75A.75.75 0 016 4.75zM6 10a.75.75 0 01.75-.75h10.5a.75.75 0 010 1.5H6.75A.75.75 0 016 10zm0 5.25a.75.75 0 01.75-.75h10.5a.75.75 0 010 1.5H6.75a.75.75 0 01-.75-.75zM1.99 4.75a1 1 0 011-1h.01a1 1 0 010 2h-.01a1 1 0 01-1-1zm1 5.25a1 1 0 100 2h.01a1 1 0 100-2h-.01zm0 5.25a1 1 0 100 2h.01a1 1 0 100-2h-.01z"
                clip-rule="evenodd"
              />
            </svg>
            Transactions
          </NuxtLink>
        </div>
      </div>
    </div>

    <!-- Empty state (shouldn't normally show since we hide panel if empty) -->
    <div v-else class="p-6 text-center text-sm text-muted">
      No budgets at risk
    </div>

    <!-- Link to budgets page -->
    <div class="border-t border-border px-6 py-3">
      <NuxtLink
        to="/planning/budgets"
        class="text-emerald-400 inline-flex items-center gap-1 text-sm hover:underline"
      >
        View all budgets
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
            clip-rule="evenodd"
          />
        </svg>
      </NuxtLink>
    </div>
  </div>
</template>

<style scoped>
.action-btn {
  @apply inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium;
  @apply bg-transparent text-muted transition-colors;
  @apply hover:bg-gray-700/50 hover:text-foreground;
}
</style>
