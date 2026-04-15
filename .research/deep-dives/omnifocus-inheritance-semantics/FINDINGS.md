# OmniFocus Inheritance Semantics — Empirical Findings

Empirical study of how OmniFocus computes `effective*` values from task hierarchy.
All findings derived from live OmniFocus testing on 2026-04-15.

## Status: In Progress

- Due date semantics: **REPLICATED** ✅ (2026-04-15, fresh 5-level hierarchy)
- Defer date semantics: **REPLICATED** ✅ (2026-04-15, fresh 5-level hierarchy)
- Planned date semantics: **REPLICATED** ✅ (2026-04-15, fresh hierarchy + 2027→2037 swap experiment)
- Flagged semantics: **REPLICATED** ✅ (2026-04-15, project unflagged + mid-chain flag test)
- Drop date semantics: **REPLICATED** ✅ (2026-04-15, reverse-drop test + nearer-ancestor test)
- Completion date semantics: **low confidence** (not yet replicated, needs distinct timestamps)

## Background

OmniFocus exposes two versions of each field on tasks:
- **Direct** (`dueDate`, `deferDate`, `plannedDate`, `flagged`, `dropDate`, `completionDate`)
- **Effective** (`effectiveDueDate`, `effectiveDeferDate`, `effectivePlannedDate`, `effectiveFlagged`, `effectiveDropDate`, `effectiveCompletionDate`)

The "effective" value is OmniFocus's resolved value after applying inheritance from the
task's ancestor chain (parent tasks → containing project → folder chain).

Our `_walk_one` function in `service/domain.py` computes `inherited*` fields that represent
the ancestor's contribution. Understanding the exact OF semantics is critical to computing
these correctly.

## Test Setup

All tests used the `🧪 GM-TestProject-Dated` project (id: `e-OCRt-smkH`):
- `dueDate`: 2036-03-01
- `deferDate`: 2026-03-21
- `plannedDate`: 2026-03-25
- `flagged`: true

### Hierarchy for date/flag testing (5-level chain)

```
🧪 GM-TestProject-Dated              due=2036-03-01  defer=2026-03-21  planned=2026-03-25  flagged=true
  └─ UAT-Deep-L1                     due=2032-06-15  defer=—           planned=2028-01-01  flagged=false
      └─ UAT-Deep-L2                 due=—           defer=2027-05-01  planned=—           flagged=false
          └─ UAT-Deep-L3             due=2029-12-31  defer=2025-01-01  planned=2030-07-01  flagged=true
              └─ UAT-Deep-L4         due=2035-01-01  defer=—           planned=—           flagged=false
                  └─ UAT-Deep-L5     due=2028-03-15  defer=2026-06-01  planned=2027-11-11  flagged=false
```

Design choices:
- Gaps in the chain (L2 has no due, L4 has no defer/planned) to test skip behavior
- Dates at different levels that are both sooner AND later than ancestors
- L5's own due (2028) is sooner than any ancestor's — key edge case for the original bug
- Flagged at project + L3 only — tests any-True propagation


---

## Finding 1: Due Date — Cascading MIN

**Confidence: HIGH**

**Rule:** `effectiveDueDate = min(own dueDate, parent's effectiveDueDate)`

Tightest deadline in the ancestor chain wins. A child cannot escape a parent's deadline.

### Raw OmniJS output

```
=== UAT-Deep-L1 ===
  dueDate:              2032-06-15
  effectiveDueDate:     2032-06-15      ← own (2032) < project (2036), own wins

=== UAT-Deep-L2 ===
  dueDate:              —
  effectiveDueDate:     2032-06-15      ← inherited from L1

=== UAT-Deep-L3 ===
  dueDate:              2029-12-31
  effectiveDueDate:     2029-12-31      ← own (2029) < L1 effective (2032), own wins

=== UAT-Deep-L4 ===
  dueDate:              2035-01-01
  effectiveDueDate:     2029-12-31      ← parent L3 effective (2029) < own (2035), parent wins

=== UAT-Deep-L5 ===
  dueDate:              2028-03-15
  effectiveDueDate:     2028-03-15      ← own (2028) < L4 effective (2029), own wins
```

### Verification

| Task | own | parent eff | min(own, parent eff) | OF shows | Match? |
|------|-----|-----------|---------------------|----------|--------|
| L1 | 2032-06-15 | 2036-03-01 | 2032-06-15 | 2032-06-15 | YES |
| L2 | — | 2032-06-15 | 2032-06-15 | 2032-06-15 | YES |
| L3 | 2029-12-31 | 2032-06-15 | 2029-12-31 | 2029-12-31 | YES |
| L4 | 2035-01-01 | 2029-12-31 | 2029-12-31 | 2029-12-31 | YES |
| L5 | 2028-03-15 | 2029-12-31 | 2028-03-15 | 2028-03-15 | YES |

All 5 levels match. **MIN confirmed.**

### Replication (2026-04-15, session 2)

Fresh 5-level hierarchy (UAT-Due-L1–L5) created from scratch. Same date pattern, same gaps.
All 5 levels matched min prediction identically. **REPLICATED.**

### Implication for `inheritedDueDate`

Our `_walk_one` should compute: min of all ancestor due dates in the chain.
This is equivalent to the parent's effectiveDueDate (since cascading min = aggregate min).
**Current implementation uses min — CORRECT.**


---

## Finding 2: Defer Date — Cascading MAX

**Confidence: HIGH**

**Rule:** `effectiveDeferDate = max(own deferDate, parent's effectiveDeferDate)`

Latest deferral in the ancestor chain wins. A child cannot unblock itself past a parent's deferral.

### Raw OmniJS output

```
=== UAT-Deep-L1 ===
  deferDate:            —
  effectiveDeferDate:   2026-03-21      ← inherited from project

=== UAT-Deep-L2 ===
  deferDate:            2027-05-01
  effectiveDeferDate:   2027-05-01      ← own (2027-05) > project via L1 (2026-03), own wins

=== UAT-Deep-L3 ===
  deferDate:            2025-01-01
  effectiveDeferDate:   2027-05-01      ← parent L2 effective (2027-05) > own (2025-01), parent wins!

=== UAT-Deep-L4 ===
  deferDate:            —
  effectiveDeferDate:   2027-05-01      ← inherited from L3 effective

=== UAT-Deep-L5 ===
  deferDate:            2026-06-01
  effectiveDeferDate:   2027-05-01      ← parent L4 effective (2027-05) > own (2026-06), parent wins
```

### Verification

| Task | own | parent eff | max(own, parent eff) | OF shows | Match? |
|------|-----|-----------|---------------------|----------|--------|
| L1 | — | 2026-03-21 | 2026-03-21 | 2026-03-21 | YES |
| L2 | 2027-05-01 | 2026-03-21 | 2027-05-01 | 2027-05-01 | YES |
| L3 | 2025-01-01 | 2027-05-01 | 2027-05-01 | 2027-05-01 | YES |
| L4 | — | 2027-05-01 | 2027-05-01 | 2027-05-01 | YES |
| L5 | 2026-06-01 | 2027-05-01 | 2027-05-01 | 2027-05-01 | YES |

L3 is the key proof: own defer is 2025-01 (past!), but effective is 2027-05 (from L2).
If min, L3 would show 2025-01. It shows 2027-05. **MAX confirmed.**

### Replication (2026-04-15, session 2)

Same 5-level hierarchy reused (defer dates added to UAT-Due-L* tasks). Same gap/date pattern.
All 5 levels matched max prediction identically. **REPLICATED.**

### Implication for `inheritedDeferDate`

Our `_walk_one` should compute: max of all ancestor defer dates in the chain.
**Current implementation uses min — WRONG. Must change to max.**


---

## Finding 3: Planned Date — Simple Override (own ?? parent)

**Confidence: HIGH**

**Rule:** `effectivePlannedDate = own plannedDate ?? parent's effectivePlannedDate`

No aggregation. The task's own value takes precedence unconditionally. If unset,
falls back to the parent's effective. This is a simple cascade/override.

### Raw OmniJS output

```
=== UAT-Deep-L1 ===
  plannedDate:          2028-01-01
  effectivePlannedDate: 2028-01-01      ← own (2028), even though project has 2026-03

=== UAT-Deep-L2 ===
  plannedDate:          —
  effectivePlannedDate: 2028-01-01      ← inherited from L1

=== UAT-Deep-L3 ===
  plannedDate:          2030-07-01
  effectivePlannedDate: 2030-07-01      ← own (2030), even though L1 has 2028

=== UAT-Deep-L4 ===
  plannedDate:          —
  effectivePlannedDate: 2030-07-01      ← inherited from L3

=== UAT-Deep-L5 ===
  plannedDate:          2027-11-11
  effectivePlannedDate: 2027-11-11      ← own (2027), even though L3 effective is 2030!
```

### Why this is NOT min or max

| Task | own | parent eff | min | max | own ?? parent | OF shows | Matches |
|------|-----|-----------|-----|-----|--------------|----------|---------|
| L1 | 2028-01 | 2026-03 | 2026-03 | 2028-01 | 2028-01 | 2028-01 | own??parent (and max) |
| L5 | 2027-11 | 2030-07 | 2027-11 | 2030-07 | 2027-11 | 2027-11 | own??parent (and min) |

**L1 rules out min** (min would give 2026-03, OF shows 2028-01).
**L5 rules out max** (max would give 2030-07, OF shows 2027-11).
Only **own ?? parent** matches both.

### Replication (2026-04-15, session 2)

Fresh hierarchy, two rounds:
1. Same date pattern as original — all 5 levels matched first-found. L1 rules out min, L5 rules out max.
2. Moved planned from L3 to L2, then swapped L2's date from 2027-12-01 → 2037-12-01.
   L3/L4 followed L2 in both cases (2027 and 2037), confirming no comparison — purely nearest ancestor.
   The 2037 swap is especially decisive: max would also give 2037, but the 2027 round already ruled out max.
   UI confirmed: L3/L4 shown as "inherited" (gray), L1/L2/L5 as "real" (own values).
**REPLICATED.**

### Implication for `inheritedPlannedDate`

Our `_walk_one` should compute: the nearest ancestor's planned date (first non-null walking up).
Equivalent to: parent's effectivePlannedDate.
**Current implementation uses min — WRONG. Must change to first-found.**

### Design Discussion: Why first-found is the right choice for `inheritedPlannedDate`

After replicating the empirical findings, we discussed whether to match OmniFocus (first-found) or
expose a different aggregation (e.g. min) that might be more useful. Conclusion: **first-found is
correct both empirically and conceptually.**

**Key reframing:** Planned date means "when I'll engage with this / give it attention," NOT "when
I plan to complete this." For leaf tasks the distinction is subtle (you might finish the same day),
but for parent tasks it's structural — you can't finish a parent the day you start it. Even leaf
tasks can span multiple days in practice.

**Why min (earliest ancestor) is wrong conceptually:**

Consider a phased project:
```
Launch Website Redesign                    planned: March 1
├── Phase 1: Design                        planned: March 15
│   ├── Write copy                         (no plan) → inherits March 15
│   └── Create mockups                     (no plan) → inherits March 15
└── Phase 2: Build                         planned: April 1
    ├── Frontend                           (no plan) → inherits April 1
    └── Backend API                        planned: April 15
        └── Auth endpoints                 (no plan) → inherits April 15
```

With min, ALL unplanned tasks would collapse to March 1 (the project root). The user's phased
schedule disappears. Filtering "what should I work on March 15?" would surface Build and Backend
tasks — work the user deliberately scheduled for April.

With first-found, filtering "March 15" shows Design tasks. Filtering "April 1" shows Build tasks.
The phased schedule is preserved.

**Why first-found works:** Planned dates are **scoped intent** — "I plan to engage with this scope
on this date." A deeper node overriding a shallower one isn't a contradiction; it's a refinement.
Like nested variable scoping: the closest declaration wins.

**Decision:** Match OmniFocus semantics (first-found). `inheritedPlannedDate` = nearest ancestor's
planned date walking up. This is consistent with how due/defer also match OmniFocus exactly, and
it preserves the user's phased scheduling intent.


---

## Finding 4: Flagged — Any-True (OR)

**Confidence: HIGH**

**Rule:** `effectiveFlagged = own flagged || parent's effectiveFlagged`

If any ancestor is flagged, the task is effectively flagged. The signal propagates down.

### Raw OmniJS output

```
All 5 levels show effectiveFlagged: true
Project is flagged (true), so all descendants are effectively flagged.
```

### Limitation (original test)

Since the project was flagged, all tasks showed `effectiveFlagged: true` regardless of their
own value. Consistent with any-True / OR, but couldn't distinguish from other aggregations.

### Replication (2026-04-15, session 2) — DECISIVE

Project unflagged manually, then only L3 flagged. Result:
- L1: false/false, L2: false/false (above the flag — unaffected)
- L3: true/true (own flag)
- L4: false/true, L5: false/true (below the flag — propagates down)

This proves flag propagates **downward only** via OR. L1/L2 being false rules out any
whole-chain aggregation. The original limitation is now resolved.
**REPLICATED.**

### Implication for `inheritedFlagged`

**Current implementation uses any-True — CORRECT.**


---

## Finding 5: Drop Date — Override (own ?? parent)

**Confidence: MEDIUM**

**Rule (tentative):** `effectiveDropDate = own dropDate ?? parent's effectiveDropDate`

### Test methodology

Drop dates can't be set directly (read-only property). Testing required manually dropping
tasks via the OmniFocus UI and reading back values with OmniJS.

Three test rounds were conducted:

#### Tests 1-2 (without blocker siblings)

Hierarchy: `Top → Mid → Leaf` (single-child chain)

**Problem discovered:** When Mid was dropped (Top's only active child), Top auto-completed.
This is because OmniFocus completes a task group when all remaining children are
dropped/completed. This muddied the results.

**Test 1 result (Drop Mid, then Drop Top):**
```
Drop1-Leaf:  own=—           eff=2026-04-15T15:06:04
Drop1-Mid:   own=15:06:04    eff=15:06:04
Drop1-Top:   own=15:06:15    eff=15:06:15
```

Leaf.effective = Mid's date (15:06:04), not Top's later date (15:06:15).
**Rules out MAX** (max would show 15:06:15).

**Test 2 result (Drop Top, then Drop Mid):**
```
Drop2-Leaf:  own=—           eff=2026-04-15T15:06:58
Drop2-Mid:   own=15:06:58    eff=15:06:58
Drop2-Top:   own=—           eff=—           ← Top's dropDate was CLEARED (auto-completed!)
```

**Inconclusive** — Top's state changed during the test.

#### Tests 3-4 (with blocker siblings — DECISIVE)

Hierarchy with blocker siblings to prevent auto-completion:
```
Top
├── Top-Blocker (stays active)
└── Mid
    └── Leaf
```

**Test 3 (Drop Mid first at T1=:42, then Top at T2=:52):**
```
Drop3-Leaf:          own=—     eff=15:09:42 (= Mid's T1)
Drop3-Mid:           own=:42   eff=:42
Drop3-Top:           own=:52   eff=:52
Drop3-Top-Blocker:   own=—     eff=:52 (= Top's T2)
```

Leaf shows T1 (Mid, nearest ancestor). Consistent with both first-found and min.

**Test 4 (Drop Top first at T3=:01, then Mid at T4=:09):**
```
Drop4-Leaf:          own=—     eff=15:10:09 (= Mid's T4)
Drop4-Mid:           own=:09   eff=:09
Drop4-Top:           own=:01   eff=:01
Drop4-Top-Blocker:   own=—     eff=:01 (= Top's T3)
```

**THIS IS THE DECISIVE TEST.**
- Leaf's nearest ancestor (Mid) has T4=:09 (LATER)
- Leaf's further ancestor (Top) has T3=:01 (EARLIER)
- Leaf shows **T4 = :09 (Mid's date)**

| Strategy | Would show | Actual | Match? |
|----------|-----------|--------|--------|
| min | :01 (Top, earlier) | :09 | NO |
| max | :09 (Mid, later) | :09 | YES |
| first-found | :09 (Mid, nearest) | :09 | YES |

Min is ruled out. **Cannot distinguish max from first-found** in this one test, but:
- Test 3 ruled out max (Leaf showed :42 not :52)
- Test 4 rules out min (Leaf showed :09 not :01)
- Only **first-found** is consistent with BOTH tests.

### Key observation: drop does NOT cascade own dates

In all tests, Leaf never received its own `dropDate`. It only got `effectiveDropDate`
from ancestors. This confirms that inheritance IS meaningful for drop dates — children
don't get their own date when a parent is dropped.

### Caveats (why medium confidence in session 1)

1. **Auto-completion side effects:** Dropping a task's only child auto-completes the parent,
   which can change lifecycle states unexpectedly. Blocker siblings mitigate but don't
   eliminate all interactions.
2. **Only tested task-to-task inheritance**, not project-to-task (dropping a project).
3. **Small sample size:** Only 4 tests, with 2 being decisive.

### Replication (2026-04-15, session 2) — min ruled out, max not yet distinguished

5-level hierarchy with blocker siblings at every level (UAT-Drop-A through E, plus *-Blocker).
Drops applied top-down: A first (16:12:31), then C (16:13:19), then D (16:14:01).

**Min ruled out:** After dropping C, tasks below C (D, D-Blocker, E) switched from A's 16:12:31
to C's 16:13:19. If min, they would have kept A's earlier timestamp.

**Max vs first-found NOT YET distinguished** in this test: each successive drop was both nearer
AND later, so max and first-found give the same answer.

**Auto-completion discovery (major finding — see Finding 7 below):** After drop testing,
we explored lifecycle interactions by completing/dropping blocker siblings. This revealed
rich auto-completion behavior documented in Finding 7.

### Replication (2026-04-15, session 3) — CONFIRMED first-found ✅

Fresh 4-level hierarchy with blocker siblings (UAT-Test-Root/Mid/Inner/Leaf + *-Blocker).
**Reverse drop order** — nearer ancestor dropped first (earlier timestamp), further ancestor
dropped second (later timestamp). This is the decisive test that distinguishes max from first-found.

**Step 1: Drop Mid (T1 = 16:44:11)**

| Task | own dropDate | effectiveDropDate |
|------|-------------|-------------------|
| Root | — | — |
| Root-Blocker | — | — |
| Mid | 16:44:11 | 16:44:11 |
| Mid-Blocker | — | 16:44:11 |
| Inner | — | 16:44:11 |
| Inner-Blocker | — | 16:44:11 |
| Leaf | — | 16:44:11 |

**Step 2: Drop Root (T2 = 16:45:05)**

| Task | own dropDate | effectiveDropDate |
|------|-------------|-------------------|
| Root | 16:45:05 | 16:45:05 |
| Root-Blocker | — | 16:45:05 |
| Mid | 16:44:11 | 16:44:11 |
| Mid-Blocker | — | 16:44:11 |
| Inner | — | 16:44:11 |
| Inner-Blocker | — | 16:44:11 |
| **Leaf** | **—** | **16:44:11** |

**Max ruled out:** If max, Leaf would show 16:45:05 (Root's later timestamp). Instead Leaf
shows 16:44:11 — Mid's timestamp, the **nearest** ancestor with a drop date.

**Step 3: Drop Inner (T3 = 16:51:54) — bonus confirmation**

| Task | own dropDate | effectiveDropDate |
|------|-------------|-------------------|
| Root | 16:45:05 | 16:45:05 |
| Mid | 16:44:11 | 16:44:11 |
| Inner | 16:51:54 | 16:51:54 |
| **Leaf** | **—** | **16:51:54** |

Leaf's effectiveDropDate **changed** from 16:44:11 (Mid) to 16:51:54 (Inner), because Inner
is nearer. This proves the value is not latched on first transition — it recalculates from the
current tree state (see "Effective values are derived, not stored" below).

### Implication for `inheritedDropDate`

Nearest ancestor's drop date (first non-null walking up).
**Current implementation uses min — WRONG. Should be first-found (same as planned).**
Min ruled out in sessions 1+2. Max ruled out in session 3. First-found confirmed across all sessions.


---

## Finding 6: Completion Date — Override (own ?? parent) — TENTATIVE

**Confidence: LOW**

**Rule (tentative):** `effectiveCompletionDate = own completionDate ?? parent's effectiveCompletionDate`

### Test methodology

Single-child chain: `A → B → C → D`

Completed C via UI. Result:
```
UAT-Lifecycle-A:  completionDate=14:41:54  effectiveCompletion=14:41:54
UAT-Lifecycle-B:  completionDate=14:41:54  effectiveCompletion=14:41:54
UAT-Lifecycle-C:  completionDate=14:41:54  effectiveCompletion=14:41:54
UAT-Lifecycle-D:  completionDate=—         effectiveCompletion=14:41:54
```

### What we learned

1. **D has NO own completionDate** — only effective. Completion does NOT cascade the
   `completionDate` property to children. Children inherit via `effectiveCompletionDate`.
2. **A and B auto-completed** at the same instant because each was a single-child parent.
   When their only child was done, OF auto-completed them.
3. **All timestamps are identical** — can't distinguish aggregation strategy.

### Why tentative

- All ancestors completed at the same instant (14:41:54), so min, max, and first-found
  all return the same value.
- We would need a test with distinct timestamps at multiple levels (requires blocker
  siblings, like the drop tests) to confirm the aggregation strategy.
- By analogy with drop (which uses first-found/override), completion likely uses the same,
  but this is an assumption, not empirically verified.

### Recommended follow-up test

Create hierarchy with blocker siblings:
```
Complete-Top
├── Complete-Top-Blocker (stays active)
└── Complete-Mid
    ├── Complete-Mid-Blocker (stays active)
    └── Complete-Leaf
```

1. Complete Complete-Mid-Blocker and Complete-Leaf (to allow Mid to auto-complete)
   — actually this is tricky, because completing children auto-completes the parent
2. Alternative: complete Leaf first, then manually complete Mid (which has blocker),
   then complete Top (which has blocker). Get distinct timestamps.

This test was not conducted due to context window constraints.

### Implication for `inheritedCompletionDate`

Tentatively: nearest ancestor's completion date (first non-null walking up).
**Current implementation uses min — LIKELY WRONG. Should probably be first-found.**


---

## Finding 7: Auto-Completion Lifecycle Behavior (session 2)

**Confidence: HIGH** — replicated with 5-level hierarchy, multiple rounds.

Discovered during drop date testing. When all children of a task have their **own** lifecycle
status (completed or dropped), OmniFocus auto-completes the parent. This interacts with
drop/completion inheritance in important ways.

### Test hierarchy

```
UAT-Drop-A                          dropped at 16:12:31
├── UAT-Drop-A-Blocker              completed at 16:24:58
└── UAT-Drop-B                      (effectively dropped, no own status)
    ├── UAT-Drop-B-Blocker          completed at 16:29:00
    └── UAT-Drop-C                  dropped at 16:13:19 → FLIPPED to completed at 16:25:31
        ├── UAT-Drop-C-Blocker      dropped at 16:25:31
        └── UAT-Drop-D              dropped at 16:14:01
            ├── UAT-Drop-D-Blocker  completed at 16:20:21
            └── UAT-Drop-E          (effectively dropped, no own status)
```

### Key findings

**1. Auto-complete requires ALL children to have own lifecycle status.**

| Parent | Children status | Auto-complete? | Why |
|--------|----------------|----------------|-----|
| D | D-Blocker completed + E effectively dropped | NO | E has no own status |
| C | C-Blocker explicitly dropped + D explicitly dropped | YES | Both have own status |
| A | A-Blocker completed + B effectively dropped | NO (initially) | B had no own status |
| B | B-Blocker completed + C completed | YES | Both have own status |
| A | A-Blocker completed + B completed | YES (cascaded) | Both now have own status |

"Effectively dropped" (inherited only, no own dropDate) does NOT count as "done."

**2. Auto-complete always produces "completed", never "dropped".**

C had both children dropped (C-Blocker dropped, D dropped). C still became **completed**,
not dropped. Auto-completion is about "all work is resolved," and the resolution is always completion.

**3. Auto-complete erases existing dropDate.**

C was explicitly dropped at 16:13:19. When auto-complete triggered, the dropDate was **cleared**
and replaced with completionDate 16:25:31. The drop is gone — no trace in the data model.
Same happened to A: explicitly dropped at 16:12:31, auto-completed at 16:29:00, drop erased.

**4. Auto-complete cascades upward.**

Completing B-Blocker at 16:29:00 triggered a chain:
- B auto-completed (children: B-Blocker completed + C completed) → B gets completionDate 16:29:00
- A auto-completed (children: A-Blocker completed + B just completed) → A gets completionDate 16:29:00
- Both B and A received the same timestamp as the triggering action

**5. Completing a task in an effectively-dropped subtree works normally.**

D-Blocker was effectively dropped (inherited from D), but we could still complete it.
It received both own completionDate=16:20:21 AND effectiveDropDate=16:14:01 simultaneously.
Both lifecycle states coexist in the data model for inherited-drop + own-completion.

### Implications for the operator

- Auto-completion is driven by the "complete when completing last item" OmniFocus setting (on by default)
- The distinction between "own" and "effective" lifecycle status is critical — only own status counts
- Drop-to-completion flips are real and erase drop data — any caching/snapshot logic must handle this
- This behavior is NOT directly relevant to `inherited*` field computation, but is important for
  understanding lifecycle state transitions in the data model


---

## Summary: Three Semantic Families

| Family | Fields | Rule | Rationale |
|--------|--------|------|-----------|
| **Constraint (min)** | `dueDate` | `min(own, parent_eff)` | Tightest deadline propagates down |
| **Constraint (max)** | `deferDate` | `max(own, parent_eff)` | Latest block propagates down |
| **Override** | `plannedDate`, `dropDate`, `completionDate` | `own ?? parent_eff` | Events/intentions — nearest ancestor wins |
| **Boolean OR** | `flagged` | `own \|\| parent_eff` | Attention signal propagates down |

### Conceptual model

- **Due and defer are CONSTRAINTS** — the hierarchy imposes limits on what you can do.
  Due = "you must finish by X" (tightest wins). Defer = "you can't start until X" (latest wins).
- **Planned, drop, completion are EVENTS/INTENTIONS** — they represent when something
  happened or is planned. The task's own value always takes precedence; if unset,
  the nearest ancestor's value is used.
- **Flagged is a SIGNAL** — once any ancestor is flagged, the attention signal
  propagates to all descendants.

### Effective values are derived, not stored

There is no "effectively dropped at" event. OmniFocus doesn't timestamp when a task
*becomes* effectively dropped — it re-walks the ancestor chain every time and derives the
value from the current tree state.

This means:
- Dropping a **further** ancestor when a nearer one is already dropped → no change (nearer
  still intercepted first)
- Dropping a **nearer** ancestor → effective value **changes**, even though the task was
  already effectively dropped

**Proof (session 3):** Drop Mid (T1=16:44:11), then Root (T2=16:45:05) → Leaf sees T1.
Then drop Inner (T3=16:51:54) → Leaf switches to T3. The value isn't latched on first
transition — it's recomputed from the tree.

This applies to all override-family fields (planned, drop, completion) and extends to
constraint fields (min/max also recompute from current state). The effective value at any
point in time is purely a function of the current ancestor chain, with no memory of
previous states.


---

## Current Implementation vs Correct Behavior

| Field | Current `_walk_one` | Correct | Status |
|-------|--------------------|---------|----|
| `inherited_flagged` | any-True | any-True | **CORRECT** |
| `inherited_due_date` | min | min | **CORRECT** |
| `inherited_defer_date` | min | **max** | **BUG** |
| `inherited_planned_date` | min | **first-found** | **BUG** |
| `inherited_drop_date` | min | **first-found** | **BUG** |
| `inherited_completion_date` | min | **first-found** (tentative) | **LIKELY BUG** |

### What "first-found" means for `_walk_one`

When walking the ancestor chain (parent tasks, then containing project), take the
FIRST non-null value encountered and stop. Do not aggregate across all ancestors.

This is equivalent to: parent task's effective value for that field.

### What "max" means for `_walk_one`

When walking the ancestor chain, track the MAXIMUM value across all ancestors that
have the field set. This is the mirror of the current min implementation.


---

## Test Artifacts Still in OmniFocus

### Session 3 (current)

- `UAT-Due-L1` through `UAT-Due-L5` — 5-level date/flag hierarchy. Dates cleared, L3 flagged,
  project unflagged. Active/blocked status.
- `UAT-Drop-A` through `UAT-Drop-E` + `*-Blocker` — session 2 drop hierarchy. All completed/dropped.
  User deleted the old session 1 tasks at start of session 3.
- `UAT-Test-Root/Mid/Inner/Leaf` + `*-Blocker` — session 3 drop test hierarchy. All dropped
  (Root at 16:45:05, Mid at 16:44:11, Inner at 16:51:54). Spent — cannot reuse for completion test.

### Session 1 (deleted by user at start of session 3)

- `UAT-Inheritance-Parent` / `UAT-Inheritance-Child` (2-level, first simple test)
- `UAT-Deep-L1` through `UAT-Deep-L5` (5-level hierarchy — original)
- `UAT-Lifecycle-A` through `UAT-Lifecycle-D` (completion test — all completed)
- `UAT-Drop1-*`, `UAT-Drop2-*` (drop tests without blockers — dropped/completed)
- `UAT-Drop3-*`, `UAT-Drop4-*` (drop tests with blockers — dropped)


---

## Next Steps

### ✅ Test A: Drop date — DONE (session 3)

Reverse-drop test confirmed first-found. See Finding 5 replication (session 3) above.

### Remaining: Test B — Completion date inheritance with distinct timestamps

Needs a fresh hierarchy (drop test hierarchy is spent). Create with blocker siblings:

```
UAT-Comp-Root
├── UAT-Comp-Root-Blocker
└── UAT-Comp-Mid
    ├── UAT-Comp-Mid-Blocker
    └── UAT-Comp-Inner
        ├── UAT-Comp-Inner-Blocker
        └── UAT-Comp-Leaf
```

Protocol: complete tasks at different levels with pauses to get distinct timestamps.
Think through auto-completion cascades before executing (Finding 7 — auto-complete fires
when ALL children have own lifecycle status).

Hypothesis: completion uses first-found (same as drop), with auto-completion as a separate
mechanism that creates own completionDates on parents when triggered.

### Then: Fix `_walk_one` implementation

After all 6 fields are confirmed:
1. Fix `_walk_one` in `service/domain.py` — three code paths:
   - `min` for `due_date`
   - `max` for `defer_date`
   - `first-found` for `planned_date`, `drop_date`, `completion_date`
   - `any-True` for `flagged` (already correct)
2. Write tests (TDD RED → GREEN)
3. Update UAT file
4. Architecture documentation for inheritance semantics


---

## OmniJS Scripts Used

All scripts were pasted into the OmniFocus Automation Console (Automation > Show Console).

### Script 1: Read date/flag hierarchy

```javascript
(() => {
    var lines = [];
    var fmt = function(dt) { return dt ? dt.toISOString().slice(0, 10) : "—"; };

    var proj = flattenedProjects.find(function(p) { return p.name === "🧪 GM-TestProject-Dated"; });
    lines.push("=== PROJECT: " + proj.name + " ===");
    lines.push("  dueDate:              " + fmt(proj.task.dueDate));
    lines.push("  effectiveDueDate:     " + fmt(proj.task.effectiveDueDate));
    lines.push("  deferDate:            " + fmt(proj.task.deferDate));
    lines.push("  effectiveDeferDate:   " + fmt(proj.task.effectiveDeferDate));
    lines.push("  plannedDate:          " + fmt(proj.task.plannedDate));
    lines.push("  effectivePlannedDate: " + fmt(proj.task.effectivePlannedDate));
    lines.push("  flagged:              " + proj.task.flagged);
    lines.push("  effectiveFlagged:     " + proj.task.effectiveFlagged);
    lines.push("");

    var tasks = flattenedTasks.filter(function(t) { return t.name.startsWith("UAT-Deep-L"); });
    tasks.sort(function(a, b) { return a.name.localeCompare(b.name); });

    tasks.forEach(function(t) {
        lines.push("=== " + t.name + " ===");
        lines.push("  parent:               " + (t.parent ? t.parent.name : "—"));
        lines.push("  dueDate:              " + fmt(t.dueDate));
        lines.push("  effectiveDueDate:     " + fmt(t.effectiveDueDate));
        lines.push("  deferDate:            " + fmt(t.deferDate));
        lines.push("  effectiveDeferDate:   " + fmt(t.effectiveDeferDate));
        lines.push("  plannedDate:          " + fmt(t.plannedDate));
        lines.push("  effectivePlannedDate: " + fmt(t.effectivePlannedDate));
        lines.push("  flagged:              " + t.flagged);
        lines.push("  effectiveFlagged:     " + t.effectiveFlagged);
        lines.push("");
    });
    console.log(lines.join("\n"));
})();
```

### Script 2: Read drop date hierarchy

```javascript
(() => {
    var lines = [];
    var fmt = function(dt) { return dt ? dt.toISOString().slice(0, 19) : "—"; };
    var tasks = flattenedTasks.filter(function(t) {
        return t.name.startsWith("UAT-Drop3") || t.name.startsWith("UAT-Drop4");
    });
    tasks.sort(function(a, b) { return a.name.localeCompare(b.name); });
    tasks.forEach(function(t) {
        lines.push(t.name + ": own=" + fmt(t.dropDate) + "  eff=" + fmt(t.effectiveDropDate));
    });
    console.log(lines.join("\n"));
})();
```

### Script 3: Read completion date hierarchy

```javascript
(() => {
    var lines = [];
    var fmt = function(dt) { return dt ? dt.toISOString().slice(0, 19) : "—"; };
    var tasks = flattenedTasks.filter(function(t) { return t.name.startsWith("UAT-Lifecycle-"); });
    tasks.sort(function(a, b) { return a.name.localeCompare(b.name); });
    tasks.forEach(function(t) {
        lines.push("=== " + t.name + " ===");
        lines.push("  completionDate:       " + fmt(t.completionDate));
        lines.push("  effectiveCompletion:  " + fmt(t.effectiveCompletionDate));
        lines.push("  dropDate:             " + fmt(t.dropDate));
        lines.push("  effectiveDrop:        " + fmt(t.effectiveDropDate));
        lines.push("");
    });
    console.log(lines.join("\n"));
})();
```
