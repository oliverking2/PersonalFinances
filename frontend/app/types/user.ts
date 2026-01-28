/**
 * User API types
 * Matches backend Pydantic models for user endpoints
 */

/** Telegram link status */
export interface TelegramStatusResponse {
  is_linked: boolean
  chat_id: string | null
}

/** Response when generating a link code */
export interface TelegramLinkCodeResponse {
  code: string
  expires_in_seconds: number
  instructions: string
}

/** Response when unlinking Telegram */
export interface TelegramUnlinkResponse {
  ok: boolean
}
