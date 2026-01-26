<!-- ==========================================================================
Accounts Page
Main page for managing bank connections and accounts
Shows connections grouped with their nested accounts
============================================================================ -->

<script setup lang="ts">
import type { Connection, Account, AccountCategory } from '~/types/accounts'
import type { Job } from '~/types/jobs'
import { useToastStore } from '~/stores/toast'

useHead({ title: 'Accounts | Finances' })

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
  triggerConnectionSync,
  fetchJob,
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
const showEditConnectionModal = ref(false)
const showAccountSettingsModal = ref(false)
const showDeleteConfirm = ref(false)
const editingConnection = ref<Connection | null>(null)
const editingAccount = ref<Account | null>(null)
const deletingConnection = ref<Connection | null>(null)

// Sync state - tracks which connections are currently syncing
const syncingConnections = ref<Set<string>>(new Set())
const syncJobs = ref<Map<string, Job>>(new Map()) // Latest job per connection

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

    // Initialize syncJobs from connection data and start polling for running jobs
    for (const conn of connections.value) {
      if (conn.latest_sync_job && !syncingConnections.value.has(conn.id)) {
        syncJobs.value.set(conn.id, conn.latest_sync_job)

        // If there's a running job (e.g., initial sync after OAuth), start polling
        if (conn.latest_sync_job.status === 'running') {
          syncingConnections.value.add(conn.id)
          pollJobStatus(conn.latest_sync_job.id, conn.id)
        }
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load data'
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// OAuth Callback Handling
// ---------------------------------------------------------------------------

// State for callback processing
const processingCallback = ref(false)

// Handle return from GoCardless OAuth flow
// GoCardless redirects to /accounts?ref=xxx (or ?ref=xxx&error=xxx&details=xxx on error)
async function handleOAuthCallback() {
  const ref = route.query.ref as string | undefined
  const gcError = route.query.error as string | undefined

  // If no ref, check for legacy callback param (in case backend redirects directly)
  if (!ref) {
    const callback = route.query.callback as string | undefined
    if (callback === 'success') {
      toast.success('Bank account connected successfully')
      router.replace({ query: {} })
    } else if (callback === 'error') {
      const reason = (route.query.reason as string) || 'Unknown error'
      toast.error(`Failed to connect bank: ${reason}`)
      router.replace({ query: {} })
    }
    return
  }

  // Handle GoCardless error (user cancelled, access denied, etc.)
  if (gcError) {
    const errorMessages: Record<string, string> = {
      UserCancelledSession: 'You cancelled the bank connection',
      AccessDenied: 'Access was denied by your bank',
      InstitutionError: 'Your bank reported an error',
    }
    const message = errorMessages[gcError] || `Connection failed: ${gcError}`
    toast.error(message)
    router.replace({ query: {} })
    return
  }

  // Process successful callback via backend API
  processingCallback.value = true
  try {
    const config = useRuntimeConfig()

    const response = await fetch(
      `${config.public.apiUrl}/api/connections/callback?ref=${encodeURIComponent(ref)}`,
      { method: 'GET', credentials: 'include' },
    )

    const data = await response.json()

    if (data.success) {
      toast.success('Bank account connected successfully')
    } else {
      const reasonMessages: Record<string, string> = {
        unknown_requisition: 'Connection not found',
        no_connection: 'Connection not found',
        internal_error: 'An error occurred',
      }
      const message =
        reasonMessages[data.reason] || `Connection failed: ${data.reason}`
      toast.error(message)
    }
  } catch (e) {
    console.error('Failed to process callback:', e)
    toast.error('Failed to complete bank connection')
  } finally {
    processingCallback.value = false
    router.replace({ query: {} })
  }
}

// Load data on mount and handle any OAuth callback
onMounted(async () => {
  await handleOAuthCallback()
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
  editingConnection.value = connection
  showEditConnectionModal.value = true
}

function openEditAccountModal(account: Account) {
  editingAccount.value = account
  showAccountSettingsModal.value = true
}

function closeEditConnectionModal() {
  showEditConnectionModal.value = false
  editingConnection.value = null
}

function closeAccountSettingsModal() {
  showAccountSettingsModal.value = false
  editingAccount.value = null
}

async function handleSaveConnectionName(id: string, newName: string) {
  try {
    const updated = await updateConnection(id, { friendly_name: newName })
    // Update local state
    const index = connections.value.findIndex((c) => c.id === id)
    if (index !== -1) {
      connections.value[index] = updated
    }
    closeEditConnectionModal()
  } catch (e) {
    console.error('Failed to save:', e)
    throw e
  }
}

async function handleSaveAccountSettings(
  id: string,
  settings: {
    display_name: string | null
    category: AccountCategory | null
    min_balance: number | null
    credit_limit: number | null
  },
) {
  try {
    const updated = await updateAccount(id, settings)
    // Update local state
    const index = accounts.value.findIndex((a) => a.id === id)
    if (index !== -1) {
      accounts.value[index] = updated
    }
    closeAccountSettingsModal()
  } catch (e) {
    console.error('Failed to save:', e)
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

// ---------------------------------------------------------------------------
// Sync Handling
// ---------------------------------------------------------------------------

async function handleSync(connection: Connection) {
  // Don't start another sync if already syncing
  if (syncingConnections.value.has(connection.id)) {
    return
  }

  try {
    // Mark as syncing
    syncingConnections.value.add(connection.id)

    // Trigger sync and get job
    const job = await triggerConnectionSync(connection.id)
    syncJobs.value.set(connection.id, job)

    // If job failed immediately (e.g., Dagster unavailable), show error
    if (job.status === 'failed') {
      toast.error(`Sync failed: ${job.error_message || 'Unknown error'}`)
      syncingConnections.value.delete(connection.id)
      return
    }

    // Show starting message
    toast.success('Sync started')

    // Start polling for job status
    pollJobStatus(job.id, connection.id)
  } catch (e) {
    console.error('Failed to trigger sync:', e)
    toast.error('Failed to start sync')
    syncingConnections.value.delete(connection.id)
  }
}

// Poll for job completion
async function pollJobStatus(
  jobId: string,
  connectionId: string,
  pollCount = 0,
) {
  // Stop polling after ~5 minutes (150 polls * 2 seconds)
  const maxPolls = 150

  try {
    const job = await fetchJob(jobId)
    syncJobs.value.set(connectionId, job)

    if (job.status === 'completed') {
      // Success! Reload data and notify
      toast.success('Sync complete')
      syncingConnections.value.delete(connectionId)
      await loadData()
    } else if (job.status === 'failed') {
      // Failed
      toast.error(`Sync failed: ${job.error_message || 'Unknown error'}`)
      syncingConnections.value.delete(connectionId)
    } else if (pollCount < maxPolls) {
      // Still running, poll again in 2 seconds
      setTimeout(() => pollJobStatus(jobId, connectionId, pollCount + 1), 2000)
    } else {
      // Timeout
      toast.error('Sync timed out. Check back later.')
      syncingConnections.value.delete(connectionId)
    }
  } catch (e) {
    console.error('Failed to poll job status:', e)
    // Keep trying a few more times on network errors
    if (pollCount < 5) {
      setTimeout(() => pollJobStatus(jobId, connectionId, pollCount + 1), 2000)
    } else {
      syncingConnections.value.delete(connectionId)
    }
  }
}
</script>

<template>
  <div>
    <!-- Full-page overlay when processing OAuth callback -->
    <div
      v-if="processingCallback"
      class="fixed inset-0 z-50 flex items-center justify-center bg-onyx"
    >
      <div class="text-center">
        <div
          class="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
        />
        <p class="text-foreground">Connecting to your bank...</p>
      </div>
    </div>

    <div class="space-y-6">
      <!-- Page header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold sm:text-3xl">Accounts</h1>
          <p class="mt-1 text-muted">Manage your connected bank accounts</p>
        </div>

        <!-- Action buttons -->
        <div class="flex items-center gap-3">
          <!-- Refresh button (only shown when there are connections) -->
          <button
            v-if="hasConnections"
            type="button"
            class="flex items-center gap-2 rounded-lg border border-border px-4 py-2 font-medium text-muted transition-colors hover:bg-border hover:text-foreground"
            :disabled="syncingConnections.size > 0"
            @click="loadData"
          >
            <!-- Refresh icon -->
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              class="h-5 w-5"
              :class="{ 'animate-spin': syncingConnections.size > 0 }"
            >
              <path
                fill-rule="evenodd"
                d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.433a.75.75 0 0 0 0-1.5H3.989a.75.75 0 0 0-.75.75v4.242a.75.75 0 0 0 1.5 0v-2.43l.31.31a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm1.23-3.723a.75.75 0 0 0 .219-.53V2.929a.75.75 0 0 0-1.5 0V5.36l-.31-.31A7 7 0 0 0 3.239 8.188a.75.75 0 1 0 1.448.389A5.5 5.5 0 0 1 13.89 6.11l.311.31h-2.432a.75.75 0 0 0 0 1.5h4.243a.75.75 0 0 0 .53-.219Z"
                clip-rule="evenodd"
              />
            </svg>
            Refresh
          </button>

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
          :sync-job="syncJobs.get(connection.id) || null"
          :syncing="syncingConnections.has(connection.id)"
          @edit-connection="openEditConnectionModal"
          @edit-account="openEditAccountModal"
          @reauthorise="handleReauthorise"
          @delete="openDeleteConfirm"
          @sync="handleSync"
        />
      </div>

      <!-- Create Connection Modal -->
      <AccountsCreateConnectionModal
        :show="showCreateModal"
        @close="closeCreateModal"
        @created="handleConnectionCreated"
      />

      <!-- Edit Connection Name Modal -->
      <AccountsEditDisplayNameModal
        v-if="editingConnection"
        :show="showEditConnectionModal"
        entity-type="connection"
        :entity-id="editingConnection.id"
        :current-name="editingConnection.friendly_name"
        @close="closeEditConnectionModal"
        @save="handleSaveConnectionName"
      />

      <!-- Account Settings Modal -->
      <AccountsAccountSettingsModal
        v-if="editingAccount"
        :show="showAccountSettingsModal"
        :account="editingAccount"
        @close="closeAccountSettingsModal"
        @save="handleSaveAccountSettings"
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
