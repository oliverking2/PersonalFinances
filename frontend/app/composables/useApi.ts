/**
 * Composable for making API calls to the backend.
 */
export function useApi() {
  const config = useRuntimeConfig()
  const baseUrl = config.public.apiUrl

  /**
   * Make a GET request to the API.
   */
  async function get<T>(path: string): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`)
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return response.json()
  }

  /**
   * Make a POST request to the API.
   */
  async function post<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return response.json()
  }

  /**
   * Make a PATCH request to the API.
   */
  async function patch<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return response.json()
  }

  /**
   * Make a DELETE request to the API.
   */
  async function del(path: string): Promise<void> {
    const response = await fetch(`${baseUrl}${path}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
  }

  return { get, post, patch, del }
}

// Type definitions for API responses
export interface Account {
  id: string
  name: string | null
  display_name: string | null
  iban: string | null
  currency: string | null
  owner_name: string | null
  status: string | null
  product: string | null
  requisition_id: string | null
  transaction_extract_date: string | null
}

export interface AccountListResponse {
  accounts: Account[]
  total: number
}

export interface Connection {
  id: string
  institution_id: string
  status: string
  friendly_name: string
  created: string
  link: string
  account_count: number
  expired: boolean
}

export interface ConnectionListResponse {
  connections: Connection[]
  total: number
}
