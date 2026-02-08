import type { Config } from 'tailwindcss'
import { red, amber } from 'tailwindcss/colors'

// =============================================================================
// Tailwind Configuration
// Defines the colour scheme and typography for the app
// =============================================================================

export default {
  content: [],
  theme: {
    extend: {
      fontFamily: {
        sans: ['museo-sans-rounded', 'sans-serif'],
        display: ['museo-sans-rounded', 'sans-serif'],
      },
      colors: {
        // ---------------------------------------------------------------------
        // Brand colours - Dark Slate + Green
        // Calm, trustworthy, money/growth association
        // ---------------------------------------------------------------------
        onyx: '#121212', // Primary background - darkest
        graphite: '#1e1e1e', // Surface - cards, elevated elements
        sage: '#6ee7b7', // Accents, highlights

        // ---------------------------------------------------------------------
        // Semantic colours (mapped from brand)
        // ---------------------------------------------------------------------

        // Backgrounds
        background: '#121212', // onyx - main page background
        surface: '#1e1e1e', // graphite - cards, modals
        border: '#2e2e2e', // subtle border, slightly lighter than surface

        // Text
        foreground: '#f5f5f5', // near-white - primary text
        muted: '#a3a3a3', // neutral-400 - secondary text

        // Actions
        primary: '#10b981', // emerald - primary buttons
        'primary-hover': '#059669', // emerald-600 - hover state

        // Finance indicators
        positive: '#10b981', // emerald - income, gains (matches primary)
        negative: red[500], // expenses, losses
        warning: amber[500], // alerts, pending
      },
    },
  },
} satisfies Config
