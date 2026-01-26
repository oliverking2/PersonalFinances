<!-- ==========================================================================
ConnectionCard
Card displaying a bank connection with its nested accounts
Includes actions: edit name, reauthorise (if expired or pending), delete
============================================================================ -->

<script setup lang="ts">
import type { Connection, Account } from '~/types/accounts'
import type { Job } from '~/types/jobs'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  connection: Connection
  accounts: Account[]
  syncJob?: Job | null // Most recent sync job for this connection
  syncing?: boolean // Whether a sync is currently in progress
}>()

const emit = defineEmits<{
  editConnection: [connection: Connection]
  editAccount: [account: Account]
  reauthorise: [connection: Connection]
  delete: [connection: Connection]
  sync: [connection: Connection]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Controls the dropdown menu visibility
const showMenu = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Check if connection needs reauthorisation (expired or pending/abandoned OAuth)
const needsReauth = computed(() =>
  ['expired', 'pending'].includes(props.connection.status),
)
const isExpired = computed(() => props.connection.status === 'expired')
const isPending = computed(() => props.connection.status === 'pending')
const isActive = computed(() => props.connection.status === 'active')

// Sync status
const isSyncing = computed(() => props.syncing === true)
const isInitialSync = computed(
  () => isSyncing.value && props.accounts.length === 0,
)
const lastSyncFailed = computed(
  () => props.syncJob?.status === 'failed' && !isSyncing.value,
)

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function handleEditConnection() {
  showMenu.value = false
  emit('editConnection', props.connection)
}

function handleEditAccount(account: Account) {
  emit('editAccount', account)
}

function handleReauthorise() {
  emit('reauthorise', props.connection)
}

function handleSync() {
  showMenu.value = false
  emit('sync', props.connection)
}

function handleDelete() {
  showMenu.value = false
  emit('delete', props.connection)
}

function toggleMenu() {
  showMenu.value = !showMenu.value
}

// Close menu when clicking outside
function closeMenu() {
  showMenu.value = false
}
</script>

<template>
  <!-- Card container with border and background -->
  <div class="rounded-lg border border-border bg-surface">
    <!-- Header: institution info, status, and actions -->
    <div
      class="flex items-center justify-between border-b border-border px-6 py-4"
    >
      <!-- Left: institution logo, name, and friendly name -->
      <div class="flex items-center gap-4">
        <!-- Institution logo (fallback to first letter) -->
        <div
          class="flex h-10 w-10 items-center justify-center rounded-lg bg-onyx"
        >
          <img
            v-if="connection.institution.logo_url"
            :src="connection.institution.logo_url"
            :alt="connection.institution.name"
            class="h-8 w-8 object-contain"
          />
          <span v-else class="text-lg font-bold text-muted">
            {{ connection.institution.name.charAt(0) }}
          </span>
        </div>

        <!-- Name and institution -->
        <div>
          <h3 class="font-semibold text-foreground">
            {{ connection.friendly_name }}
          </h3>
          <p class="text-sm text-muted">
            {{ connection.institution.name }}
          </p>
        </div>
      </div>

      <!-- Right: status badge, sync status, and actions -->
      <div class="flex items-center gap-3">
        <AccountsStatusIndicator :status="connection.status" />

        <!-- Sync status indicator (shown when syncing or last sync failed) -->
        <span
          v-if="isSyncing"
          class="flex items-center gap-1.5 text-sm text-muted"
        >
          <!-- Spinning refresh icon -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            class="h-4 w-4 animate-spin"
          >
            <path
              fill-rule="evenodd"
              d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.433a.75.75 0 0 0 0-1.5H3.989a.75.75 0 0 0-.75.75v4.242a.75.75 0 0 0 1.5 0v-2.43l.31.31a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm1.23-3.723a.75.75 0 0 0 .219-.53V2.929a.75.75 0 0 0-1.5 0V5.36l-.31-.31A7 7 0 0 0 3.239 8.188a.75.75 0 1 0 1.448.389A5.5 5.5 0 0 1 13.89 6.11l.311.31h-2.432a.75.75 0 0 0 0 1.5h4.243a.75.75 0 0 0 .53-.219Z"
              clip-rule="evenodd"
            />
          </svg>
          {{ isInitialSync ? 'Running initial sync...' : 'Syncing...' }}
        </span>
        <span
          v-else-if="lastSyncFailed"
          class="flex items-center gap-1.5 text-sm text-negative"
          title="Last sync failed"
        >
          <!-- Warning icon -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            class="h-4 w-4"
          >
            <path
              fill-rule="evenodd"
              d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-8-5a.75.75 0 0 1 .75.75v4.5a.75.75 0 0 1-1.5 0v-4.5A.75.75 0 0 1 10 5Zm0 10a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
              clip-rule="evenodd"
            />
          </svg>
          Sync failed
        </span>

        <!-- Reauthorise button (shown when expired or pending) -->
        <button
          v-if="needsReauth"
          type="button"
          class="rounded-lg bg-warning/10 px-3 py-1.5 text-sm font-medium text-warning transition-colors hover:bg-warning/20"
          @click="handleReauthorise"
        >
          {{ isPending ? 'Authorise' : 'Reauthorise' }}
        </button>

        <!-- Sync button (shown for active connections) -->
        <button
          v-if="isActive && !isSyncing"
          type="button"
          class="rounded p-1.5 text-muted transition-colors hover:bg-border hover:text-foreground"
          title="Sync now"
          @click="handleSync"
        >
          <!-- Refresh icon -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            class="h-5 w-5"
          >
            <path
              fill-rule="evenodd"
              d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.433a.75.75 0 0 0 0-1.5H3.989a.75.75 0 0 0-.75.75v4.242a.75.75 0 0 0 1.5 0v-2.43l.31.31a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm1.23-3.723a.75.75 0 0 0 .219-.53V2.929a.75.75 0 0 0-1.5 0V5.36l-.31-.31A7 7 0 0 0 3.239 8.188a.75.75 0 1 0 1.448.389A5.5 5.5 0 0 1 13.89 6.11l.311.31h-2.432a.75.75 0 0 0 0 1.5h4.243a.75.75 0 0 0 .53-.219Z"
              clip-rule="evenodd"
            />
          </svg>
        </button>

        <!-- Overflow menu -->
        <div class="relative">
          <button
            type="button"
            class="rounded p-1.5 text-muted transition-colors hover:bg-border hover:text-foreground"
            title="More options"
            @click="toggleMenu"
            @blur="closeMenu"
          >
            <!-- Ellipsis icon (heroicons/mini) -->
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              class="h-5 w-5"
            >
              <path
                d="M10 3a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM10 8.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM11.5 15.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0Z"
              />
            </svg>
          </button>

          <!-- Dropdown menu -->
          <div
            v-if="showMenu"
            class="absolute right-0 top-full z-10 mt-1 w-40 rounded-lg border border-border bg-surface py-1 shadow-lg"
          >
            <button
              type="button"
              class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-foreground transition-colors hover:bg-onyx"
              @mousedown.prevent="handleEditConnection"
            >
              <!-- Pencil icon -->
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                class="h-4 w-4"
              >
                <path
                  d="m5.433 13.917 1.262-3.155A4 4 0 0 1 7.58 9.42l6.92-6.918a2.121 2.121 0 0 1 3 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 0 1-.65-.65Z"
                />
                <path
                  d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0 0 10 3H4.75A2.75 2.75 0 0 0 2 5.75v9.5A2.75 2.75 0 0 0 4.75 18h9.5A2.75 2.75 0 0 0 17 15.25V10a.75.75 0 0 0-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5Z"
                />
              </svg>
              Edit name
            </button>
            <button
              type="button"
              class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-negative transition-colors hover:bg-onyx"
              @mousedown.prevent="handleDelete"
            >
              <!-- Trash icon -->
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                class="h-4 w-4"
              >
                <path
                  fill-rule="evenodd"
                  d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.519.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z"
                  clip-rule="evenodd"
                />
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Warning banner for connections needing attention -->
    <div
      v-if="needsReauth"
      class="flex items-center gap-2 px-6 py-2 text-sm"
      :class="
        isExpired
          ? 'bg-negative/10 text-negative'
          : 'bg-warning/10 text-warning'
      "
    >
      <!-- Warning icon -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        class="h-4 w-4"
      >
        <path
          fill-rule="evenodd"
          d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
          clip-rule="evenodd"
        />
      </svg>
      {{
        isExpired
          ? 'Connection expired. Reauthorise to continue syncing.'
          : 'Authorisation incomplete. Click Authorise to complete setup.'
      }}
    </div>

    <!-- Accounts list -->
    <div class="divide-y divide-border">
      <AccountsAccountRow
        v-for="account in accounts"
        :key="account.id"
        :account="account"
        @edit="handleEditAccount"
      />

      <!-- Empty state if no accounts -->
      <div
        v-if="accounts.length === 0"
        class="px-6 py-4 text-center text-sm text-muted"
      >
        {{
          isInitialSync
            ? 'Fetching your accounts from the bank...'
            : 'No accounts found for this connection.'
        }}
      </div>
    </div>
  </div>
</template>
