/**
 * Tag type definitions
 */

// ----------------------------------------------------------------------------
// API Response Types
// ----------------------------------------------------------------------------

export interface Tag {
  id: string
  name: string
  colour: string | null
  usage_count: number
  created_at: string
  updated_at: string
}

export interface TagListResponse {
  tags: Tag[]
  total: number
}

// ----------------------------------------------------------------------------
// Request Types
// ----------------------------------------------------------------------------

export interface TagCreateRequest {
  name: string
  colour?: string | null
}

export interface TagUpdateRequest {
  name?: string
  colour?: string | null
}

export interface TransactionTagsRequest {
  tag_ids: string[]
}

export interface BulkTagRequest {
  transaction_ids: string[]
  add_tag_ids?: string[]
  remove_tag_ids?: string[]
}

// ----------------------------------------------------------------------------
// Response Types
// ----------------------------------------------------------------------------

export interface TransactionTagsResponse {
  transaction_id: string
  tags: TransactionTagResponse[]
}

export interface TransactionTagResponse {
  id: string
  name: string
  colour: string | null
}

export interface BulkTagResponse {
  updated_count: number
}
