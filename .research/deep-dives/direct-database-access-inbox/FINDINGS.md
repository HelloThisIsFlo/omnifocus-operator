# Inbox Equivalence — Findings

> `containingProjectInfo IS NULL` is equivalent to `effectiveInInbox` across all 3298 tasks. Zero contradictions.

**Date:** 2026-04-08
**Database:** 3298 tasks (148 root inbox, 168 inbox subtasks, 2982 non-inbox)

---

## Question

Our `query_builder.py` uses `containingProjectInfo IS NULL` to determine inbox membership. Is this equivalent to what OmniFocus computes as `effectiveInInbox`?

## Result

**Yes — perfect equivalence.**

| Comparison | Count |
|---|---|
| Both agree inbox | 316 |
| Both agree not inbox | 2982 |
| `effectiveInInbox=1` but has project (contradiction) | **0** |
| `effectiveInInbox=0` but no project (contradiction) | **0** |

## The original bug in numbers

| `inInbox` | `effectiveInInbox` | Count | Meaning |
|---|---|---|---|
| 1 | 1 | 148 | Root inbox items — no bug |
| 0 | 1 | 168 | Inbox subtasks — **invisible to raw `inInbox`** |
| 1 | 0 | 0 | Should not happen — confirmed |
| 0 | 0 | 2982 | Non-inbox tasks — no bug |

Over half of inbox tasks (168/316 = 53%) are subtasks that the raw `inInbox` flag misses. The `containingProjectInfo IS NULL` approach catches all of them.

## Conclusion

- `containingProjectInfo IS NULL` ≡ `effectiveInInbox` — they agree on every task in the database
- Either could be used as the inbox signal; our choice of `containingProjectInfo` is validated
- The raw `inInbox` column is unreliable for subtasks and should not be used alone
