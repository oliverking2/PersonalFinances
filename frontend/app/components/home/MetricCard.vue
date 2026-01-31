<!-- ==========================================================================
MetricCard
Displays a single metric with label, value, and optional trend/subtitle
Used on the home page for net worth, spending totals, etc.
============================================================================ -->

<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  label: string // Card title (e.g., "Net Worth")
  value: string // Main display value (e.g., "£12,345.67")
  subtitle?: string // Optional subtitle (e.g., "spent" or "this month")
  trend?: number | null // Optional percentage change (positive = up, negative = down)
  trendInverted?: boolean // If true, positive trend is good (green), e.g., for net worth growth
  valueColor?: 'positive' | 'negative' | 'default' // Colour the value (green/red/default)
  loading?: boolean // Show skeleton loading state
  muted?: boolean // Grey out the card (e.g., analytics unavailable)
  to?: RouteLocationRaw // Optional navigation destination (renders as NuxtLink)
  sparklineData?: number[] // Optional array of values for sparkline chart
}>()

// Compute whether card should be clickable
const isClickable = computed(() => props.to && !props.loading && !props.muted)

// ---------------------------------------------------------------------------
// Sparkline - simple SVG path from data points
// ---------------------------------------------------------------------------

// Generate SVG path for sparkline
const sparklinePath = computed(() => {
  if (!props.sparklineData?.length || props.sparklineData.length < 2) return ''

  const data = props.sparklineData
  const width = 80
  const height = 24
  const padding = 2

  // Calculate min/max for scaling
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1 // Avoid division by zero

  // Scale points to fit the SVG
  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * (width - padding * 2) + padding
    const y =
      height - padding - ((value - min) / range) * (height - padding * 2)
    return { x, y }
  })

  // Build SVG path
  const pathParts = points.map((p, i) =>
    i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`,
  )
  return pathParts.join(' ')
})

// Determine sparkline colour based on trend direction
const sparklineColor = computed(() => {
  if (!props.sparklineData?.length || props.sparklineData.length < 2)
    return '#6b7280'

  const first = props.sparklineData[0] ?? 0
  const last = props.sparklineData[props.sparklineData.length - 1] ?? 0
  const increasing = last >= first

  // If trendInverted, increasing is good (green); otherwise increasing is bad (red)
  if (props.trendInverted) {
    return increasing ? '#10b981' : '#ef4444'
  }
  return increasing ? '#ef4444' : '#10b981'
})
</script>

<template>
  <!-- Clickable version: renders as NuxtLink -->
  <!-- no-underline and text-foreground prevent link styling from bleeding through -->
  <NuxtLink
    v-if="isClickable"
    :to="to!"
    class="block cursor-pointer rounded-lg border border-border bg-surface p-4 no-underline transition-colors hover:border-primary/50 sm:p-5"
  >
    <!-- Label -->
    <p class="text-sm font-medium text-muted">{{ label }}</p>

    <!-- Value row with optional sparkline -->
    <div class="mt-1 flex items-center justify-between gap-2">
      <!-- Value - text-foreground ensures it's not styled as a link -->
      <p
        class="text-2xl font-bold sm:text-3xl"
        :class="{
          'text-positive': valueColor === 'positive',
          'text-negative': valueColor === 'negative',
          'text-foreground': !valueColor || valueColor === 'default',
        }"
      >
        {{ value }}
      </p>

      <!-- Sparkline - small inline trend chart -->
      <svg
        v-if="sparklinePath"
        width="80"
        height="24"
        class="shrink-0"
        viewBox="0 0 80 24"
      >
        <path
          :d="sparklinePath"
          fill="none"
          :stroke="sparklineColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </div>

    <!-- Subtitle and/or trend -->
    <div class="mt-1 flex items-center gap-2 text-sm">
      <!-- Trend indicator (if provided) -->
      <!-- trendInverted: if true, positive is good (green); default: positive is bad (red, for spending) -->
      <span
        v-if="trend !== undefined && trend !== null"
        class="font-medium"
        :class="
          trendInverted
            ? trend >= 0
              ? 'text-positive'
              : 'text-negative'
            : trend >= 0
              ? 'text-negative'
              : 'text-positive'
        "
      >
        {{ trend >= 0 ? '↑' : '↓' }}
        {{ Math.abs(trend).toFixed(1) }}%
      </span>

      <!-- Subtitle -->
      <span v-if="subtitle" class="text-muted">{{ subtitle }}</span>
    </div>
  </NuxtLink>

  <!-- Non-clickable version: renders as div -->
  <div
    v-else
    class="rounded-lg border border-border bg-surface p-4 sm:p-5"
    :class="{ 'opacity-50': muted }"
  >
    <!-- Loading skeleton -->
    <template v-if="loading">
      <div class="mb-2 h-4 w-20 animate-pulse rounded bg-border" />
      <div class="mb-1 h-8 w-32 animate-pulse rounded bg-border" />
      <div class="h-4 w-16 animate-pulse rounded bg-border" />
    </template>

    <!-- Actual content -->
    <template v-else>
      <!-- Label -->
      <p class="text-sm font-medium text-muted">{{ label }}</p>

      <!-- Value row with optional sparkline -->
      <div class="mt-1 flex items-center justify-between gap-2">
        <!-- Value -->
        <p
          class="text-2xl font-bold sm:text-3xl"
          :class="{
            'text-positive': valueColor === 'positive',
            'text-negative': valueColor === 'negative',
          }"
        >
          {{ value }}
        </p>

        <!-- Sparkline - small inline trend chart -->
        <svg
          v-if="sparklinePath"
          width="80"
          height="24"
          class="shrink-0"
          viewBox="0 0 80 24"
        >
          <path
            :d="sparklinePath"
            fill="none"
            :stroke="sparklineColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </div>

      <!-- Subtitle and/or trend -->
      <div class="mt-1 flex items-center gap-2 text-sm">
        <!-- Trend indicator -->
        <span
          v-if="trend !== undefined && trend !== null"
          class="font-medium"
          :class="
            trendInverted
              ? trend >= 0
                ? 'text-positive'
                : 'text-negative'
              : trend >= 0
                ? 'text-negative'
                : 'text-positive'
          "
        >
          {{ trend >= 0 ? '↑' : '↓' }}
          {{ Math.abs(trend).toFixed(1) }}%
        </span>

        <!-- Subtitle -->
        <span v-if="subtitle" class="text-muted">{{ subtitle }}</span>
      </div>
    </template>
  </div>
</template>
