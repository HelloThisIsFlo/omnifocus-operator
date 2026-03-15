---
created: 2026-03-15T21:51:11.609Z
title: Explore write interface asymmetry across layers
area: service
files:
  - src/omnifocus_operator/server.py
  - src/omnifocus_operator/service.py
  - src/omnifocus_operator/repository/protocol.py
  - src/omnifocus_operator/repository/bridge.py
  - src/omnifocus_operator/repository/hybrid.py
  - src/omnifocus_operator/repository/in_memory.py
  - src/omnifocus_operator/models/write.py
---

## Problem

The two write operations have different type signatures and responsibility splits at each layer boundary. This document maps where the type mismatches are.

## Layer 1: Server → Service (clean)

Both paths follow the same pattern — Pydantic validation at the boundary:

| | `add_tasks` | `edit_tasks` |
|---|---|---|
| **Server receives** | `list[dict[str, Any]]` | `list[dict[str, Any]]` |
| **Server validates into** | `TaskCreateSpec` | `TaskEditSpec` |
| **Service accepts** | `TaskCreateSpec` | `TaskEditSpec` |
| **Service returns** | `TaskCreateResult` | `TaskEditResult` |

No issues here. Both tools: raw dict in, typed spec out, typed result back.

## Layer 2: Service → Repository (asymmetric)

| | `add_task` | `edit_task` |
|---|---|---|
| **Service passes** | `TaskCreateSpec` + `resolved_tag_ids` + `resolved_repetition_rule` kwargs | `dict[str, Any]` (fully bridge-ready payload) |
| **Who converts tags** | Service resolves names→IDs, but repo swaps them in | Service computes diff → `addTagIds`/`removeTagIds` |
| **Who converts repetition rule** | Service converts `RepetitionRuleSpec`→bridge dict, but repo swaps it in | Service converts inline |
| **Who serializes to bridge format** | Repository (`model_dump(by_alias=True)` → camelCase) | Service (builds dict field-by-field) |
| **Repository role** | `model_dump` spec, pop `tags`/`repetitionRule`, insert resolved values | Pass-through to `bridge.send_command` |
| **Return type** | `TaskCreateResult` (typed) | `dict[str, Any]` (raw) |

### Protocol signature asymmetry

```python
# protocol.py
async def add_task(
    self,
    spec: TaskCreateSpec,
    *,
    resolved_tag_ids: list[str] | None = None,
    resolved_repetition_rule: dict[str, Any] | None = None,
) -> TaskCreateResult: ...

async def edit_task(
    self, payload: dict[str, Any],
) -> dict[str, Any]: ...
```

`add_task` receives a typed spec + band-aid kwargs. `edit_task` receives an untyped dict.

## Layer 3: Repository → Bridge (converges)

Both paths ultimately call the same thing:

```python
await self._bridge.send_command("add_task", payload)   # dict[str, Any]
await self._bridge.send_command("edit_task", payload)   # dict[str, Any]
```

But they arrive at that dict differently:
- **add_task**: repo does `spec.model_dump()` → pops/swaps resolved values → dict
- **edit_task**: service already built the dict → repo passes through

## InMemoryRepository (test double) divergence

The test double handles each path with completely different logic:

| | `add_task` | `edit_task` |
|---|---|---|
| **What it does** | Builds a `Task` from spec fields | Mutates existing `Task` from bridge-format dict |
| **Tag handling** | Uses `resolved_tag_ids` to look up Tag objects | Maps `addTagIds`/`removeTagIds` to Tag mutations |
| **Repetition rules** | **Ignores** `resolved_repetition_rule`, rebuilds from spec | Stores bridge dict keys directly on task |
| **Validation** | Doesn't validate output matches bridge format | Doesn't validate input dict shape |

## Bridge payload format (what both paths must produce)

**add_task bridge expects:**
- `name`, `parent`, `dueDate`, `deferDate`, `plannedDate`, `flagged`, `estimatedMinutes`, `note` (camelCase)
- `tagIds: list[str]` (not `tags`)
- `repetitionRule: {ruleString, scheduleType, anchorDateKey, catchUp}` (bridge format, not user-facing)

**edit_task bridge expects:**
- `id` (required), plus any changed fields in camelCase
- `addTagIds` / `removeTagIds` (diff, not absolute)
- `moveTo: {position, containerId|anchorId}`
- `lifecycle: "complete" | "drop"`
- `repetitionRule: {ruleString, scheduleType, anchorDateKey, catchUp} | None`

## Summary of where conversion logic lives

| Conversion | `add_task` | `edit_task` |
|---|---|---|
| Tag names → IDs | Service resolves, repo swaps | Service resolves + computes diff |
| `RepetitionRuleSpec` → bridge dict | Service converts, repo swaps | Service converts |
| Field serialization (snake→camel) | Repository (`model_dump(by_alias=True)`) | Service (manual dict building) |
| `tags` → `tagIds` key rename | Repository (pop + insert) | N/A (service uses `addTagIds`/`removeTagIds`) |
| `repetitionRule` key swap | Repository (pop + insert) | N/A (service inserts bridge format directly) |

## Idea to explore: single-file protocol map

One thought: have a single file that declares the protocol (types in, types out) at each layer boundary — server, service, repository. Not the implementation, just the contracts. Something like:

```python
# Strawman — not a real proposal yet
class ServerProtocol:
    async def add_tasks(items: list[dict]) -> list[TaskCreateResult]: ...
    async def edit_tasks(items: list[dict]) -> list[TaskEditResult]: ...

class ServiceProtocol:
    async def add_task(spec: TaskCreateSpec) -> TaskCreateResult: ...
    async def edit_task(spec: TaskEditSpec) -> TaskEditResult: ...

class RepositoryProtocol:
    async def add_task(???) -> ???: ...
    async def edit_task(???) -> ???: ...
```

The value would be: seeing the full information flow top-to-bottom in one place, making asymmetries obvious at a glance. Right now you have to hop between 5+ files to understand what types cross which boundary.

Open questions:
- Is this just documentation, or would it actually be enforced (e.g. runtime-checked Protocol classes)?
- Does co-locating protocols create a coupling problem? Each layer currently owns its own interface.
- Might be overkill — maybe just cleaning up the repo protocol signatures is enough.
