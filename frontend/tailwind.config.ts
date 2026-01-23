import type { Config } from 'tailwindcss'
import { slate, blue, emerald, red, amber } from 'tailwindcss/colors'

export default {
  content: [],
  theme: {
    extend: {
      colors: {
        // Backgrounds
        background: slate[900],
        surface: slate[800],
        border: slate[700],

        // Text
        foreground: slate[100], // primary text
        muted: slate[400], // secondary text

        // Actions
        primary: blue[500],

        // Finance
        positive: emerald[500],
        negative: red[500],
        warning: amber[500],
      },
    },
  },
} satisfies Config
