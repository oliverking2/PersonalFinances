# Vue & Nuxt Patterns

## Component Structure
```
app/
├── components/       # Reusable UI components
│   ├── common/       # Shared components (buttons, inputs)
│   └── <feature>/    # Feature-specific components
├── composables/      # Shared logic (useApi, useState)
├── layouts/          # Page layouts
├── pages/            # File-based routing
└── types/            # TypeScript definitions
```

## Component Template
```vue
<script setup lang="ts">
// 1. Props and emits
const props = defineProps<{
  title: string
  items?: string[]
}>()

const emit = defineEmits<{
  select: [item: string]
}>()

// 2. Composables
const { data, pending } = useApi<DataType>('/endpoint')

// 3. Reactive state
const isOpen = ref(false)
const selected = ref<string | null>(null)

// 4. Computed properties
const hasItems = computed(() => (props.items?.length ?? 0) > 0)

// 5. Methods
function handleSelect(item: string) {
  selected.value = item
  emit('select', item)
}

// 6. Lifecycle (if needed)
onMounted(() => {
  // ...
})
</script>

<template>
  <div>
    <!-- Template -->
  </div>
</template>
```

## Naming Conventions
- Components: `PascalCase.vue` (e.g., `UserCard.vue`)
- Composables: `useCamelCase.ts` (e.g., `useApi.ts`)
- Pages: `kebab-case.vue` (e.g., `user-profile.vue`)
- Layouts: `kebab-case.vue` (e.g., `dashboard.vue`)

## Reactivity
- Use `ref()` for primitives
- Use `reactive()` for objects (sparingly)
- Use `computed()` for derived values
- Use `watch()` for side effects

```typescript
// Good
const count = ref(0)
const doubled = computed(() => count.value * 2)

// Avoid - loses reactivity
const { value } = ref(0)  // Don't destructure refs
```

## Props and Events
- Type props explicitly with TypeScript
- Use object syntax for complex props
- Events use past tense or actions

```vue
<script setup lang="ts">
// Props with defaults
const props = withDefaults(defineProps<{
  size?: 'sm' | 'md' | 'lg'
}>(), {
  size: 'md'
})

// Typed events
const emit = defineEmits<{
  update: [value: string]
  submit: []
}>()
</script>
```

## API Calls
Use composables for data fetching:

```typescript
// In composables/useApi.ts
export function useApi<T>(endpoint: string) {
  return useFetch<T>(`${API_BASE}${endpoint}`)
}

// In component
const { data, pending, error, refresh } = await useApi<User[]>('/users')
```

## Nuxt Conventions
- `useFetch()` for SSR-compatible data fetching
- `useState()` for cross-component state
- Auto-imports for Vue and Nuxt utilities
- File-based routing in `pages/`

## Error Handling
- Use `<NuxtErrorBoundary>` for component errors
- Handle API errors in composables
- Show user-friendly messages

```vue
<template>
  <div v-if="error">
    <p>Something went wrong. Please try again.</p>
  </div>
  <div v-else-if="pending">
    <USpinner />
  </div>
  <div v-else>
    <!-- Content -->
  </div>
</template>
```
