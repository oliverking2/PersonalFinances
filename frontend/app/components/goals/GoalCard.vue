<!-- ==========================================================================
GoalCard
Displays a single savings goal with progress ring and actions
============================================================================ -->

<script setup lang="ts">
import type { Goal } from '~/types/goals'
import {
  getStatusLabel,
  getStatusColour,
  getStatusBgColour,
  formatDaysRemaining,
  getTrackingModeLabel,
  allowsContributions,
} from '~/types/goals'

// Props
const props = defineProps<{
  goal: Goal
}>()

// Emits
const emit = defineEmits<{
  contribute: []
  complete: []
  pause: []
  resume: []
  cancel: []
  edit: []
  delete: []
}>()

// Format currency
function formatCurrency(amount: number, currency: string = 'GBP'): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

// Is the goal active (can contribute)
const isActive = computed(() => props.goal.status === 'active')

// Is the goal paused
const isPaused = computed(() => props.goal.status === 'paused')

// Is the goal completed or cancelled
const isFinished = computed(() =>
  ['completed', 'cancelled'].includes(props.goal.status),
)

// Can this goal receive manual contributions?
const canContribute = computed(
  () => isActive.value && allowsContributions(props.goal.tracking_mode),
)

// Is this goal automatically tracked (non-manual)?
const isAutoTracked = computed(
  () => !allowsContributions(props.goal.tracking_mode),
)
</script>

<template>
  <div class="goal-card">
    <!-- Header: name + badges -->
    <div class="flex items-start justify-between gap-4">
      <!-- Left: name and tracking info -->
      <div class="min-w-0 flex-1">
        <h3 class="truncate text-lg font-semibold">{{ goal.name }}</h3>
        <!-- Show linked account for auto-tracked goals -->
        <p v-if="goal.account_name" class="mt-0.5 text-sm text-muted">
          <span v-if="isAutoTracked">Tracking:</span>
          <span v-else>Linked to</span>
          {{ goal.account_name }}
        </p>
      </div>

      <!-- Right: badges -->
      <div class="flex flex-shrink-0 items-center gap-2">
        <!-- Tracking mode badge (only for non-manual) -->
        <span
          v-if="isAutoTracked"
          class="rounded-full bg-sky-500/20 px-2 py-0.5 text-xs font-medium text-sky-400"
        >
          {{ getTrackingModeLabel(goal.tracking_mode) }}
        </span>
        <!-- Status badge -->
        <span
          class="rounded-full px-2 py-0.5 text-xs font-medium"
          :class="[
            getStatusBgColour(goal.status),
            getStatusColour(goal.status),
          ]"
        >
          {{ getStatusLabel(goal.status) }}
        </span>
      </div>
    </div>

    <!-- Progress section -->
    <div class="mt-4 flex items-center gap-4">
      <!-- Progress ring -->
      <GoalsProgressRing
        :percentage="goal.progress_percentage"
        :size="64"
        :stroke-width="5"
      />

      <!-- Progress details -->
      <div class="flex-1">
        <div class="flex items-baseline justify-between">
          <span class="text-lg font-semibold">
            {{ formatCurrency(goal.current_amount, goal.currency) }}
          </span>
          <span class="text-muted">
            of {{ formatCurrency(goal.target_amount, goal.currency) }}
          </span>
        </div>
        <!-- Remaining -->
        <p class="mt-1 text-sm text-muted">
          {{
            formatCurrency(
              goal.target_amount - goal.current_amount,
              goal.currency,
            )
          }}
          to go
        </p>
      </div>
    </div>

    <!-- Deadline info -->
    <div
      v-if="goal.deadline || goal.days_remaining !== null"
      class="mt-3 text-sm"
    >
      <span class="text-muted">Deadline:</span>
      <span
        class="ml-1"
        :class="
          goal.days_remaining !== null && goal.days_remaining < 0
            ? 'text-red-400'
            : ''
        "
      >
        {{ formatDaysRemaining(goal.days_remaining) }}
      </span>
    </div>

    <!-- Notes -->
    <p v-if="goal.notes" class="mt-2 text-sm italic text-muted">
      {{ goal.notes }}
    </p>

    <!-- Actions -->
    <div class="mt-4 flex flex-wrap items-center gap-2">
      <!-- Contribute button (only for active manual tracking goals) -->
      <button
        v-if="canContribute"
        type="button"
        class="action-btn action-btn-primary"
        @click="emit('contribute')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
          />
        </svg>
        Add Funds
      </button>

      <!-- Complete button (active goals only) -->
      <button
        v-if="isActive"
        type="button"
        class="action-btn action-btn-secondary"
        @click="emit('complete')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
            clip-rule="evenodd"
          />
        </svg>
        Complete
      </button>

      <!-- Pause button (active goals only) -->
      <button
        v-if="isActive"
        type="button"
        class="action-btn action-btn-ghost"
        @click="emit('pause')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M5.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 007.25 3h-1.5zM12.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75a.75.75 0 00-.75-.75h-1.5z"
          />
        </svg>
        Pause
      </button>

      <!-- Resume button (paused goals only) -->
      <button
        v-if="isPaused"
        type="button"
        class="action-btn action-btn-primary"
        @click="emit('resume')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"
          />
        </svg>
        Resume
      </button>

      <!-- Cancel button (active or paused) -->
      <button
        v-if="isActive || isPaused"
        type="button"
        class="action-btn action-btn-danger"
        @click="emit('cancel')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
          />
        </svg>
        Cancel
      </button>

      <!-- Spacer -->
      <div class="flex-1" />

      <!-- Edit button -->
      <button
        type="button"
        class="action-btn action-btn-ghost"
        @click="emit('edit')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z"
          />
        </svg>
      </button>

      <!-- Delete button (finished goals only) -->
      <button
        v-if="isFinished"
        type="button"
        class="action-btn action-btn-danger"
        @click="emit('delete')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.goal-card {
  @apply rounded-lg border border-border bg-surface p-4;
}

.action-btn {
  @apply inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium;
  @apply transition-colors;
}

.action-btn-primary {
  @apply bg-primary/20 text-primary hover:bg-primary/30;
}

.action-btn-secondary {
  @apply bg-gray-700/50 text-gray-300 hover:bg-gray-700;
}

.action-btn-ghost {
  @apply bg-transparent text-muted hover:bg-gray-700/50 hover:text-foreground;
}

.action-btn-danger {
  @apply bg-transparent text-muted hover:bg-negative/20 hover:text-negative;
}
</style>
