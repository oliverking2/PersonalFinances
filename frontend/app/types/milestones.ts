// =============================================================================
// Milestone Types
// TypeScript interfaces matching backend Pydantic models
// =============================================================================

// Financial milestone with net worth target
export interface Milestone {
  id: string
  user_id: string
  name: string
  target_amount: string // Decimal from API as string
  target_date: string | null
  colour: string
  achieved: boolean
  achieved_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

// Response for listing milestones
export interface MilestoneListResponse {
  milestones: Milestone[]
  total: number
}

// Request for creating a milestone
export interface MilestoneCreateRequest {
  name: string
  target_amount: number
  target_date?: string | null
  colour?: string
  notes?: string | null
}

// Request for updating a milestone
export interface MilestoneUpdateRequest {
  name?: string
  target_amount?: number
  target_date?: string | null
  clear_target_date?: boolean
  colour?: string
  notes?: string | null
  clear_notes?: boolean
}
