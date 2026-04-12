# Phase 51: Task Ordering - Discussion Log

> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Participants:** User + Claude

---

## Gray Area 1: Order Computation Location

**Question:** Where should the `order` value be computed?

**Options presented:**
1. **SQL `ROW_NUMBER()` in the CTE** — Order computed at data source, mapper passes through
2. **Python post-processing** — SQL returns rank, Python groups siblings and assigns ordinals

**Discussion:**
- User asked if Python would give cross-path equivalence between HybridRepository and BridgeOnlyRepository
- Claude clarified: No — the divergence isn't WHERE we compute, it's WHAT data is available. OmniJS doesn't expose `rank`, so BridgeOnlyRepository can't compute order regardless of SQL vs Python.
- Requirements explicitly relax cross-path equivalence for ordering ("approximate ordering acceptable for BridgeOnlyRepository fallback")

**Decision:** SQL `ROW_NUMBER()` — simpler, faster, no cross-path equivalence possible anyway.

---

## Gray Area 2: Scope of Ordering

**Question:** Which read operations should include the `order` field?

**Options presented:**
1. **All reads** — `get_task`, `list_tasks`, `get_all` — every Task has `order`
2. **`list_tasks` + `get_all` only** — Bulk reads get ordering, single lookup stays simple
3. **`list_tasks` only** — Order only where pagination matters

**Discussion:**
- Claude recommended all reads for consistent model shape
- User agreed — agents shouldn't need to know which method fetched the task

**Decision:** All reads include `order`. One model shape everywhere.

---

## Gray Area 3: Bridge-Only Degradation Strategy

**Question:** What should BridgeOnlyRepository return for `order`, given it can't access rank?

**Options presented:**
1. **`null` (explicit absence)** — `order: str | None`, bridge returns `None`
2. **Arbitrary position (1, 2, 3...)** — Assign sequential order based on iteration
3. **Sentinel value (0)** — `order: int`, always 0 on bridge path

**Discussion:**
- Claude recommended `null` — honest signal of degraded mode
- User agreed — no misleading arbitrary values

**Decision:** `order: null` on bridge path. Model type is `str | None`.

---

## Gray Area 4: Order Format (emerged during discussion)

**Question:** Should order be an integer ordinal or dotted string notation?

**Initial assumption:** `order: int` — position among siblings (1, 2, 3...)

**User challenge:** "What if for subtasks we use dotted notation — 1.1, 1.2?"

**Tradeoffs explored:**

| Concern | Integer | Dotted | Resolution |
|---------|---------|--------|------------|
| Type change | `int` is "cleaner" | `str` | LLMs see everything as text anyway — moot |
| String sort | N/A | `"1.10"` < `"1.2"` alphabetically | Tasks are pre-sorted by `sort_path`; agents don't sort |
| Cascading changes | Only leaf changes | Full path changes if ancestors move | Agents see fresh state each request; no reconciliation needed |
| Deep nesting | `order: 6` → "6 of what?" | `order: "1.2.3.4.5.6"` → immediate context | Dotted is clearer |
| Redundancy | `parent` + `order` | `parent` + `order` (overlapping info) | Different questions: parent = "who contains me", order = "where am I in the full tree" |

**Key insight from user:**
> "The output of this MCP is not going to be consumed by a machine; it's going to be consumed by LLM. LLM processes information much, much closer to human than Python programmes do. The use case I imagine is that it is way more intuitive for a human, so potentially it would be way more intuitive for an agent as well."

**Decision:** Dotted notation (`"2.3.1"` style). Agent-first design principle — optimize for LLM readability.

---

## Gray Area 5: Per-Project Namespace (clarification)

**Question:** How does dotted notation work across projects?

**User clarification:**
> "Every project would start at one... one is always the first task of a project. We have the parent, so we know what I mean. The first number would be the order within the project, and therefore inbox is kind of like its own project."

**Decision:** Each project/inbox is its own numbering space starting at "1". The `project` field identifies which namespace.

---

## Gray Area 6: Format Details

**Questions:**
1. Format: dots vs dashes vs slashes?
2. Root-level: `"1"` vs `"1."`?
3. Sparse filtered results — confusing?

**Decisions:**
1. Dots (most natural for hierarchical numbering)
2. No trailing dot (`"1"` not `"1."`)
3. Document sparse results in tool descriptions — expected behavior, agents should know why

---

## Gray Area 7: Cross-Path Equivalence Testing

**Question:** How should existing 32 cross-path equivalence tests handle the intentional `order` divergence?

**Discussion:**
- HybridRepository returns `order: "2.3.1"`
- BridgeOnlyRepository returns `order: None`
- These are intentionally different (D-03)

**Decision:** Cross-path tests must exclude `order` from comparison (or add to "known divergence fields" list).

---

## Deferred Ideas

- Add `order` field to Project/Folder/Tag entities — evaluate after task ordering ships

---

*Discussion completed: 2026-04-12*
