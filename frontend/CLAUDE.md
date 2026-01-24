# Frontend Guide

## Claude's Role

Claude writes code directly with clear comments explaining the how and why. Changes are small and incremental. Simplicity is preferred over complexity - slightly slower load times are acceptable.

## Code Style

**Comments:** Add comments liberally to explain:

- What groups of Tailwind classes do
- Why certain patterns are used
- What each section of a component does

**Reducing Tailwind duplication:** Extract repeated styles into components:

- `AppButton` - Styled button with hover/focus states
- `AppInput` - Styled text input with focus states
- Use `@apply` in component `<style scoped>` blocks for base styles

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
│   ├── components/          # Reusable UI components (AppButton, AppInput, etc.)
│   ├── layouts/             # Page layouts (default, etc.)
│   ├── middleware/          # Route middleware (auth, etc.)
│   ├── pages/               # File-based routing
│   └── stores/              # Pinia stores
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

- **Client-only auth**: Auth middleware runs only on the client for simplicity. SSR would require cookie forwarding which adds complexity.
- **Simple refresh flow**: Check token expiry before API calls. If expired, refresh. If refresh fails, redirect to login.
- **Component-based styling**: Reusable components (AppButton, AppInput) encapsulate Tailwind classes to reduce duplication.

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
