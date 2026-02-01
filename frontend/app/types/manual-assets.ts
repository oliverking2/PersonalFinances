// =============================================================================
// Manual Assets & Liabilities Types
// TypeScript interfaces for manually tracked assets/liabilities and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Enums (matching backend)
// -----------------------------------------------------------------------------

export type ManualAssetType =
  | 'student_loan'
  | 'mortgage'
  | 'vehicle'
  | 'property'
  | 'savings_account'
  | 'pension'
  | 'investments'
  | 'crypto'
  | 'other_asset'
  | 'other_liability'

// -----------------------------------------------------------------------------
// Manual Asset
// Represents a manually tracked asset or liability
// -----------------------------------------------------------------------------

export interface ManualAsset {
  id: string
  asset_type: ManualAssetType
  custom_type: string | null
  display_type: string // Formatted type name (custom_type if set, else formatted asset_type)
  is_liability: boolean // Whether this counts against net worth
  name: string
  notes: string | null
  current_value: number
  currency: string
  interest_rate: number | null // For loans/mortgages
  acquisition_date: string | null // ISO datetime
  acquisition_value: number | null // Original purchase price
  is_active: boolean
  value_updated_at: string // ISO datetime
  created_at: string
  updated_at: string
}

// Value history snapshot
export interface ValueSnapshot {
  id: number
  value: number
  currency: string
  notes: string | null
  captured_at: string // ISO datetime
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface ManualAssetListResponse {
  assets: ManualAsset[]
  total: number
}

export interface ManualAssetSummaryResponse {
  total_assets: number
  total_liabilities: number
  net_impact: number
  asset_count: number
  liability_count: number
}

export interface ValueHistoryResponse {
  asset_id: string
  snapshots: ValueSnapshot[]
  total: number
}

// -----------------------------------------------------------------------------
// API Request Types
// -----------------------------------------------------------------------------

export interface ManualAssetCreateRequest {
  name: string
  asset_type: ManualAssetType
  current_value: number
  custom_type?: string
  is_liability?: boolean // Override default based on type
  currency?: string
  notes?: string
  interest_rate?: number
  acquisition_date?: string // YYYY-MM-DD
  acquisition_value?: number
}

export interface ManualAssetUpdateRequest {
  name?: string
  custom_type?: string
  is_liability?: boolean
  notes?: string
  interest_rate?: number
  acquisition_date?: string // YYYY-MM-DD
  acquisition_value?: number
  clear_custom_type?: boolean
  clear_notes?: boolean
  clear_interest_rate?: boolean
  clear_acquisition_date?: boolean
  clear_acquisition_value?: boolean
}

export interface ValueUpdateRequest {
  new_value: number
  notes?: string
}

// -----------------------------------------------------------------------------
// Helper Functions
// -----------------------------------------------------------------------------

// Get user-friendly label for asset type
export function getAssetTypeLabel(type: ManualAssetType): string {
  const labels: Record<ManualAssetType, string> = {
    student_loan: 'Student Loan',
    mortgage: 'Mortgage',
    vehicle: 'Vehicle',
    property: 'Property',
    savings_account: 'Savings Account',
    pension: 'Pension',
    investments: 'Investments',
    crypto: 'Cryptocurrency',
    other_asset: 'Other Asset',
    other_liability: 'Other Liability',
  }
  return labels[type] || type
}

// Get icon name for asset type (using heroicons names)
export function getAssetTypeIcon(type: ManualAssetType): string {
  const icons: Record<ManualAssetType, string> = {
    student_loan: 'academic-cap',
    mortgage: 'home',
    vehicle: 'truck',
    property: 'building-office-2',
    savings_account: 'banknotes',
    pension: 'chart-bar',
    investments: 'chart-pie',
    crypto: 'currency-dollar',
    other_asset: 'cube',
    other_liability: 'credit-card',
  }
  return icons[type] || 'cube'
}

// Get default is_liability status for a type
export function getDefaultIsLiability(type: ManualAssetType): boolean {
  const liabilityTypes: ManualAssetType[] = [
    'student_loan',
    'mortgage',
    'other_liability',
  ]
  return liabilityTypes.includes(type)
}

// Get colour for asset/liability badge
export function getAssetColour(isLiability: boolean): string {
  return isLiability ? 'text-rose-400' : 'text-emerald-400'
}

// Get background colour for asset/liability badge
export function getAssetBgColour(isLiability: boolean): string {
  return isLiability ? 'bg-rose-500/20' : 'bg-emerald-500/20'
}

// Format value as signed amount for display
export function formatValueImpact(value: number, isLiability: boolean): string {
  const sign = isLiability ? '-' : '+'
  return `${sign}${value.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// Get all asset types grouped by category
export function getAssetTypesByCategory(): {
  assets: ManualAssetType[]
  liabilities: ManualAssetType[]
} {
  return {
    assets: [
      'property',
      'vehicle',
      'savings_account',
      'pension',
      'investments',
      'crypto',
      'other_asset',
    ],
    liabilities: ['student_loan', 'mortgage', 'other_liability'],
  }
}

// Format interest rate for display
export function formatInterestRate(rate: number | null): string {
  if (rate === null) return ''
  return `${rate.toFixed(2)}% APR`
}
