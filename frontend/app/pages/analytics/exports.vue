<!-- ==========================================================================
Exports History Page
View past exports and download files
============================================================================ -->

<script setup lang="ts">
import type { ExportListItem } from '~/types/analytics'

useHead({ title: 'Export History | Finances' })

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

const { listExports, getExportStatus } = useExportsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// List of export jobs
const exports = ref<ExportListItem[]>([])

// Loading and error states
const loading = ref(true)
const error = ref('')

// Track which exports are currently being downloaded (to show loading state)
const downloadingIds = ref<Set<string>>(new Set())

// Auto-polling for pending/running exports
const pollInterval = ref<ReturnType<typeof setInterval> | null>(null)
const POLL_INTERVAL_MS = 5000

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const response = await listExports()
    exports.value = response.exports

    // Start polling if there are pending exports
    startPollingIfNeeded()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load exports'
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Format file size as human-readable string (KB, MB)
function formatFileSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Format row count with commas
function formatRowCount(count: number | null): string {
  if (count === null || count === undefined) return '-'
  return count.toLocaleString()
}

// Format relative time (e.g., "2 hours ago")
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} min ago`
  if (diffHours < 24)
    return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`

  // For older dates, show the actual date
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
}

// Get status badge colour classes
function getStatusClasses(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-primary/20 text-primary'
    case 'pending':
    case 'running':
      return 'bg-amber-500/20 text-amber-400'
    case 'failed':
      return 'bg-negative/20 text-negative'
    default:
      return 'bg-gray-500/20 text-gray-400'
  }
}

// Format status label
function getStatusLabel(status: string): string {
  switch (status) {
    case 'completed':
      return 'Completed'
    case 'pending':
      return 'Pending'
    case 'running':
      return 'Running'
    case 'failed':
      return 'Failed'
    default:
      return status
  }
}

// ---------------------------------------------------------------------------
// Download Handler
// ---------------------------------------------------------------------------

async function handleDownload(jobId: string) {
  // Prevent multiple clicks
  if (downloadingIds.value.has(jobId)) return

  downloadingIds.value.add(jobId)

  try {
    // Fetch fresh status with regenerated presigned URL
    const status = await getExportStatus(jobId)

    if (status.download_url) {
      // Open download in new tab
      window.open(status.download_url, '_blank')
    } else if (status.status === 'failed') {
      toast.error(status.error_message || 'Export failed')
    } else {
      toast.error('Download URL not available')
    }
  } catch (e) {
    const message =
      e instanceof Error ? e.message : 'Failed to get download URL'
    toast.error(message)
  } finally {
    downloadingIds.value.delete(jobId)
  }
}

// ---------------------------------------------------------------------------
// Auto-Polling
// ---------------------------------------------------------------------------

// Check if any exports are still pending or running
function hasPendingExports(): boolean {
  return exports.value.some(
    (e) => e.status === 'pending' || e.status === 'running',
  )
}

// Start polling if there are pending exports
function startPollingIfNeeded() {
  if (hasPendingExports() && !pollInterval.value) {
    pollInterval.value = setInterval(async () => {
      // Silent refresh (don't show loading state)
      try {
        const response = await listExports()
        exports.value = response.exports

        // Stop polling if no more pending exports
        if (!hasPendingExports()) {
          stopPolling()
        }
      } catch {
        // Silently ignore polling errors to avoid spamming user
      }
    }, POLL_INTERVAL_MS)
  }
}

function stopPolling() {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Back link -->
    <NuxtLink
      to="/analytics/datasets"
      class="inline-flex items-center gap-1 text-sm text-muted transition-colors hover:text-foreground"
    >
      <!-- Left arrow icon -->
      <svg
        class="h-4 w-4"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 19l-7-7 7-7"
        />
      </svg>
      Back to Datasets
    </NuxtLink>

    <!-- Page header with refresh button -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">Export History</h1>
        <p class="mt-1 text-muted">View and download your past exports</p>
      </div>

      <!-- Refresh button -->
      <button
        class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-border disabled:opacity-50"
        :disabled="loading"
        @click="loadData"
      >
        <!-- Refresh icon (spins when loading) -->
        <svg
          class="h-4 w-4"
          :class="{ 'animate-spin': loading }"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        <span class="hidden sm:inline">Refresh</span>
      </button>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="rounded-lg border border-negative/50 bg-negative/10 p-4 text-negative"
    >
      {{ error }}
    </div>

    <!-- Loading skeleton - table rows -->
    <div v-if="loading" class="space-y-2">
      <div
        v-for="i in 5"
        :key="i"
        class="flex items-center gap-4 rounded-lg border border-border bg-surface p-4"
      >
        <div class="h-5 w-32 animate-pulse rounded bg-border" />
        <div class="h-5 w-16 animate-pulse rounded-full bg-border" />
        <div class="h-5 w-20 animate-pulse rounded bg-border" />
        <div class="h-5 w-16 animate-pulse rounded bg-border" />
        <div class="ml-auto h-8 w-24 animate-pulse rounded bg-border" />
      </div>
    </div>

    <!-- Exports table -->
    <div v-if="!loading && exports.length > 0" class="space-y-2">
      <!-- Table header (desktop only) -->
      <div
        class="hidden items-center gap-4 rounded-lg border border-border bg-surface/50 px-4 py-2 text-xs font-medium uppercase tracking-wide text-muted sm:flex"
      >
        <div class="w-40">Dataset</div>
        <div class="w-20">Format</div>
        <div class="w-24">Status</div>
        <div class="w-20 text-right">Rows</div>
        <div class="w-20 text-right">Size</div>
        <div class="w-28">Date</div>
        <div class="ml-auto w-28" />
      </div>

      <!-- Export rows -->
      <div
        v-for="exportItem in exports"
        :key="exportItem.job_id"
        class="flex flex-col gap-2 rounded-lg border border-border bg-surface p-4 sm:flex-row sm:items-center sm:gap-4"
      >
        <!-- Dataset name -->
        <div class="w-40 truncate font-medium">
          {{ exportItem.dataset_name || 'Unknown' }}
        </div>

        <!-- Format badge -->
        <div class="w-20">
          <span
            class="inline-block rounded-full bg-gray-500/20 px-2 py-0.5 text-xs font-medium uppercase text-gray-400"
          >
            {{ exportItem.format || '?' }}
          </span>
        </div>

        <!-- Status badge -->
        <div class="w-24">
          <span
            class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
            :class="getStatusClasses(exportItem.status)"
          >
            {{ getStatusLabel(exportItem.status) }}
          </span>
        </div>

        <!-- Row count -->
        <div class="w-20 text-right text-sm text-muted sm:text-foreground">
          <span class="text-xs text-muted sm:hidden">Rows: </span>
          {{ formatRowCount(exportItem.row_count) }}
        </div>

        <!-- File size -->
        <div class="w-20 text-right text-sm text-muted sm:text-foreground">
          <span class="text-xs text-muted sm:hidden">Size: </span>
          {{ formatFileSize(exportItem.file_size_bytes) }}
        </div>

        <!-- Date -->
        <div class="w-28 text-sm text-muted">
          {{ formatRelativeTime(exportItem.created_at) }}
        </div>

        <!-- Download button (or error message) -->
        <div class="ml-auto flex w-28 justify-end">
          <template v-if="exportItem.status === 'completed'">
            <button
              class="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
              :disabled="downloadingIds.has(exportItem.job_id)"
              @click="handleDownload(exportItem.job_id)"
            >
              <!-- Download icon or spinner -->
              <svg
                v-if="downloadingIds.has(exportItem.job_id)"
                class="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <svg
                v-else
                class="h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              Download
            </button>
          </template>

          <!-- Pending/running status indicator -->
          <template
            v-else-if="
              exportItem.status === 'pending' || exportItem.status === 'running'
            "
          >
            <span class="flex items-center gap-1.5 text-sm text-muted">
              <svg
                class="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Processing
            </span>
          </template>

          <!-- Failed status -->
          <template v-else-if="exportItem.status === 'failed'">
            <span
              class="text-sm text-negative"
              :title="exportItem.error_message || 'Export failed'"
            >
              Failed
            </span>
          </template>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-if="!loading && exports.length === 0 && !error"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p class="text-muted">No exports yet.</p>
      <NuxtLink
        to="/analytics/datasets"
        class="mt-4 inline-block text-primary underline"
      >
        Go to Datasets to create your first export
      </NuxtLink>
    </div>
  </div>
</template>
