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
}>()

// Compute whether card should be clickable
const isClickable = computed(() => props.to && !props.loading && !props.muted)
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

    <!-- Value - text-foreground ensures it's not styled as a link -->
    <p
      class="mt-1 text-2xl font-bold sm:text-3xl"
      :class="{
        'text-positive': valueColor === 'positive',
        'text-negative': valueColor === 'negative',
        'text-foreground': !valueColor || valueColor === 'default',
      }"
    >
      {{ value }}
    </p>

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

      <!-- Value -->
      <p
        class="mt-1 text-2xl font-bold sm:text-3xl"
        :class="{
          'text-positive': valueColor === 'positive',
          'text-negative': valueColor === 'negative',
        }"
      >
        {{ value }}
      </p>

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
