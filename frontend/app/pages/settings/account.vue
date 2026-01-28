<!-- ==========================================================================
Settings / Account Page
User account settings including Telegram integration
============================================================================ -->

<script setup lang="ts">
import type {
  TelegramStatusResponse,
  TelegramLinkCodeResponse,
} from '~/types/user'
import { useToastStore } from '~/stores/toast'

useHead({ title: 'Account Settings | Finances' })

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------
const {
  getTelegramStatus,
  generateTelegramLinkCode,
  unlinkTelegram,
  ApiError,
} = useUserApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Page state
const loading = ref(true)
const error = ref('')

// Telegram status
const telegramStatus = ref<TelegramStatusResponse | null>(null)

// Link code state (when generating a code)
const linkCode = ref<TelegramLinkCodeResponse | null>(null)
const generatingCode = ref(false)

// Countdown timer for code expiry
const expiryCountdown = ref(0)
let countdownInterval: ReturnType<typeof setInterval> | null = null

// Auto-polling for status check (polls while link code is displayed)
let pollInterval: ReturnType<typeof setInterval> | null = null
const POLL_INTERVAL_MS = 3000 // Check every 3 seconds

// Unlink state
const unlinking = ref(false)
const showUnlinkConfirm = ref(false)

// Check status state
const checkingStatus = ref(false)

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    telegramStatus.value = await getTelegramStatus()
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = 'Failed to load account settings'
    }
  } finally {
    loading.value = false
  }
}

// Load on mount
onMounted(loadData)

// Clean up intervals on unmount
onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})

// ---------------------------------------------------------------------------
// Telegram Linking
// ---------------------------------------------------------------------------

/**
 * Generate a new link code and start the countdown timer
 */
async function handleGenerateCode() {
  generatingCode.value = true

  try {
    linkCode.value = await generateTelegramLinkCode()

    // Start countdown and polling
    expiryCountdown.value = linkCode.value.expires_in_seconds
    startCountdown()
    startPolling()

    toast.success('Link code generated - send /link to the bot')
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to generate link code')
    }
  } finally {
    generatingCode.value = false
  }
}

/**
 * Start the expiry countdown timer
 */
function startCountdown() {
  // Clear any existing countdown
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }

  countdownInterval = setInterval(() => {
    expiryCountdown.value--
    if (expiryCountdown.value <= 0) {
      // Code expired - stop everything
      stopAllTimers()
      linkCode.value = null
      toast.info('Link code expired. Generate a new one if needed.')
    }
  }, 1000)
}

/**
 * Start polling for status changes (auto-detects when user links via bot)
 */
function startPolling() {
  // Clear any existing poll
  if (pollInterval) {
    clearInterval(pollInterval)
  }

  pollInterval = setInterval(async () => {
    try {
      const status = await getTelegramStatus()
      if (status.is_linked) {
        // Success! Stop polling and update UI
        stopAllTimers()
        telegramStatus.value = status
        linkCode.value = null
        toast.success('Telegram linked successfully!')
      }
    } catch {
      // Silently ignore polling errors - will retry on next interval
    }
  }, POLL_INTERVAL_MS)
}

/**
 * Stop all timers (countdown and polling)
 */
function stopAllTimers() {
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

/**
 * Format seconds as MM:SS
 */
function formatCountdown(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * Copy the link code to clipboard
 */
async function copyCode() {
  if (!linkCode.value) return

  try {
    await navigator.clipboard.writeText(linkCode.value.code)
    toast.success('Code copied to clipboard')
  } catch {
    toast.error('Failed to copy code')
  }
}

/**
 * Cancel the link code (hide it without unlinking)
 */
function cancelLinkCode() {
  stopAllTimers()
  linkCode.value = null
}

// ---------------------------------------------------------------------------
// Telegram Unlinking
// ---------------------------------------------------------------------------

function openUnlinkConfirm() {
  showUnlinkConfirm.value = true
}

function closeUnlinkConfirm() {
  showUnlinkConfirm.value = false
}

async function handleUnlink() {
  unlinking.value = true

  try {
    await unlinkTelegram()
    telegramStatus.value = { is_linked: false, chat_id: null }
    toast.success('Telegram unlinked successfully')
    closeUnlinkConfirm()
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to unlink Telegram')
    }
  } finally {
    unlinking.value = false
  }
}

/**
 * Refresh the status after the user has linked via the bot
 */
async function refreshStatus() {
  checkingStatus.value = true

  try {
    telegramStatus.value = await getTelegramStatus()
    if (telegramStatus.value.is_linked) {
      // Success - stop timers and clear code
      stopAllTimers()
      linkCode.value = null
      toast.success('Telegram linked successfully!')
    } else {
      // Not linked yet - give user feedback
      toast.info(
        'Not linked yet. Make sure you sent /link with the code to the bot.',
      )
    }
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message)
    } else {
      toast.error('Failed to check status. Please try again.')
    }
  } finally {
    checkingStatus.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <!-- Settings navigation -->
    <nav class="settings-nav">
      <NuxtLink to="/settings/account" class="settings-nav-link active">
        Account
      </NuxtLink>
      <NuxtLink to="/settings/tags" class="settings-nav-link"> Tags </NuxtLink>
      <NuxtLink to="/settings/rules" class="settings-nav-link">
        Auto-Tagging Rules
      </NuxtLink>
    </nav>

    <!-- Header -->
    <header class="page-header">
      <div>
        <h1 class="page-title">Account Settings</h1>
        <p class="page-subtitle">Manage your account and integrations</p>
      </div>
    </header>

    <!-- Loading state -->
    <div v-if="loading" class="loading">Loading settings...</div>

    <!-- Error state -->
    <div v-else-if="error" class="error">{{ error }}</div>

    <!-- Content -->
    <div v-else class="settings-content">
      <!-- Telegram Integration Section -->
      <section class="settings-section">
        <div class="section-header">
          <div class="section-icon">
            <!-- Telegram icon (simplified) -->
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              class="h-6 w-6"
            >
              <path
                d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"
              />
            </svg>
          </div>
          <div class="section-title-area">
            <h2 class="section-title">Telegram Integration</h2>
            <p class="section-description">
              Link your Telegram account to receive notifications about budget
              alerts, large transactions, and more.
            </p>
          </div>
        </div>

        <div class="section-content">
          <!-- Status display -->
          <div class="status-row">
            <span class="status-label">Status:</span>
            <span
              v-if="telegramStatus?.is_linked"
              class="status-badge status-badge--linked"
            >
              Linked
            </span>
            <span v-else class="status-badge status-badge--not-linked">
              Not Linked
            </span>
          </div>

          <!-- Show chat ID if linked -->
          <div v-if="telegramStatus?.is_linked" class="linked-info">
            <div class="info-row">
              <span class="info-label">Chat ID:</span>
              <span class="info-value">{{ telegramStatus.chat_id }}</span>
            </div>
            <AppButton
              type="button"
              variant="danger"
              @click="openUnlinkConfirm"
            >
              Unlink Telegram
            </AppButton>
          </div>

          <!-- Link flow (when not linked) -->
          <div v-else class="link-flow">
            <!-- Not generating yet -->
            <div v-if="!linkCode" class="link-start">
              <p class="link-instructions">
                To link your Telegram account, click the button below to
                generate a one-time code. Then send
                <code>/link &lt;code&gt;</code> to the bot.
              </p>
              <AppButton
                type="button"
                :disabled="generatingCode"
                @click="handleGenerateCode"
              >
                {{ generatingCode ? 'Generating...' : 'Generate Link Code' }}
              </AppButton>
            </div>

            <!-- Code generated - show it -->
            <div v-else class="link-code-display">
              <div class="code-box">
                <span class="code-label">Your link code:</span>
                <div class="code-value-row">
                  <code class="code-value">{{ linkCode.code }}</code>
                  <button
                    type="button"
                    class="copy-btn"
                    title="Copy to clipboard"
                    @click="copyCode"
                  >
                    <!-- Copy icon -->
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      class="h-5 w-5"
                    >
                      <path
                        d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z"
                      />
                      <path
                        d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.44A1.5 1.5 0 008.378 6H4.5z"
                      />
                    </svg>
                  </button>
                </div>
                <span class="code-expiry">
                  Expires in {{ formatCountdown(expiryCountdown) }}
                </span>
              </div>

              <div class="code-instructions">
                <p><strong>Step 1:</strong> Open Telegram and find the bot</p>
                <p>
                  <strong>Step 2:</strong> Send the command:
                  <code>/link {{ linkCode.code }}</code>
                </p>
                <p class="auto-detect-note">
                  This page will automatically update when you link.
                </p>
              </div>

              <div class="code-actions">
                <AppButton
                  type="button"
                  :disabled="checkingStatus"
                  @click="refreshStatus"
                >
                  {{ checkingStatus ? 'Checking...' : 'Check Status' }}
                </AppButton>
                <button
                  type="button"
                  class="cancel-link"
                  @click="cancelLinkCode"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- Unlink Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="showUnlinkConfirm"
        class="modal-overlay"
        @click.self="closeUnlinkConfirm"
      >
        <div class="modal">
          <h3 class="modal-title">Unlink Telegram</h3>

          <p class="confirm-text">
            Are you sure you want to unlink your Telegram account? You will stop
            receiving notifications.
          </p>

          <div class="modal-actions">
            <button
              type="button"
              class="btn-secondary"
              @click="closeUnlinkConfirm"
            >
              Cancel
            </button>
            <button
              type="button"
              class="btn-danger"
              :disabled="unlinking"
              @click="handleUnlink"
            >
              {{ unlinking ? 'Unlinking...' : 'Unlink' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* Settings navigation - matches tags.vue */
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
  @apply mx-auto max-w-4xl px-4 py-8;
}

.page-header {
  @apply mb-8;
}

.page-title {
  @apply text-2xl font-bold text-foreground;
}

.page-subtitle {
  @apply mt-1 text-muted;
}

/* Settings content */
.settings-content {
  @apply space-y-6;
}

/* Section styling */
.settings-section {
  @apply rounded-lg bg-surface p-6;
}

.section-header {
  @apply mb-6 flex items-start gap-4;
}

.section-icon {
  @apply flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary;
}

.section-title-area {
  @apply flex-1;
}

.section-title {
  @apply text-lg font-semibold text-foreground;
}

.section-description {
  @apply mt-1 text-sm text-muted;
}

.section-content {
  @apply space-y-4;
}

/* Status display */
.status-row {
  @apply flex items-center gap-3;
}

.status-label {
  @apply text-sm text-muted;
}

.status-badge {
  @apply rounded-full px-3 py-1 text-sm font-medium;

  &.status-badge--linked {
    @apply bg-primary/20 text-primary;
  }

  &.status-badge--not-linked {
    @apply bg-gray-700 text-gray-400;
  }
}

/* Linked info */
.linked-info {
  @apply mt-4 flex items-center justify-between rounded-lg bg-gray-800/50 p-4;
}

.info-row {
  @apply flex items-center gap-2;
}

.info-label {
  @apply text-sm text-muted;
}

.info-value {
  @apply font-mono text-foreground;
}

/* Link flow */
.link-flow {
  @apply mt-4;
}

.link-start {
  @apply space-y-4;
}

.link-instructions {
  @apply text-sm text-muted;

  code {
    @apply rounded bg-gray-800 px-1.5 py-0.5 font-mono text-sage;
  }
}

/* Link code display */
.link-code-display {
  @apply space-y-4;
}

.code-box {
  @apply rounded-lg bg-gray-800 p-4 text-center;
}

.code-label {
  @apply block text-sm text-muted;
}

.code-value-row {
  @apply mt-2 flex items-center justify-center gap-2;
}

.code-value {
  @apply text-3xl font-bold tracking-widest text-sage;
}

.copy-btn {
  @apply rounded p-1 text-muted transition-colors hover:bg-gray-700 hover:text-foreground;
  @apply cursor-pointer border-none bg-transparent;
}

.code-expiry {
  @apply mt-2 block text-sm text-amber-400;
}

.code-instructions {
  @apply space-y-2 rounded-lg bg-gray-800/50 p-4 text-sm text-muted;

  code {
    @apply rounded bg-gray-800 px-1.5 py-0.5 font-mono text-sage;
  }

  strong {
    @apply text-foreground;
  }

  .auto-detect-note {
    @apply mt-3 italic text-primary;
  }
}

.code-actions {
  @apply flex items-center gap-3;
}

.cancel-link {
  @apply text-sm text-muted underline transition-colors hover:text-foreground;
  @apply cursor-pointer border-none bg-transparent;
}

/* States */
.loading,
.empty-state {
  @apply py-8 text-center text-muted;
}

.error {
  @apply py-8 text-center text-red-400;
}

/* Modal - matches tags.vue */
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
</style>
