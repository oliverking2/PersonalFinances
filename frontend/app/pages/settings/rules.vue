<!-- ==========================================================================
Settings / Rules Page
Manage auto-tagging rules for automatically categorising transactions
============================================================================ -->

<script setup lang="ts">
import type { TagRule, TransactionMatch } from '~/types/rules'
import type { Tag } from '~/types/tags'
import type { Account } from '~/types/accounts'
import { useToastStore } from '~/stores/toast'

useHead({ title: 'Auto-Tagging Rules | Finances' })

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const {
  fetchRules,
  createRule,
  updateRule,
  deleteRule,
  testConditions,
  reorderRules,
  applyRules,
  ApiError,
} = useRulesApi()
const { fetchTags } = useTagsApi()
const { fetchAccounts } = useAccountsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Data
const rules = ref<TagRule[]>([])
const tags = ref<Tag[]>([])
const accounts = ref<Account[]>([])
const loading = ref(true)
const error = ref('')

// Tag filter (optional, filters rules by target tag)
const filterTagId = ref('')

// Apply rules state
const applying = ref(false)

// Create/Edit modal state
const showModal = ref(false)
const editingRule = ref<TagRule | null>(null)
const saving = ref(false)

// Form fields for create/edit
const formName = ref('')
const formTagId = ref('')
const formEnabled = ref(true)
const formMerchantContains = ref('')
const formMerchantExact = ref('')
const formDescriptionContains = ref('')
const formMinAmountRaw = ref<string>('')
const formMinAmount = computed({
  get: () => {
    const val = parseFloat(formMinAmountRaw.value)
    return Number.isFinite(val) && val > 0 ? val : null
  },
  set: (val: number | null) => {
    formMinAmountRaw.value = val !== null && val > 0 ? String(val) : ''
  },
})
const formMaxAmountRaw = ref<string>('')
const formMaxAmount = computed({
  get: () => {
    const val = parseFloat(formMaxAmountRaw.value)
    return Number.isFinite(val) && val > 0 ? val : null
  },
  set: (val: number | null) => {
    formMaxAmountRaw.value = val !== null && val > 0 ? String(val) : ''
  },
})
const formAccountId = ref('')
const formMerchantNotContains = ref('')
const formDescriptionNotContains = ref('')

// Test preview state
const testing = ref(false)
const testMatches = ref<TransactionMatch[]>([])
const testTotal = ref(0)
const showTestResults = ref(false)

// Delete confirmation
const deletingRule = ref<TagRule | null>(null)
const deleting = ref(false)

// Drag and drop state
const draggingIndex = ref<number | null>(null)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Filter rules by selected tag
const displayedRules = computed(() => {
  if (!filterTagId.value) {
    return rules.value
  }
  return rules.value.filter((rule) => rule.tag_id === filterTagId.value)
})

// Tag options for select dropdowns
const tagOptions = computed(() =>
  tags.value
    .filter((t) => !t.is_hidden)
    .map((tag) => ({
      value: tag.id,
      label: tag.name,
    })),
)

// Account options for select dropdowns
const accountOptions = computed(() =>
  accounts.value.map((acc) => ({
    value: acc.id,
    label: acc.display_name || acc.name || 'Unknown Account',
  })),
)

// Check if form has at least one matching condition set
// Note: account_id is a scope filter, not a matching condition
// (a rule with only account_id would tag ALL transactions from that account)
const hasCondition = computed(() => {
  return !!(
    formMerchantContains.value.trim() ||
    formMerchantExact.value.trim() ||
    formDescriptionContains.value.trim() ||
    isValidAmount(formMinAmount.value) ||
    isValidAmount(formMaxAmount.value) ||
    formMerchantNotContains.value.trim() ||
    formDescriptionNotContains.value.trim()
  )
})

// Helper to check if an amount value is valid (not null, undefined, NaN, or empty)
// v-model.number can produce NaN when input is cleared
function isValidAmount(value: number | null): boolean {
  return value !== null && Number.isFinite(value) && value > 0
}

// Helper to convert form amount to API value (null if invalid)
function toAmountOrNull(value: number | null): number | null {
  return isValidAmount(value) ? value : null
}

// Form validation
const canSave = computed(() => {
  return formName.value.trim() && formTagId.value && hasCondition.value
})

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    // Load rules, tags, and accounts in parallel
    const [rulesRes, tagsRes, accountsRes] = await Promise.all([
      fetchRules(),
      fetchTags(),
      fetchAccounts(),
    ])
    rules.value = rulesRes.rules
    tags.value = tagsRes.tags
    accounts.value = accountsRes.accounts
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = 'Failed to load rules'
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// ---------------------------------------------------------------------------
// Create/Edit Modal
// ---------------------------------------------------------------------------

function openCreateModal() {
  editingRule.value = null
  resetForm()
  showModal.value = true
}

function openEditModal(rule: TagRule) {
  editingRule.value = rule
  // Populate form with rule data
  formName.value = rule.name
  formTagId.value = rule.tag_id
  formEnabled.value = rule.enabled
  // Extract conditions from nested object
  const cond = rule.conditions || {}
  formMerchantContains.value = cond.merchant_contains || ''
  formMerchantExact.value = cond.merchant_exact || ''
  formDescriptionContains.value = cond.description_contains || ''
  formMinAmount.value = cond.min_amount ?? null
  formMaxAmount.value = cond.max_amount ?? null
  formAccountId.value = rule.account_id || ''
  formMerchantNotContains.value = cond.merchant_not_contains || ''
  formDescriptionNotContains.value = cond.description_not_contains || ''
  showTestResults.value = false
  testMatches.value = []
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingRule.value = null
  resetForm()
}

function resetForm() {
  formName.value = ''
  formTagId.value = ''
  formEnabled.value = true
  formMerchantContains.value = ''
  formMerchantExact.value = ''
  formDescriptionContains.value = ''
  formMinAmount.value = null
  formMaxAmount.value = null
  formAccountId.value = ''
  formMerchantNotContains.value = ''
  formDescriptionNotContains.value = ''
  showTestResults.value = false
  testMatches.value = []
  testTotal.value = 0
}

async function handleSave() {
  if (!canSave.value) return

  saving.value = true

  try {
    // Build conditions object (nested for API contract)
    const conditions = {
      merchant_contains: formMerchantContains.value.trim() || null,
      merchant_exact: formMerchantExact.value.trim() || null,
      description_contains: formDescriptionContains.value.trim() || null,
      min_amount: toAmountOrNull(formMinAmount.value),
      max_amount: toAmountOrNull(formMaxAmount.value),
      merchant_not_contains: formMerchantNotContains.value.trim() || null,
      description_not_contains: formDescriptionNotContains.value.trim() || null,
    }

    const data = {
      name: formName.value.trim(),
      tag_id: formTagId.value,
      enabled: formEnabled.value,
      conditions,
      account_id: formAccountId.value || null,
    }

    if (editingRule.value) {
      // Update existing rule
      const updated = await updateRule(editingRule.value.id, data)
      const index = rules.value.findIndex((r) => r.id === updated.id)
      if (index >= 0) {
        rules.value[index] = updated
      }
      toast.success(`Rule "${updated.name}" updated`)
    } else {
      // Create new rule
      const created = await createRule(data)
      rules.value.push(created)
      toast.success(`Rule "${created.name}" created`)
    }

    closeModal()
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to save rule')
    }
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------------------
// Test Rule Preview
// ---------------------------------------------------------------------------

async function handleTest() {
  // Must have at least one condition to test
  if (!hasCondition.value) {
    toast.error('Add at least one condition to test')
    return
  }

  testing.value = true
  showTestResults.value = true

  try {
    // Build conditions from form
    const conditions = {
      merchant_contains: formMerchantContains.value.trim() || null,
      merchant_exact: formMerchantExact.value.trim() || null,
      description_contains: formDescriptionContains.value.trim() || null,
      min_amount: toAmountOrNull(formMinAmount.value),
      max_amount: toAmountOrNull(formMaxAmount.value),
      merchant_not_contains: formMerchantNotContains.value.trim() || null,
      description_not_contains: formDescriptionNotContains.value.trim() || null,
    }

    // Use testConditions (works for both create and edit)
    const result = await testConditions({
      conditions,
      account_id: formAccountId.value || null,
      limit: 10,
    })
    testMatches.value = result.matches
    testTotal.value = result.total
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to test rule')
    }
    testMatches.value = []
    testTotal.value = 0
  } finally {
    testing.value = false
  }
}

// ---------------------------------------------------------------------------
// Delete Rule
// ---------------------------------------------------------------------------

function confirmDelete(rule: TagRule) {
  deletingRule.value = rule
}

function cancelDelete() {
  deletingRule.value = null
}

async function handleDelete() {
  if (!deletingRule.value) return

  deleting.value = true

  try {
    await deleteRule(deletingRule.value.id)
    rules.value = rules.value.filter((r) => r.id !== deletingRule.value?.id)
    toast.success(`Rule "${deletingRule.value.name}" deleted`)
    cancelDelete()
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to delete rule')
    }
  } finally {
    deleting.value = false
  }
}

// ---------------------------------------------------------------------------
// Toggle Enabled
// ---------------------------------------------------------------------------

async function toggleEnabled(rule: TagRule) {
  try {
    const updated = await updateRule(rule.id, { enabled: !rule.enabled })
    const index = rules.value.findIndex((r) => r.id === updated.id)
    if (index >= 0) {
      rules.value[index] = updated
    }
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to update rule')
    }
  }
}

// ---------------------------------------------------------------------------
// Drag and Drop Reordering
// ---------------------------------------------------------------------------

function handleDragStart(index: number) {
  draggingIndex.value = index
}

function handleDragOver(event: DragEvent, index: number) {
  event.preventDefault()
  if (draggingIndex.value === null || draggingIndex.value === index) return

  // Reorder in the displayedRules array
  const draggedRule = displayedRules.value[draggingIndex.value]
  if (!draggedRule) return

  // Create new array with reordered items
  const newOrder = [...displayedRules.value]
  newOrder.splice(draggingIndex.value, 1)
  newOrder.splice(index, 0, draggedRule)

  // Update the main rules array to match new order
  // This is a bit complex because we're working with filtered list
  if (!filterTagId.value) {
    // No filter - update directly
    rules.value = newOrder
  }

  draggingIndex.value = index
}

async function handleDragEnd() {
  if (draggingIndex.value === null) return

  draggingIndex.value = null

  // Save new order to backend
  try {
    // Get the current order of rule IDs from displayed list
    const ruleIds = displayedRules.value.map((r) => r.id)
    const result = await reorderRules({ rule_ids: ruleIds })
    rules.value = result.rules
  } catch (e) {
    // Revert by reloading
    await loadData()
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to reorder rules')
    }
  }
}

// ---------------------------------------------------------------------------
// Apply Rules
// ---------------------------------------------------------------------------

async function handleApplyRules() {
  applying.value = true

  try {
    const result = await applyRules({ untagged_only: true })
    if (result.tagged_count > 0) {
      toast.success(
        `Applied rules to ${result.tagged_count} transaction${result.tagged_count === 1 ? '' : 's'}`,
      )
    } else {
      toast.info('No untagged transactions matched any rules')
    }
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to apply rules')
    }
  } finally {
    applying.value = false
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Format a rule's conditions for display
function formatConditions(rule: TagRule): string {
  const parts: string[] = []
  const cond = rule.conditions || {}

  if (cond.merchant_contains) {
    parts.push(`"${cond.merchant_contains}"`)
  }
  if (cond.merchant_exact) {
    parts.push(`exactly "${cond.merchant_exact}"`)
  }
  if (cond.description_contains) {
    parts.push(`description has "${cond.description_contains}"`)
  }
  if (cond.min_amount != null && cond.max_amount != null) {
    parts.push(`£${cond.min_amount}-£${cond.max_amount}`)
  } else if (cond.min_amount != null) {
    parts.push(`≥ £${cond.min_amount}`)
  } else if (cond.max_amount != null) {
    parts.push(`≤ £${cond.max_amount}`)
  }
  if (rule.account_id) {
    const acc = accounts.value.find((a) => a.id === rule.account_id)
    parts.push(`from ${acc?.display_name || acc?.name || 'account'}`)
  }
  if (cond.merchant_not_contains) {
    parts.push(`not "${cond.merchant_not_contains}"`)
  }
  if (cond.description_not_contains) {
    parts.push(`desc not "${cond.description_not_contains}"`)
  }

  return parts.join(', ') || 'No conditions'
}

// Format amount for display
function formatAmount(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  }).format(amount)
}
</script>

<template>
  <div class="page-container">
    <!-- Settings navigation -->
    <nav class="settings-nav">
      <NuxtLink to="/settings/tags" class="settings-nav-link"> Tags </NuxtLink>
      <NuxtLink to="/settings/rules" class="settings-nav-link active">
        Auto-Tagging Rules
      </NuxtLink>
    </nav>

    <!-- Header -->
    <header class="page-header">
      <div>
        <h1 class="page-title">Auto-Tagging Rules</h1>
        <p class="page-subtitle">
          Create rules to automatically tag transactions based on conditions
        </p>
      </div>
      <NuxtLink to="/transactions" class="back-link">
        ← Back to Transactions
      </NuxtLink>
    </header>

    <!-- Actions bar -->
    <section class="actions-bar">
      <div class="actions-left">
        <!-- Filter by tag -->
        <div class="filter-group">
          <label class="filter-label">Filter by tag:</label>
          <AppSelect
            v-model="filterTagId"
            :options="tagOptions"
            placeholder="All tags"
            class="filter-select"
          />
        </div>
      </div>

      <div class="actions-right">
        <!-- Apply rules button -->
        <AppButton
          variant="secondary"
          :disabled="applying || rules.length === 0"
          @click="handleApplyRules"
        >
          {{ applying ? 'Applying...' : 'Apply to Untagged' }}
        </AppButton>

        <!-- Create rule button -->
        <AppButton @click="openCreateModal"> Create Rule </AppButton>
      </div>
    </section>

    <!-- Loading state -->
    <div v-if="loading" class="loading">Loading rules...</div>

    <!-- Error state -->
    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <!-- Rules list -->
    <section v-else class="rules-section">
      <div class="section-header">
        <h2 class="section-title">
          Your Rules ({{ displayedRules.length
          }}{{ filterTagId ? ' filtered' : '' }})
        </h2>
        <p class="section-hint">Drag to reorder priority (first match wins)</p>
      </div>

      <div v-if="displayedRules.length === 0" class="empty-state">
        <p v-if="rules.length === 0">
          No rules yet. Create your first rule to start auto-tagging!
        </p>
        <p v-else>No rules match the selected filter.</p>
      </div>

      <!-- Rules list with drag support -->
      <div v-else class="rules-list">
        <div
          v-for="(rule, index) in displayedRules"
          :key="rule.id"
          class="rule-row"
          :class="{
            'rule-row--disabled': !rule.enabled,
            'rule-row--dragging': draggingIndex === index,
          }"
          draggable="true"
          @dragstart="handleDragStart(index)"
          @dragover="handleDragOver($event, index)"
          @dragend="handleDragEnd"
        >
          <!-- Drag handle -->
          <div class="drag-handle" title="Drag to reorder">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              class="h-5 w-5"
            >
              <path
                fill-rule="evenodd"
                d="M2 4.75A.75.75 0 0 1 2.75 4h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 4.75Zm0 5A.75.75 0 0 1 2.75 9h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 9.75Zm0 5a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75Z"
                clip-rule="evenodd"
              />
            </svg>
          </div>

          <!-- Priority number -->
          <span class="priority-badge">{{ index + 1 }}</span>

          <!-- Rule info -->
          <div class="rule-info">
            <div class="rule-name">{{ rule.name }}</div>
            <div class="rule-conditions">{{ formatConditions(rule) }}</div>
          </div>

          <!-- Target tag -->
          <TagsTagChip :name="rule.tag_name" :colour="rule.tag_colour" />

          <!-- Enabled toggle -->
          <label class="enabled-toggle" title="Toggle enabled">
            <input
              type="checkbox"
              :checked="rule.enabled"
              class="toggle-checkbox"
              @change="toggleEnabled(rule)"
            />
            <span class="toggle-slider" />
          </label>

          <!-- Actions -->
          <div class="actions">
            <button
              type="button"
              class="action-btn edit"
              @click="openEditModal(rule)"
            >
              Edit
            </button>
            <button
              type="button"
              class="action-btn delete"
              @click="confirmDelete(rule)"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal modal--wide">
          <h3 class="modal-title">
            {{ editingRule ? 'Edit Rule' : 'Create Rule' }}
          </h3>

          <form class="modal-form" @submit.prevent="handleSave">
            <!-- Basic info row -->
            <div class="form-row">
              <!-- Name -->
              <label class="form-label flex-1">
                <span>Rule Name</span>
                <input
                  v-model="formName"
                  type="text"
                  class="form-input"
                  placeholder="e.g., Tesco Groceries"
                  maxlength="100"
                />
              </label>

              <!-- Target tag -->
              <label class="form-label flex-1">
                <span>Apply Tag</span>
                <AppSelect
                  v-model="formTagId"
                  :options="tagOptions"
                  placeholder="Select tag..."
                />
              </label>
            </div>

            <!-- Include conditions -->
            <fieldset class="conditions-fieldset">
              <legend class="conditions-legend">
                Include Conditions (all must match)
              </legend>

              <div class="conditions-grid">
                <!-- Business name contains -->
                <label class="form-label">
                  <span>Business name contains</span>
                  <input
                    v-model="formMerchantContains"
                    type="text"
                    class="form-input"
                    placeholder="e.g., Tesco, Amazon"
                  />
                </label>

                <!-- Business name exact -->
                <label class="form-label">
                  <span>Business name equals</span>
                  <input
                    v-model="formMerchantExact"
                    type="text"
                    class="form-input"
                    placeholder="Exact match"
                  />
                </label>

                <!-- Description contains -->
                <label class="form-label">
                  <span>Description contains</span>
                  <input
                    v-model="formDescriptionContains"
                    type="text"
                    class="form-input"
                    placeholder="e.g., subscription"
                  />
                </label>

                <!-- Account -->
                <label class="form-label">
                  <span>Account</span>
                  <AppSelect
                    v-model="formAccountId"
                    :options="accountOptions"
                    placeholder="Any account"
                  />
                </label>

                <!-- Amount range -->
                <label class="form-label">
                  <span>Min amount (absolute)</span>
                  <input
                    v-model="formMinAmountRaw"
                    type="number"
                    class="form-input"
                    placeholder="0.00"
                    min="0"
                    step="0.01"
                  />
                </label>

                <label class="form-label">
                  <span>Max amount (absolute)</span>
                  <input
                    v-model="formMaxAmountRaw"
                    type="number"
                    class="form-input"
                    placeholder="1000.00"
                    min="0"
                    step="0.01"
                  />
                </label>
              </div>
            </fieldset>

            <!-- Exclude conditions -->
            <fieldset class="conditions-fieldset">
              <legend class="conditions-legend">
                Exclude Conditions (none must match)
              </legend>

              <div class="conditions-grid">
                <!-- Business name not contains -->
                <label class="form-label">
                  <span>Business name does NOT contain</span>
                  <input
                    v-model="formMerchantNotContains"
                    type="text"
                    class="form-input"
                    placeholder="e.g., refund"
                  />
                </label>

                <!-- Description not contains -->
                <label class="form-label">
                  <span>Description does NOT contain</span>
                  <input
                    v-model="formDescriptionNotContains"
                    type="text"
                    class="form-input"
                    placeholder="e.g., refund"
                  />
                </label>
              </div>
            </fieldset>

            <!-- Enabled toggle -->
            <label class="form-checkbox">
              <input v-model="formEnabled" type="checkbox" />
              <span>Enabled (rule will be applied automatically)</span>
            </label>

            <!-- Validation hint -->
            <p v-if="!hasCondition" class="validation-hint">
              Add at least one condition for this rule
            </p>

            <!-- Test section (available for both create and edit) -->
            <div class="test-section">
              <button
                type="button"
                class="test-btn"
                :disabled="testing || !hasCondition"
                @click="handleTest"
              >
                {{ testing ? 'Testing...' : 'Preview Matches' }}
              </button>

              <div v-if="showTestResults" class="test-results">
                <p v-if="testTotal === 0" class="test-empty">
                  No matching transactions found
                </p>
                <template v-else>
                  <p class="test-count">
                    {{ testTotal }} matching transaction{{
                      testTotal === 1 ? '' : 's'
                    }}
                    {{ testTotal > 10 ? '(showing first 10)' : '' }}
                  </p>
                  <div class="test-list">
                    <div
                      v-for="match in testMatches"
                      :key="match.id"
                      class="test-match"
                    >
                      <div class="match-info">
                        <span class="match-merchant">
                          {{ match.counterparty_name || 'Unknown' }}
                        </span>
                        <span
                          v-if="match.description"
                          class="match-description"
                        >
                          {{ match.description }}
                        </span>
                      </div>
                      <span class="match-amount">
                        {{ formatAmount(match.amount, match.currency) }}
                      </span>
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- Actions -->
            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="closeModal">
                Cancel
              </button>
              <AppButton type="submit" :disabled="!canSave || saving">
                {{
                  saving
                    ? 'Saving...'
                    : editingRule
                      ? 'Save Changes'
                      : 'Create Rule'
                }}
              </AppButton>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div v-if="deletingRule" class="modal-overlay" @click.self="cancelDelete">
        <div class="modal">
          <h3 class="modal-title">Delete Rule</h3>

          <p class="confirm-text">
            Are you sure you want to delete "<strong>{{
              deletingRule.name
            }}</strong
            >"?
          </p>
          <p class="warning-text">
            This will not remove tags that were already applied by this rule.
          </p>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="cancelDelete">
              Cancel
            </button>
            <button
              type="button"
              class="btn-danger"
              :disabled="deleting"
              @click="handleDelete"
            >
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* Settings navigation */
.settings-nav {
  @apply mb-6 flex gap-1 border-b border-border;
}

.settings-nav-link {
  @apply px-4 py-2 text-sm font-medium text-muted;
  @apply border-b-2 border-transparent transition-colors;
  @apply hover:text-foreground;

  &.active,
  &.router-link-active {
    @apply border-primary text-primary;
  }
}

/* Page layout */
.page-container {
  @apply mx-auto max-w-5xl px-4 py-8;
}

.page-header {
  @apply mb-8 flex items-start justify-between;
}

.page-title {
  @apply text-2xl font-bold text-foreground;
}

.page-subtitle {
  @apply mt-1 text-muted;
}

.back-link {
  @apply text-sm text-muted hover:text-foreground;
}

/* Actions bar */
.actions-bar {
  @apply mb-6 flex flex-wrap items-center justify-between gap-4 rounded-lg bg-surface p-4;
}

.actions-left {
  @apply flex items-center gap-4;
}

.actions-right {
  @apply flex items-center gap-3;
}

.filter-group {
  @apply flex items-center gap-2;
}

.filter-label {
  @apply text-sm text-muted;
}

.filter-select {
  @apply w-48;
}

/* Rules section */
.rules-section {
  @apply rounded-lg bg-surface p-6;
}

.section-header {
  @apply mb-4 flex items-baseline justify-between;
}

.section-title {
  @apply text-lg font-semibold text-foreground;
}

.section-hint {
  @apply text-sm text-muted;
}

/* Rules list */
.rules-list {
  @apply space-y-2;
}

.rule-row {
  @apply flex items-center gap-4 rounded-md bg-gray-800/50 px-4 py-3;
  @apply cursor-grab transition-all;

  &:hover {
    @apply bg-gray-800;
  }

  &.rule-row--disabled {
    @apply opacity-50;
  }

  &.rule-row--dragging {
    @apply cursor-grabbing bg-gray-700 shadow-lg;
  }
}

.drag-handle {
  @apply cursor-grab text-muted;
  @apply hover:text-foreground;
}

.priority-badge {
  @apply flex h-6 w-6 items-center justify-center rounded-full;
  @apply bg-gray-700 text-xs font-medium text-muted;
}

.rule-info {
  @apply min-w-0 flex-1;
}

.rule-name {
  @apply font-medium text-foreground;
}

.rule-conditions {
  @apply text-sm text-muted;
}

/* Enabled toggle (slider style) */
.enabled-toggle {
  @apply relative inline-flex cursor-pointer items-center;
}

.toggle-checkbox {
  @apply sr-only;
}

.toggle-slider {
  @apply h-6 w-11 rounded-full bg-gray-600 transition-colors;
  @apply after:absolute after:left-[2px] after:top-[2px];
  @apply after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-transform;
  @apply after:content-[''];
}

.toggle-checkbox:checked + .toggle-slider {
  @apply bg-primary;
}

.toggle-checkbox:checked + .toggle-slider::after {
  @apply translate-x-5;
}

/* Actions */
.actions {
  @apply flex gap-2;
}

.action-btn {
  @apply rounded-md px-3 py-1 text-sm;
  @apply cursor-pointer border-none transition-colors;
  @apply disabled:cursor-not-allowed disabled:opacity-50;

  &.edit {
    @apply bg-gray-700 text-foreground hover:bg-gray-600;
  }

  &.delete {
    @apply bg-red-900/30 text-red-400 hover:bg-red-900/50;
  }
}

/* States */
.loading,
.empty-state {
  @apply py-8 text-center text-muted;
}

.error {
  @apply py-8 text-center text-red-400;
}

/* Modal */
.modal-overlay {
  @apply fixed inset-0 z-50 flex items-center justify-center;
  @apply bg-black/70 backdrop-blur-sm;
}

.modal {
  @apply w-full max-w-md rounded-lg bg-surface p-6;
  @apply shadow-xl;

  &.modal--wide {
    @apply max-h-[80vh] max-w-2xl overflow-y-auto;
  }
}

.modal-title {
  @apply mb-4 text-lg font-semibold text-foreground;
}

.modal-form {
  @apply space-y-4;
}

.form-row {
  @apply flex gap-4;
}

.form-label {
  @apply block space-y-1;

  & > span {
    @apply text-sm text-muted;
  }
}

.form-input {
  @apply w-full rounded-md bg-gray-800 px-3 py-2;
  @apply text-foreground placeholder-gray-500;
  @apply border border-gray-700 outline-none;
  @apply focus:border-primary focus:ring-1 focus:ring-primary;
}

/* Conditions fieldsets */
.conditions-fieldset {
  @apply rounded-md border border-gray-700 p-4;
}

.conditions-legend {
  @apply px-2 text-sm font-medium text-muted;
}

.conditions-grid {
  @apply grid grid-cols-2 gap-4;
}

/* Form checkbox */
.form-checkbox {
  @apply flex items-center gap-2 text-sm text-foreground;

  & input {
    @apply h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-800;
    @apply text-primary focus:ring-primary;
  }
}

.validation-hint {
  @apply text-sm text-amber-400;
}

/* Test section */
.test-section {
  @apply rounded-md border border-gray-700 p-4;
}

.test-btn {
  @apply rounded-md bg-gray-700 px-4 py-2 text-sm text-foreground;
  @apply cursor-pointer border-none transition-colors;
  @apply hover:bg-gray-600;
  @apply disabled:cursor-not-allowed disabled:opacity-50;
}

.test-results {
  @apply mt-4;
}

.test-empty {
  @apply text-sm text-muted;
}

.test-count {
  @apply mb-2 text-sm font-medium text-foreground;
}

.test-list {
  @apply max-h-40 space-y-1 overflow-y-auto;
}

.test-match {
  @apply flex justify-between rounded bg-gray-800 px-3 py-2 text-sm;
}

.match-info {
  @apply min-w-0 flex-1;
}

.match-merchant {
  @apply block text-foreground;
}

.match-description {
  @apply block truncate text-xs text-muted;
}

.match-amount {
  @apply shrink-0 text-muted;
}

/* Modal actions */
.modal-actions {
  @apply flex justify-end gap-3 pt-4;
}

.btn-secondary {
  @apply rounded-full px-4 py-2;
  @apply bg-gray-700 text-foreground;
  @apply cursor-pointer border-none;
  @apply hover:bg-gray-600;
}

.btn-danger {
  @apply rounded-full px-4 py-2;
  @apply bg-red-600 text-white;
  @apply cursor-pointer border-none;
  @apply hover:bg-red-700;
  @apply disabled:cursor-not-allowed disabled:opacity-50;
}

.confirm-text {
  @apply text-foreground;
}

.warning-text {
  @apply mt-2 text-sm text-muted;
}
</style>
