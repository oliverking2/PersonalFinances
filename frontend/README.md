# Personal Finances Frontend

Vue 3 + Nuxt 4 frontend for the Personal Finances app.

## Stack

| Technology   | Purpose                           |
| ------------ | --------------------------------- |
| Nuxt 4       | Vue meta-framework (routing, SSR) |
| Vue 3        | Reactive UI framework             |
| Tailwind CSS | Utility-first CSS                 |
| Pinia        | State management                  |
| TypeScript   | Type safety                       |
| ApexCharts   | Analytics visualisations          |

## Setup

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env
# Edit NUXT_PUBLIC_API_URL if needed
```

## Development

```bash
npm run dev
```

Opens at <http://localhost:3000>

## Production Build

```bash
npm run build
npm run preview  # Preview production build locally
```

## Linting & Type Checking

```bash
npm run lint       # Auto-fix lint issues
npm run lint:check # Check only (CI)
make check         # Full validation (lint + typecheck)
```

## Project Structure

```
app/
├── components/          # Reusable Vue components
│   ├── App*.vue         # Design system (AppButton, AppInput, AppSelect, AppToast)
│   ├── accounts/        # Account/connection components
│   ├── analytics/       # Charts and analytics components
│   ├── assets/          # Manual assets/liabilities
│   ├── budgets/         # Budget tracking
│   ├── cashflow/        # Cash flow forecast
│   ├── datasets/        # Dataset explorer/export
│   ├── goals/           # Savings goals
│   ├── home/            # Home page widgets
│   ├── jobs/            # Background job status
│   ├── milestones/      # Financial milestones
│   ├── notifications/   # Notification bell/panel
│   ├── planning/        # Planning tab components
│   ├── subscriptions/   # Recurring patterns
│   ├── tags/            # Tag management components
│   └── transactions/    # Transaction list components
├── composables/         # Reusable logic
│   ├── useAuthenticatedFetch.ts  # API client with auth
│   └── use*Api.ts       # Domain-specific API composables (19 total)
├── layouts/             # Page layouts
│   └── default.vue      # Main layout with header/nav
├── middleware/          # Route guards
│   └── auth.global.ts   # SSR auth validation
├── pages/               # File-based routing
│   ├── index.vue        # Home dashboard
│   ├── transactions.vue # Transaction list
│   ├── insights.vue     # Analytics (tabs: analytics, net-worth, datasets)
│   ├── planning.vue     # Planning (tabs: budgets, goals, subscriptions, forecasting)
│   ├── settings.vue     # Settings (tabs: accounts, tags, rules, jobs, assets)
│   └── login.vue        # Login page (public)
├── stores/              # Pinia stores
│   ├── auth.ts          # Authentication state
│   └── toast.ts         # Toast notifications
└── types/               # TypeScript interfaces
```

## Authentication

Authentication uses JWT with HttpOnly refresh token cookies:

1. **Login**: Returns access token + sets refresh cookie
2. **Access token**: Stored in Pinia (memory only, lost on refresh)
3. **Refresh token**: HttpOnly cookie (survives page refresh)
4. **SSR validation**: Middleware validates auth server-side before rendering

Protected pages redirect to `/login` if not authenticated. Public pages use:

```typescript
definePageMeta({ public: true })
```

## Environment Variables

| Variable              | Description     | Default                 |
| --------------------- | --------------- | ----------------------- |
| `NUXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

For production (Cloudflare Tunnel):

```bash
NUXT_PUBLIC_API_URL=https://finances-api.oliverking.me.uk
```

## Design System

Custom Tailwind components for consistent styling:

- `AppButton` - Primary/secondary buttons with loading states
- `AppInput` - Text inputs with focus styles
- `AppSelect` - Custom dropdown (not native select)

Colour scheme: Dark slate (#121212, #1e1e1e) + Emerald green (#10b981)

## Documentation

- [Nuxt](https://nuxt.com/docs)
- [Vue 3](https://vuejs.org/guide/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Pinia](https://pinia.vuejs.org/)
