<!-- ==========================================================================
MetricCard
Displays a single metric with label, value, and optional trend/subtitle
Used on the home page for net worth, spending totals, etc.
============================================================================ -->

<script setup lang="ts">
// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
defineProps<{
  label: string // Card title (e.g., "Net Worth")
  value: string // Main display value (e.g., "£12,345.67")
  subtitle?: string // Optional subtitle (e.g., "spent" or "this month")
  trend?: number | null // Optional percentage change (positive = up, negative = down)
  valueColor?: 'positive' | 'negative' | 'default' // Colour the value (green/red/default)
  loading?: boolean // Show skeleton loading state
  muted?: boolean // Grey out the card (e.g., analytics unavailable)
}>()
</script>

<template>
  <!-- Card container -->
  <!-- rounded-lg border: consistent card styling -->
  <!-- p-4 sm:p-5: responsive padding -->
  <div
    class="rounded-lg border border-border bg-surface p-4 sm:p-5"
    :class="{ 'opacity-50': muted }"
  >
    <!-- Loading skeleton -->
    <template v-if="loading">
      <!-- Label skeleton -->
      <div class="mb-2 h-4 w-20 animate-pulse rounded bg-border" />
      <!-- Value skeleton -->
      <div class="mb-1 h-8 w-32 animate-pulse rounded bg-border" />
      <!-- Subtitle skeleton -->
      <div class="h-4 w-16 animate-pulse rounded bg-border" />
    </template>

    <!-- Actual content -->
    <template v-else>
      <!-- Label -->
      <p class="text-sm font-medium text-muted">{{ label }}</p>

      <!-- Value -->
      <!-- text-2xl sm:text-3xl: larger on bigger screens -->
      <!-- valueColor: positive (green), negative (red), default (inherit) -->
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
        <!-- Trend indicator (if provided) -->
        <span
          v-if="trend !== undefined && trend !== null"
          class="font-medium"
          :class="trend >= 0 ? 'text-negative' : 'text-positive'"
        >
          <!-- Up arrow for increase, down for decrease -->
          <!-- Note: for spending, increase is bad (negative color) -->
          {{ trend >= 0 ? '↑' : '↓' }}
          {{ Math.abs(trend).toFixed(1) }}%
        </span>

        <!-- Subtitle -->
        <span v-if="subtitle" class="text-muted">{{ subtitle }}</span>
      </div>
    </template>
  </div>
</template>
