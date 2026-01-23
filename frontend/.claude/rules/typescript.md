# TypeScript Standards

## Configuration
- Strict mode enabled
- ESLint for linting
- Path aliases via `tsconfig.json`

## Type Definitions

### Prefer interfaces for objects
```typescript
// Good
interface User {
  id: string
  name: string
  email: string
}

// Use type for unions, intersections, mapped types
type Status = 'pending' | 'active' | 'disabled'
type UserWithRole = User & { role: string }
```

### Avoid `any`
```typescript
// Bad
function process(data: any) { ... }

// Good
function process(data: unknown) {
  if (isUser(data)) { ... }
}

// Or use generics
function process<T>(data: T) { ... }
```

## Naming Conventions
- Interfaces: `PascalCase` (no `I` prefix)
- Types: `PascalCase`
- Enums: `PascalCase` with `PascalCase` members
- Constants: `UPPER_SNAKE_CASE`
- Functions/variables: `camelCase`

```typescript
// Good
interface UserResponse { ... }
type HttpMethod = 'GET' | 'POST'
enum UserStatus { Active, Disabled }
const API_BASE_URL = '/api'
function fetchUser() { ... }
```

## Function Types
```typescript
// Explicit return types for exported functions
export function calculateTotal(items: Item[]): number {
  return items.reduce((sum, item) => sum + item.price, 0)
}

// Arrow functions for callbacks
const doubled = items.map((item) => item.value * 2)
```

## Null Handling
- Use `X | null` not `X | undefined` for intentional absence
- Use optional chaining `?.` and nullish coalescing `??`
- Avoid non-null assertion `!` unless absolutely necessary

```typescript
// Good
const name = user?.profile?.name ?? 'Anonymous'

// Avoid
const name = user!.profile!.name
```

## API Response Types
```typescript
// Define response types
interface ApiResponse<T> {
  data: T
  meta?: {
    total: number
    page: number
  }
}

// Use with generics
const response = await useApi<ApiResponse<User[]>>('/users')
```

## Vue-Specific Types
```typescript
// Ref types
const count = ref<number>(0)
const user = ref<User | null>(null)

// Reactive types
const state = reactive<{ items: Item[]; loading: boolean }>({
  items: [],
  loading: false
})

// Computed types (usually inferred)
const total = computed<number>(() => items.value.length)
```

## File Organisation
```
app/types/
├── api.ts           # API response types
├── models.ts        # Domain models
└── index.ts         # Re-exports
```

## Imports
- Use path aliases (`@/`, `~/`)
- Group: Vue/Nuxt, third-party, local
- Prefer named exports

```typescript
// Good
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import type { User } from '~/types'
```
