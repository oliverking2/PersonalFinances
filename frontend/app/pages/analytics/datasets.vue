<!-- ==========================================================================
Datasets Page
Browse available datasets and export data to CSV/Parquet
============================================================================ -->

<script setup lang="ts">
import type { Dataset } from '~/types/analytics'
import type { Account } from '~/types/accounts'
import type { Tag } from '~/types/tags'

useHead({ title: 'Datasets | Finances' })

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

const { fetchDatasets, fetchAnalyticsStatus } = useAnalyticsApi()
const { fetchAccounts } = useAccountsApi()
const { fetchTags } = useTagsApi()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// List of available datasets
const datasets = ref<Dataset[]>([])

// Accounts and tags for export filters
const accounts = ref<Account[]>([])
const tags = ref<Tag[]>([])

// Loading and error states
const loading = ref(true)
const error = ref('')

// Analytics availability
const analyticsAvailable = ref(false)

// Export modal state
const exportModalOpen = ref(false)
const selectedDataset = ref<Dataset | null>(null)

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    // Check if analytics is available
    const status = await fetchAnalyticsStatus()
    analyticsAvailable.value =
      status.duckdb_available && status.manifest_available

    if (!analyticsAvailable.value) {
      loading.value = false
      return
    }

    // Load datasets, accounts, and tags in parallel
    const [datasetsResponse, accountsResponse, tagsResponse] =
      await Promise.all([fetchDatasets(), fetchAccounts(), fetchTags()])
    datasets.value = datasetsResponse.datasets
    accounts.value = accountsResponse.accounts
    tags.value = tagsResponse.tags
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load datasets'
    analyticsAvailable.value = false
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Export Modal Handlers
// ---------------------------------------------------------------------------

function openExportModal(dataset: Dataset) {
  selectedDataset.value = dataset
  exportModalOpen.value = true
}

function closeExportModal() {
  exportModalOpen.value = false
  selectedDataset.value = null
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Back link -->
    <NuxtLink
      to="/analytics"
      class="inline-flex items-center gap-1 text-sm text-muted transition-colors hover:text-foreground"
    >
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
      Back to Analytics
    </NuxtLink>

    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold sm:text-3xl">Datasets</h1>
      <p class="mt-1 text-muted">
        Export your financial data for external analysis
      </p>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="rounded-lg border border-negative/50 bg-negative/10 p-4 text-negative"
    >
      {{ error }}
    </div>

    <!-- Analytics unavailable state -->
    <div
      v-if="!loading && !analyticsAvailable"
      class="rounded-lg border border-warning/50 bg-warning/10 p-8 text-center"
    >
      <p class="text-warning">
        Analytics data is being prepared. Please refresh the analytics data
        first.
      </p>
      <NuxtLink
        to="/analytics"
        class="mt-4 inline-block text-primary underline"
      >
        Go to Analytics
      </NuxtLink>
    </div>

    <!-- Loading skeleton - grid of card placeholders -->
    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="i in 6"
        :key="i"
        class="rounded-lg border border-border bg-surface p-5"
      >
        <div class="h-6 w-3/4 animate-pulse rounded bg-border" />
        <div class="mt-2 h-4 w-full animate-pulse rounded bg-border" />
        <div class="mt-1 h-4 w-2/3 animate-pulse rounded bg-border" />
        <div class="mt-4 flex gap-2">
          <div class="h-6 w-16 animate-pulse rounded-full bg-border" />
          <div class="h-6 w-12 animate-pulse rounded-full bg-border" />
        </div>
        <div class="mt-4 h-9 w-full animate-pulse rounded bg-border" />
      </div>
    </div>

    <!-- Dataset grid -->
    <div
      v-if="!loading && analyticsAvailable && datasets.length > 0"
      class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <DatasetsDatasetCard
        v-for="dataset in datasets"
        :key="dataset.id"
        :dataset="dataset"
        @export="openExportModal"
      />
    </div>

    <!-- Empty state -->
    <div
      v-if="!loading && analyticsAvailable && datasets.length === 0"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p class="text-muted">No datasets available yet.</p>
    </div>

    <!-- Export Modal -->
    <DatasetsExportModal
      :is-open="exportModalOpen"
      :dataset="selectedDataset"
      :accounts="accounts"
      :tags="tags"
      @close="closeExportModal"
    />
  </div>
</template>
