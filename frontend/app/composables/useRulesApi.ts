// =============================================================================
// Tag Rules API Composable
// All API functions for managing auto-tagging rules
// =============================================================================

import type {
  TagRule,
  TagRuleListResponse,
  TagRuleCreateRequest,
  TagRuleUpdateRequest,
  ReorderRulesRequest,
  ApplyRulesRequest,
  ApplyRulesResponse,
  TestRuleRequest,
  TestConditionsRequest,
  TestRuleResponse,
} from '~/types/rules'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useRulesApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Rules CRUD
  // ---------------------------------------------------------------------------

  // Fetch all rules for the current user
  // Optionally filter by target tag
  async function fetchRules(tagId?: string): Promise<TagRuleListResponse> {
    const params = tagId ? `?tag_id=${tagId}` : ''
    return authFetch<TagRuleListResponse>(`/api/tag-rules${params}`)
  }

  // Create a new auto-tagging rule
  async function createRule(req: TagRuleCreateRequest): Promise<TagRule> {
    return authFetch<TagRule>('/api/tag-rules', {
      method: 'POST',
      body: req,
    })
  }

  // Get a single rule by ID
  async function fetchRule(ruleId: string): Promise<TagRule> {
    return authFetch<TagRule>(`/api/tag-rules/${ruleId}`)
  }

  // Update a rule's conditions or settings
  async function updateRule(
    ruleId: string,
    req: TagRuleUpdateRequest,
  ): Promise<TagRule> {
    return authFetch<TagRule>(`/api/tag-rules/${ruleId}`, {
      method: 'PUT',
      body: req,
    })
  }

  // Delete a rule
  async function deleteRule(ruleId: string): Promise<void> {
    await authFetch(`/api/tag-rules/${ruleId}`, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Rule Testing & Application
  // ---------------------------------------------------------------------------

  // Test a saved rule against existing transactions to preview matches
  async function testRule(
    ruleId: string,
    req?: TestRuleRequest,
  ): Promise<TestRuleResponse> {
    return authFetch<TestRuleResponse>(`/api/tag-rules/${ruleId}/test`, {
      method: 'POST',
      body: req || {},
    })
  }

  // Test conditions before saving a rule (preview matches)
  async function testConditions(
    req: TestConditionsRequest,
  ): Promise<TestRuleResponse> {
    return authFetch<TestRuleResponse>('/api/tag-rules/test-conditions', {
      method: 'POST',
      body: req,
    })
  }

  // Update the priority order of rules
  async function reorderRules(
    req: ReorderRulesRequest,
  ): Promise<TagRuleListResponse> {
    return authFetch<TagRuleListResponse>('/api/tag-rules/reorder', {
      method: 'POST',
      body: req,
    })
  }

  // Apply all enabled rules to existing transactions
  async function applyRules(
    req?: ApplyRulesRequest,
  ): Promise<ApplyRulesResponse> {
    return authFetch<ApplyRulesResponse>('/api/tag-rules/apply', {
      method: 'POST',
      body: req || {},
    })
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // Rules CRUD
    fetchRules,
    createRule,
    fetchRule,
    updateRule,
    deleteRule,

    // Rule testing & application
    testRule,
    testConditions,
    reorderRules,
    applyRules,

    // Export ApiError for error type checking
    ApiError,
  }
}
