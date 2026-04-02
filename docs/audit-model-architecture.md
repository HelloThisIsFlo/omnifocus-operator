# Model Architecture Audit: "Core Model + Sidecar" Simplification

*Audit date: 2026-04-02*

## Context

This audit evaluates whether the current multi-model-per-layer architecture could be simplified to a "core model + repo payload sidecar" approach -- one well-validated core model per use case, with a small sidecar for the few fields that differ at the repository boundary (resolved IDs, computed diffs, ISO strings).

The audit examines the full model inventory, traces actual transformations at each boundary, and evaluates the proposed simplification against the codebase's architectural principles (structure-over-discipline, model-taxonomy, service boundary principle).

---

## Current State Inventory

**Total: 60 model classes** across `models/` (23) and `contracts/` (37).

### Per-Use-Case Model Counts

| Use Case | Agent Input | Repo Input | Agent Output | Repo Output | Total |
|----------|------------|------------|-------------|-------------|-------|
| add_task | `AddTaskCommand` | `AddTaskRepoPayload` | `AddTaskResult` | `AddTaskRepoResult` | 4 |
| edit_task | `EditTaskCommand` + `EditTaskActions` | `EditTaskRepoPayload` + `MoveToRepoPayload` | `EditTaskResult` | `EditTaskRepoResult` | 6 |
| list_tasks | `ListTasksQuery` | `ListTasksRepoQuery` | `ListResult[Task]` | `ListRepoResult[Task]` | 4 (2 generic) |
| list_tags | `ListTagsQuery` | `ListTagsRepoQuery` | (shared generic) | (shared generic) | 2 |
| list_folders | `ListFoldersQuery` | `ListFoldersRepoQuery` | (shared generic) | (shared generic) | 2 |

### Repetition Rule Family: 12 Classes

| Layer | Classes |
|-------|---------|
| Core read (`models/`) | `RepetitionRule`, `Frequency`, `OrdinalWeekday`, `EndByDate`, `EndByOccurrences` |
| Add spec (`contracts/`) | `RepetitionRuleAddSpec`, `FrequencyAddSpec`, `OrdinalWeekdaySpec` |
| Edit spec (`contracts/`) | `RepetitionRuleEditSpec`, `FrequencyEditSpec` |
| Repo payload (`contracts/`) | `RepetitionRuleRepoPayload` |

---

## Field Duplication Analysis

### AddTaskCommand vs AddTaskRepoPayload (strongest unification case)

| Field | Command Type | RepoPayload Type | Transformation |
|-------|-------------|------------------|----------------|
| `name` | `str` | `str` | None |
| `parent` | `str \| None` | `str \| None` | None |
| `tags` / `tag_ids` | `list[str]` (names) | `list[str]` (IDs) | Name-to-ID resolution |
| `due_date` | `AwareDatetime` | `str` | `.isoformat()` |
| `defer_date` | `AwareDatetime` | `str` | `.isoformat()` |
| `planned_date` | `AwareDatetime` | `str` | `.isoformat()` |
| `flagged` | `bool` | `bool` | None |
| `estimated_minutes` | `float \| None` | `float \| None` | None |
| `note` | `str \| None` | `str \| None` | None |
| `repetition_rule` | `RepetitionRuleAddSpec` | `RepetitionRuleRepoPayload` | Full structural reshape |

**6 of 10 fields identical (60%).** 4 differ: name-to-ID resolution, datetime-to-string, repetition rule structural transformation.

### ListTasksQuery vs ListTasksRepoQuery

**7 of 9 fields identical (78%).** Only `project`/`project_ids` and `tags`/`tag_ids` differ.

### ListTagsQuery vs ListTagsRepoQuery / ListFoldersQuery vs ListFoldersRepoQuery

**100% identical fields.** Split exists purely for the Service Boundary Principle.

### Result vs RepoResult

Always differ by 1-2 fields (`success`, `warnings`).

---

## Concrete Sidecar Approach

```python
# Unified model (replaces AddTaskCommand + AddTaskRepoPayload)
class TaskInput(StrictModel):
    name: str = Field(min_length=1, description=NAME_ADD_COMMAND)
    parent: str | None = None
    tags: list[str] | None = None
    due_date: AwareDatetime | None = None
    # ... all fields ...

# Sidecar for resolved repo data
class TaskRepoSidecar(OmniFocusBaseModel):
    tag_ids: list[str] | None = None
    due_date_iso: str | None = None
    defer_date_iso: str | None = None
    planned_date_iso: str | None = None
    repetition_rule_resolved: RepetitionRuleRepoPayload | None = None
```

Repository signature: `add_task(input: TaskInput, sidecar: TaskRepoSidecar)`

**For edit_task:** The sidecar needs computed tag diff, resolved move payload, lifecycle action, resolved repetition rule, plus flattened Patch fields. It becomes essentially `EditTaskRepoPayload` with a different name -- no simplification.

---

## What You'd Gain

| Savings | Classes | Lines |
|---------|---------|-------|
| Merge `AddTaskRepoPayload` into core | 1 | ~15 |
| Merge `AddTaskRepoResult` into `AddTaskResult` | 1 | ~5 |
| Merge `ListTagsRepoQuery` (100% identical) | 1 | ~5 |
| Merge `ListFoldersRepoQuery` (100% identical) | 1 | ~5 |
| Simplify `PayloadBuilder.build_add()` | 0 | ~25 |
| **Total** | **~4 classes** | **~50 lines** |

**7% reduction** in class count (4 of 60). Does NOT reduce: repetition rule family (12 classes), edit pipeline, or list-tasks/list-projects splits.

---

## What You'd Lose

### 1. Type Safety at the Repository Boundary

`AddTaskRepoPayload` guarantees all tag names are resolved, dates are ISO strings, repetition rules are bridge-ready. With a sidecar, the repository must trust the caller; reading `input.due_date` (AwareDatetime) instead of `sidecar.due_date_iso` (string) becomes the path of least resistance.

### 2. The `extra="forbid"` Tension (Irreconcilable)

Commands need `extra="forbid"` (reject agent typos). Read models need permissive mode (handle bridge JSON). Pydantic's `model_config` is class-level -- cannot have both on one class.

### 3. Patch Semantics Cannot Be Unified

Edit uses `Patch[T]`/`PatchOrClear[T]` with UNSET (three states: omitted/null/value). Read models need `name: str` (always present). Edit needs `name: Patch[str]` (possibly UNSET). Incompatible on one class.

### 4. Schema Generation Quality

Commands generate agent-facing JSON Schema with descriptions, examples, constraints. RepoPayloads are internal. Unifying means either bridge sees unnecessary metadata or agents lose helpful descriptions.

### 5. Service Boundary Principle Violation

Documented principle: "agent-facing and repo-facing ALWAYS separate types." Merging makes future divergence a structural refactor instead of a field addition.

---

## Repetition Rule Special Analysis

Of 12 classes, only **`OrdinalWeekdaySpec`** is genuinely eliminable (identical to `OrdinalWeekday` which already has `extra="forbid"`). The rest have real structural differences: `FrequencyEditSpec` uses Patch wrappers, `RepetitionRuleRepoPayload` has 4 completely different flat fields, `FrequencyAddSpec` differs in nested types and base class.

---

## Verdict

**The current architecture is structural enforcement of boundary contracts, not accidental duplication.**

The "core model + sidecar" approach saves ~4 classes / ~50 lines (7%) but:
- Breaks type safety at the repo boundary
- Cannot resolve the `extra="forbid"` tension
- Cannot handle Patch semantics (edit pipeline is incompatible)
- Degrades schema quality
- Violates documented architectural principles

### Two Targeted Improvements Worth Considering

1. **Eliminate `OrdinalWeekdaySpec`**: Core `OrdinalWeekday` already has `extra="forbid"` and identical fields/validators. Use it directly in `FrequencyAddSpec`/`FrequencyEditSpec`.

2. **Eliminate `ListTagsRepoQuery` and `ListFoldersRepoQuery`**: 100% field-identical to agent-facing counterparts. Re-splitting if needed later is trivial.

### Recommendation

Do not pursue broad unification. The duplication is intentional, cheap to maintain (per structure-over-discipline), and the type safety is load-bearing.
