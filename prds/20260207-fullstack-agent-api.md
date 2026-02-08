# PRD: Agent API — Natural Language Financial Assistant

**Status**: Draft
**Author**: Claude
**Created**: 2026-02-07
**Updated**: 2026-02-07

---

## Overview

Natural language financial assistant that interprets user questions, generates structured query specs against the semantic layer (PRD 2), executes them via DuckDB, and returns formatted responses with full provenance. Uses a two-LLM-call pattern: query planning (structured output) then response generation (narrative). Includes a metadata service for LLM context and guardrails for query validation.

## Problem Statement

Users currently navigate pre-built analytics pages to find financial insights. For ad-hoc questions ("How much did I spend on eating out last quarter?", "What's my average monthly spending?"), they must know which page to visit and which filters to apply. A natural language interface removes this friction and makes the data more accessible.

## Goals

- `POST /api/agent/ask` endpoint accepting NL questions, returning answers with provenance
- Two-LLM-call pattern: query planning (Claude structured output) → response generation (narrative)
- Metadata service providing semantic schema context for LLM prompts (from dbt manifest)
- Guardrails: validate all query specs against known schema, rate limiting
- `GET /api/agent/suggestions` for example questions

## Non-Goals

- Multi-step agent refinement loop (PRD 5 — implement after single-shot is validated)
- Multi-turn conversation with context (defer until refinement is working)
- Conversation memory across sessions
- Agent modifying data or dbt models
- Streaming responses (Phase 2)
- Frontend chat UI (PRD 4 — developed in parallel)

---

## User Stories

1. **As a** user, **I want to** ask "How much did I spend last month?" in natural language, **so that** I get an instant answer without navigating analytics pages
2. **As a** user, **I want to** see what data was queried to produce the answer, **so that** I can trust the result
3. **As a** user, **I want** suggested questions, **so that** I know what kind of questions I can ask
4. **As a** developer, **I want** all agent queries validated against the semantic schema, **so that** the LLM can't generate invalid or dangerous queries

---

## Proposed Solution

### High-Level Design

```
User question
    ↓
POST /api/agent/ask
    ↓
MetadataService.get_schema_context() → semantic metadata from dbt manifest
    ↓
LLM Call 1: Query Planning (Claude tool_use → structured JSON)
  Input: question + semantic schema + sample questions + constraints
  Output: QuerySpec (dataset, measures, dimensions, filters, time_granularity)
    ↓
Guardrails: validate_query_spec() against semantic schema
    ↓
execute_semantic_query(spec) → DuckDB via semantic query builder (PRD 2)
    ↓
LLM Call 2: Response Generation
  Input: question + query results + provenance
  Output: natural language answer + optional chart spec
    ↓
AgentResponse { answer, provenance, data, chart_spec, suggestions }
```

### Metadata Service

**`backend/src/metadata/`** (new module):

- `service.py` — `MetadataService`:
  - `get_schema_context()` → calls `get_semantic_datasets()` from PRD 2, returns structured metadata (datasets, measures, dimensions, descriptions, sample questions)
  - `get_schema_summary()` → concise text summary for LLM system prompt (~2000 tokens). Iterates through datasets and formats measures/dimensions/descriptions compactly.
  - `get_suggestions()` → calls `get_all_sample_questions()` from PRD 2
  - No caching — the 11 datasets are small enough (~2000 tokens) that parsing the manifest on each call is negligible. If this changes, add caching later.

- `models.py` — Pydantic models:
  - `SchemaContext` — full semantic schema context for LLM (list of `DatasetSummary`)
  - `DatasetSummary` — dataset name, friendly name, description, measures (name + description), dimensions (name + description), sample questions

**Note:** No `search_relevant_datasets()` — with 11 datasets (~2000 tokens total), we send the full context to the LLM. The LLM picks the right dataset. This avoids keyword-matching heuristics that could miss the right dataset.

### Agent Module

**`backend/src/agent/`** (new module):

- `service.py` — `AgentService` orchestrating the full flow:
  - `ask(question: str, user_id: UUID) -> AgentResponse` — synchronous (matching existing codebase pattern)
  - Calls metadata service, LLM planner, guardrails (via `validate_query_spec` from PRD 2), semantic query builder, LLM responder
  - Returns structured response with provenance

- `llm.py` — Thin wrapper around `anthropic` SDK:
  - `generate_query_plan(question: str, schema_context: SchemaContext) -> QuerySpec` — uses Claude `tool_use` for structured output
  - `generate_response(question: str, results: QueryResult) -> ResponseOutput` — narrative text with optional chart spec and follow-up suggestions
  - Model: `claude-sonnet-4-5-20250929` (fast, good structured output)
  - The `anthropic` SDK does not ship type stubs. Use `# type: ignore[import-untyped]` on the import, or create a thin `py.typed` wrapper if mypy strictness is needed.

- `prompts.py` — System prompt templates:
  - **Query planner**: You are a financial data analyst. Given the user's question and available datasets with their measures and dimensions, generate a query spec. Only reference known datasets, measures, and dimensions. The system will automatically filter by user_id — do not include user_id as a filter.
  - **Response generator**: You are a personal finance assistant. Summarise the query results in plain English. Be concise. Cite the data source. Suggest 2-3 follow-up questions the user might find useful.

- `models.py` — Pydantic models:
  - `AgentResponse` — answer (str), provenance (`QueryProvenance` from PRD 2), data (list[dict]), chart_spec (ChartSpec | None), suggestions (list[str])
  - `ChartSpec` — see full definition below
  - `ResponseOutput` — intermediate model from LLM Call 2: answer (str), chart_spec (ChartSpec | None), suggestions (list[str])

- `guardrails.py` — Validation:
  - Delegates to `validate_query_spec()` from `semantic.py` (PRD 2) — measures/dimensions exist, operators valid
  - `handle_empty_results(question: str) -> str` — generates a graceful "I don't have data for that" message with suggestions
  - `enforce_rate_limit(user_id: UUID) -> None` — raises `RateLimitExceededError` if exceeded

**`ChartSpec` Pydantic model:**

```python
class ChartSeries(BaseModel):
    name: str
    data: list[float]
    labels: list[str] | None = None

class ChartSpec(BaseModel):
    type: Literal["bar", "line", "donut"]
    title: str
    x_axis: str         # Column name for X axis
    y_axis: str         # Column name for Y axis
    series: list[ChartSeries]
```

The LLM generates `ChartSpec` as part of response generation. The frontend (PRD 4) maps this to ApexCharts options. The LLM decides whether a chart is appropriate — if not, `chart_spec` is `None`.

### Rate Limiting

In-memory rate limiting using a simple dict with TTL:

```python
_rate_limit_store: dict[UUID, list[datetime]] = {}
RATE_LIMIT_MAX = int(os.environ.get("AGENT_RATE_LIMIT", "100"))  # requests per day

class RateLimitExceededError(Exception):
    """Raised when a user exceeds their daily agent request limit."""

def enforce_rate_limit(user_id: UUID) -> None:
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=1)
    requests = _rate_limit_store.get(user_id, [])
    requests = [r for r in requests if r > cutoff]  # Prune old entries
    if len(requests) >= RATE_LIMIT_MAX:
        raise RateLimitExceededError(f"Rate limit exceeded: {RATE_LIMIT_MAX} requests/day")
    requests.append(now)
    _rate_limit_store[user_id] = requests
```

This resets on process restart, which is acceptable for a single-user application. If multi-user scaling is needed later, move to Redis.

### API Endpoints

**`backend/src/api/agent/`** (new router):

| Method | Path                    | Description                              |
|--------|-------------------------|------------------------------------------|
| POST   | `/api/agent/ask`        | NL question → answer with provenance     |
| GET    | `/api/agent/suggestions`| Example questions from semantic metadata |

**Note:** `POST /api/agent/refine` (follow-up with context) is intentionally deferred. The single-shot pattern should be validated first. Multi-turn conversation adds significant complexity (conversation state management, context window budgeting) that isn't justified until we know single-shot works well.

**Request model** (`AskRequest`):

```python
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
```

**Response model** (`AgentResponse`):

```python
class AgentResponse(BaseModel):
    answer: str
    provenance: QueryProvenance  # From PRD 2's semantic.py — single source of truth
    data: list[dict[str, Any]]
    chart_spec: ChartSpec | None = None
    suggestions: list[str]
```

**Note:** `provenance` uses `QueryProvenance` directly from PRD 2 — there is no separate `Provenance` type. This avoids duplicating the type and ensures the agent endpoint returns exactly what the query builder produces.

**Endpoint implementations:**

```python
@router.post("/ask", response_model=AgentResponse, responses={**UNAUTHORIZED, **INTERNAL_ERROR})
def ask_question(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
) -> AgentResponse:
    """Ask a natural language financial question."""
    agent = AgentService()
    return agent.ask(request.question, current_user.id)  # user_id is UUID

@router.get("/suggestions", responses=UNAUTHORIZED)
def get_suggestions(
    current_user: User = Depends(get_current_user),
) -> dict[str, list[str]]:
    """Get example questions the agent can answer."""
    metadata = MetadataService()
    return {"suggestions": metadata.get_suggestions()}
```

Endpoints are **synchronous** (`def`, not `async def`) — this matches the existing codebase pattern. The `anthropic` SDK supports synchronous calls. FastAPI runs sync endpoints in a threadpool automatically.

### UI/UX

No frontend changes in this PRD. The frontend chat UI is covered in PRD 4.

---

## Technical Considerations

### Dependencies

- `anthropic` — Anthropic Python SDK for Claude API calls (new dependency). Add to `backend/pyproject.toml`.
- No other new dependencies. Uses existing DuckDB client and the semantic query builder from PRD 2.

### Migration

No database migration. All new code — new modules, new router.

### Performance

- LLM Call 1 (query planning): ~1-2s (Claude Sonnet with structured output)
- Semantic query execution: ~10-50ms (DuckDB + Parquet)
- LLM Call 2 (response generation): ~1-3s
- Total: ~2-5s for a typical question
- Rate limiting prevents runaway API costs

### Security

- All endpoints require authentication (JWT Bearer token)
- `user_id` from JWT (`current_user.id`, type `UUID`) is always injected into the semantic query — users can only query their own data
- `validate_query_spec()` rejects unknown measures/dimensions before any SQL is generated
- No raw SQL is generated by the LLM — the agent outputs a structured `QuerySpec`, and the query builder (PRD 2) translates it to safe parameterised SQL
- `ANTHROPIC_API_KEY` stored as environment variable, never logged
- Rate limiting prevents excessive API usage and cost

---

## Implementation Plan

### Phase 1: Metadata Service

- [ ] Create `backend/src/metadata/__init__.py`, `service.py`, `models.py`
- [ ] Implement `MetadataService` reading from `get_semantic_datasets()` (PRD 2)
- [ ] Implement `get_schema_summary()` for LLM prompt formatting
- [ ] Write unit tests for metadata service (mock `get_semantic_datasets()` return value)

### Phase 2: Agent Core

- [ ] Add `anthropic` to `backend/pyproject.toml`
- [ ] Create `backend/src/agent/__init__.py`, `service.py`, `llm.py`, `prompts.py`, `models.py`, `guardrails.py`
- [ ] Implement two-LLM-call flow in `AgentService.ask()`
- [ ] Implement rate limiting in `guardrails.py`
- [ ] Write unit tests with mocked LLM responses (mock `anthropic.Anthropic.messages.create`)
- [ ] Add `ANTHROPIC_API_KEY` to `backend/.env_example`
- [ ] Add `AGENT_RATE_LIMIT` to `backend/.env_example`

### Phase 3: API Endpoints

- [ ] Create `backend/src/api/agent/__init__.py`, `endpoints.py`
- [ ] Register agent router in `backend/src/api/app.py` with `prefix="/api/agent"`
- [ ] Implement `POST /api/agent/ask` and `GET /api/agent/suggestions`
- [ ] Write API endpoint tests (mock `AgentService.ask()` return value for endpoint tests, avoiding real LLM calls)

### Phase 4: Integration Testing

- [ ] End-to-end test: mock LLM to return a known `QuerySpec`, verify DuckDB returns correct data, verify `AgentResponse` has correct provenance
- [ ] Guardrails reject invalid queries (delegate to PRD 2's `validate_query_spec` tests)
- [ ] Rate limiting returns 429 after exceeding limit
- [ ] `make check` passes in backend/

### Testing Strategy

Mocking approach for tests:
- **Unit tests for `AgentService`**: Mock `anthropic.Anthropic` client at the class level. The `llm.py` wrapper returns typed dataclasses, so tests mock `llm.generate_query_plan()` and `llm.generate_response()` directly.
- **Unit tests for `MetadataService`**: Mock `get_semantic_datasets()` to return a fixture list of `SemanticDataset` objects.
- **API endpoint tests**: Mock `AgentService.ask()` to return a fixture `AgentResponse`. This tests routing, auth, and serialisation without LLM calls.
- **Integration tests**: Use real DuckDB with test Parquet files, but still mock the LLM. This tests the full flow from `QuerySpec` → SQL → DuckDB → results.

---

## Testing Strategy

- [ ] Unit tests for `MetadataService` (mock `get_semantic_datasets()`)
- [ ] Unit tests for `AgentService` (mock LLM wrapper methods, not the SDK directly)
- [ ] Unit tests for guardrails (rate limiting, empty result handling)
- [ ] API endpoint tests for both routes (mock `AgentService`)
- [ ] Integration test: `POST /api/agent/ask {"question": "How much did I spend last month?"}` returns correct total (mock LLM, real DuckDB)
- [ ] Provenance shows: dataset used, measures queried, filters applied, row count
- [ ] Invalid questions get graceful "I don't have data for that" response
- [ ] Rate limit exceeded returns HTTP 429
- [ ] `make check` passes in backend/

---

## Rollout Plan

1. **Development**: Local testing with DuckDB + Parquet (PRD 1) and semantic layer (PRD 2) in place
2. **Production**: Deploy behind feature flag initially. Enable once verified with real data.

---

## Open Questions

- [ ] Should the agent support multi-dataset queries (joining data from multiple datasets)? → Start with single-dataset queries. Multi-dataset can be added later.
- [ ] Should chart specs use a standard like Vega-Lite, or a custom format? → Custom format mapped to ApexCharts options in the frontend (PRD 4). Simpler, and we control the chart library.
- [ ] Should `anthropic` type stubs be added via a stub package? → Start with `# type: ignore[import-untyped]`. Create a thin typed wrapper in `llm.py` that isolates the untyped boundary.

---

## Files to Create/Modify

**New:**
- `backend/src/metadata/__init__.py` — Exports `MetadataService`
- `backend/src/metadata/service.py` — `MetadataService` class
- `backend/src/metadata/models.py` — `SchemaContext`, `DatasetSummary`
- `backend/src/agent/__init__.py` — Exports `AgentService`
- `backend/src/agent/service.py` — `AgentService` orchestration
- `backend/src/agent/llm.py` — Anthropic SDK wrapper
- `backend/src/agent/prompts.py` — System prompt templates
- `backend/src/agent/models.py` — `AgentResponse`, `ChartSpec`, `ChartSeries`, `ResponseOutput`, `RateLimitExceededError`
- `backend/src/agent/guardrails.py` — Rate limiting, empty result handling
- `backend/src/api/agent/__init__.py` — Exports router
- `backend/src/api/agent/endpoints.py` — Route handlers
- `backend/testing/agent/` — Unit tests
- `backend/testing/metadata/` — Unit tests

**Modified:**
- `backend/src/api/app.py` — Register agent router
- `backend/pyproject.toml` — Add `anthropic` dependency
- `backend/.env_example` — Add `ANTHROPIC_API_KEY`, `AGENT_RATE_LIMIT`

---

## References

- [Anthropic Python SDK — tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- Semantic query builder: `backend/src/duckdb/semantic.py` (PRD 2)
- Depends on: PRD 2 (Semantic Layer)
- Depended on by: PRD 4 (Frontend Chat UI), PRD 5 (Refinement)
