// =============================================================================
// Tags API Composable
// All API functions for managing user-defined tags
// =============================================================================

import type {
  Tag,
  TagListResponse,
  TagCreateRequest,
  TagUpdateRequest,
  TransactionTagsRequest,
  TransactionTagsResponse,
  BulkTagRequest,
  BulkTagResponse,
} from '~/types/tags'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useTagsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Tags CRUD
  // ---------------------------------------------------------------------------

  // Fetch all tags for the current user
  async function fetchTags(): Promise<TagListResponse> {
    return authFetch<TagListResponse>('/api/tags')
  }

  // Create a new tag
  async function createTag(req: TagCreateRequest): Promise<Tag> {
    return authFetch<Tag>('/api/tags', {
      method: 'POST',
      body: req,
    })
  }

  // Get a single tag by ID
  async function fetchTag(tagId: string): Promise<Tag> {
    return authFetch<Tag>(`/api/tags/${tagId}`)
  }

  // Update a tag's name and/or colour
  async function updateTag(tagId: string, req: TagUpdateRequest): Promise<Tag> {
    return authFetch<Tag>(`/api/tags/${tagId}`, {
      method: 'PUT',
      body: req,
    })
  }

  // Delete a tag (removes from all transactions)
  async function deleteTag(tagId: string): Promise<void> {
    await authFetch(`/api/tags/${tagId}`, {
      method: 'DELETE',
    })
  }

  // Hide a tag from the UI (standard tags cannot be deleted, only hidden)
  async function hideTag(tagId: string): Promise<Tag> {
    return authFetch<Tag>(`/api/tags/${tagId}/hide`, {
      method: 'PUT',
    })
  }

  // Unhide a previously hidden tag
  async function unhideTag(tagId: string): Promise<Tag> {
    return authFetch<Tag>(`/api/tags/${tagId}/unhide`, {
      method: 'PUT',
    })
  }

  // ---------------------------------------------------------------------------
  // Transaction Tagging
  // ---------------------------------------------------------------------------

  // Add tags to a transaction
  async function addTagsToTransaction(
    transactionId: string,
    req: TransactionTagsRequest,
  ): Promise<TransactionTagsResponse> {
    return authFetch<TransactionTagsResponse>(
      `/api/transactions/${transactionId}/tags`,
      {
        method: 'POST',
        body: req,
      },
    )
  }

  // Remove a tag from a transaction
  async function removeTagFromTransaction(
    transactionId: string,
    tagId: string,
  ): Promise<TransactionTagsResponse> {
    return authFetch<TransactionTagsResponse>(
      `/api/transactions/${transactionId}/tags/${tagId}`,
      {
        method: 'DELETE',
      },
    )
  }

  // Bulk add/remove tags from multiple transactions
  async function bulkTagTransactions(
    req: BulkTagRequest,
  ): Promise<BulkTagResponse> {
    return authFetch<BulkTagResponse>('/api/transactions/bulk/tags', {
      method: 'POST',
      body: req,
    })
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // Tags CRUD
    fetchTags,
    createTag,
    fetchTag,
    updateTag,
    deleteTag,
    hideTag,
    unhideTag,

    // Transaction tagging
    addTagsToTransaction,
    removeTagFromTransaction,
    bulkTagTransactions,

    // Export ApiError for error type checking
    ApiError,
  }
}
