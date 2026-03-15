---
created: 2026-03-15T21:51:11.609Z
title: Unify write interface at service-repository boundary
area: service
files:
  - src/omnifocus_operator/repository/protocol.py
  - src/omnifocus_operator/repository/bridge.py
  - src/omnifocus_operator/repository/hybrid.py
  - src/omnifocus_operator/repository/in_memory.py
  - src/omnifocus_operator/service.py
---

## Problem

Write interface asymmetry at the service → repository boundary. The two write operations (`add_task` / `edit_task`) have completely different responsibility boundaries:

| | `add_task` | `edit_task` |
|---|---|---|
| **Service passes** | `TaskCreateSpec` (typed) | `dict[str, Any]` (raw bridge-ready payload) |
| **Who serializes** | Repository (`model_dump`) | Service (builds dict manually) |
| **Who converts to bridge format** | Repository (but gets it wrong — user-facing fields, not bridge fields) | Service (`_process_repetition_rule`, `_compute_tag_diff`, moveTo builder) |
| **Repository role** | Deserialize spec + swap resolved values | Dumb pass-through to `bridge.send_command` |
| **Return type** | `TaskCreateResult` (typed) | `dict[str, Any]` (raw) |

### Consequences

- Bridge format conversion logic is scattered across two layers
- `resolved_*` kwargs are band-aids — service converts, passes alongside spec, repo swaps into the model_dump'd payload
- InMemoryRepository (test double) has different code paths for each: builds a Task from spec for add, mutates a Task from dict for edit — neither validates the payload shape matches what bridge.js expects
- Adding a new field to `add_task` requires touching service (validation), repository (swap logic), AND the spec model. For `edit_task` it's just the service.

## Solution

Unify both paths so there is one consistent pattern at the service → repository boundary. The service should own all conversion logic (FrequencySpec → ruleString, schedule → scheduleType, tag names → IDs, etc.) for both add and edit, passing a bridge-ready payload to the repository in both cases. Repository becomes a consistent pass-through for writes.

Key design question: whether the service passes a typed "bridge command" object or a raw dict. Either way, conversion logic should live in exactly one layer.
