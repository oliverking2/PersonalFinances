<!-- ==========================================================================
Accounts Page
Main page for managing bank connections and accounts
Shows connections grouped with their nested accounts
============================================================================ -->

<script setup lang="ts">
import type { Connection, Account } from '~/types/accounts'
import { useToastStore } from '~/stores/toast'

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const {
  fetchConnections,
  fetchAccounts,
  updateConnection,
  updateAccount,
  deleteConnection,
  reauthoriseConnection,
  ApiError,
} = useAccountsApi()

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const connections = ref<Connection[]>([])
const accounts = ref<Account[]>([])
const loading = ref(true)
const error = ref('')

// Modal state
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteConfirm = ref(false)
const editingEntity = ref<{
  type: 'account' | 'connection'
  id: string
  currentName: string
} | null>(null)
const deletingConnection = ref<Connection | null>(null)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Group accounts by connection_id for efficient lookup
const accountsByConnection = computed(() => {
  const grouped: Record<string, Account[]> = {}
  for (const account of accounts.value) {
    const connectionId = account.connection_id
    const existing = grouped[connectionId]
    if (existing) {
      existing.push(account)
    } else {
      grouped[connectionId] = [account]
    }
  }
  return grouped
})

// Check if there are any connections
const hasConnections = computed(() => connections.value.length > 0)

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    // Fetch connections and accounts in parallel
    const [connectionsResponse, accountsResponse] = await Promise.all([
      fetchConnections(),
      fetchAccounts(),
    ])

    connections.value = connectionsResponse.connections
    accounts.value = accountsResponse.accounts
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load data'
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// OAuth Callback Handling
// ---------------------------------------------------------------------------

// Handle return from GoCardless OAuth flow
// Backend redirects to /accounts?callback=success or ?callback=error&reason=...
function handleOAuthCallback() {
  const callback = route.query.callback as string | undefined

  if (callback === 'success') {
    toast.success('Bank account connected successfully')
    // Clear query params from URL to prevent re-triggering on refresh
    router.replace({ query: {} })
  } else if (callback === 'error') {
    const reason = (route.query.reason as string) || 'Unknown error'
    toast.error(`Failed to connect bank: ${reason}`)
    router.replace({ query: {} })
  }
}

// Load data on mount and handle any OAuth callback
onMounted(() => {
  handleOAuthCallback()
  loadData()
})

// ---------------------------------------------------------------------------
// Modal Handlers
// ---------------------------------------------------------------------------

function openCreateModal() {
  showCreateModal.value = true
}

function closeCreateModal() {
  showCreateModal.value = false
}

function handleConnectionCreated(authUrl: string) {
  showCreateModal.value = false

  // Redirect user to the bank's authentication page
  window.location.href = authUrl
}

function openEditConnectionModal(connection: Connection) {
  editingEntity.value = {
    type: 'connection',
    id: connection.id,
    currentName: connection.friendly_name,
  }
  showEditModal.value = true
}

function openEditAccountModal(account: Account) {
  editingEntity.value = {
    type: 'account',
    id: account.id,
    currentName: account.display_name || account.name || '',
  }
  showEditModal.value = true
}

function closeEditModal() {
  showEditModal.value = false
  editingEntity.value = null
}

async function handleSaveEdit(id: string, newName: string) {
  if (!editingEntity.value) return

  try {
    if (editingEntity.value.type === 'connection') {
      const updated = await updateConnection(id, { friendly_name: newName })
      // Update local state
      const index = connections.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        connections.value[index] = updated
      }
    } else {
      const updated = await updateAccount(id, { display_name: newName })
      // Update local state
      const index = accounts.value.findIndex((a) => a.id === id)
      if (index !== -1) {
        accounts.value[index] = updated
      }
    }
    closeEditModal()
  } catch (e) {
    console.error('Failed to save:', e)
    // Error will be shown in modal
    throw e
  }
}

function openDeleteConfirm(connection: Connection) {
  deletingConnection.value = connection
  showDeleteConfirm.value = true
}

function closeDeleteConfirm() {
  showDeleteConfirm.value = false
  deletingConnection.value = null
}

async function handleConfirmDelete() {
  if (!deletingConnection.value) return

  try {
    await deleteConnection(deletingConnection.value.id)
    // Remove from local state
    connections.value = connections.value.filter(
      (c) => c.id !== deletingConnection.value?.id,
    )
    accounts.value = accounts.value.filter(
      (a) => a.connection_id !== deletingConnection.value?.id,
    )
    closeDeleteConfirm()
  } catch (e) {
    console.error('Failed to delete:', e)
    alert('Failed to delete connection')
  }
}

async function handleReauthorise(connection: Connection) {
  try {
    const response = await reauthoriseConnection(connection.id)

    // Redirect user to the bank's reauthorisation page
    window.location.href = response.link
  } catch (e) {
    // Handle 501 Not Implemented - feature coming soon
    if (e instanceof ApiError && e.status === 501) {
      alert('Reauthorisation coming soon! This feature is still being built.')
    } else {
      console.error('Failed to reauthorise:', e)
      alert('Failed to start reauthorisation')
    }
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">Accounts</h1>
        <p class="mt-1 text-muted">Manage your connected bank accounts</p>
      </div>

      <!-- New Connection button -->
      <button
        type="button"
        class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 font-medium text-white transition-colors hover:bg-primary-hover"
        @click="openCreateModal"
      >
        <!-- Plus icon -->
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          class="h-5 w-5"
        >
          <path
            d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
          />
        </svg>
        New Connection
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="py-12 text-center text-muted">
      Loading accounts...
    </div>

    <!-- Error state -->
    <div
      v-else-if="error"
      class="rounded-lg border border-negative/50 bg-negative/10 px-6 py-4 text-negative"
    >
      {{ error }}
      <button
        type="button"
        class="ml-2 underline hover:no-underline"
        @click="loadData"
      >
        Retry
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!hasConnections"
      class="rounded-lg border border-border bg-surface px-6 py-12 text-center"
    >
      <!-- Bank icon -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="1.5"
        stroke="currentColor"
        class="mx-auto h-12 w-12 text-muted"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z"
        />
      </svg>
      <h3 class="mt-4 font-semibold text-foreground">No connections yet</h3>
      <p class="mt-1 text-sm text-muted">
        Connect your first bank account to start tracking your finances.
      </p>
      <button
        type="button"
        class="mt-4 rounded-lg bg-primary px-4 py-2 font-medium text-white transition-colors hover:bg-primary-hover"
        @click="openCreateModal"
      >
        Connect Bank Account
      </button>
    </div>

    <!-- Connections list -->
    <div v-else class="space-y-4">
      <AccountsConnectionCard
        v-for="connection in connections"
        :key="connection.id"
        :connection="connection"
        :accounts="accountsByConnection[connection.id] || []"
        @edit-connection="openEditConnectionModal"
        @edit-account="openEditAccountModal"
        @reauthorise="handleReauthorise"
        @delete="openDeleteConfirm"
      />
    </div>

    <!-- Create Connection Modal -->
    <AccountsCreateConnectionModal
      :show="showCreateModal"
      @close="closeCreateModal"
      @created="handleConnectionCreated"
    />

    <!-- Edit Display Name Modal -->
    <AccountsEditDisplayNameModal
      v-if="editingEntity"
      :show="showEditModal"
      :entity-type="editingEntity.type"
      :entity-id="editingEntity.id"
      :current-name="editingEntity.currentName"
      @close="closeEditModal"
      @save="handleSaveEdit"
    />

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showDeleteConfirm && deletingConnection"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          @click.self="closeDeleteConfirm"
        >
          <div
            class="w-full max-w-md rounded-lg border border-border bg-surface p-6"
          >
            <h2 class="text-lg font-semibold text-foreground">
              Delete Connection
            </h2>
            <p class="mt-2 text-muted">
              Are you sure you want to delete
              <strong class="text-foreground">{{
                deletingConnection.friendly_name
              }}</strong
              >? This will also remove all associated accounts and cannot be
              undone.
            </p>
            <div class="mt-6 flex justify-end gap-3">
              <button
                type="button"
                class="rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted transition-colors hover:bg-border hover:text-foreground"
                @click="closeDeleteConfirm"
              >
                Cancel
              </button>
              <button
                type="button"
                class="rounded-lg bg-negative px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-negative/80"
                @click="handleConfirmDelete"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* Fade transition for modal backdrop */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
