# Token Comparison: JSON vs TaskPaper

**Date:** 2026-02-21
**Encoding:** cl100k_base (tiktoken) — used by GPT-4, Claude, and most modern LLMs

## Test Data

Realistic mock OmniFocus database:
- 5 folders (nested)
- 20 projects (with various statuses, dates, review intervals)
- ~100 tasks (with sub-tasks, due dates, estimates, tags, repetition rules)
- 30 tags (hierarchical)
- 5 custom perspectives
- 5 inbox tasks

## Results

| Format | Characters | Tokens | Ratio vs JSON |
|--------|-----------|--------|---------------|
| JSON (pretty, indent=2) | 129,112 | 38,207 | 1.00x (baseline) |
| JSON (compact, no whitespace) | 93,585 | 27,745 | 0.73x |
| **TaskPaper (full mode)** | **32,452** | **12,184** | **0.32x** |
| **TaskPaper (LLM mode)** | **18,334** | **6,408** | **0.17x** |

## Token Savings

| Comparison | Savings |
|-----------|---------|
| LLM mode vs pretty JSON | **83.2%** |
| LLM mode vs compact JSON | **76.9%** |
| Full mode vs pretty JSON | 68.1% |
| Full mode vs compact JSON | 56.1% |

## What LLM Mode Strips

LLM mode removes fields that an LLM doesn't need for reasoning about tasks:

1. **Internal IDs** (`id`, `assignedContainer`) — LLM refers to tasks by name
2. **Metadata timestamps** (`added`, `modified`) — rarely relevant for task management decisions
3. **Active/effective-active flags** — redundant with status
4. **Redundant effective dates** — only shown when they differ from the direct date (i.e., inherited from parent)
5. **Implementation details** (`shouldUseFloatingTimeZone`, `completedByChildren`, `hasChildren`)
6. **Computed statuses** (`taskStatus` on projects, `effectiveFlagged`)
7. **Internal references** (`nextTask`)

## What LLM Mode Preserves

Everything an LLM needs to understand tasks and make decisions:

- Task/project/folder names and notes
- Due dates and defer dates (direct and effective when inherited)
- Flagged status
- Sequential/parallel project type
- Time estimates
- OmniFocus tags
- Completion/drop status with dates
- Review dates and intervals
- Repetition rules
- Project status (Active, OnHold, etc.)
- Full hierarchy (folder → project → task → sub-task)

## Extrapolation to Flo's Real Database

Flo's database: 2,418 tasks, 363 projects, 64 tags, 79 folders

Assuming linear scaling from our 100-task test:

| Format | Estimated Tokens |
|--------|-----------------|
| JSON (pretty) | ~920,000 |
| JSON (compact) | ~670,000 |
| TaskPaper (full) | ~294,000 |
| **TaskPaper (LLM)** | **~155,000** |

The LLM mode estimate of ~155K tokens is well within a single context window for Claude (200K tokens), leaving ample room for system prompts, conversation history, and tool definitions. The JSON dump at ~670K-920K tokens would exceed most context windows entirely.

## Conclusion

TaskPaper LLM mode achieves a **~6x compression ratio** over pretty-printed JSON and **~4.3x** over compact JSON. This transforms the OmniFocus database from a context-window challenge into a manageable injection that leaves plenty of room for the LLM to reason about tasks.
