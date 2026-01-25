/**
 * useDatePresets
 * Utilities for date range preset calculations
 * Used by DateFilterDropdown for quick date filtering options
 */

export type DatePreset =
  | 'this_month'
  | 'last_30_days'
  | 'last_month'
  | 'this_year'
  | 'last_year'
  | 'all_time'
  | 'custom'

export interface DateRange {
  start_date: string | undefined
  end_date: string | undefined
}

export interface DatePresetOption {
  value: DatePreset
  label: string
}

// Available preset options for the dropdown
export const DATE_PRESET_OPTIONS: DatePresetOption[] = [
  { value: 'this_month', label: 'This month' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_month', label: 'Last month' },
  { value: 'this_year', label: 'This year' },
  { value: 'last_year', label: 'Last year' },
  { value: 'all_time', label: 'All time' },
  { value: 'custom', label: 'Custom' },
]

export function useDatePresets() {
  /**
   * Format a Date object to ISO date string (YYYY-MM-DD)
   * Uses local timezone to avoid off-by-one errors
   */
  function formatDateISO(date: Date): string {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  /**
   * Get the first day of the month for a given date
   */
  function getStartOfMonth(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), 1)
  }

  /**
   * Get the first day of the year for a given date
   */
  function getStartOfYear(date: Date): Date {
    return new Date(date.getFullYear(), 0, 1)
  }

  /**
   * Get a date N days ago from today
   */
  function getDaysAgo(days: number): Date {
    const date = new Date()
    date.setDate(date.getDate() - days)
    return date
  }

  /**
   * Calculate the date range for a given preset
   * Returns undefined dates for 'custom' preset (user must specify)
   */
  function getPresetDateRange(preset: DatePreset): DateRange {
    const today = new Date()

    switch (preset) {
      case 'all_time':
        // No date filters - show all transactions
        return {
          start_date: undefined,
          end_date: undefined,
        }

      case 'this_month':
        return {
          start_date: formatDateISO(getStartOfMonth(today)),
          end_date: formatDateISO(today),
        }

      case 'last_month': {
        // First day of last month to last day of last month
        const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
        const lastDayOfLastMonth = new Date(
          today.getFullYear(),
          today.getMonth(),
          0,
        )
        return {
          start_date: formatDateISO(lastMonth),
          end_date: formatDateISO(lastDayOfLastMonth),
        }
      }

      case 'last_30_days':
        return {
          start_date: formatDateISO(getDaysAgo(30)),
          end_date: formatDateISO(today),
        }

      case 'this_year':
        return {
          start_date: formatDateISO(getStartOfYear(today)),
          end_date: formatDateISO(today),
        }

      case 'last_year': {
        const lastYearStart = new Date(today.getFullYear() - 1, 0, 1)
        const lastYearEnd = new Date(today.getFullYear() - 1, 11, 31)
        return {
          start_date: formatDateISO(lastYearStart),
          end_date: formatDateISO(lastYearEnd),
        }
      }

      case 'custom':
      default:
        // Custom preset doesn't set dates - user specifies them
        return {
          start_date: undefined,
          end_date: undefined,
        }
    }
  }

  /**
   * Detect which preset (if any) matches the given date range
   * Returns 'custom' if no preset matches
   */
  function detectPreset(startDate?: string, endDate?: string): DatePreset {
    // No dates set = all time
    if (!startDate && !endDate) {
      return 'all_time'
    }

    // Check each preset
    const thisMonth = getPresetDateRange('this_month')
    if (startDate === thisMonth.start_date && endDate === thisMonth.end_date) {
      return 'this_month'
    }

    const lastMonth = getPresetDateRange('last_month')
    if (startDate === lastMonth.start_date && endDate === lastMonth.end_date) {
      return 'last_month'
    }

    const last30Days = getPresetDateRange('last_30_days')
    if (
      startDate === last30Days.start_date &&
      endDate === last30Days.end_date
    ) {
      return 'last_30_days'
    }

    const thisYear = getPresetDateRange('this_year')
    if (startDate === thisYear.start_date && endDate === thisYear.end_date) {
      return 'this_year'
    }

    const lastYear = getPresetDateRange('last_year')
    if (startDate === lastYear.start_date && endDate === lastYear.end_date) {
      return 'last_year'
    }

    // If we have dates but they don't match any preset, it's custom
    return 'custom'
  }

  /**
   * Format a date range for display in the dropdown trigger
   * Returns human-readable string like "Jan 1 - Jan 25"
   */
  function formatDateRangeDisplay(
    startDate?: string,
    endDate?: string,
  ): string {
    if (!startDate && !endDate) {
      return ''
    }

    const formatShort = (dateStr: string): string => {
      const date = new Date(dateStr + 'T00:00:00')
      return new Intl.DateTimeFormat('en-GB', {
        day: 'numeric',
        month: 'short',
      }).format(date)
    }

    if (startDate && endDate) {
      return `${formatShort(startDate)} - ${formatShort(endDate)}`
    }

    if (startDate) {
      return `From ${formatShort(startDate)}`
    }

    if (endDate) {
      return `Until ${formatShort(endDate)}`
    }

    return ''
  }

  return {
    formatDateISO,
    getPresetDateRange,
    detectPreset,
    formatDateRangeDisplay,
  }
}
