<!-- ==========================================================================
GoalProgressRing
Circular progress indicator for savings goals
============================================================================ -->

<script setup lang="ts">
import { getProgressColour } from '~/types/goals'

// Props
const props = defineProps<{
  percentage: number // 0-100+
  size?: number // Diameter in pixels (default 80)
  strokeWidth?: number // Stroke width (default 6)
}>()

// Defaults
const size = computed(() => props.size ?? 80)
const strokeWidth = computed(() => props.strokeWidth ?? 6)

// SVG calculations
const radius = computed(() => (size.value - strokeWidth.value) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const center = computed(() => size.value / 2)

// Progress (capped at 100 for display)
const displayPercentage = computed(() => Math.min(props.percentage, 100))
const strokeDashoffset = computed(
  () => circumference.value * (1 - displayPercentage.value / 100),
)

// Colour based on percentage
const strokeClass = computed(() => getProgressColour(props.percentage))
</script>

<template>
  <div class="relative inline-flex items-center justify-center">
    <!-- SVG ring -->
    <svg :width="size" :height="size" class="rotate-[-90deg]">
      <!-- Background track -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        class="stroke-gray-700/50"
        :stroke-width="strokeWidth"
      />
      <!-- Progress arc -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :class="strokeClass"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="strokeDashoffset"
        stroke-linecap="round"
        class="transition-all duration-500"
      />
    </svg>

    <!-- Center label -->
    <div class="absolute inset-0 flex items-center justify-center">
      <span class="text-sm font-semibold"> {{ Math.round(percentage) }}% </span>
    </div>
  </div>
</template>
