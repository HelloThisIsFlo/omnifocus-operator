# Side-by-Side Verification: SQLite flags vs OmniFocus API taskStatus

## Experiment

Selected 10 tasks where SQLite reports **both** `blocked=1` AND `overdue=1`.
Then queried the same tasks via OmniFocus Automation (`taskStatus`) to see which status wins.

## Result

**Overdue always wins over Blocked.** All 10 tasks report `taskStatus: Overdue`.

**Key takeaway:** SQLite exposes urgency (`overdue`, `dueSoon`) and availability (`blocked`, `blockedByFutureStart`) as independent flags, while the OmniFocus API collapses them into a single `taskStatus` enum with a hidden priority order. From SQLite we get the full picture — a task can be both blocked *and* overdue — whereas the API only surfaces whichever status "wins".

## Details

| # | SQLite blocked | SQLite overdue | API taskStatus | Project Status | blockedByFutureStart |
|---|:-:|:-:|---|---|:-:|
| 1 | 1 | 1 | Overdue | Overdue | 0 |
| 2 | 1 | 1 | Overdue | Overdue | 0 |
| 3 | 1 | 1 | Overdue | **Blocked** | 0 |
| 4 | 1 | 1 | Overdue | **Blocked** | 0 |
| 5 | 1 | 1 | Overdue | **Blocked** | 0 |
| 6 | 1 | 1 | Overdue | **Blocked** | 1 |
| 7 | 1 | 1 | Overdue | **Blocked** | 0 |
| 8 | 1 | 1 | Overdue | Overdue | 0 |
| 9 | 1 | 1 | Overdue | **Blocked** | 0 |
| 10 | 1 | 1 | Overdue | Overdue | 0 |

## Key Observations

1. **Overdue > Blocked**: When both flags are set, `taskStatus` returns Overdue, never Blocked.
2. **Project status doesn't matter**: Tasks in Blocked projects still report Overdue if their due date has passed. 6 of 10 tasks live in Blocked projects.
3. **Future defer date doesn't matter**: Task #6 has `blockedByFutureStart=1` with a defer date in the future, but since the due date has passed, it's still Overdue.

## Implication for Bridge

When deriving `taskStatus` from SQLite flags, check in this order:
1. Overdue (if `overdue=1`)
2. Blocked (if `blocked=1`)
3. DueSoon (if `dueSoon=1`)
4. Available / Next (remaining)

Overdue must be evaluated **before** Blocked to match OmniFocus API behavior.
