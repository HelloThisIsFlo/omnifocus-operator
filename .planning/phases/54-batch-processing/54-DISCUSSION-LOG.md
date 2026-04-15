# Phase 54: Batch Processing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 54-batch-processing
**Areas discussed:** Validation boundary, Response model design, Error detail & indexing, Tool description strategy

---

## Validation Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Whole-batch (Recommended) | Schema validation rejects the whole request. Service-layer errors are per-item. Clean boundary: malformed input vs legitimate failures. | ✓ |
| Per-item schema validation | Validate each item individually in handler loop. Requires list[dict] + manual model_validate(). Loses typed params. | |

**User's choice:** Whole-batch (Recommended)
**Notes:** Clean conceptual boundary agreed upon immediately. No debate.

---

## Response Model Design

| Option | Description | Selected |
|--------|-------------|----------|
| Flat model (Recommended) | Single model per tool with status Literal, optional fields. Consistent with outbound model patterns. | ✓ |
| Discriminated union | Separate SuccessResult, ErrorResult, SkippedResult per tool. Type-enforced but adds schema complexity. | |

**User's choice:** Flat model (Recommended)
**Notes:** Aligned with model taxonomy principle — discriminated unions are for inbound routing, not outbound construction.

---

## Error Detail & Indexing

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit prefix (Recommended) | "Task 3: Invalid tag 'Foo'" — self-documenting, consistent with middleware pattern. | ✓ |
| Implicit (array position) | No prefix, rely on array index alignment. | |

**User's choice:** Explicit "Task N:" prefix
**Notes:** Consistent with `_format_validation_errors` in middleware. Catch ToolError + ValueError per-item; unexpected exceptions kill the batch.

### Sub-question: Fail-fast skip message

| Option | Description | Selected |
|--------|-------------|----------|
| Reference failing item | "Skipped: task 2 failed" — direct pointer to root cause. | ✓ |
| Generic message | "Skipped due to earlier failure" — simpler but less actionable. | |
| You decide | Claude's discretion. | |

**User's choice:** Reference failing item
**Notes:** User initially wanted to see concrete examples of both options before deciding. After seeing JSON output examples, chose reference failing item. Added fallback note: if implementation proves complex, generic is acceptable — but it's trivial (one variable).

---

## Tool Description Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Inline per tool (Recommended) | Each tool has its own batch section. Shared bits duplicated. | |
| Mixed: shared fragments + inline differences | Small shared parameterized fragments for identical parts, inline for tool-specific semantics. | ✓ |
| You decide | Claude's discretion. | |

**User's choice:** Mixed with parameterized fragments
**Notes:** User specified that fragments should use template parameters (like f-strings with placeholders), not just static text. Shared structural framing with `{failure_mode}` etc. injected per tool. Avoids one-word fragments that aren't worth the indirection.

---

## Claude's Discretion

- Exact fragment decomposition (how many, naming, parameters)
- `MAX_BATCH_SIZE` enforcement mechanism (max_length vs model_validator)
- Test organization for batch scenarios
- Whether AddTaskResult/EditTaskResult merge into shared BatchItemResult or stay separate
- Exact wording of description fragments and inline prose

## Deferred Ideas

None — discussion stayed within phase scope.
