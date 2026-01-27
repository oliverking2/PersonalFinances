<!-- ==========================================================================
TransactionRow
Displays a single transaction with merchant/description, tags, and amount
Click to select for bulk operations
============================================================================ -->

<script setup lang="ts">
import type { Transaction } from '~/types/transactions'
import type { Tag } from '~/types/tags'
import type { RecurringFrequency, RecurringStatus } from '~/types/subscriptions'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = withDefaults(
  defineProps<{
    transaction: Transaction
    accountName?: string // Display name of the account this transaction belongs to
    availableTags?: Tag[] // All user's tags for the selector
    selected?: boolean // Whether this row is selected (for bulk operations)
    selectable?: boolean // Show selection checkbox (default true, set false on home page)
  }>(),
  {
    accountName: '',
    availableTags: () => [],
    selected: false,
    selectable: true,
  },
)

const emit = defineEmits<{
  'toggle-select': []
  'add-tag': [tagId: string]
  'remove-tag': [tagId: string]
  'create-tag': [name: string]
  'open-detail': []
}>()

// ---------------------------------------------------------------------------
// Local State
// ---------------------------------------------------------------------------

const showTagSelector = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Display name: prefer merchant_name, fall back to description
const displayName = computed(() => {
  return (
    props.transaction.merchant_name ||
    props.transaction.description ||
    'Unknown Transaction'
  )
})

// Secondary line: show description if merchant is displayed, otherwise category
const secondaryText = computed(() => {
  if (props.transaction.merchant_name && props.transaction.description) {
    return props.transaction.description
  }
  return props.transaction.category || null
})

// Build the metadata line (account name + secondary text)
const metadataText = computed(() => {
  const parts: string[] = []
  if (props.accountName) {
    parts.push(props.accountName)
  }
  if (secondaryText.value) {
    parts.push(secondaryText.value)
  }
  return parts.join(' · ')
})

// Format amount with currency symbol and +/- prefix
const formattedAmount = computed(() => {
  const { amount, currency } = props.transaction
  const formatted = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: currency,
  }).format(Math.abs(amount))

  // Add +/- prefix for clarity
  return amount >= 0 ? `+${formatted}` : `-${formatted}`
})

// Amount colour: green for income (positive), default for expenses (negative)
const amountColorClass = computed(() => {
  return props.transaction.amount >= 0 ? 'text-positive' : 'text-foreground'
})

// Get tag IDs for selector
const selectedTagIds = computed(() => {
  return props.transaction.tags?.map((t) => t.id) || []
})

// All tags to display (regular tags + split tags)
const allDisplayTags = computed(() => {
  const tags: {
    id: string
    name: string
    colour: string | null
    isSplit?: boolean
  }[] = []

  // Add regular tags
  if (props.transaction.tags) {
    for (const tag of props.transaction.tags) {
      tags.push({ id: tag.id, name: tag.name, colour: tag.colour })
    }
  }

  // Add split tags (if not already in regular tags)
  if (props.transaction.splits) {
    const existingIds = new Set(tags.map((t) => t.id))
    for (const split of props.transaction.splits) {
      if (!existingIds.has(split.tag_id)) {
        tags.push({
          id: split.tag_id,
          name: split.tag_name,
          colour: split.tag_colour,
          isSplit: true,
        })
      }
    }
  }

  return tags
})

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

// Handle row click - behavior depends on selection mode
function handleRowClick(event: MouseEvent) {
  // Don't handle clicks on interactive elements
  const target = event.target as HTMLElement
  if (
    target.closest('button') ||
    target.closest('.tag-chip') ||
    target.closest('.tag-selector-container')
  ) {
    return
  }

  // In selection mode, click toggles selection
  // Otherwise, click opens detail
  if (props.selectable) {
    emit('toggle-select')
  } else {
    emit('open-detail')
  }
}

function toggleTagSelector(event: MouseEvent) {
  event.stopPropagation()
  showTagSelector.value = !showTagSelector.value
}

function handleTagSelect(tagId: string) {
  emit('add-tag', tagId)
  showTagSelector.value = false // Close after selecting (single tag only)
}

function handleTagDeselect(tagId: string) {
  emit('remove-tag', tagId)
}

function handleTagCreate(name: string) {
  emit('create-tag', name)
  showTagSelector.value = false
}

function handleRemoveTag(tagId: string) {
  emit('remove-tag', tagId)
}

// Close selector when clicking outside
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.tag-selector-container')) {
    showTagSelector.value = false
  }
}

// Set up click outside listener
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <!-- Transaction row - click behavior depends on selection mode -->
  <div
    class="group flex items-center gap-3 rounded-lg px-4 py-3 transition-colors"
    :class="[
      'cursor-pointer',
      selected
        ? 'bg-primary/10 ring-1 ring-inset ring-primary/30'
        : 'hover:bg-onyx/50',
    ]"
    @click="handleRowClick"
  >
    <!-- Selection indicator (checkmark when selected) - only shown when selectable -->
    <div
      v-if="selectable"
      class="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full transition-all"
      :class="
        selected
          ? 'bg-primary text-background'
          : 'border border-gray-600 bg-transparent'
      "
    >
      <svg
        v-if="selected"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        class="h-3 w-3"
      >
        <path
          fill-rule="evenodd"
          d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
          clip-rule="evenodd"
        />
      </svg>
    </div>

    <!-- Left side: merchant/description (no flex-1, only takes needed space) -->
    <div class="min-w-0 max-w-[50%] flex-shrink">
      <div class="flex items-center gap-2">
        <p class="truncate font-medium text-foreground">{{ displayName }}</p>
        <!-- Recurring badge (if this transaction is part of a recurring pattern) -->
        <SubscriptionsRecurringBadge
          v-if="
            transaction.recurring_pattern_id &&
            transaction.recurring_frequency &&
            transaction.recurring_status
          "
          :frequency="transaction.recurring_frequency as RecurringFrequency"
          :status="transaction.recurring_status as RecurringStatus"
        />
      </div>
      <p v-if="metadataText" class="mt-0.5 truncate text-sm text-muted">
        {{ metadataText }}
      </p>
    </div>

    <!-- Tags (right after transaction name, with left margin for spacing) -->
    <div
      class="tag-selector-container relative ml-4 flex flex-shrink-0 items-center gap-1.5"
    >
      <!-- All tags (regular + split tags) -->
      <TagsTagChip
        v-for="tag in allDisplayTags"
        :key="tag.id"
        class="tag-chip"
        :name="tag.name"
        :colour="tag.colour"
        :removable="!tag.isSplit"
        @remove="handleRemoveTag(tag.id)"
      />

      <!-- Add tag button (show if no tags at all) -->
      <button
        v-if="allDisplayTags.length === 0"
        type="button"
        class="add-tag-btn"
        title="Add tag"
        @click="toggleTagSelector"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          class="h-3 w-3"
        >
          <path
            d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
          />
        </svg>
      </button>

      <!-- Tag selector popover -->
      <!-- z-20 to appear above sticky date headers (z-10) -->
      <div
        v-if="showTagSelector && availableTags"
        class="absolute left-0 top-full z-20 mt-1"
        @click.stop
      >
        <TagsTagSelector
          :available-tags="availableTags"
          :selected-tag-ids="selectedTagIds"
          @select="handleTagSelect"
          @deselect="handleTagDeselect"
          @create="handleTagCreate"
        />
      </div>
    </div>

    <!-- Spacer to push amount to the right -->
    <div class="flex-1" />

    <!-- Right side: amount -->
    <div class="flex-shrink-0">
      <span class="font-medium" :class="amountColorClass">
        {{ formattedAmount }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.add-tag-btn {
  /* Layout: small circular button */
  @apply flex h-5 w-5 items-center justify-center rounded-full;

  /* Colours */
  @apply border border-dashed border-gray-600 bg-transparent;

  /* Typography */
  @apply text-xs text-gray-500;

  /* Interaction */
  @apply cursor-pointer transition-colors;
  @apply hover:border-primary hover:text-primary;

  /* Only show on hover (except on touch devices) */
  @apply opacity-0 group-hover:opacity-100;
}

/* Always show add button if there are no tags */
.group:has(.add-tag-btn:only-child) .add-tag-btn {
  @apply opacity-100;
}

/* Always show add button when row is selected */
.group:has(.bg-primary\/10) .add-tag-btn {
  @apply opacity-100;
}
</style>
