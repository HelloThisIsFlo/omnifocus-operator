# Milestone v1.4 — Response Shaping & Batch Processing

**Generated:** 2026-04-17
**Status:** ✅ Shipped (tagged `v1.4`, archived)
**Purpose:** Team onboarding and project review — read this to understand what v1.4 delivered, why, and how.

---

## 1. Project Overview

**OmniFocus Operator** is a Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Reads via SQLite cache (~46ms), writes via OmniJS bridge, with 11 MCP tools across read, list/filter, and write.

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

**What v1.4 did in one line:** Agents now get clean, projectable responses (defaults + opt-in field groups), genuine inherited-field semantics, note editing with append/replace, and batch writes up to 50 items — without the noise of null/empty/false fields or OmniFocus self-echoes.

**Where this sits in the roadmap:**

- v1.0–v1.3.3 shipped ✅ — foundation, SQLite caching, writes, read-tool filtering, first-class references, date filtering, ordering
- **v1.4 shipped** ✅ (this milestone) — response shaping, true inheritance, batch writes, notes graduation
- v1.5 planning 🔧 — UI & Perspectives (perspective switching, deep links)
- v1.6 planned — production hardening (retry, crash recovery, serial execution)
- v1.7 planned — project writes (add/edit projects)

---

## 2. Architecture & Technical Decisions

v1.4 did **not** change the three-layer architecture (MCP server → Service → Repository). Instead, it sharpened the **boundary** between service and server: service returns full Pydantic models; server owns all response shaping (stripping, projection, field selection). Write-tool results are also shaped by the server — but separately from entities.

Key architectural moves:

- **`server.py` → `server/` package** — new sub-modules: `__init__.py` (`create_server`), `handlers.py` (11 tool handlers), `lifespan.py` (context manager), `projection.py` (stripping + field selection).
- **Field group definitions centralized in `config.py`** — `TASK_DEFAULT_FIELDS`, `PROJECT_DEFAULT_FIELDS`, `TASK_FIELD_GROUPS`, `PROJECT_FIELD_GROUPS`. Pure data; consumed by `server/projection.py`. AST enforcement test verifies bidirectional sync (every model field in exactly one group, every group field exists on the model).
- **Projection is post-filter, pre-serialization** — `shape_list_response` receives already-filtered `ListResult[Task]`, serializes via `model_dump(by_alias=True)`, then strips and projects. Service never sees the projection concern.
- **Inherited fields are task-only** — moved from `ActionableEntity` (base class) to `Task` (leaf), making inherited fields on projects structurally impossible rather than merely empty.
- **Batch is a handler concern, not a service concern** — service pipelines (`_AddTaskPipeline`, `_EditTaskPipeline`) are unchanged. Handlers loop over items with per-tool failure semantics. Zero service surgery.
- **Actions pattern extended** — `NoteAction` joins `TagAction` and `MoveAction` in the actions block on `edit_tasks`. Same file (`contracts/shared/actions.py`), same `@model_validator` shape, same constant-family naming.

### Key Implementation Decisions

| Decision | Why | Phase |
|----------|-----|-------|
| Universal stripping via `_is_strip_value` helper | `frozenset` can't contain `list` (unhashable). Pure `isinstance` check before frozenset lookup. `projection.py` stays a pure dict-transform on `model_dump(by_alias=True)` output. | 53 |
| `include` + `only` → warning with `only` winning (not error) | Error wastes a round trip (agent retries with nothing). Warning teaches equally well but still returns data. Consistent with `["all", "available"]` availability warning. | 53 |
| Walk ancestry in `DomainLogic`, not repository | Self-echo stripping needs the **real parent chain**, not OmniFocus's `effectiveX`. Uses `self._repo.get_all()` (cached), builds `task_map` + `project_map`, walks `parent.task.id` chain and finally the containing project. | 53.1 |
| `ancestor_vals` dict, per-field strategy constants | Tracks actual computed values (dates/bools), not presence booleans. Strategy constants as frozensets (`_MIN_FIELDS`, `_MAX_FIELDS`, `_FIRST_FOUND_FIELDS`) give O(1) dispatch. Matches OmniFocus empirical behavior per `omnifocus-inheritance-semantics` deep-dive. | 53.1 |
| Flat result model with `status: Literal` (not discriminated union) | Discriminated unions are for **inbound** models where Pydantic routes ambiguous input (DateFilter, Frequency). Batch results are **outbound** and system-constructed; flat models give agents a clean enum without `oneOf` indirection. Construction discipline enforced by tests. | 54 |
| Whole-batch Pydantic validation, per-item service errors | Schema errors = malformed input, reject the whole batch. Service errors (not found, ambiguous name) = legitimate per-item failures. Clean conceptual boundary. `ValidationReformatterMiddleware` already formats `Task N:` prefixes. | 54 |
| `NoteAction` mirrors `TagAction` exactly | Same file, same `@model_validator(mode="after")` shape (exclusivity + required), same constant-family style. Pattern composability → zero design risk → 3 plans. | 55 |
| Composition in `DomainLogic.process_note_action`, bridge unchanged | Service composes the final note string (append = concat with `\n` separator, replace = set or clear). Bridge still receives `note: string | null` as a setter. No golden master recapture needed. | 55 |
| `\n` separator on append (revised from `\n\n` during UAT) | Minimal-useful-separator principle — agents can prepend their own `\n` to compose `\n\n` (paragraph break); `\n\n` default couldn't be reduced. OmniFocus renders `\n` as visible soft break. | 55 |
| Batch result stripping via dedicated `strip_batch_results` | Batch items are flat dicts, not full entities. Separate helper from `strip_entity`; `status` Literal always preserved (never matches STRIP_VALUES). Caught during audit; promoted to STRIP-04 + BATCH-10. | Quick 260417-oiw |

---

## 3. Phases Delivered

| # | Phase | Status | One-liner |
|---|-------|--------|-----------|
| 53 | Response Shaping | ✅ Complete (2026-04-14) | Universal stripping, `effective*` → `inherited*` rename, `include`/`only` field selection, count-only via `limit: 0`, `server/` package split. |
| 53.1 | True Inherited Fields (**INSERTED**) | ✅ Complete (2026-04-15) | Genuine ancestor-chain walk with per-field aggregation (min/max/first-found/any-True). Projects lose inherited fields via model surgery. |
| 54 | Batch Processing | ✅ Complete (2026-04-16) | `add_tasks` best-effort + `edit_tasks` fail-fast, up to 50 items, flat result array with `status: "success" \| "error" \| "skipped"`. |
| 55 | Notes Graduation | ✅ Complete (2026-04-16) | `actions.note.append`/`actions.note.replace` on `edit_tasks` with 3 no-op warnings; top-level `note` removed from edit input. |

Plus **Quick Task 260417-oiw** (same-day during audit): batch result stripping asymmetry — `strip_batch_results` helper added in `server/projection.py`, wired to both batch handlers. Promoted to STRIP-04 + BATCH-10 as first-class requirements.

**Execution order:** 53 → 53.1 (inserted after 53 UAT revealed self-echo problem) → 54 → 55.

---

## 4. Requirements Coverage

**41 / 41 satisfied** — audit closed with zero gaps, zero unsatisfied, zero orphaned.

### Response Stripping (4)
- ✅ **STRIP-01** — Strip `null`, `[]`, `""`, `false`, `"none"` from entity fields
- ✅ **STRIP-02** — `availability` is never stripped
- ✅ **STRIP-03** — Envelope fields (`hasMore`, `total`, `status`) are never stripped
- ✅ **STRIP-04** — Batch result items (`AddTaskResult`, `EditTaskResult`) stripped with same rules; `status` always preserved

### Inherited Rename (1)
- ✅ **RENAME-01** — `effective*` → `inherited*` across all 6 field pairs

### Field Selection (13)
- ✅ **FSEL-01 … FSEL-13** — `include`/`only` on list tools, groups defined in `config.py`, projection is a server-only concern, get-tools return full stripped entities

### True Inheritance (10)
- ✅ **INHERIT-01** — `inherited*` only appears when truly inherited; self-echoes stripped
- ✅ **INHERIT-02** — Projects never have `inherited*` fields
- ✅ **INHERIT-03** — Walk covers all 6 pairs (flagged, dueDate, deferDate, plannedDate, dropDate, completionDate)
- ✅ **INHERIT-04** — Walk applies to `get_all`, `get_task`, `list_tasks`
- ✅ **INHERIT-05 … INHERIT-10** — Per-field aggregation: min (due), max (defer), first-found (planned/drop/completion), any-True (flagged)

### Count-Only (1)
- ✅ **COUNT-01** — `limit: 0` returns `{items: [], total: N, hasMore: total > 0}`

### Batch Processing (10)
- ✅ **BATCH-01 … BATCH-09** — 1–50 items, best-effort (add) + fail-fast (edit), flat result array, serial order, same-task edits allowed, cross-item refs unsupported (documented)
- ✅ **BATCH-10** — Batch tools advertise a loose `array of object` outputSchema; clients infer item shape from BATCH-04/05/06

### Notes Graduation (5)
- ✅ **NOTE-01** — Top-level `note` removed from `edit_tasks` input schema
- ✅ **NOTE-02** — `append` adds with `\n` separator; `""` or whitespace-only is N1 no-op with `NOTE_APPEND_EMPTY` warning *(revised from `\n\n` during UAT)*
- ✅ **NOTE-03** — `replace` sets/clears; identical content is N2 no-op
- ✅ **NOTE-04** — Append on empty/whitespace-only note sets directly (no leading separator)
- ✅ **NOTE-05** — `add_tasks` retains top-level `note` for initial content

### Audit verdict
> Milestone **PASSED** — 41/41 requirements, 4/4 phases, 30/30 integration paths, 6/6 E2E flows, 1/1 quick tasks. Zero unsatisfied, zero orphaned. Ready to archive.

---

## 5. Key Decisions Log

Beyond the architectural decisions in §2, here are the finer-grained decisions that shaped v1.4:

| ID | Decision | Phase | Rationale |
|----|----------|-------|-----------|
| D-01 (53) | Full Python rename `effective_*` → `inherited_*` at model level | 53 | Pre-release, no compat — mechanical find-and-replace beats alias tricks. `to_camel` generator produces `inheritedDueDate` automatically. |
| D-03 (53) | Entity-level stripping; write results not stripped in Phase 53 | 53 | Result envelopes (`AddTaskResult`, `EditTaskResult`) aren't entities — original scope. *Reopened by quick-260417-oiw audit.* |
| D-04 (53) | Separate `TaskFieldGroup` / `ProjectFieldGroup` Literals | 53 | Projects additionally support `"review"`. Two separate fields at the contract, but shared `INCLUDE_FIELD_DESC` constant. |
| D-09 (53) | Explicit per-handler shaping, not middleware | 53 | Different tools clearly apply different transforms (get/list/batch/get_all). 3-4 lines per handler beats generic middleware with conditionals. |
| D-01 (53.1) | Walk includes the containing project as final ancestor | 53.1 | Projects **can** have dates/flags that tasks inherit. Stopping at the project boundary would incorrectly strip inherited fields on tasks under flagged/dated projects. |
| D-02 (53.1) | Keep `inherited_flagged` as `bool`; date fields as `None` on self-echo | 53.1 | OmniFocus flagging is OR (any-True) — no meaningful "ancestor explicitly set False" case. D-03 server stripping removes `None`/`False` from output. |
| D-01 (54) | Whole-batch Pydantic validation; per-item service errors | 54 | Schema errors = fix-and-retry. Service errors = partial success. `ValidationReformatterMiddleware` handles the whole-batch rejection path automatically. |
| D-02 (54) | `AddTaskResult` and `EditTaskResult` stay as separate models (same shape) | 54 | Precedent in codebase — per-use-case result models. No reason to merge just because fields happen to align. |
| D-04 (54) | Skip message references failing index ("Skipped: task 2 failed") | 54 | Direct pointer to root cause — one variable (`failed_idx`), zero complexity. |
| D-13 (55) | `process_note_action` in `DomainLogic` (returns `(note_value, should_skip, warnings)`) | 55 | Parallels `process_lifecycle`. Called by `_EditTaskPipeline` before `PayloadBuilder`. Bridge unchanged — service composes the final string. |
| D-14 (55) | Remove unreachable `command.note is None` branch from `normalize_clear_intents` | 55 | Dead code removal — after NOTE-01 the branch is unreachable. Keeps the domain layer honest. |

**UAT-driven revisions (Phase 55):**

- NOTE-02 separator tightened from `\n\n` to `\n` (commit 0cb60e58). Rationale: agent-controllability. Agents can prepend their own `\n` to compose `\n\n`; the reverse isn't possible.
- NOTE-02 no-op scope broadened: whitespace-only append is now N1 no-op (commit c9ad1329). OmniFocus normalizes whitespace-only writes to empty and trims trailing whitespace — the operation was silently no-op'd upstream, giving agents no feedback. Now treated as N1 with `NOTE_APPEND_EMPTY` warning.

---

## 6. Tech Debt & Deferred Items

### Open
1. **Pre-existing `TODO(Phase 30)` in `server/handlers.py:15`** — no FastMCP equivalent identified; unrelated to v1.4 work; carried over from v1.2.2 migration. Low priority.
2. **MCP progress-notification upstream regression** — Claude Code CLI 2.1.105+ rejects echoed `progressToken` and tears down stdio after N strikes. Root-caused on 2026-04-17 (upstream issues #47378 open / #47765 closed as dup). Server-side mitigation: `PROGRESS_NOTIFICATIONS_ENABLED=False` in `src/omnifocus_operator/config.py`. Re-enable procedure documented in the same file. Reproducer + evidence: `.research/deep-dives/bugfix-progress-handler-stdio-disconnect/`.

### Resolved during audit (not tech debt)
- 32 stale `[ ] Pending` → `[x] Complete` checkboxes in REQUIREMENTS.md (commit 7486a93c)
- 4 missing `requirements-completed` SUMMARY frontmatter tags (commit 7486a93c)
- NOTE-02 VERIFICATION.md drift rewritten to match post-UAT revised behavior (commit 7486a93c)
- Batch result stripping asymmetry closed via Quick 260417-oiw (commits 85bab2f5 + adecc261 + e645c61b)

### Deferred (by design)
- **Cross-batch concurrency serialization** — documented as known limitation; v1.6 concern.
- **Hierarchy creation within a single batch** — batch items cannot reference siblings; documented in `_BATCH_CROSS_ITEM_NOTE`.
- **Return full task object in `edit_tasks` response** — intentionally unmapped, awaiting real-world usage data. Write-through makes follow-up `get_task` fast enough.
- **Rich text / note templates** — out of scope for v1.4; no spec demand.

### Lessons forward (from RETROSPECTIVE)
- **Audit as quality gate works** — found STRIP-04, NOTE-02 drift, and 32 stale checkboxes in one day. Formalized audit step is worth it.
- **Quick tasks beat scope creep** — batch stripping asymmetry captured, shipped in 2 commits, promoted to requirements rather than derailing close.
- **Empirical research prevents silent wrong behavior** — `omnifocus-inheritance-semantics` deep-dive saved `_walk_one` from shipping wrong aggregation (e.g., `max` for due dates instead of `min`).
- **SUMMARY `one_liner` quality matters at archival** — gsd-tools extracted code-review lint notes as "accomplishments" at archival, forcing manual MILESTONES.md rewrite. 30 seconds per plan during execution saves 20 minutes at archival.
- **Known-unresolved bugs need explicit acknowledgment, not threshold tweaks** — C-3 (progress-notification disconnect) had a mitigation since v1.2.2 but was never root-caused. Making it explicit in the audit forced a principled fix.

---

## 7. Getting Started

### Run the project

```sh
# Claude Desktop (no install)
# ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "omnifocus-operator": {
      "command": "uvx",
      "args": ["omnifocus-operator"]
    }
  }
}

# Development install
git clone https://github.com/HelloThisIsFlo/omnifocus-operator.git
cd omnifocus-operator
uv sync
uv run pytest           # 2,167 tests (+ 26 Vitest for the bridge)
uv run pytest tests/test_output_schema.py -x -q   # Output-schema regression guard
```

### Where to look first (v1.4 reading order)

| Question | Start here |
|----------|-----------|
| **How does a read tool flow end-to-end?** | `src/omnifocus_operator/server/handlers.py` → `server/projection.py` (shape) → `service/service.py` (`_ListTasksPipeline`) → `repository/hybrid/hybrid.py` (SQL). |
| **How does stripping work?** | `server/projection.py` — `strip_entity`, `strip_all_entities`, `resolve_fields`, `shape_list_response`, `shape_list_response_strip_only`, `strip_batch_results`. |
| **Where are field groups defined?** | `src/omnifocus_operator/config.py` — `TASK_DEFAULT_FIELDS`, `PROJECT_DEFAULT_FIELDS`, `TASK_FIELD_GROUPS`, `PROJECT_FIELD_GROUPS`, `MAX_BATCH_SIZE`. Enforcement tests in `tests/test_projection.py::TestFieldGroupSync`. |
| **How does true inheritance work?** | `src/omnifocus_operator/service/domain.py` — `DomainLogic.compute_true_inheritance` (~line 203), `_walk_one` (~line 220), `_INHERITED_FIELD_PAIRS` (~line 104). |
| **How does the batch loop work?** | `src/omnifocus_operator/server/handlers.py` — `add_tasks` (best-effort try/except around `service.add_task`), `edit_tasks` (fail-fast with `failed_idx`). Tests: `tests/test_server.py::TestAddTasksBatch` and `TestEditTasksBatch` (26 tests). |
| **How does note editing compose?** | `src/omnifocus_operator/service/domain.py::process_note_action` (~line 531). Decision tree: UNSET → skip; `append` → N1/direct-set/concat; `replace` → N3/N2/set-or-clear. `NoteAction` contract: `contracts/shared/actions.py:71`. |
| **Where are the agent-facing strings?** | `src/omnifocus_operator/agent_messages/descriptions.py` (tool/field/class docs, AST-enforced), `agent_messages/errors.py` (hard errors), `agent_messages/warnings.py` (educational no-op guidance). |
| **How does the `server/` package compose?** | `server/__init__.py` exports `create_server`; wires `handlers.py` + `lifespan.py`. `projection.py` is pure functions imported by handlers. |

### Safety boundaries (always relevant)

- **SAFE-01/02**: Automated tests never touch `RealBridge`. Use `InMemoryBridge` or `SimulatorBridge`. The `uat/` directory is excluded from pytest and CI.
- **GOLD-01**: Any phase that modifies bridge operations must recapture the golden master (`uat/capture_golden_master.py`) — human-only step. v1.4 did not touch the bridge, so no recapture was required.

### Running MCP tool calls locally

```sh
# Tool descriptions, field docs, and schemas come from:
uv run python -c "from omnifocus_operator.agent_messages.descriptions import LIST_TASKS_TOOL_DOC; print(LIST_TASKS_TOOL_DOC)"

# Validate all serialized tool output against MCP outputSchema:
uv run pytest tests/test_output_schema.py -x -q
```

---

## Stats

| Metric | Value |
|--------|-------|
| **Timeline** | 2026-04-12 → 2026-04-17 (6 days from v1.3.3 tag to v1.4 tag) |
| **Phases** | 4 complete (53, 53.1 inserted, 54, 55) |
| **Plans** | 15 executed |
| **Commits** | 187 (v1.3.3..v1.4) |
| **Files changed** | 180 (+28,202 / -1,798 lines) |
| **Contributors** | Flo Kempenich |
| **Tests at close** | 2,193 (2,167 pytest + 26 Vitest), ~97% coverage |
| **Requirements** | 41 / 41 satisfied (0 unsatisfied, 0 orphaned) |
| **Tech debt incurred** | 0 new items (2 carry-over / upstream dependency) |
| **Quick tasks** | 1 (260417-oiw — batch result stripping; promoted to STRIP-04 + BATCH-10) |

---

*Generated from: `.planning/milestones/v1.4-ROADMAP.md`, `v1.4-REQUIREMENTS.md`, `v1.4-MILESTONE-AUDIT.md`, `.planning/PROJECT.md`, `.planning/RETROSPECTIVE.md`, `.planning/phases/53-response-shaping/`, `53.1-true-inherited-fields/`, `54-batch-processing/`, `55-notes-graduation/`.*
