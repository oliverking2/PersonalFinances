<!-- ==========================================================================
SubscriptionCard
Displays a single subscription/recurring pattern with actions
============================================================================ -->

<script setup lang="ts">
import type { Subscription } from '~/types/subscriptions'
import { getFrequencyLabel, getStatusLabel } from '~/types/subscriptions'

// Props
const props = defineProps<{
  subscription: Subscription
}>()

// Emits
const emit = defineEmits<{
  confirm: []
  dismiss: []
  pause: []
  restore: []
  edit: []
}>()

// Format currency
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 2,
  }).format(Math.abs(amount))
}

// Format date as relative or absolute
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.ceil(
    (date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24),
  )

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays === -1) return 'Yesterday'
  if (diffDays > 0 && diffDays <= 7) return `In ${diffDays} days`
  if (diffDays < 0 && diffDays >= -7) return `${Math.abs(diffDays)} days ago`

  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
}

// Status badge colours
const statusBadgeClass = computed(() => {
  switch (props.subscription.status) {
    case 'confirmed':
    case 'manual':
      return 'bg-primary/20 text-primary border-primary/40'
    case 'detected':
      return 'bg-gray-700/50 text-gray-300 border-gray-600'
    case 'paused':
      return 'bg-warning/20 text-warning border-warning/40'
    case 'dismissed':
      return 'bg-negative/20 text-negative border-negative/40'
    default:
      return 'bg-gray-700 text-gray-300 border-gray-600'
  }
})

// Confidence indicator
const confidenceClass = computed(() => {
  const score = props.subscription.confidence_score
  if (score >= 0.8) return 'text-positive'
  if (score >= 0.5) return 'text-warning'
  return 'text-negative'
})
</script>

<template>
  <div class="subscription-card">
    <!-- Header row: name + amount -->
    <div class="flex items-start justify-between gap-4">
      <!-- Left: name and badges -->
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <h3 class="truncate text-lg font-semibold">
            {{ subscription.display_name }}
          </h3>
          <!-- Status badge -->
          <span
            class="flex-shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium"
            :class="statusBadgeClass"
          >
            {{ getStatusLabel(subscription.status) }}
          </span>
        </div>

        <!-- Frequency badge -->
        <div class="mt-1 flex items-center gap-2 text-sm text-muted">
          <span
            class="rounded bg-gray-700/50 px-1.5 py-0.5 text-xs font-medium text-gray-300"
          >
            {{ getFrequencyLabel(subscription.frequency) }}
          </span>
        </div>
      </div>

      <!-- Right: amount -->
      <div class="text-right">
        <p class="text-lg font-semibold">
          -{{ formatCurrency(subscription.expected_amount) }}
        </p>
        <p class="text-sm text-muted">
          ~{{ formatCurrency(subscription.monthly_equivalent) }}/mo
        </p>
      </div>
    </div>

    <!-- Dates row -->
    <div class="mt-3 flex items-center gap-6 text-sm">
      <div>
        <span class="text-muted">Last:</span>
        <span class="ml-1">{{
          formatDate(subscription.last_occurrence_date)
        }}</span>
      </div>
      <div>
        <span class="text-muted">Next:</span>
        <span class="ml-1">{{
          formatDate(subscription.next_expected_date)
        }}</span>
      </div>
      <!-- Confidence (for detected patterns) -->
      <div v-if="subscription.status === 'detected'" class="text-sm">
        <span class="text-muted">Confidence:</span>
        <span class="ml-1" :class="confidenceClass">
          {{ Math.round(subscription.confidence_score * 100) }}%
        </span>
      </div>
    </div>

    <!-- Notes (if any) -->
    <p v-if="subscription.notes" class="mt-2 text-sm italic text-muted">
      {{ subscription.notes }}
    </p>

    <!-- Actions row -->
    <div class="mt-4 flex items-center gap-2">
      <!-- Confirm button (for detected patterns) -->
      <button
        v-if="subscription.status === 'detected'"
        type="button"
        class="action-btn action-btn-primary"
        @click="emit('confirm')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
            clip-rule="evenodd"
          />
        </svg>
        Confirm
      </button>

      <!-- Pause/Resume button -->
      <button
        v-if="
          subscription.status !== 'paused' &&
          subscription.status !== 'dismissed'
        "
        type="button"
        class="action-btn action-btn-secondary"
        @click="emit('pause')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M5.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 007.25 3h-1.5zM12.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75a.75.75 0 00-.75-.75h-1.5z"
          />
        </svg>
        Pause
      </button>

      <!-- Resume button (for paused) -->
      <button
        v-if="subscription.status === 'paused'"
        type="button"
        class="action-btn action-btn-primary"
        @click="emit('confirm')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"
          />
        </svg>
        Resume
      </button>

      <!-- Dismiss button -->
      <button
        v-if="subscription.status !== 'dismissed'"
        type="button"
        class="action-btn action-btn-danger"
        @click="emit('dismiss')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
          />
        </svg>
        Dismiss
      </button>

      <!-- Restore button (for dismissed subscriptions) -->
      <button
        v-if="subscription.status === 'dismissed'"
        type="button"
        class="action-btn action-btn-primary"
        @click="emit('restore')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
            clip-rule="evenodd"
          />
        </svg>
        Restore
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
    </div>
  </div>
</template>

<style scoped>
.subscription-card {
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

.action-btn-danger {
  @apply bg-negative/20 text-negative hover:bg-negative/30;
}

.action-btn-ghost {
  @apply bg-transparent text-muted hover:bg-gray-700/50 hover:text-foreground;
}
</style>
