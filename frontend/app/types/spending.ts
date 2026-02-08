// Spending pace types matching backend SpendingPaceResponse

export type PaceStatus = 'ahead' | 'on_track' | 'behind' | 'no_history'

export interface SpendingPaceResponse {
  month_spending_so_far: string
  expected_spending: string
  projected_month_total: string
  pace_ratio: number | null
  pace_status: PaceStatus
  amount_difference: string
  days_elapsed: number
  days_in_month: number
  currency: string
}
