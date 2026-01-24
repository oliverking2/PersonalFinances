<!-- ==========================================================================
ConnectionCard
Card displaying a bank connection with its nested accounts
Includes actions: edit name, reauthorise (if expired), delete
============================================================================ -->

<script setup lang="ts">
import type { Connection, Account } from '~/types/accounts'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------
const props = defineProps<{
  connection: Connection
  accounts: Account[]
}>()

const emit = defineEmits<{
  editConnection: [connection: Connection]
  editAccount: [account: Account]
  reauthorise: [connection: Connection]
  delete: [connection: Connection]
}>()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Controls the dropdown menu visibility
const showMenu = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Check if connection is expired (needs reauthorisation)
const isExpired = computed(() => props.connection.status === 'expired')

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

      <!-- Right: status badge and actions -->
      <div class="flex items-center gap-3">
        <AccountsStatusIndicator :status="connection.status" />

        <!-- Reauthorise button (shown when expired) -->
        <button
          v-if="isExpired"
          type="button"
          class="rounded-lg bg-warning/10 px-3 py-1.5 text-sm font-medium text-warning transition-colors hover:bg-warning/20"
          @click="handleReauthorise"
        >
          Reauthorise
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

    <!-- Expired warning banner -->
    <div
      v-if="isExpired"
      class="flex items-center gap-2 bg-negative/10 px-6 py-2 text-sm text-negative"
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
      Connection expired. Reauthorise to continue syncing.
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
        No accounts found for this connection.
      </div>
    </div>
  </div>
</template>
