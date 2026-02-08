<!-- ==========================================================================
Assets Page
Manage manual assets and liabilities
============================================================================ -->

<script setup lang="ts">
import type {
  ManualAsset,
  ManualAssetSummaryResponse,
  ManualAssetCreateRequest,
  ManualAssetUpdateRequest,
  ValueUpdateRequest,
} from '~/types/manual-assets'

useHead({ title: 'Assets & Liabilities | Finances' })

// API
const {
  fetchManualAssets,
  fetchManualAssetsSummary,
  createManualAsset,
  updateManualAsset,
  deleteManualAsset,
  updateManualAssetValue,
} = useManualAssetsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const assets = ref<ManualAsset[]>([])
const summary = ref<ManualAssetSummaryResponse | null>(null)
const loading = ref(true)
const error = ref('')

// Modal state
const createModalOpen = ref(false)
const editingAsset = ref<ManualAsset | null>(null)

// Value update modal
const valueUpdateModalOpen = ref(false)
const updatingAsset = ref<ManualAsset | null>(null)

// Detail modal
const detailModalOpen = ref(false)
const viewingAsset = ref<ManualAsset | null>(null)

// Filter: 'all' | 'assets' | 'liabilities'
const typeFilter = ref<'all' | 'assets' | 'liabilities'>('all')

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Filter assets by type
const filteredAssets = computed(() => {
  if (typeFilter.value === 'all') return assets.value
  if (typeFilter.value === 'assets') {
    return assets.value.filter((a) => !a.is_liability)
  }
  return assets.value.filter((a) => a.is_liability)
})

// Separate into assets and liabilities for display
const assetItems = computed(() => assets.value.filter((a) => !a.is_liability))
const liabilityItems = computed(() =>
  assets.value.filter((a) => a.is_liability),
)

// Tab counts
const tabCounts = computed(() => ({
  all: assets.value.length,
  assets: assetItems.value.length,
  liabilities: liabilityItems.value.length,
}))

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [assetsResponse, summaryResponse] = await Promise.all([
      fetchManualAssets(),
      fetchManualAssetsSummary(),
    ])
    assets.value = assetsResponse.assets
    summary.value = summaryResponse
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load assets'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function openCreateModal() {
  editingAsset.value = null
  createModalOpen.value = true
}

function handleEdit(asset: ManualAsset) {
  editingAsset.value = asset
  createModalOpen.value = true
}

function handleUpdateValue(asset: ManualAsset) {
  updatingAsset.value = asset
  valueUpdateModalOpen.value = true
}

function closeCreateModal() {
  createModalOpen.value = false
  editingAsset.value = null
}

function closeValueUpdateModal() {
  valueUpdateModalOpen.value = false
  updatingAsset.value = null
}

function handleView(asset: ManualAsset) {
  viewingAsset.value = asset
  detailModalOpen.value = true
}

function closeDetailModal() {
  detailModalOpen.value = false
  viewingAsset.value = null
}

// Handle edit from detail modal
function handleEditFromDetail(asset: ManualAsset) {
  closeDetailModal()
  handleEdit(asset)
}

// Handle update value from detail modal
function handleUpdateValueFromDetail(asset: ManualAsset) {
  closeDetailModal()
  handleUpdateValue(asset)
}

async function handleSave(data: ManualAssetCreateRequest, isEdit: boolean) {
  try {
    if (isEdit && editingAsset.value) {
      // Convert create request to update request (they overlap)
      const updateReq: ManualAssetUpdateRequest = {
        name: data.name,
        custom_type: data.custom_type,
        is_liability: data.is_liability,
        notes: data.notes,
        interest_rate: data.interest_rate,
        acquisition_date: data.acquisition_date,
        acquisition_value: data.acquisition_value,
      }
      const updated = await updateManualAsset(editingAsset.value.id, updateReq)
      const idx = assets.value.findIndex((a) => a.id === updated.id)
      if (idx >= 0) assets.value[idx] = updated
      toast.success('Asset updated')
    } else {
      const created = await createManualAsset(data)
      assets.value.unshift(created)
      toast.success('Asset created')
    }
    // Refresh summary
    const newSummary = await fetchManualAssetsSummary()
    summary.value = newSummary
    createModalOpen.value = false
    editingAsset.value = null
  } catch {
    toast.error(isEdit ? 'Failed to update asset' : 'Failed to create asset')
  }
}

async function handleValueUpdate(assetId: string, data: ValueUpdateRequest) {
  try {
    const updated = await updateManualAssetValue(assetId, data)
    const idx = assets.value.findIndex((a) => a.id === updated.id)
    if (idx >= 0) assets.value[idx] = updated
    // Refresh summary
    const newSummary = await fetchManualAssetsSummary()
    summary.value = newSummary
    toast.success('Value updated')
    valueUpdateModalOpen.value = false
    updatingAsset.value = null
  } catch {
    toast.error('Failed to update value')
  }
}

async function handleDelete(asset: ManualAsset) {
  if (!confirm(`Delete "${asset.name}"?`)) return

  try {
    await deleteManualAsset(asset.id)
    assets.value = assets.value.filter((a) => a.id !== asset.id)
    // Refresh summary
    const newSummary = await fetchManualAssetsSummary()
    summary.value = newSummary
    toast.success('Asset deleted')
  } catch {
    toast.error('Failed to delete asset')
  }
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-bold sm:text-3xl">Assets & Liabilities</h1>
        <p class="mt-1 text-muted">
          Track property, vehicles, pensions, loans, and other holdings
        </p>
      </div>
      <button
        type="button"
        class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
        @click="openCreateModal"
      >
        + Add Asset
      </button>
    </div>

    <!-- Summary cards -->
    <div v-if="summary && !loading" class="grid gap-4 sm:grid-cols-3">
      <!-- Total assets -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Total Assets</p>
        <p class="mt-1 text-2xl font-bold text-emerald-400">
          {{ formatCurrency(summary.total_assets) }}
        </p>
        <p class="mt-1 text-xs text-muted">
          {{ summary.asset_count }}
          {{ summary.asset_count === 1 ? 'asset' : 'assets' }}
        </p>
      </div>

      <!-- Total liabilities -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Total Liabilities</p>
        <p class="mt-1 text-2xl font-bold text-rose-400">
          -{{ formatCurrency(summary.total_liabilities) }}
        </p>
        <p class="mt-1 text-xs text-muted">
          {{ summary.liability_count }}
          {{ summary.liability_count === 1 ? 'liability' : 'liabilities' }}
        </p>
      </div>

      <!-- Net impact -->
      <div class="rounded-lg border border-border bg-surface p-4">
        <p class="text-sm text-muted">Net Impact</p>
        <p
          class="mt-1 text-2xl font-bold"
          :class="
            summary.net_impact >= 0 ? 'text-emerald-400' : 'text-rose-400'
          "
        >
          {{ summary.net_impact >= 0 ? '+' : ''
          }}{{ formatCurrency(summary.net_impact) }}
        </p>
        <p class="mt-1 text-xs text-muted">Contribution to net worth</p>
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="rounded-lg border border-negative/50 bg-negative/10 p-4 text-negative"
    >
      {{ error }}
    </div>

    <!-- Filters row -->
    <div class="flex flex-wrap items-center gap-4">
      <!-- Type tabs -->
      <div class="flex rounded-lg border border-border bg-surface p-1">
        <button
          v-for="tab in ['all', 'assets', 'liabilities'] as const"
          :key="tab"
          type="button"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="
            typeFilter === tab
              ? 'bg-primary/20 text-primary'
              : 'text-muted hover:text-foreground'
          "
          @click="typeFilter = tab"
        >
          {{
            tab === 'all' ? 'All' : tab === 'assets' ? 'Assets' : 'Liabilities'
          }}
          <span class="ml-1 text-xs opacity-60"> ({{ tabCounts[tab] }}) </span>
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="space-y-4">
      <div
        v-for="i in 3"
        :key="i"
        class="rounded-lg border border-border bg-surface p-4"
      >
        <div class="flex items-start justify-between">
          <div class="space-y-2">
            <div class="h-5 w-40 animate-pulse rounded bg-border" />
            <div class="h-4 w-24 animate-pulse rounded bg-border" />
          </div>
          <div class="h-8 w-24 animate-pulse rounded bg-border" />
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="filteredAssets.length === 0"
      class="rounded-lg border border-border bg-surface p-8 text-center"
    >
      <p v-if="typeFilter === 'all'" class="text-muted">
        No assets or liabilities yet. Add your property, vehicles, pensions, or
        loans to track your full net worth.
      </p>
      <p v-else-if="typeFilter === 'assets'" class="text-muted">
        No assets tracked. Add property, vehicles, or investments.
      </p>
      <p v-else class="text-muted">
        No liabilities tracked. Add loans or mortgages.
      </p>
      <button
        type="button"
        class="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
        @click="openCreateModal"
      >
        + Add {{ typeFilter === 'liabilities' ? 'Liability' : 'Asset' }}
      </button>
    </div>

    <!-- Assets grid (when filter is 'all', show grouped sections) -->
    <template v-else-if="typeFilter === 'all'">
      <!-- Assets section -->
      <div v-if="assetItems.length > 0">
        <h2 class="mb-3 text-lg font-semibold text-emerald-400">Assets</h2>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <AssetsManualAssetCard
            v-for="asset in assetItems"
            :key="asset.id"
            :asset="asset"
            @view="handleView"
            @edit="handleEdit"
            @update-value="handleUpdateValue"
            @delete="handleDelete"
          />
        </div>
      </div>

      <!-- Liabilities section -->
      <div v-if="liabilityItems.length > 0" class="mt-8">
        <h2 class="mb-3 text-lg font-semibold text-rose-400">Liabilities</h2>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <AssetsManualAssetCard
            v-for="asset in liabilityItems"
            :key="asset.id"
            :asset="asset"
            @view="handleView"
            @edit="handleEdit"
            @update-value="handleUpdateValue"
            @delete="handleDelete"
          />
        </div>
      </div>
    </template>

    <!-- Filtered grid (single type) -->
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <AssetsManualAssetCard
        v-for="asset in filteredAssets"
        :key="asset.id"
        :asset="asset"
        @view="handleView"
        @edit="handleEdit"
        @update-value="handleUpdateValue"
        @delete="handleDelete"
      />
    </div>

    <!-- Create/Edit modal -->
    <AssetsManualAssetModal
      :show="createModalOpen"
      :asset="editingAsset"
      @close="closeCreateModal"
      @save="handleSave"
    />

    <!-- Value update modal -->
    <AssetsValueUpdateModal
      :show="valueUpdateModalOpen"
      :asset="updatingAsset"
      @close="closeValueUpdateModal"
      @save="handleValueUpdate"
    />

    <!-- Detail modal with history chart -->
    <AssetsAssetDetailModal
      :show="detailModalOpen"
      :asset="viewingAsset"
      @close="closeDetailModal"
      @edit="handleEditFromDetail"
      @update-value="handleUpdateValueFromDetail"
    />
  </div>
</template>
