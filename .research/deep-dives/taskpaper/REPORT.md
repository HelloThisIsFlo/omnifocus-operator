# TaskPaper Research & Converter Report

**Date:** 2026-02-21
**Author:** Claude (research agent)
**Status:** Complete — all phases delivered

---

## Executive Summary

TaskPaper format is an excellent fit for presenting OmniFocus data to LLMs. A custom bidirectional converter (JSON ↔ TaskPaper) achieves **83% token reduction** vs pretty-printed JSON and **77% vs compact JSON**, while preserving all information an LLM needs for task management reasoning.

The converter is ~400 lines of dependency-free Python, supports two modes (full/lossless and LLM-optimised), and handles the complete OmniFocus data model including hierarchical nesting, all date types, tags, review intervals, and repetition rules.

---

## 1. Key Findings: TaskPaper Format

TaskPaper is a plain-text format by Jesse Grosjean (Hog Bay Software) with three item types: projects (lines ending with `:`), tasks (lines starting with `- `), and notes (plain lines). Hierarchy is expressed through tab indentation. Metadata uses `@tag` and `@tag(value)` syntax.

**OmniFocus recognises these standard tags on import:**
`@due(date)`, `@defer(date)`, `@done(date)`, `@dropped(date)`, `@flagged`, `@estimate(minutes)`, `@parallel`, `@sequential`, `@autodone`, `@context(name)`, `@tags(list)`, `@repeat-rule(rrule)`, `@repeat-method(type)`

**What TaskPaper can't natively represent** (requires custom tags):
- Review intervals (`@review(1 weeks)`)
- Task/project IDs (`@id(...)`)
- Effective (inherited) dates (`@effective-due(...)`)
- Computed task status
- Perspectives
- Metadata timestamps

These limitations are acceptable because the converter uses custom `@tag(value)` extensions for all non-standard fields, and the LLM mode deliberately omits most of them as unnecessary.

**Full spec notes:** See `spec-notes.md`

---

## 2. Library Evaluation Verdict

**Decision: Build custom.** All three existing Python libraries are abandoned (last commits 2011-2016), untested on modern Python, and none fully supports bidirectional conversion.

| Library | Last Active | Verdict |
|---------|------------|---------|
| python-taskpaper | 2011 | Dead. GPL. Python 2 heritage. |
| TodoFlow | 2016 | Dead. Removed file I/O. |
| RobTrew parser | Unknown | Parse-only. No write support. |

The TaskPaper format is deliberately minimal — a robust custom parser/serializer is ~400 lines with zero dependencies. This is clearly the right engineering choice.

**Full evaluation:** See `library-evaluation.md`

---

## 3. OmniFocus Property Coverage

Two independent research agents compiled the complete OmniFocus 4 Omni Automation API property lists. After cross-comparison, the verified counts are:

| Entity | Instance Properties | In Bridge Script |
|--------|-------------------|-----------------|
| Task | 39-43 (including insertion locations) | 28 (data fields only) |
| Project | 33-35 | 27 |
| Tag | 16-17 | 8 |
| Folder | 14 | 7 |
| Perspective.Custom | 5 | 2 (id, name) |

The bridge script (`operatorBridgeScript.js`) captures all the data-relevant properties. Properties excluded from the bridge (insertion locations, collection accessors, class methods) are positional/structural and not needed for the TaskPaper presentation layer.

**Key OmniFocus 4 additions:** `plannedDate` (v4.7+), `effectivePlannedDate` (v4.7.1), `iconColor` on perspectives (v4.5.2+), `archivedFilterRules` (v4.2+).

---

## 4. Converter Design Decisions

### Architecture

```
JSON dump (from OmniFocus bridge)
        ↓
   json_to_taskpaper.py   ←→   Mode.FULL / Mode.LLM
        ↓
   TaskPaper string (for LLM context injection)
        ↓
   taskpaper_to_json.py   (for round-tripping if LLM outputs modifications)
        ↓
   JSON structure (for writing back via bridge)
```

### Key design choices

1. **Tree reconstruction from flat lists.** The JSON dump contains flat arrays with ID references (parent, project, folder). The converter rebuilds the hierarchy: folders → projects → tasks → sub-tasks, then serializes depth-first with tab indentation.

2. **Two modes, one code path.** Full and LLM modes use the same serializer; the only difference is a skip-set of fields. This keeps the code simple and the two modes guaranteed-consistent.

3. **Smart effective date handling.** In LLM mode, effective dates (inherited from parent) are only shown when they differ from the direct date. This avoids redundant `@due(2026-03-01) @effective-due(2026-03-01)` pairs while still surfacing inherited dates when they matter.

4. **Date compression.** ISO dates are shortened: `2026-02-21T00:00:00.000Z` → `2026-02-21`, `2026-02-21T17:00:00.000Z` → `2026-02-21T17:00`. This alone saves significant tokens.

5. **Inbox grouping.** Tasks without a project (inbox tasks) are grouped under a synthetic `Inbox:` folder at the top of the output.

6. **Tags section.** Tag definitions (with hierarchy) are serialised as a separate `Tags:` section at the bottom, preserving parent-child relationships.

7. **Notes truncation in LLM mode.** Notes longer than 500 characters are truncated in LLM mode to prevent one verbose note from dominating the token budget.

### Limitations and trade-offs

- **IDs don't round-trip.** The parser generates placeholder IDs (`task_1`, `proj_1`, etc.). Original OmniFocus IDs are only preserved in full mode as `@id(...)` tags. For the primary use case (JSON→TaskPaper for LLM context), this is irrelevant.

- **Folder vs project ambiguity.** In TaskPaper, both folders and projects end with `:`. The parser uses a heuristic: top-level `:` items are folders; items inside folders are projects; items inside projects are action groups (tasks with children). This matches OmniFocus conventions.

- **Perspectives are one-way.** Perspectives are included in full mode output but not parsed back, since they're application-specific filter configurations, not task data.

---

## 5. Token Efficiency Results

Tested with a realistic mock (20 projects, 100 tasks, 30 tags, 5 folders):

| Format | Tokens | vs JSON |
|--------|--------|---------|
| JSON (pretty) | 38,207 | baseline |
| JSON (compact) | 27,745 | 0.73x |
| TaskPaper (full) | 12,184 | 0.32x |
| **TaskPaper (LLM)** | **6,408** | **0.17x** |

**LLM mode achieves 83% token savings over pretty JSON.**

Extrapolated to Flo's real database (2,418 tasks, 363 projects):
- JSON would consume ~670K-920K tokens (exceeds most context windows)
- TaskPaper LLM mode: ~155K tokens (fits comfortably in Claude's 200K window)

**Full analysis:** See `token-comparison.md`

---

## 6. Recommendations

1. **Use TaskPaper LLM mode as the default presentation format** when injecting OmniFocus state into the LLM context. The 6x token savings are transformative.

2. **Keep JSON as the canonical backend format.** TaskPaper is a presentation layer; all reads/writes go through JSON via the bridge.

3. **Consider selective injection.** Even at 155K tokens for the full database, it may be worth filtering to active/relevant tasks before conversion. The converter accepts the same JSON structure, so pre-filtering is trivial.

4. **TaskPaper→JSON parsing is secondary.** The primary path is JSON→TaskPaper. The reverse parser exists for completeness and round-trip testing, but in practice the LLM will output specific edit commands (via MCP tools), not modified TaskPaper text.

5. **No external dependencies needed.** The converter is self-contained Python. Keep it that way.

---

## Deliverables

```
TaskPaper/
├── REPORT.md              ← This document
├── spec-notes.md          ← TaskPaper format spec & OmniFocus conventions
├── library-evaluation.md  ← Python library assessment
├── token-comparison.md    ← Token count analysis
├── converter/
│   ├── __init__.py
│   ├── json_to_taskpaper.py
│   ├── taskpaper_to_json.py
│   └── test_converter.py
└── token-comparison-data.json  ← Raw token count data
```
