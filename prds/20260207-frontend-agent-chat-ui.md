# PRD: Frontend Agent Chat UI

**Status**: Draft
**Author**: Claude
**Created**: 2026-02-07
**Updated**: 2026-02-07

---

## Overview

Chat interface in the frontend for interacting with the Agent API (PRD 3). Users can ask natural language financial questions, see formatted answers with provenance, view inline charts, and provide feedback. Sits under the Insights section as a new "Ask" tab.

## Problem Statement

The Agent API (PRD 3) provides a natural language interface to financial data, but without a frontend, users can't access it. A dedicated chat page provides a conversational experience where users type questions and receive formatted answers with supporting data visualisations.

## Goals

- Dedicated `/insights/ask` page with chat interface
- Message history within a session (not persisted across sessions)
- Expandable provenance section showing what data was queried
- Inline chart rendering when agent returns chart specs
- Follow-up suggestion chips
- Thumbs up/down feedback on each response (local state only)
- Mobile responsive

## Non-Goals

- Persistent conversation history across sessions (Phase 2)
- Voice input
- Streaming responses (Phase 2)
- Sidebar/widget mode (standalone page only)
- Custom chart configuration by users
- Multi-turn conversation with backend context (PRD 3 is single-shot only)

---

## User Stories

1. **As a** user, **I want to** type a financial question and get a formatted answer, **so that** I can understand my finances without navigating complex pages
2. **As a** user, **I want to** see charts inline with answers, **so that** I can visualise trends at a glance
3. **As a** user, **I want to** click suggestion chips, **so that** I discover what questions I can ask
4. **As a** user, **I want to** expand provenance details, **so that** I can verify what data was used
5. **As a** user, **I want to** give thumbs up/down, **so that** I can flag bad answers for improvement

---

## Proposed Solution

### High-Level Design

```
/insights/ask (page)
    └── AgentChat.vue (component)
        ├── Message list (scrollable)
        │   ├── User messages (right-aligned)
        │   └── AgentMessageBubble.vue (left-aligned)
        │       ├── Formatted text (markdown via markdown-it)
        │       ├── Confidence indicator (if medium/low)
        │       ├── Inline chart (ApexCharts)
        │       ├── Provenance (collapsible)
        │       ├── Suggestion chips
        │       └── Feedback buttons
        ├── Text input + send button
        └── Suggestion cards (shown when empty)
```

### New Files

**`frontend/app/composables/useAgentApi.ts`**:

```typescript
export function useAgentApi() {
  const { authenticatedFetch } = useAuthenticatedFetch()

  async function askQuestion(question: string): Promise<AgentResponse> {
    return authenticatedFetch<AgentResponse>('/api/agent/ask', {
      method: 'POST',
      body: { question },
    })
  }

  async function getSuggestions(): Promise<string[]> {
    const response = await authenticatedFetch<{ suggestions: string[] }>(
      '/api/agent/suggestions',
    )
    return response.suggestions
  }

  return { askQuestion, getSuggestions }
}
```

**Note:** No `refineQuestion()` — PRD 3 only exposes `POST /api/agent/ask` (single-shot). Each question in the chat is an independent request. Follow-up suggestions use `askQuestion()` with the suggestion text. Multi-turn context will be added if/when PRD 3 adds a refine endpoint.

**`frontend/app/types/agent.ts`**:

```typescript
export interface AgentResponse {
  answer: string
  provenance: QueryProvenance
  data: Record<string, unknown>[]
  chart_spec: ChartSpec | null
  suggestions: string[]
  confidence: 'high' | 'medium' | 'low'   // Added by PRD 5 (defaults to 'high')
  iterations: number                        // Added by PRD 5 (defaults to 1)
}

export interface QueryProvenance {
  dataset_name: string
  dataset_friendly_name: string
  measures_queried: string[]
  dimensions_queried: string[]
  filters_applied: Record<string, unknown>[]
  row_count: number
  query_duration_ms: number
}

export interface ChartSpec {
  type: 'bar' | 'line' | 'donut'
  title: string
  x_axis: string
  y_axis: string
  series: ChartSeries[]
}

export interface ChartSeries {
  name: string
  data: number[]
  labels?: string[]
}
```

**Note:** `confidence` and `iterations` are included now (with defaults) so the frontend doesn't need changes when PRD 5 (Refinement) is implemented. Until PRD 5, the backend always returns `confidence: "high"` and `iterations: 1`.

**`frontend/app/components/agent/AgentChat.vue`**:

Main chat component containing:

- Scrollable message area with auto-scroll to bottom
- Text input with send button (Enter to send, Shift+Enter for newline)
- User messages styled right-aligned with emerald accent
- Agent messages rendered via `AgentMessageBubble` sub-component (see below)
- Loading state: typing indicator animation (three dots)
- Error state: error message with retry button
- Empty state: suggestion cards (see below)

**`frontend/app/components/agent/AgentMessageBubble.vue`**:

Extracted component for a single agent response. Receives an `AgentResponse` as prop. Renders:

- Markdown-rendered answer text (via `markdown-it`, see Dependencies below)
- Confidence indicator:
  - `high` → no indicator (default, clean)
  - `medium` → subtle amber dot/badge: "Refined answer"
  - `low` → subtle amber text: "Best attempt — results may be incomplete"
- Inline ApexCharts chart if `chart_spec` is present
- Expandable provenance in `<details>` element
- Follow-up suggestion chips (clicking one calls `askQuestion()` with the chip text)
- Thumbs up/down buttons (local state only — stores in a reactive `Map<number, 'up' | 'down'>` keyed by message index)

Extracting this component keeps `AgentChat.vue` focused on the chat container/scroll/input logic, while the bubble handles rendering complexity (markdown, charts, provenance, feedback).

**`frontend/app/components/agent/AgentSuggestionCard.vue`**:

- Clickable cards showing example questions
- Displayed on initial page load (before any messages)
- Uses emerald border/accent on hover
- Grid layout: 2 columns on desktop, 1 on mobile

**`frontend/app/pages/insights/ask.vue`**:

- Full-page layout
- `AgentChat` component as main content
- Suggestion cards shown when chat is empty
- Page title: "Ask about your finances"

### Navigation

Update `frontend/app/pages/insights.vue` to add "Ask" tab:

```typescript
const tabs = [
  { to: '/insights/ask', label: 'Ask' },
  { to: '/insights/analytics', label: 'Analytics' },
]
```

"Ask" is listed first as the primary action.

### Data Model

No backend data model changes. Frontend-only types.

### API Endpoints

Uses endpoints defined in PRD 3:

| Method | Path                    | Description                  |
|--------|-------------------------|------------------------------|
| POST   | `/api/agent/ask`        | Ask a question               |
| GET    | `/api/agent/suggestions`| Get example questions        |

### UI/UX

**Design**: Follow existing dark theme (Onyx/Graphite/Emerald/Sage). Use `AppButton`, `AppInput` base components.

**Layout** (empty state):

```
┌─────────────────────────────────────────────────────────┐
│  Insights                                                │
│  [Ask] [Analytics]                                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Ask about your finances                                 │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ How much did I   │  │ What's my savings│             │
│  │ spend last month?│  │ rate this year?  │             │
│  └──────────────────┘  └──────────────────┘             │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ Show me spending │  │ Am I on track    │             │
│  │ by category      │  │ with my budgets? │             │
│  └──────────────────┘  └──────────────────┘             │
│                                                          │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  [Ask a question about your finances...]   [Send]│   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

After asking a question:

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│                        How much did I spend last month?  │ ← user (right)
│                                                          │
│  You spent £2,340.50 in January 2026, across 87         │ ← agent (left)
│  transactions. This is 12% less than December.           │
│                                                          │
│  [▸ Show details]                                        │ ← collapsible
│                                                          │
│  ┌────────────────────────────────────────────┐          │
│  │  [Bar chart: spending by week]             │          │ ← inline chart
│  └────────────────────────────────────────────┘          │
│                                                          │
│  [What did I spend most on?] [Compare to last year]      │ ← suggestions
│                                                          │
│  [thumbs up] [thumbs down]                               │ ← feedback
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  [Ask another question...]                 [Send]│   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Provenance details** (when expanded):

```
▾ Show details
  Dataset: Monthly Trends
  Measures: total_spending, total_transactions
  Filters: month = 2026-01, user_id = (your account)
  Rows returned: 1
  Query time: 45ms
```

---

## Technical Considerations

### Dependencies

- `vue3-apexcharts` (already used in analytics pages) — inline charts
- `markdown-it` — Markdown rendering for agent responses. Install as a new npm dependency. The project does not currently have a markdown library. Use `markdown-it` over alternatives because: lightweight (~15KB gzipped), no framework coupling, widely used, supports HTML sanitisation via `markdown-it` options (`html: false`).

### Migration

No migration. Frontend-only changes.

### Performance

- Suggestion cards load on page mount (single API call, fast — no caching needed)
- Agent responses take 2-5s (LLM processing time) — typing indicator shown
- Charts rendered client-side after data arrives
- Message history is in-memory (cleared on page navigation)

### Security

- All API calls use authenticated fetch (JWT Bearer token)
- User can only see responses for their own data (enforced server-side by user_id injection)
- No raw SQL or query details exposed (provenance shows dataset/measures only)
- Markdown rendering with `html: false` prevents XSS from agent responses

### Testing

This project's frontend does **not** have automated component tests (no Vitest component testing setup, no `@vue/test-utils`). All testing is manual. The testing strategy below reflects this — items are manual verification steps, not automated test cases.

---

## Implementation Plan

### Phase 1: Types and API Composable

- [ ] Create `frontend/app/types/agent.ts`
- [ ] Create `frontend/app/composables/useAgentApi.ts`

### Phase 2: Chat Components

- [ ] Install `markdown-it` via npm
- [ ] Create `frontend/app/components/agent/AgentMessageBubble.vue`
- [ ] Create `frontend/app/components/agent/AgentChat.vue`
- [ ] Create `frontend/app/components/agent/AgentSuggestionCard.vue`
- [ ] Handle loading, error, and empty states

### Phase 3: Page and Navigation

- [ ] Create `frontend/app/pages/insights/ask.vue`
- [ ] Update `frontend/app/pages/insights.vue` to add "Ask" tab
- [ ] Verify routing works correctly

### Phase 4: Charts and Feedback

- [ ] Implement inline chart rendering from `chart_spec` (map `ChartSpec` → ApexCharts options)
- [ ] Implement feedback buttons (thumbs up/down, local state only)
- [ ] Implement confidence indicator display
- [ ] Test mobile responsiveness

---

## Testing Strategy

All items below are **manual verification** (no automated component tests in this frontend):

- [ ] Can type a question and see a formatted response
- [ ] Markdown formatting renders correctly in responses
- [ ] Provenance section expands/collapses correctly
- [ ] Charts render inline when `chart_spec` is present
- [ ] Suggestion chips trigger new questions (via `askQuestion()`)
- [ ] Feedback buttons toggle state on click
- [ ] Mobile layout works (single column, responsive input)
- [ ] Loading indicator shows during API call
- [ ] Error state shows retry button
- [ ] `make check` passes in frontend/ (linting/type checking still runs)

---

## Rollout Plan

1. **Development**: Local testing with backend Agent API (PRD 3) running
2. **Production**: Deploy alongside Agent API. No impact on existing pages.

---

## Open Questions

- [ ] Should message history persist in `localStorage` for session continuity? → Start without, add if users want it
- [ ] Should the chat be accessible from other pages (e.g., sidebar widget)? → Start as standalone page, evaluate later

---

## Files to Create/Modify

**New:**
- `frontend/app/composables/useAgentApi.ts` — API composable
- `frontend/app/types/agent.ts` — TypeScript interfaces
- `frontend/app/components/agent/AgentChat.vue` — Chat container
- `frontend/app/components/agent/AgentMessageBubble.vue` — Individual agent response bubble
- `frontend/app/components/agent/AgentSuggestionCard.vue` — Example question cards
- `frontend/app/pages/insights/ask.vue` — Chat page

**Modified:**
- `frontend/app/pages/insights.vue` — Add "Ask" tab to navigation
- `frontend/package.json` — Add `markdown-it` dependency

---

## References

- [ApexCharts Vue 3](https://apexcharts.com/docs/vue-charts/)
- [markdown-it](https://github.com/markdown-it/markdown-it)
- Depends on: PRD 3 (Agent API)
- Design follows existing Insights page patterns
