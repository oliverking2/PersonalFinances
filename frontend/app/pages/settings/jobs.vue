<!-- ==========================================================================
Jobs Settings Page
Consolidated job management: trigger syncs, view running jobs, browse history
============================================================================ -->

<script setup lang="ts">
import type { Job } from '~/types/jobs'
import type { Connection } from '~/types/accounts'

useHead({ title: 'Jobs | Finances' })

// ---------------------------------------------------------------------------
// Composables
// ---------------------------------------------------------------------------

const toast = useToastStore()
const { fetchJob, fetchJobs, triggerConnectionSync, triggerAnalyticsRefresh } =
  useJobsApi()
const { fetchConnections } = useAccountsApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Job lists
const allJobs = ref<Job[]>([])
const connections = ref<Connection[]>([])

// Loading states
const loading = ref(true)
const syncingBanks = ref(false)
const refreshingAnalytics = ref(false)

// Filters
const statusFilter = ref('all')
const typeFilter = ref('all')

// Filter options for AppSelect
const typeFilterOptions = [
  { value: 'all', label: 'All Types' },
  { value: 'connection', label: 'Bank Syncs' },
  { value: 'analytics', label: 'Analytics' },
]

const statusFilterOptions = [
  { value: 'all', label: 'All Statuses' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'running', label: 'Running' },
  { value: 'pending', label: 'Pending' },
]

// Pagination
const pageSize = 20
const hasMore = ref(false)

// Running job polling
const runningJobIds = ref<Set<string>>(new Set())
let pollIntervalId: ReturnType<typeof setInterval> | null = null

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Jobs that are currently running (for the Running Jobs section)
const runningJobs = computed(() => {
  return allJobs.value.filter(
    (job) => job.status === 'pending' || job.status === 'running',
  )
})

// Jobs for history (completed/failed, filtered)
const filteredJobs = computed(() => {
  return allJobs.value.filter((job) => {
    // Status filter
    if (statusFilter.value !== 'all' && job.status !== statusFilter.value) {
      return false
    }
    // Type filter
    if (typeFilter.value !== 'all') {
      if (typeFilter.value === 'analytics' && job.entity_type !== 'analytics') {
        return false
      }
      if (
        typeFilter.value === 'connection' &&
        job.entity_type !== 'connection'
      ) {
        return false
      }
    }
    return true
  })
})

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  try {
    // Fetch jobs and connections in parallel
    const [jobsResponse, connectionsResponse] = await Promise.all([
      fetchJobs({ limit: pageSize }),
      fetchConnections(),
    ])

    allJobs.value = jobsResponse.jobs
    hasMore.value = jobsResponse.total > pageSize
    connections.value = connectionsResponse.connections

    // Start polling for any running jobs
    updateRunningJobPolling()
  } catch (e) {
    console.error('Failed to load jobs:', e)
    toast.error('Failed to load jobs')
  } finally {
    loading.value = false
  }
}

// Load more jobs (pagination)
async function loadMore() {
  if (!hasMore.value) return

  try {
    const response = await fetchJobs({
      limit: pageSize,
      offset: allJobs.value.length,
    })

    allJobs.value = [...allJobs.value, ...response.jobs]
    hasMore.value = allJobs.value.length < response.total
  } catch (e) {
    console.error('Failed to load more jobs:', e)
    toast.error('Failed to load more jobs')
  }
}

// ---------------------------------------------------------------------------
// Running Job Polling
// ---------------------------------------------------------------------------

function updateRunningJobPolling() {
  // Track running job IDs
  const newRunningIds = new Set(
    allJobs.value
      .filter((j) => j.status === 'pending' || j.status === 'running')
      .map((j) => j.id),
  )

  runningJobIds.value = newRunningIds

  // Start or stop polling based on whether we have running jobs
  if (newRunningIds.size > 0 && !pollIntervalId) {
    pollIntervalId = setInterval(pollRunningJobs, 3000)
  } else if (newRunningIds.size === 0 && pollIntervalId) {
    clearInterval(pollIntervalId)
    pollIntervalId = null
  }
}

async function pollRunningJobs() {
  if (runningJobIds.value.size === 0) return

  try {
    // Fetch updated status for all running jobs
    const updates = await Promise.all(
      Array.from(runningJobIds.value).map((id) => fetchJob(id)),
    )

    // Update jobs in our list
    for (const updatedJob of updates) {
      const index = allJobs.value.findIndex((j) => j.id === updatedJob.id)
      if (index !== -1) {
        allJobs.value[index] = updatedJob
      }

      // Show toast when job completes
      if (updatedJob.status === 'completed') {
        const label = getJobLabel(updatedJob)
        toast.success(`${label} completed`)
      } else if (updatedJob.status === 'failed') {
        const label = getJobLabel(updatedJob)
        toast.error(
          `${label} failed: ${updatedJob.error_message || 'Unknown error'}`,
        )
      }
    }

    // Update polling state
    updateRunningJobPolling()
  } catch (e) {
    console.error('Failed to poll running jobs:', e)
  }
}

// ---------------------------------------------------------------------------
// Sync Actions
// ---------------------------------------------------------------------------

async function handleSyncAllBanks() {
  if (syncingBanks.value || connections.value.length === 0) return

  syncingBanks.value = true
  toast.info(`Syncing ${connections.value.length} bank connection(s)...`)

  try {
    // Trigger sync for all connections
    const jobs = await Promise.all(
      connections.value.map((conn) => triggerConnectionSync(conn.id)),
    )

    // Add jobs to our list and start polling
    for (const job of jobs) {
      // Check if job already exists (shouldn't, but be safe)
      const existingIndex = allJobs.value.findIndex((j) => j.id === job.id)
      if (existingIndex === -1) {
        allJobs.value.unshift(job)
      }
    }

    updateRunningJobPolling()
  } catch (e) {
    console.error('Failed to sync banks:', e)
    toast.error('Failed to start bank sync')
  } finally {
    syncingBanks.value = false
  }
}

async function handleRefreshAnalytics() {
  if (refreshingAnalytics.value) return

  refreshingAnalytics.value = true

  try {
    // Check if there's already a running analytics job
    const existingJobs = await fetchJobs({
      entity_type: 'analytics',
      job_type: 'sync',
      limit: 5,
    })
    const runningJob = existingJobs.jobs.find(
      (job) => job.status === 'pending' || job.status === 'running',
    )

    if (runningJob) {
      toast.info('Analytics refresh already in progress')
      // Make sure it's in our list
      const existingIndex = allJobs.value.findIndex(
        (j) => j.id === runningJob.id,
      )
      if (existingIndex === -1) {
        allJobs.value.unshift(runningJob)
      }
      updateRunningJobPolling()
      return
    }

    // Start new refresh
    toast.info('Starting analytics refresh...')
    const response = await triggerAnalyticsRefresh('/settings/jobs')

    if (response.status === 'failed') {
      toast.error(response.message || 'Failed to start analytics refresh')
      return
    }

    // Fetch the job to add to our list
    const job = await fetchJob(response.job_id)
    allJobs.value.unshift(job)
    updateRunningJobPolling()
  } catch (e) {
    console.error('Failed to refresh analytics:', e)
    toast.error('Failed to start analytics refresh')
  } finally {
    refreshingAnalytics.value = false
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Get human-readable label for a job
function getJobLabel(job: Job): string {
  if (job.entity_type === 'analytics') {
    return 'Analytics Refresh'
  }
  if (job.entity_type === 'connection') {
    // Find connection name
    const conn = connections.value.find((c) => c.id === job.entity_id)
    return conn ? `${conn.friendly_name} Sync` : 'Bank Sync'
  }
  return job.job_type === 'sync' ? 'Sync' : 'Job'
}

// Get icon for job type
function getJobIcon(job: Job): 'bank' | 'chart' | 'gear' {
  if (job.entity_type === 'analytics') return 'chart'
  if (job.entity_type === 'connection') return 'bank'
  return 'gear'
}

// Format relative time
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffSec < 60) return 'just now'
  if (diffMin < 60) return `${diffMin} min ago`
  if (diffHour < 24) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`
  if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`

  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Calculate job duration
function getJobDuration(job: Job): string | null {
  if (!job.started_at) return null

  const start = new Date(job.started_at)
  const end = job.completed_at ? new Date(job.completed_at) : new Date()
  const diffSec = Math.floor((end.getTime() - start.getTime()) / 1000)

  if (diffSec < 60) return `${diffSec}s`
  const min = Math.floor(diffSec / 60)
  const sec = diffSec % 60
  return `${min}m ${sec}s`
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  // Cleanup polling
  if (pollIntervalId) {
    clearInterval(pollIntervalId)
    pollIntervalId = null
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold sm:text-3xl">Jobs</h1>
      <p class="mt-1 text-muted">View and manage background jobs</p>
    </div>

    <!-- Quick Actions Card -->
    <div class="rounded-lg border border-border bg-surface p-4">
      <h2 class="mb-3 text-sm font-medium text-muted">Quick Actions</h2>
      <div class="flex flex-wrap gap-3">
        <!-- Sync All Banks button -->
        <button
          type="button"
          class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="syncingBanks || connections.length === 0"
          @click="handleSyncAllBanks"
        >
          <!-- Bank icon or spinner -->
          <svg
            v-if="syncingBanks"
            class="h-4 w-4 animate-spin"
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
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z"
            />
          </svg>
          {{ syncingBanks ? 'Syncing...' : 'Sync All Banks' }}
        </button>

        <!-- Refresh Analytics button -->
        <button
          type="button"
          class="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 font-medium text-foreground transition-colors hover:bg-border disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="refreshingAnalytics"
          @click="handleRefreshAnalytics"
        >
          <!-- Chart icon or spinner -->
          <svg
            v-if="refreshingAnalytics"
            class="h-4 w-4 animate-spin"
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
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          {{ refreshingAnalytics ? 'Starting...' : 'Refresh Analytics' }}
        </button>
      </div>

      <!-- No connections message -->
      <p
        v-if="!loading && connections.length === 0"
        class="mt-3 text-sm text-muted"
      >
        <NuxtLink to="/settings/accounts" class="text-primary hover:underline">
          Connect a bank account
        </NuxtLink>
        to sync transactions.
      </p>
    </div>

    <!-- Running Jobs Section (shown when there are running jobs) -->
    <div
      v-if="runningJobs.length > 0"
      class="rounded-lg border border-blue-500/30 bg-blue-500/5 p-4"
    >
      <h2
        class="mb-3 flex items-center gap-2 text-sm font-medium text-blue-400"
      >
        <!-- Animated spinner -->
        <svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
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
        Running Jobs
      </h2>

      <div class="space-y-2">
        <div
          v-for="job in runningJobs"
          :key="job.id"
          class="flex items-center justify-between rounded bg-surface px-3 py-2"
        >
          <div class="flex items-center gap-3">
            <!-- Job type icon -->
            <svg
              v-if="getJobIcon(job) === 'bank'"
              class="h-5 w-5 text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z"
              />
            </svg>
            <svg
              v-else-if="getJobIcon(job) === 'chart'"
              class="h-5 w-5 text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <span class="font-medium">{{ getJobLabel(job) }}</span>
          </div>

          <div class="flex items-center gap-3">
            <!-- Duration -->
            <span v-if="getJobDuration(job)" class="text-sm text-muted">
              {{ getJobDuration(job) }}
            </span>
            <JobsJobStatusBadge :status="job.status" />
          </div>
        </div>
      </div>
    </div>

    <!-- Job History Section -->
    <div class="rounded-lg border border-border bg-surface">
      <!-- Section header with filters -->
      <div class="border-b border-border px-6 py-4">
        <div
          class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <h2 class="text-lg font-semibold">Job History</h2>

          <!-- Filters -->
          <div class="flex gap-2">
            <!-- Type filter -->
            <div class="w-36">
              <AppSelect v-model="typeFilter" :options="typeFilterOptions" />
            </div>

            <!-- Status filter -->
            <div class="w-36">
              <AppSelect
                v-model="statusFilter"
                :options="statusFilterOptions"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="p-6">
        <div class="space-y-3">
          <div
            v-for="i in 5"
            :key="i"
            class="flex items-center justify-between"
          >
            <div class="flex items-center gap-3">
              <div class="h-5 w-5 animate-pulse rounded bg-border" />
              <div class="h-5 w-32 animate-pulse rounded bg-border" />
            </div>
            <div class="h-5 w-20 animate-pulse rounded bg-border" />
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="filteredJobs.length === 0"
        class="p-6 text-center text-muted"
      >
        <p v-if="allJobs.length === 0">
          No jobs yet. Trigger a sync to get started.
        </p>
        <p v-else>No jobs match the selected filters.</p>
      </div>

      <!-- Job list -->
      <div v-else class="divide-y divide-border/50">
        <div
          v-for="job in filteredJobs"
          :key="job.id"
          class="flex items-center justify-between px-6 py-3 transition-colors hover:bg-border/10"
        >
          <div class="flex items-center gap-3">
            <!-- Job type icon -->
            <svg
              v-if="getJobIcon(job) === 'bank'"
              class="h-5 w-5 text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z"
              />
            </svg>
            <svg
              v-else-if="getJobIcon(job) === 'chart'"
              class="h-5 w-5 text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <svg
              v-else
              class="h-5 w-5 text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>

            <div>
              <span class="font-medium">{{ getJobLabel(job) }}</span>
              <!-- Error message for failed jobs -->
              <p
                v-if="job.status === 'failed' && job.error_message"
                class="text-sm text-red-400"
              >
                {{ job.error_message }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-4">
            <!-- Relative time -->
            <span class="text-sm text-muted">
              {{ formatRelativeTime(job.created_at) }}
            </span>
            <JobsJobStatusBadge :status="job.status" />
          </div>
        </div>

        <!-- Load more button -->
        <div v-if="hasMore" class="px-6 py-3 text-center">
          <button
            type="button"
            class="text-sm text-primary hover:underline"
            @click="loadMore"
          >
            Load More
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
