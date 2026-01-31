<!-- ==========================================================================
RunwayWidget
Displays financial runway - days until balance reaches threshold
============================================================================ -->

<script setup lang="ts">
import type { CashFlowForecastResponse } from '~/types/analytics'
import { formatCurrency, parseAmount } from '~/composables/useFormatting'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
defineProps<{
  forecast: CashFlowForecastResponse | null
  loading?: boolean
}>()

// ---------------------------------------------------------------------------
// Computed helpers
// ---------------------------------------------------------------------------

// Format currency values (whole numbers for cleaner display)
function formatWholeNumber(amount: string): string {
  return formatCurrency(Math.round(parseAmount(amount)))
}

// Get runway status colour (green = healthy, amber = warning, red = danger)
function getRunwayColor(days: number | null): string {
  if (days === null) return 'text-emerald-400' // No threshold hit = good
  if (days > 90) return 'text-emerald-400'
  if (days > 30) return 'text-amber-400'
  return 'text-red-400'
}

// Get progress bar width based on runway
function getProgressWidth(days: number | null): string {
  if (days === null) return '100%' // Runway > 90 days
  if (days > 90) return '100%'
  // Scale from 0-90 days to 0-100%
  return `${Math.min(100, (days / 90) * 100)}%`
}

// Get progress bar colour
function getProgressColor(days: number | null): string {
  if (days === null) return 'bg-emerald-500'
  if (days > 90) return 'bg-emerald-500'
  if (days > 30) return 'bg-amber-500'
  return 'bg-red-500'
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-4 sm:p-5">
    <!-- Loading state -->
    <template v-if="loading">
      <div class="mb-2 h-4 w-24 animate-pulse rounded bg-border" />
      <div class="mb-3 h-8 w-32 animate-pulse rounded bg-border" />
      <div class="h-2 w-full animate-pulse rounded bg-border" />
    </template>

    <!-- Content -->
    <template v-else-if="forecast">
      <!-- Header with link to forecasting page -->
      <div class="mb-2 flex items-center justify-between">
        <p class="text-sm font-medium text-muted">Financial Runway</p>
        <NuxtLink
          to="/planning/forecast"
          class="text-xs text-primary hover:text-primary-hover"
        >
          View forecast →
        </NuxtLink>
      </div>

      <!-- Main runway display -->
      <div class="mb-3">
        <p
          class="text-2xl font-bold sm:text-3xl"
          :class="getRunwayColor(forecast.summary.runway_days)"
        >
          <template v-if="forecast.summary.runway_days === null">
            90+ days
          </template>
          <template v-else> {{ forecast.summary.runway_days }} days </template>
        </p>
        <p class="text-sm text-muted">
          <template v-if="forecast.summary.runway_days === null">
            until reaching £0
          </template>
          <template v-else-if="forecast.summary.runway_days > 0">
            until balance hits £0
          </template>
          <template v-else> Balance already negative </template>
        </p>
      </div>

      <!-- Progress bar visualisation -->
      <div class="mb-4 h-2 w-full overflow-hidden rounded-full bg-border">
        <div
          class="h-full rounded-full transition-all duration-500"
          :class="getProgressColor(forecast.summary.runway_days)"
          :style="{ width: getProgressWidth(forecast.summary.runway_days) }"
        />
      </div>

      <!-- Summary stats -->
      <div class="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p class="text-muted">Projected Balance</p>
          <p class="font-medium">
            {{ formatWholeNumber(forecast.summary.ending_balance) }}
          </p>
        </div>
        <div>
          <p class="text-muted">Min Balance</p>
          <p class="font-medium">
            {{ formatWholeNumber(forecast.summary.min_balance) }}
          </p>
        </div>
      </div>
    </template>

    <!-- No data state -->
    <template v-else>
      <p class="text-sm font-medium text-muted">Financial Runway</p>
      <p class="mt-2 text-sm text-muted">
        No forecast data available. Run analytics refresh to generate
        projections.
      </p>
    </template>
  </div>
</template>
