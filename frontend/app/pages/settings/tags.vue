<!-- ==========================================================================
Settings / Tags Page
Manage user-defined tags for categorising transactions
============================================================================ -->

<script setup lang="ts">
import type { Tag } from '~/types/tags'
import { useToastStore } from '~/stores/toast'

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const { fetchTags, createTag, updateTag, deleteTag, ApiError } = useTagsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const tags = ref<Tag[]>([])
const loading = ref(true)
const error = ref('')

// Create form
const newTagName = ref('')
const newTagColour = ref('#10B981') // Default emerald
const creating = ref(false)

// Edit modal
const editingTag = ref<Tag | null>(null)
const editName = ref('')
const editColour = ref('')
const saving = ref(false)

// Delete confirmation
const deletingTag = ref<Tag | null>(null)
const deleting = ref(false)

// Predefined colours for quick selection
const colourPresets = [
  '#10B981', // Emerald
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#6366F1', // Indigo
  '#14B8A6', // Teal
]

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetchTags()
    tags.value = response.tags
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = 'Failed to load tags'
    }
  } finally {
    loading.value = false
  }
}

// Load on mount
onMounted(loadData)

// ---------------------------------------------------------------------------
// Create Tag
// ---------------------------------------------------------------------------

async function handleCreate() {
  const trimmed = newTagName.value.trim()
  if (!trimmed) return

  creating.value = true

  try {
    const tag = await createTag({
      name: trimmed,
      colour: newTagColour.value,
    })
    tags.value.push(tag)
    tags.value.sort((a, b) => a.name.localeCompare(b.name))
    newTagName.value = ''
    toast.success(`Tag "${tag.name}" created`)
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to create tag')
    }
  } finally {
    creating.value = false
  }
}

// ---------------------------------------------------------------------------
// Edit Tag
// ---------------------------------------------------------------------------

function openEditModal(tag: Tag) {
  editingTag.value = tag
  editName.value = tag.name
  editColour.value = tag.colour || '#10B981'
}

function closeEditModal() {
  editingTag.value = null
}

async function handleSave() {
  if (!editingTag.value) return

  const trimmed = editName.value.trim()
  if (!trimmed) return

  saving.value = true

  try {
    const updated = await updateTag(editingTag.value.id, {
      name: trimmed,
      colour: editColour.value,
    })
    // Update in list
    const index = tags.value.findIndex((t) => t.id === updated.id)
    if (index >= 0) {
      tags.value[index] = updated
    }
    tags.value.sort((a, b) => a.name.localeCompare(b.name))
    toast.success(`Tag "${updated.name}" updated`)
    closeEditModal()
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to update tag')
    }
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------------------
// Delete Tag
// ---------------------------------------------------------------------------

function confirmDelete(tag: Tag) {
  deletingTag.value = tag
}

function cancelDelete() {
  deletingTag.value = null
}

async function handleDelete() {
  if (!deletingTag.value) return

  deleting.value = true

  try {
    await deleteTag(deletingTag.value.id)
    tags.value = tags.value.filter((t) => t.id !== deletingTag.value?.id)
    toast.success(`Tag "${deletingTag.value.name}" deleted`)
    cancelDelete()
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to delete tag')
    }
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <!-- Header -->
    <header class="page-header">
      <div>
        <h1 class="page-title">Tags</h1>
        <p class="page-subtitle">
          Create and manage tags to categorise your transactions
        </p>
      </div>
      <NuxtLink to="/transactions" class="back-link">
        ← Back to Transactions
      </NuxtLink>
    </header>

    <!-- Create new tag -->
    <section class="create-section">
      <h2 class="section-title">Create New Tag</h2>
      <form class="create-form" @submit.prevent="handleCreate">
        <!-- Name input -->
        <input
          v-model="newTagName"
          type="text"
          placeholder="Tag name..."
          class="name-input"
          maxlength="30"
        />

        <!-- Colour picker -->
        <div class="colour-picker">
          <!-- Preset colours -->
          <button
            v-for="colour in colourPresets"
            :key="colour"
            type="button"
            class="colour-preset"
            :class="{ selected: newTagColour === colour }"
            :style="{ backgroundColor: colour }"
            @click="newTagColour = colour"
          />
          <!-- Custom colour input -->
          <input
            v-model="newTagColour"
            type="color"
            class="colour-input"
            title="Custom colour"
          />
        </div>

        <!-- Preview -->
        <TagsTagChip :name="newTagName || 'Preview'" :colour="newTagColour" />

        <!-- Submit -->
        <AppButton type="submit" :disabled="!newTagName.trim() || creating">
          {{ creating ? 'Creating...' : 'Create Tag' }}
        </AppButton>
      </form>
    </section>

    <!-- Loading state -->
    <div v-if="loading" class="loading">Loading tags...</div>

    <!-- Error state -->
    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <!-- Tags list -->
    <section v-else class="tags-section">
      <h2 class="section-title">Your Tags ({{ tags.length }})</h2>

      <div v-if="tags.length === 0" class="empty-state">
        <p>No tags yet. Create your first tag above!</p>
      </div>

      <div v-else class="tags-list">
        <div v-for="tag in tags" :key="tag.id" class="tag-row">
          <!-- Tag chip -->
          <TagsTagChip :name="tag.name" :colour="tag.colour" />

          <!-- Usage count -->
          <span class="usage-count">
            {{ tag.usage_count }}
            {{ tag.usage_count === 1 ? 'transaction' : 'transactions' }}
          </span>

          <!-- Actions -->
          <div class="actions">
            <button
              type="button"
              class="action-btn edit"
              @click="openEditModal(tag)"
            >
              Edit
            </button>
            <button
              type="button"
              class="action-btn delete"
              @click="confirmDelete(tag)"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Edit Modal -->
    <Teleport to="body">
      <div v-if="editingTag" class="modal-overlay" @click.self="closeEditModal">
        <div class="modal">
          <h3 class="modal-title">Edit Tag</h3>

          <form class="modal-form" @submit.prevent="handleSave">
            <!-- Name -->
            <label class="form-label">
              <span>Name</span>
              <input
                v-model="editName"
                type="text"
                class="form-input"
                maxlength="30"
              />
            </label>

            <!-- Colour -->
            <label class="form-label">
              <span>Colour</span>
              <div class="colour-picker">
                <button
                  v-for="colour in colourPresets"
                  :key="colour"
                  type="button"
                  class="colour-preset"
                  :class="{ selected: editColour === colour }"
                  :style="{ backgroundColor: colour }"
                  @click="editColour = colour"
                />
                <input v-model="editColour" type="color" class="colour-input" />
              </div>
            </label>

            <!-- Preview -->
            <div class="preview-row">
              <span class="preview-label">Preview:</span>
              <TagsTagChip :name="editName || 'Preview'" :colour="editColour" />
            </div>

            <!-- Actions -->
            <div class="modal-actions">
              <button
                type="button"
                class="btn-secondary"
                @click="closeEditModal"
              >
                Cancel
              </button>
              <AppButton type="submit" :disabled="!editName.trim() || saving">
                {{ saving ? 'Saving...' : 'Save' }}
              </AppButton>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div v-if="deletingTag" class="modal-overlay" @click.self="cancelDelete">
        <div class="modal">
          <h3 class="modal-title">Delete Tag</h3>

          <p class="confirm-text">
            Are you sure you want to delete "<strong>{{
              deletingTag.name
            }}</strong
            >"?
          </p>
          <p v-if="deletingTag.usage_count > 0" class="warning-text">
            This will remove the tag from {{ deletingTag.usage_count }}
            {{
              deletingTag.usage_count === 1 ? 'transaction' : 'transactions'
            }}.
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
/* Page layout */
.page-container {
  @apply mx-auto max-w-4xl px-4 py-8;
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

/* Sections */
.section-title {
  @apply mb-4 text-lg font-semibold text-foreground;
}

.create-section {
  @apply mb-8 rounded-lg bg-surface p-6;
}

.tags-section {
  @apply rounded-lg bg-surface p-6;
}

/* Create form */
.create-form {
  @apply flex flex-wrap items-center gap-4;
}

.name-input {
  @apply w-48 rounded-md bg-gray-800 px-3 py-2;
  @apply text-foreground placeholder-gray-500;
  @apply border border-gray-700 outline-none;
  @apply focus:border-primary focus:ring-1 focus:ring-primary;
}

/* Colour picker */
.colour-picker {
  @apply flex items-center gap-2;
}

.colour-preset {
  @apply h-6 w-6 cursor-pointer rounded-full;
  @apply border-2 border-transparent;
  @apply transition-transform hover:scale-110;

  &.selected {
    @apply border-white ring-2 ring-primary;
  }
}

.colour-input {
  @apply h-6 w-6 cursor-pointer rounded-full;
  @apply border-none bg-transparent;
}

/* Tags list */
.tags-list {
  @apply space-y-2;
}

.tag-row {
  @apply flex items-center gap-4 rounded-md bg-gray-800/50 px-4 py-3;
}

.usage-count {
  @apply flex-1 text-sm text-muted;
}

.actions {
  @apply flex gap-2;
}

.action-btn {
  @apply rounded-md px-3 py-1 text-sm;
  @apply cursor-pointer border-none transition-colors;

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
}

.modal-title {
  @apply mb-4 text-lg font-semibold text-foreground;
}

.modal-form {
  @apply space-y-4;
}

.form-label {
  @apply block space-y-1;

  & > span {
    @apply text-sm text-muted;
  }
}

.form-input {
  @apply w-full rounded-md bg-gray-800 px-3 py-2;
  @apply text-foreground;
  @apply border border-gray-700 outline-none;
  @apply focus:border-primary focus:ring-1 focus:ring-primary;
}

.preview-row {
  @apply flex items-center gap-3;
}

.preview-label {
  @apply text-sm text-muted;
}

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
  @apply mt-2 text-sm text-amber-400;
}
</style>
