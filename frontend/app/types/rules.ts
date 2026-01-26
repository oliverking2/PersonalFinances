/**
 * Tag rule type definitions
 */

// ----------------------------------------------------------------------------
// Shared Types
// ----------------------------------------------------------------------------

// Rule conditions (nested object for scalability)
export interface RuleConditions {
  // Include conditions (all must match)
  merchant_contains?: string | null
  merchant_exact?: string | null
  description_contains?: string | null
  min_amount?: number | null
  max_amount?: number | null

  // Exclude conditions (none must match)
  merchant_not_contains?: string | null
  description_not_contains?: string | null
}

// ----------------------------------------------------------------------------
// API Response Types
// ----------------------------------------------------------------------------

export interface TagRule {
  id: string
  name: string
  tag_id: string
  tag_name: string
  tag_colour: string | null
  priority: number
  enabled: boolean
  conditions: RuleConditions
  account_id: string | null // Kept separate as FK for referential integrity
  created_at: string
  updated_at: string
}

export interface TagRuleListResponse {
  rules: TagRule[]
  total: number
}

// ----------------------------------------------------------------------------
// Request Types
// ----------------------------------------------------------------------------

export interface TagRuleCreateRequest {
  name: string
  tag_id: string
  enabled?: boolean
  conditions?: RuleConditions | null
  account_id?: string | null
}

export interface TagRuleUpdateRequest {
  name?: string
  tag_id?: string
  enabled?: boolean
  conditions?: RuleConditions | null
  account_id?: string | null
}

export interface ReorderRulesRequest {
  rule_ids: string[]
}

export interface ApplyRulesRequest {
  account_ids?: string[] | null
  untagged_only?: boolean
}

export interface ApplyRulesResponse {
  tagged_count: number
}

export interface TestRuleRequest {
  account_ids?: string[] | null
  limit?: number
}

export interface TestConditionsRequest {
  conditions: RuleConditions
  account_id?: string | null
  limit?: number
}

export interface TestRuleResponse {
  matches: TransactionMatch[]
  total: number
}

export interface TransactionMatch {
  id: string
  booking_date: string | null
  counterparty_name: string | null
  description: string | null
  amount: number
  currency: string
}
