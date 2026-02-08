# PRD: Multi-step Agent Refinement

**Status**: Draft
**Author**: Claude
**Created**: 2026-02-07
**Updated**: 2026-02-07

---

## Overview

Upgrade the Agent API from single-shot question→answer to a multi-step refinement loop: plan → query → critique → revise. This improves answer quality by having the LLM self-evaluate results before responding, reducing "confident nonsense" outputs.

**Recommendation:** This PRD should be deferred until the single-shot Agent API (PRD 3) has been deployed and validated with real user queries. The refinement loop adds complexity (extra LLM calls, increased latency, critique prompt tuning) that is only justified once we know which failure modes actually occur in production. Deploy PRD 3 first, collect logs of bad answers, then implement this PRD targeting those specific failure modes.

## Problem Statement

Single-shot query planning can produce suboptimal results: wrong time range, missing filters, querying the wrong dataset, or returning data that doesn't actually answer the question. A refinement loop lets the agent self-correct before presenting the answer. For example, if the first query returns empty results because the time range was wrong, the critique step identifies this and triggers a revised query with a broader range.

## Goals

- Agent internally iterates up to N times (configurable, default 3) before responding
- Each iteration: generate/revise query plan → execute → critique results
- Critique checks: empty results, unexpected values, time range alignment, question coverage
- If critique passes, generate final response
- If max iterations reached, respond with best attempt + confidence indicator
- All iterations logged with structured logging for debugging

## Non-Goals

- User-facing multi-turn conversation (that's follow-up context, not refinement)
- Agent asking clarifying questions back to the user (Phase 2)
- Parallel query strategies (trying multiple datasets simultaneously)
- Changing the API contract (response format is backward-compatible)

---

## User Stories

1. **As a** user, **I want** the agent to self-correct when it gets a bad result, **so that** I get accurate answers more often
2. **As a** user, **I want** a confidence indicator on answers, **so that** I know how much to trust the result
3. **As a** developer, **I want** each refinement iteration logged, **so that** I can debug and improve the critique logic

---

## Proposed Solution

### High-Level Design

```
User question
    ↓
Iteration 1:
  ├─ LLM: Generate query plan (→ QuerySpec)
  ├─ Guardrails: validate_query_spec()
  ├─ DuckDB: execute_semantic_query()
  └─ LLM: Critique results
       ├─ PASS → Generate response → Return
       └─ FAIL (reason) → Iteration 2
    ↓
Iteration 2:
  ├─ LLM: Revise plan (given previous plan + critique)
  ├─ Guardrails: validate revised plan
  ├─ DuckDB: execute revised query
  └─ LLM: Critique results
       ├─ PASS → Generate response → Return
       └─ FAIL → Iteration 3 (or best response if max reached)
```

### Critique Module

**`backend/src/agent/critique.py`** (new file):

```python
from dataclasses import dataclass

@dataclass
class CritiqueResult:
    """Result of evaluating query results against the original question."""
    passed: bool
    reason: str | None = None
    suggested_changes: list[str] | None = None
```

`CritiqueResult` is defined **only** in `critique.py` — it is not duplicated in `models.py`.

**Critique function:**

```python
def evaluate_results(
    question: str,
    plan: QuerySpec,
    result: QueryResult,
    llm: LLMWrapper,
) -> CritiqueResult:
    """Evaluate query results against the original question using an LLM call."""
```

The critique is performed by an LLM call with a structured prompt that evaluates the results against the original question. The LLM returns a structured `CritiqueResult` via tool_use.

**Critique checks** (encoded in the LLM critique prompt):

| Check                | What it detects                                         | Action on failure                                 |
|----------------------|---------------------------------------------------------|---------------------------------------------------|
| Empty results        | Query returned no data                                  | Suggest broadening time range or changing dataset |
| Outlier detection    | Values 10x+ above/below recent averages                 | Flag for review, suggest additional context       |
| Time grain alignment | Question asks about "months" but query uses daily grain | Suggest changing granularity                      |
| Question coverage    | Result columns don't contain measures needed to answer  | Suggest different measures or dataset             |
| Row count sanity     | >1000 rows suggests missing aggregation                 | Suggest adding aggregation dimensions             |

### LLM Prompts

**Critique prompt** (added to `prompts.py`):

```
You are reviewing query results for a financial question. Evaluate:

1. Does the data answer the question? (coverage)
2. Are the results reasonable? (no nulls in key columns, sensible values, correct time range)
3. Is the aggregation level appropriate? (not too granular, not too aggregated)
4. Any obvious issues? (empty results, extreme outliers)

If issues found, respond with FAIL and explain what to change.
If results look good, respond with PASS.
```

**Revision prompt** (added to `prompts.py`):

```
Your previous query plan did not produce good results. Here's what happened:

Previous plan: {previous_plan}
Results summary: {results_summary}
Critique: {critique_reason}

Revise the query plan to address the critique. Consider:
- Broadening or narrowing the time range
- Using a different dataset that better answers the question
- Adding or removing dimensions
- Changing the aggregation level
```

### Confidence Scoring

Based on refinement loop outcome:

| Confidence   | Condition                                                 |
|--------------|-----------------------------------------------------------|
| `high`       | First attempt passed critique                             |
| `medium`     | Required 1-2 revisions but eventually passed              |
| `low`        | Max iterations reached, best attempt returned with caveat |

Confidence is included in `AgentResponse` and displayed in the frontend (PRD 4).

### Agent Service Changes

**`backend/src/agent/service.py`** — Refactor `ask()`:

```python
def ask(self, question: str, user_id: UUID) -> AgentResponse:
    """Ask a question with refinement loop.

    :param question: Natural language question.
    :param user_id: Authenticated user's UUID.
    :returns: Agent response with confidence indicator.
    """
    context = self.metadata_service.get_schema_context()
    best_result: QueryResult | None = None
    previous_plan: QuerySpec | None = None
    critique: CritiqueResult | None = None

    for i in range(self.max_iterations):
        # Generate or revise plan
        if i == 0:
            plan = self.llm.generate_query_plan(question, context)
        else:
            plan = self.llm.revise_query_plan(
                question, context, previous_plan, critique
            )

        # Validate and execute
        validate_query_spec(plan, dataset)
        result = execute_semantic_query(plan, user_id)

        logger.info(
            f"Agent iteration: iteration={i+1}, dataset={plan.dataset}, "
            f"measures={plan.measures}, result_rows={len(result.data)}"
        )

        # Critique
        critique = evaluate_results(question, plan, result, self.llm)

        logger.info(
            f"Agent critique: iteration={i+1}, "
            f"passed={critique.passed}, reason={critique.reason}"
        )

        if critique.passed:
            response = self.llm.generate_response(question, result)
            return self._build_response(
                response, result,
                confidence="high" if i == 0 else "medium",
                iterations=i + 1,
            )

        previous_plan = plan
        best_result = result

    # Max iterations — return best attempt
    response = self.llm.generate_response(question, best_result)
    return self._build_response(
        response, best_result,
        confidence="low",
        iterations=self.max_iterations,
    )
```

The function is **synchronous** (`def`, not `async def`), matching the codebase convention established in PRD 3. `user_id` is `UUID`, matching `current_user.id`.

### Data Model Changes

**`backend/src/agent/models.py`** — Add fields to `AgentResponse` (backward-compatible):

```python
class AgentResponse(BaseModel):
    # ... existing fields from PRD 3 ...
    answer: str
    provenance: QueryProvenance
    data: list[dict[str, Any]]
    chart_spec: ChartSpec | None = None
    suggestions: list[str]
    # New fields — additive, with defaults for backward compatibility
    confidence: Literal["high", "medium", "low"] = "high"
    iterations: int = 1
```

**Note:** `QuerySpec` is a `dataclass` defined in `backend/src/duckdb/semantic.py` (PRD 2). It is **not** redefined in the agent module — the agent imports it from `semantic.py`.

**`backend/src/agent/critique.py`** — `CritiqueResult` is defined here (see above). Not in `models.py`.

### Structured Logging

Each iteration is logged with structured fields for debugging:

```python
logger.info(
    f"Agent iteration: iteration={i+1}, dataset={plan.dataset}, "
    f"measures={plan.measures}, critique_passed={critique.passed}, "
    f"result_rows={len(result.data)}, duration_ms={duration_ms}"
)
```

This provides debuggability without requiring a separate observability service. If tracing is needed later, Langfuse or similar can be added as a wrapper without changing the core logic.

### Frontend Changes

**`frontend/app/components/agent/AgentMessageBubble.vue`** — Display confidence indicator:

- `high` → no indicator (default, clean)
- `medium` → subtle amber dot/badge: "Refined answer"
- `low` → subtle amber text: "Best attempt — results may be incomplete"

**Note:** The frontend TypeScript types (PRD 4) already include `confidence` and `iterations` fields with defaults, so no type changes are needed when this PRD is implemented.

### API Endpoints

No new endpoints. The existing `POST /api/agent/ask` returns the enhanced `AgentResponse` with `confidence` and `iterations` fields. Backward-compatible — new fields are additive with defaults.

---

## Technical Considerations

### Dependencies

- No new dependencies. Uses existing `anthropic` SDK (from PRD 3).

### Migration

No database migration. Changes are to in-memory agent logic only.

### Performance

- Each iteration adds ~2-4s (LLM call + DuckDB query + critique LLM call)
- Max 3 iterations = worst case ~12s total response time
- Most questions should pass on first iteration (~2-5s, same as before)
- The critique LLM call uses the same model as query planning (Claude Sonnet — fast)

### Security

- No change to security model. Refinement loop is internal to the agent.
- Rate limiting (PRD 3) still applies per request (not per iteration) — one user request = one rate limit count regardless of how many iterations it takes
- All queries still filtered by `user_id` via the semantic query builder

---

## Implementation Plan

### Phase 1: Critique Module

- [ ] Create `backend/src/agent/critique.py` with `CritiqueResult` dataclass and `evaluate_results()` function
- [ ] Add critique and revision prompt templates to `prompts.py`
- [ ] Add `revise_query_plan()` method to `llm.py`
- [ ] Write unit tests for critique logic with various scenarios (mock LLM)

### Phase 2: Refinement Loop

- [ ] Refactor `AgentService.ask()` to use iteration loop
- [ ] Add `confidence` and `iterations` fields to `AgentResponse`
- [ ] Configure max iterations via env var (`AGENT_MAX_ITERATIONS`, default 3)
- [ ] Add `AGENT_MAX_ITERATIONS` to `backend/.env_example`
- [ ] Write unit tests for refinement flow (mock LLM, test iteration logic)

### Phase 3: Logging and Frontend

- [ ] Add structured logging for each iteration
- [ ] Log: iteration number, dataset, measures, critique result, duration
- [ ] Update `AgentMessageBubble.vue` confidence indicator (already has the fields — just needs conditional rendering)

---

## Testing Strategy

- [ ] Unit tests for `evaluate_results()` — mock LLM to return PASS/FAIL for different scenarios
- [ ] Unit test: question requiring revision self-corrects (mock first query returns empty, critique says FAIL, revision succeeds)
- [ ] Unit test: max iterations caps at configured limit (mock all critiques as FAIL)
- [ ] Unit test: confidence levels correctly assigned based on iteration count
- [ ] Unit test: `QuerySpec` imported from `semantic.py` (not redefined)
- [ ] Integration test: end-to-end refinement with real DuckDB queries (mock LLM only)
- [ ] Performance: typical question still responds in <5s (passes on first attempt)
- [ ] `make check` passes in backend/ and frontend/

---

## Rollout Plan

1. **Development**: Local testing with mocked and real DuckDB queries
2. **Production**: Deploy with `AGENT_MAX_ITERATIONS=3`. Monitor logs to see how often refinement is triggered. If >50% of queries require refinement, the planner prompt needs improvement (not more iterations).

---

## Open Questions

- [ ] Should the critique use a cheaper/faster model than the planner? → Start with same model (Sonnet). If critique adds too much latency, switch to Haiku for critique only.
- [ ] Should we expose iteration details to the user beyond the confidence indicator? → Start with just confidence. Add "Show reasoning" toggle if users want transparency.
- [ ] What's the right max iteration count? → Default 3. Monitor in production — if most refinements succeed on attempt 2, consider lowering to 2.
- [ ] What failure modes from PRD 3 production usage should drive the critique prompt design? → Defer this question until PRD 3 is deployed and we have real failure data.

---

## Files to Create/Modify

**New:**

- `backend/src/agent/critique.py` — `CritiqueResult`, `evaluate_results()`

**Modified:**

- `backend/src/agent/service.py` — Refactor `ask()` with iteration loop
- `backend/src/agent/llm.py` — Add `revise_query_plan()` method
- `backend/src/agent/prompts.py` — Add critique and revision prompt templates
- `backend/src/agent/models.py` — Add `confidence`, `iterations` fields to `AgentResponse`
- `backend/.env_example` — Add `AGENT_MAX_ITERATIONS`
- `frontend/app/components/agent/AgentMessageBubble.vue` — Confidence indicator rendering
- `backend/testing/agent/test_critique.py` — Critique unit tests

---

## References

- [Anthropic structured output](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- Depends on: PRD 3 (Agent API)
- `QuerySpec` and `QueryResult` imported from: `backend/src/duckdb/semantic.py` (PRD 2)
