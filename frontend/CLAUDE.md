# Frontend CLAUDE.md

Frontend-specific guidance for Claude Code. See also root `CLAUDE.md` for project overview.

## Structure

```
frontend/
├── app/
│   ├── components/     # Reusable Vue components
│   ├── composables/    # Shared logic and API client
│   ├── layouts/        # Page layouts
│   └── pages/          # Route pages (file-based routing)
├── public/             # Static assets
├── nuxt.config.ts      # Nuxt configuration
├── app.config.ts       # App configuration
└── package.json
```

## Commands

```bash
cd frontend

# Validation (run before completing any change)
make check                    # Run lint and typecheck

# Individual checks
make lint                     # ESLint
make typecheck                # Nuxt type checking

# Development
make dev                      # Development server (http://localhost:3001)
make build                    # Production build
make preview                  # Preview production build
make clean                    # Remove build artifacts

# npm alternatives
npm run dev
npm run build
npm run lint
npm run lint:fix
```

## Technology

| Component | Technology |
|-----------|------------|
| Framework | Nuxt 4 |
| UI Library | Vue 3, Nuxt UI |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Routing | File-based (Nuxt) |

## Key Patterns

- **Composables** for API calls and shared logic (`app/composables/`)
- **Pages** for routes - file name = route path (`app/pages/`)
- **Components** for reusable UI pieces (`app/components/`)
- **Layouts** wrap pages with common structure (`app/layouts/`)

## File Placement

| Type | Location |
|------|----------|
| Pages | `app/pages/<name>.vue` |
| Components | `app/components/<Name>.vue` |
| Composables | `app/composables/use<Name>.ts` |
| Layouts | `app/layouts/<name>.vue` |
| Types | `app/types/<name>.ts` |

## Coding Standards

- TypeScript strict mode
- ESLint for linting
- Composition API with `<script setup lang="ts">`
- PascalCase for components, camelCase for composables
- British English in user-facing text

## Component Template

```vue
<script setup lang="ts">
// Props and emits first
const props = defineProps<{
  title: string
}>()

// Composables
const { data, pending } = useApi()

// Reactive state
const isOpen = ref(false)

// Computed
const displayTitle = computed(() => props.title.toUpperCase())

// Methods
function handleClick() {
  isOpen.value = !isOpen.value
}
</script>

<template>
  <div>
    <h1>{{ displayTitle }}</h1>
    <button @click="handleClick">Toggle</button>
  </div>
</template>
```

## API Calls

Use the `useApi` composable for backend communication:

```typescript
const { data, pending, error, refresh } = await useApi<ResponseType>('/endpoint')
```

## See Also

Detailed patterns in `.claude/rules/`:
- `vue.md` - Component patterns, reactivity, Nuxt conventions
- `typescript.md` - TypeScript standards, type definitions
