# Frontend Guide

## Claude's Role

Claude writes code directly with clear comments explaining the how and why. Changes are small and incremental. Simplicity is preferred over complexity - slightly slower load times are acceptable.

**Design/UX decisions**: Never make design or UX decisions without presenting options to the user first. When a task involves layout, positioning, visual feedback, or interaction patterns, propose 2-3 approaches with trade-offs and get approval before implementing.

## Code Style

**Comments:** Add comments liberally to explain:

- What groups of Tailwind classes do
- Why certain patterns are used
- What each section of a component does

**Reducing Tailwind duplication:** Extract repeated styles into components:

- `AppButton` - Styled button with hover/focus states
- `AppInput` - Styled text input with focus states
- `AppSelect` - Custom dropdown with fully styled options (not native select)
- Use `@apply` in component `<style scoped>` blocks for base styles

**Form inputs:** Always use the standard `App*` components for form elements:

- Text/number inputs: `<AppInput v-model="value" />`
- Dropdowns: `<AppSelect v-model="value" :options="options" placeholder="Select..." />`

**IMPORTANT - Never use native `<select>` elements.** Always use `<AppSelect>` for dropdowns. This applies to all select/dropdown inputs throughout the application. The AppSelect component provides consistent styling and a better UX than native selects.

## Stack

| Technology   | What It Is                        | Docs                                   |
| ------------ | --------------------------------- | -------------------------------------- |
| Vue 3        | Reactive UI framework             | <https://vuejs.org/guide/>             |
| Nuxt 4       | Vue meta-framework (routing, SSR) | <https://nuxt.com/docs>                |
| Tailwind CSS | Utility-first CSS                 | <https://tailwindcss.com/docs>         |
| TypeScript   | Typed JavaScript                  | <https://www.typescriptlang.org/docs/> |
| Pinia        | State management                  | <https://pinia.vuejs.org/>             |

## Project Structure

```
frontend/
├── app/
│   ├── app.vue              # Root component
│   ├── components/          # UI components
│   │   ├── App*.vue         # Shared components (AppButton, AppInput)
│   │   ├── accounts/        # Account/connection components
│   │   └── transactions/    # Transaction components
│   ├── composables/         # Reusable logic (API calls, utilities)
│   ├── layouts/             # Page layouts (default, etc.)
│   ├── middleware/          # Route middleware (auth, etc.)
│   ├── pages/               # File-based routing
│   ├── stores/              # Pinia stores (auth)
│   └── types/               # TypeScript interfaces
├── nuxt.config.ts           # Nuxt configuration (includes Typekit fonts)
├── tailwind.config.ts       # Tailwind theme and colours
└── package.json
```

## Commands

```bash
cd frontend
make install     # Install dependencies
make dev         # Dev server at http://localhost:3000
make check       # Run lint + typecheck (run before committing)
make lint        # Format and lint (auto-fix)
make lint-check  # Lint check only (no auto-fix)
make typecheck   # Run type checking only
make build       # Production build
```

## Colour Scheme

Dark Slate + Green - calm, trustworthy, money/growth association.

| Name     | Hex       | Usage                    |
| -------- | --------- | ------------------------ |
| onyx     | `#121212` | Primary background       |
| graphite | `#1e1e1e` | Surface (cards, modals)  |
| emerald  | `#10b981` | Primary actions, buttons |
| sage     | `#6ee7b7` | Accents, highlights      |

## Typography

Font: **Museo Sans Rounded** loaded via Adobe Typekit (configured in `nuxt.config.ts`).

## Design Decisions

- **SSR auth validation**: Auth middleware runs on both server and client. On server, it forwards the refresh cookie to the backend API to validate - if invalid, redirects to `/login` before any HTML is sent (no flash of protected content). Pinia hydrates the auth state to the client. **Requirements for SSR auth with separate frontend/backend domains**: (1) Backend must set cookie with `path=/` (not `/auth`) so browser sends it to frontend, (2) Backend must set `COOKIE_DOMAIN=.example.com` to share cookie across subdomains, (3) Frontend must forward the `Set-Cookie` header from backend refresh response to browser (token rotation).
- **Simple refresh flow**: Check token expiry before API calls. If expired, refresh. If refresh fails, redirect to login.
- **Component-based styling**: Reusable components (AppButton, AppInput) encapsulate Tailwind classes to reduce duplication.
- **Toast notifications**: Pinia store (`stores/toast.ts`) for user feedback on OAuth callbacks and other actions.
- **Avoid layout shift**: Prefer showing disabled/faded elements over hiding them (e.g., disabled buttons stay visible).
- **Client-side filtering**: Filter already-loaded data locally for instant response; only paginate via API.

## Patterns

### API Composables (`composables/use*Api.ts`)

Each domain has a composable that exports API functions using `useAuthenticatedFetch` for token management.

```typescript
// Pattern: composables/useExampleApi.ts
export function useExampleApi() {
  const { authenticatedFetch, ApiError } = useAuthenticatedFetch()

  async function fetchItems(): Promise<ItemListResponse> {
    return authenticatedFetch<ItemListResponse>('/api/items')
  }

  return { fetchItems, ApiError }
}
```

### Component Organisation

Feature components are grouped in subdirectories:

```
components/
├── accounts/
│   ├── AccountRow.vue         # Single account display
│   ├── ConnectionCard.vue     # Connection with nested accounts
│   └── ...
├── subscriptions/
│   ├── RecurringPatternCard.vue    # Pattern card with status/actions
│   └── ...
├── tags/
│   ├── TagChip.vue            # Small coloured tag pill
│   └── TagSelector.vue        # Dropdown for selecting/creating tags
└── transactions/
    ├── TransactionRow.vue     # Single transaction
    ├── TransactionDayGroup.vue # Day header + transactions
    └── TransactionFilters.vue  # Filter controls
```

### Page State Pattern

Pages follow a consistent structure:

```typescript
// State
const items = ref<Item[]>([])
const loading = ref(true)
const error = ref('')

// Load data on mount
onMounted(loadData)

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetchItems()
    items.value = response.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    loading.value = false
  }
}
```

### Infinite Scroll

Use IntersectionObserver with a sentinel element:

```typescript
const sentinelRef = ref<HTMLDivElement | null>(null)

const observer = new IntersectionObserver(
  (entries) => {
    if (entries[0]?.isIntersecting && hasMore.value) {
      loadMore()
    }
  },
  { rootMargin: '100px' }, // Load early
)

watch(sentinelRef, (el) => el && observer.observe(el))
onUnmounted(() => observer.disconnect())
```

### Types (`types/*.ts`)

Each domain has a types file with interfaces matching backend Pydantic models:

```typescript
// types/example.ts
export interface Item { ... }
export interface ItemListResponse { items: Item[]; total: number }
export interface ItemQueryParams { search?: string; page?: number }
```

## Backend API

The backend API is at `http://localhost:8000`. Full API contracts are in `/docs/api/`.

**Authentication:**

- `POST /auth/login` - Returns access token + sets refresh cookie
- `POST /auth/refresh` - Refresh access token (uses HttpOnly cookie)
- `POST /auth/logout` - Revoke tokens and clear cookie
- `GET /auth/me` - Get current user (requires Bearer token)

**Protected endpoints** (require `Authorization: Bearer <token>`):

- `GET /accounts` - List bank accounts
- `GET /connections` - List bank connections
- `GET /transactions` - List transactions
- `GET /recurring` - List recurring patterns (filter by status/source)
- `POST /recurring/{id}/accept` - Accept pending pattern
- `POST /recurring/{id}/pause` - Pause pattern
- `POST /recurring/{id}/resume` - Resume paused pattern
- `POST /recurring/{id}/cancel` - Cancel pattern
- `GET /budgets` - List budgets by tag
- `GET /goals` - List savings goals
- `GET /analytics/datasets` - List available analytics datasets
