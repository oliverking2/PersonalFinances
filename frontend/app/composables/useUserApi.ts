// =============================================================================
// User API Composable
// API functions for user settings (Telegram linking, etc.)
// =============================================================================

import type {
  TelegramStatusResponse,
  TelegramLinkCodeResponse,
  TelegramUnlinkResponse,
} from '~/types/user'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useUserApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Telegram Linking
  // ---------------------------------------------------------------------------

  /**
   * Get current Telegram link status
   * Returns whether linked and a masked chat ID if linked
   */
  async function getTelegramStatus(): Promise<TelegramStatusResponse> {
    return authFetch<TelegramStatusResponse>('/api/user/telegram')
  }

  /**
   * Generate a one-time code for linking Telegram
   * User sends this code to the bot to complete linking
   */
  async function generateTelegramLinkCode(): Promise<TelegramLinkCodeResponse> {
    return authFetch<TelegramLinkCodeResponse>('/api/user/telegram/link', {
      method: 'POST',
    })
  }

  /**
   * Unlink Telegram from the account
   */
  async function unlinkTelegram(): Promise<TelegramUnlinkResponse> {
    return authFetch<TelegramUnlinkResponse>('/api/user/telegram', {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Export
  // ---------------------------------------------------------------------------

  return {
    getTelegramStatus,
    generateTelegramLinkCode,
    unlinkTelegram,
    ApiError,
  }
}
