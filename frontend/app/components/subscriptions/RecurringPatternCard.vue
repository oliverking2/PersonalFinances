<!-- ==========================================================================
RecurringPatternCard
Displays a single recurring pattern with actions
============================================================================ -->

<script setup lang="ts">
import type { RecurringPattern } from '~/types/recurring'
import { getFrequencyLabel, getStatusLabel } from '~/types/recurring'

// Props
const props = defineProps<{
  pattern: RecurringPattern
}>()

// Emits
const emit = defineEmits<{
  accept: []
  dismiss: []
  pause: []
  resume: []
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
  switch (props.pattern.status) {
    case 'active':
      return 'bg-primary/20 text-primary border-primary/40'
    case 'pending':
      return 'bg-warning/20 text-warning border-warning/40'
    case 'paused':
      return 'bg-gray-700/50 text-gray-300 border-gray-600'
    case 'cancelled':
      return 'bg-negative/20 text-negative border-negative/40'
    default:
      return 'bg-gray-700 text-gray-300 border-gray-600'
  }
})

// Confidence indicator (for pending/detected patterns)
const confidenceClass = computed(() => {
  const score = props.pattern.confidence_score
  if (!score) return 'text-muted'
  if (score >= 0.8) return 'text-positive'
  if (score >= 0.5) return 'text-warning'
  return 'text-negative'
})
</script>

<template>
  <div class="pattern-card">
    <!-- Header row: name + amount -->
    <div class="flex items-start justify-between gap-4">
      <!-- Left: name and badges -->
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <h3 class="truncate text-lg font-semibold">
            {{ pattern.name }}
          </h3>
          <!-- Status badge -->
          <span
            class="flex-shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium"
            :class="statusBadgeClass"
          >
            {{ getStatusLabel(pattern.status) }}
          </span>
          <!-- Source badge (small icon for detected vs manual) -->
          <span
            v-if="pattern.source === 'detected'"
            class="text-xs text-muted"
            title="Automatically detected"
          >
            <svg class="inline h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
                clip-rule="evenodd"
              />
            </svg>
          </span>
        </div>

        <!-- Frequency and direction badges -->
        <div class="mt-1 flex items-center gap-2 text-sm text-muted">
          <span
            class="rounded bg-gray-700/50 px-1.5 py-0.5 text-xs font-medium text-gray-300"
          >
            {{ getFrequencyLabel(pattern.frequency) }}
          </span>
          <!-- Direction badge -->
          <span
            :class="[
              'rounded px-1.5 py-0.5 text-xs font-medium',
              pattern.direction === 'income'
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-red-500/20 text-red-400',
            ]"
          >
            {{ pattern.direction === 'income' ? 'Income' : 'Expense' }}
          </span>
          <!-- Tag badge (if linked to a budget category) -->
          <span
            v-if="pattern.tag_name && pattern.tag_colour"
            class="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium"
            :style="{
              backgroundColor: `${pattern.tag_colour}20`,
              color: pattern.tag_colour,
            }"
          >
            <span
              class="h-2 w-2 rounded-full"
              :style="{ backgroundColor: pattern.tag_colour }"
            />
            {{ pattern.tag_name }}
          </span>
          <!-- Match count -->
          <span class="text-xs text-muted">
            {{ pattern.match_count }} transactions
          </span>
        </div>
      </div>

      <!-- Right: amount -->
      <div class="text-right">
        <p
          :class="[
            'text-lg font-semibold',
            pattern.direction === 'income'
              ? 'text-emerald-400'
              : 'text-red-400',
          ]"
        >
          {{ pattern.direction === 'income' ? '+' : '-'
          }}{{ formatCurrency(pattern.expected_amount) }}
        </p>
        <p class="text-sm text-muted">
          ~{{ formatCurrency(pattern.monthly_equivalent) }}/mo
        </p>
      </div>
    </div>

    <!-- Dates row -->
    <div class="mt-3 flex items-center gap-6 text-sm">
      <div>
        <span class="text-muted">Last:</span>
        <span class="ml-1">{{ formatDate(pattern.last_matched_date) }}</span>
      </div>
      <div>
        <span class="text-muted">Next:</span>
        <span class="ml-1">{{ formatDate(pattern.next_expected_date) }}</span>
      </div>
      <!-- Confidence (for pending patterns) -->
      <div
        v-if="pattern.status === 'pending' && pattern.confidence_score"
        class="text-sm"
      >
        <span class="text-muted">Confidence:</span>
        <span class="ml-1" :class="confidenceClass">
          {{ Math.round(pattern.confidence_score * 100) }}%
        </span>
      </div>
    </div>

    <!-- Detection reason (for pending patterns) -->
    <p
      v-if="pattern.status === 'pending' && pattern.detection_reason"
      class="mt-2 text-sm italic text-muted"
    >
      {{ pattern.detection_reason }}
    </p>

    <!-- Notes (if any) -->
    <p v-if="pattern.notes" class="mt-2 text-sm italic text-muted">
      {{ pattern.notes }}
    </p>

    <!-- Actions row -->
    <div class="mt-4 flex items-center gap-2">
      <!-- Accept button (for pending patterns) -->
      <button
        v-if="pattern.status === 'pending'"
        type="button"
        class="action-btn action-btn-primary"
        @click="emit('accept')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
            clip-rule="evenodd"
          />
        </svg>
        Accept
      </button>

      <!-- Pause button (for active patterns) -->
      <button
        v-if="pattern.status === 'active'"
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

      <!-- Resume button (for paused patterns) -->
      <button
        v-if="pattern.status === 'paused'"
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

      <!-- Dismiss button (for pending patterns - deletes them) -->
      <button
        v-if="pattern.status === 'pending'"
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
.pattern-card {
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
