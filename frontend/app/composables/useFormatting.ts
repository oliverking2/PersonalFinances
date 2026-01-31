/**
 * Shared formatting utilities for currency and numeric values.
 *
 * These functions handle common patterns like:
 * - Formatting amounts as currency (£1,234.56)
 * - Safely parsing string amounts from API responses to numbers
 * - Formatting relative dates (Today, Yesterday, etc.)
 */

/**
 * Format a number as GBP currency.
 *
 * @param amount - The numeric amount to format
 * @param currency - Currency code (defaults to GBP)
 * @returns Formatted currency string (e.g., "£1,234.56")
 */
export function formatCurrency(amount: number, currency = 'GBP'): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

/**
 * Parse a string amount to a number safely.
 *
 * API responses often return amounts as strings (for decimal precision).
 * This function handles the conversion with a fallback for invalid values.
 *
 * @param value - String value to parse (e.g., "123.45")
 * @param fallback - Value to return if parsing fails (defaults to 0)
 * @returns Parsed number or fallback value
 */
export function parseAmount(
  value: string | number | null | undefined,
  fallback = 0,
): number {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  if (typeof value === 'number') {
    return Number.isNaN(value) ? fallback : value
  }
  const parsed = parseFloat(value)
  return Number.isNaN(parsed) ? fallback : parsed
}

/**
 * Format a date string as a relative label (Today, Yesterday) or formatted date.
 *
 * @param dateStr - ISO date string (YYYY-MM-DD)
 * @returns Formatted date label
 */
export function formatDateLabel(dateStr: string): string {
  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  const todayStr = today.toISOString().slice(0, 10)
  const yesterdayStr = yesterday.toISOString().slice(0, 10)

  if (dateStr === todayStr) {
    return 'Today'
  }
  if (dateStr === yesterdayStr) {
    return 'Yesterday'
  }

  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

/**
 * Composable that returns all formatting functions.
 *
 * Can be used in Vue components with auto-import:
 * const { formatCurrency, parseAmount } = useFormatting()
 *
 * Or import functions directly:
 * import { formatCurrency, parseAmount } from '~/composables/useFormatting'
 */
export function useFormatting() {
  return {
    formatCurrency,
    parseAmount,
    formatDateLabel,
  }
}
