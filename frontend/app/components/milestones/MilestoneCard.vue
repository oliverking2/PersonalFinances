<!-- ==========================================================================
MilestoneCard
Progress card showing milestone target, current value, and progress
============================================================================ -->

<script setup lang="ts">
import type { Milestone } from '~/types/milestones'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps<{
  milestone: Milestone
  currentNetWorth: number // Current net worth to calculate progress
}>()

// ---------------------------------------------------------------------------
// Emits
// ---------------------------------------------------------------------------
const emit = defineEmits<{
  edit: [milestone: Milestone]
  achieve: [milestone: Milestone]
  delete: [milestone: Milestone]
}>()

// Dropdown state
const showDropdown = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const targetAmount = computed(() => parseFloat(props.milestone.target_amount))

// Progress percentage (capped at 100%)
const progressPercent = computed(() => {
  if (targetAmount.value <= 0) return 0
  const percent = (props.currentNetWorth / targetAmount.value) * 100
  return Math.min(100, Math.max(0, percent))
})

// Amount remaining to reach target
const amountRemaining = computed(() => {
  const remaining = targetAmount.value - props.currentNetWorth
  return Math.max(0, remaining)
})

// Days until target date (null if no target date)
const daysRemaining = computed(() => {
  if (!props.milestone.target_date) return null

  const target = new Date(props.milestone.target_date)
  const now = new Date()
  const diffMs = target.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  return diffDays
})

// Status text based on progress and deadline
const statusText = computed(() => {
  if (props.milestone.achieved) {
    return 'Achieved!'
  }

  if (progressPercent.value >= 100) {
    return 'Target reached!'
  }

  if (daysRemaining.value !== null) {
    if (daysRemaining.value < 0) {
      return `${Math.abs(daysRemaining.value)} days overdue`
    }
    if (daysRemaining.value === 0) {
      return 'Due today'
    }
    return `${daysRemaining.value} days left`
  }

  return `${progressPercent.value.toFixed(0)}% complete`
})

// Status colour class
const statusColorClass = computed(() => {
  if (props.milestone.achieved || progressPercent.value >= 100) {
    return 'text-emerald-400'
  }

  if (daysRemaining.value !== null && daysRemaining.value < 0) {
    return 'text-red-400'
  }

  if (daysRemaining.value !== null && daysRemaining.value <= 30) {
    return 'text-amber-400'
  }

  return 'text-muted'
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
</script>

<template>
  <div
    class="rounded-lg border border-border bg-surface p-4"
    :class="{ 'border-emerald-500/50 bg-emerald-500/5': milestone.achieved }"
  >
    <!-- Header: Name and menu -->
    <div class="mb-3 flex items-start justify-between">
      <div class="flex items-center gap-2">
        <!-- Colour indicator -->
        <div
          class="h-3 w-3 rounded-full"
          :style="{ backgroundColor: milestone.colour }"
        />
        <h3 class="font-medium">{{ milestone.name }}</h3>
      </div>

      <!-- Actions dropdown -->
      <div class="relative">
        <button
          class="rounded p-1 text-muted transition-colors hover:bg-white/10 hover:text-foreground"
          @click="showDropdown = !showDropdown"
        >
          <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"
            />
          </svg>
        </button>
        <div
          v-if="showDropdown"
          class="absolute right-0 top-full z-10 mt-1 w-32 rounded-lg border border-border bg-surface py-1 shadow-lg"
          @click="showDropdown = false"
        >
          <button
            class="w-full px-3 py-1.5 text-left text-sm text-muted hover:bg-white/5 hover:text-foreground"
            @click="emit('edit', milestone)"
          >
            Edit
          </button>
          <button
            v-if="!milestone.achieved && progressPercent >= 100"
            class="text-emerald-400 w-full px-3 py-1.5 text-left text-sm hover:bg-white/5"
            @click="emit('achieve', milestone)"
          >
            Mark Achieved
          </button>
          <button
            class="w-full px-3 py-1.5 text-left text-sm text-red-400 hover:bg-white/5"
            @click="emit('delete', milestone)"
          >
            Delete
          </button>
        </div>
      </div>
    </div>

    <!-- Progress bar -->
    <div class="mb-3">
      <div class="h-2 w-full overflow-hidden rounded-full bg-border">
        <div
          class="h-full rounded-full transition-all duration-500"
          :class="
            milestone.achieved
              ? 'bg-emerald-500'
              : progressPercent >= 100
                ? 'bg-emerald-500'
                : 'bg-primary'
          "
          :style="{ width: `${progressPercent}%` }"
        />
      </div>
    </div>

    <!-- Stats row -->
    <div class="mb-2 flex items-end justify-between">
      <div>
        <p class="text-sm text-muted">Current</p>
        <p class="text-lg font-semibold">
          {{ formatCurrency(currentNetWorth) }}
        </p>
      </div>
      <div class="text-right">
        <p class="text-sm text-muted">Target</p>
        <p class="text-lg font-semibold">{{ formatCurrency(targetAmount) }}</p>
      </div>
    </div>

    <!-- Status and remaining -->
    <div class="flex items-center justify-between text-sm">
      <span :class="statusColorClass">{{ statusText }}</span>
      <span
        v-if="!milestone.achieved && amountRemaining > 0"
        class="text-muted"
      >
        {{ formatCurrency(amountRemaining) }} to go
      </span>
      <span
        v-if="milestone.achieved && milestone.achieved_at"
        class="text-muted"
      >
        {{ formatDate(milestone.achieved_at) }}
      </span>
    </div>

    <!-- Target date (if set and not achieved) -->
    <div
      v-if="milestone.target_date && !milestone.achieved"
      class="mt-2 text-xs text-muted"
    >
      Target: {{ formatDate(milestone.target_date) }}
    </div>

    <!-- Notes (if any) -->
    <div v-if="milestone.notes" class="mt-2 text-xs italic text-muted">
      {{ milestone.notes }}
    </div>
  </div>
</template>
