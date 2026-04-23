---
suite: list-tasks
display: List Tasks
test_count: 46

discovery:
  needs:
    - type: project
      label: proj-a
      filters: [active, in_folder]
    - type: tag
      label: tag-a
      filters: [available, unambiguous]
    - type: tag
      label: tag-b
      filters: [available, unambiguous]
  ambiguous:
    tags: 3
    projects: 3

setup: |
  ### Tasks
  UAT-ListTasks (inbox parent)

  Batch A — Inbox tasks (parent: UAT-ListTasks):
    LT-Inbox1          (plain — no tags, unflagged, no estimate, no note)
    LT-Tagged-A        (tags: [tag-a])
    LT-Tagged-B        (tags: [tag-b])
    LT-Tagged-AB       (tags: [tag-a, tag-b])
    LT-Flagged         (flagged: true)
    LT-Est30           (estimatedMinutes: 30)
    LT-Est120          (estimatedMinutes: 120)
    LT-NoEstimate      (plain — explicitly no estimate)
    LT-SearchNote      (note: "unicorn_xK7_marker")
    LT-Deferred        (deferDate: "2099-01-01T00:00:00Z")
    LT-Completed       (tags: [tag-a])
    LT-Dropped         (plain)

  Batch B — Project tasks (parent: proj-a, NOT under UAT-ListTasks):
    LT-ProjTask1       (estimatedMinutes: 15)
    LT-ProjTask2       (flagged: true)
    LT-ProjTask3       (plain)

  ### Post-Create
  1. complete: LT-Completed
  2. drop: LT-Dropped

  ### Verify
  LT-Completed: availability=completed
  LT-Dropped: availability=dropped
  LT-Deferred: availability=blocked

manual_actions:
  - "If no ambiguous project or tag substrings found in discovery, tell user what's needed for tests 3a and 3e (project/tag names matching multiple entities) and ask them to create duplicates."
---

# List Tasks Test Suite

Tests `list_tasks` tool — filtering by project, tags, inbox status, flagged, availability (available/blocked/remaining), estimated minutes, search, pagination, name resolution warnings, filter combinations, `$inbox` system location, lifecycle date filter auto-inclusion, availability redundancy warnings, and null/empty filter rejection.

## Conventions

- **Search isolation.** Most tests include `search: "LT-"` to restrict results to test tasks only, avoiding interference from the user's real OmniFocus data. Tests that specifically verify search behavior (1i, 1j) use different terms.
- **Approximate counts.** `total` assertions use the expected count from test tasks. If the user happens to have other tasks matching "LT-" in their database, counts may differ — adjust expectations based on setup discovery.
- **Read-only suite.** `list_tasks` is idempotent. No cleanup is needed between tests — only after the suite completes (consolidate setup tasks under cleanup umbrella).

## Tests

> **Search isolation:** Unless noted otherwise, every test includes `search: "LT-"` to restrict results to test tasks only.

### 1. Basic Filtering

#### Test 1a: Project filter — single match
1. `list_tasks` with `project: "<proj-a-name>", search: "LT-"`
2. PASS if: LT-ProjTask1, LT-ProjTask2, LT-ProjTask3 appear in results; inbox LT-* tasks (LT-Inbox1, LT-Flagged, etc.) do NOT appear

#### Test 1b: Project filter — by ID
1. `list_tasks` with `project: "<proj-a-id>", search: "LT-"`
2. PASS if: same results as 1a — ID bypasses name resolution entirely

#### Test 1c: Tag filter — single tag
1. `list_tasks` with `tags: ["<tag-a-name>"], search: "LT-"`
2. PASS if: LT-Tagged-A and LT-Tagged-AB appear; LT-Tagged-B does NOT appear

#### Test 1d: Tag filter — multiple tags (OR logic)
1. `list_tasks` with `tags: ["<tag-a-name>", "<tag-b-name>"], search: "LT-"`
2. PASS if: LT-Tagged-A, LT-Tagged-B, and LT-Tagged-AB all appear (tasks matching ANY listed tag are included)

#### Test 1e: inInbox: true
1. `list_tasks` with `inInbox: true, search: "LT-"`
2. PASS if: inbox tasks appear (LT-Inbox1, LT-Flagged, LT-Tagged-*, etc.); project tasks (LT-ProjTask1-3) do NOT appear; inbox tasks have `project: {id: "$inbox", name: "Inbox"}`

#### Test 1f: inInbox: false
1. `list_tasks` with `inInbox: false, search: "LT-"`
2. PASS if: project tasks (LT-ProjTask1-3) appear; inbox tasks do NOT appear; project tasks have `project.id` matching the real project (not `"$inbox"`)

#### Test 1g: Flagged filter
1. `list_tasks` with `flagged: true, search: "LT-"`
2. PASS if: LT-Flagged and LT-ProjTask2 appear (both flagged); unflagged tasks do NOT appear

#### Test 1h: Estimated minutes max
1. `list_tasks` with `estimatedMinutesMax: 50, search: "LT-"`
2. PASS if: LT-Est30 (30 min) and LT-ProjTask1 (15 min) appear; LT-Est120 (120 min) does NOT appear

#### Test 1i: Search — name match
1. `list_tasks` with `search: "SearchNote"` (no "LT-" — testing search itself)
2. PASS if: LT-SearchNote appears in results (substring match on task name)

#### Test 1j: Search — note match
1. `list_tasks` with `search: "unicorn_xK7_marker"` (matches only note content)
2. PASS if: LT-SearchNote appears in results (substring match on note field)

### 2. Availability

#### Test 2a: Default availability
1. `list_tasks` with `search: "LT-"` (no availability specified)
2. PASS if: LT-Completed and LT-Dropped do NOT appear; all other LT-* tasks (including LT-Deferred) DO appear — default is AVAILABLE + BLOCKED

#### Test 2e: AVAILABLE only
1. `list_tasks` with `availability: ["available"], search: "LT-"`
2. PASS if: LT-Deferred does NOT appear (it is BLOCKED/deferred); LT-Completed and LT-Dropped also absent

#### Test 2f: REMAINING shorthand
1. `list_tasks` with `availability: ["remaining"], search: "LT-"`
2. PASS if: same result set as test 2a (default availability) — `remaining` = available + blocked. LT-Completed and LT-Dropped excluded. All other LT-* tasks present including LT-Deferred.

#### Test 2g: Empty availability — zero items
1. `list_tasks` with `availability: [], search: "LT-"`
2. PASS if: `items` is empty array; `total: 0`; `hasMore: false`. Empty list is valid and returns nothing — useful when combined with lifecycle date filters for exclusive queries.

#### Test 2h: Exclusive lifecycle query — only completed
1. `list_tasks` with `availability: [], completed: "all", search: "LT-"`
2. PASS if: ONLY LT-Completed appears. No remaining tasks. The lifecycle auto-include adds COMPLETED on top of the empty availability base, producing exclusively lifecycle results.

#### Test 2i: REMAINING + available redundancy — W-004
1. `list_tasks` with `availability: ["available", "remaining"], search: "LT-"`
2. PASS if: warning text includes "'remaining' already includes 'available'" (or equivalent); results still include all remaining tasks (filter works despite redundancy)

#### Test 2j: REMAINING + blocked redundancy — W-005
1. `list_tasks` with `availability: ["blocked", "remaining"], search: "LT-"`
2. PASS if: warning text includes "'remaining' already includes 'blocked'" (or equivalent); results still include all remaining tasks

### 3. Resolution Warnings

#### Test 3a: Project multi-match
1. `list_tasks` with `project: "<ambig-proj>", search: "LT-"`
2. PASS if: warning mentions "matched" with candidate project names and IDs, and suggests filtering by ID; filter IS applied to ALL matched projects (results include tasks from every matching project, but NOT tasks from unmatched projects or inbox)

#### Test 3b: Project no-match — did you mean?
1. `list_tasks` with `project: "<misspelling-of-proj-a>"` (e.g., swap/add a letter)
2. PASS if: warning contains "Did you mean:" with suggestions including the real project name

#### Test 3c: Project no-match — no suggestions
1. `list_tasks` with `project: "xyzzy_nonexistent_99"`
2. PASS if: warning says no project found matching the name; does NOT contain "Did you mean"

#### Test 3d: Tag no-match
1. `list_tasks` with `tags: ["xyzzy_nonexistent_tag_99"], search: "LT-"`
2. PASS if: warning about no tag matching; results are unfiltered by tag (tag filter was skipped)

#### Test 3e: Tag multi-match
1. `list_tasks` with `tags: ["<ambig-tag>"], search: "LT-"`
2. PASS if: warning mentions multiple tags matching with candidate IDs; filter IS applied to ALL matched tags (tasks with any of the matched tags are included)

#### Test 3f: Project name matches "Inbox" — virtual location warning
1. `list_tasks` with `project: "Inbox"`
2. PASS if: warning explains that the inbox is a virtual location, not a named project, and suggests using `project: "$inbox"` or `inInbox: true` to query inbox tasks

### 4. Pagination

#### Test 4a: Default limit
1. `list_tasks` with `search: "LT-"` (no limit specified — default 50)
2. PASS if: all available+blocked LT-* tasks returned (we have < 50 test tasks); `total` matches item count; `hasMore: false`

#### Test 4b: Custom limit
1. `list_tasks` with `search: "LT-", limit: 2`
2. PASS if: exactly 2 items returned; `hasMore: true`; `total` reflects all matching tasks (same as test 4a's total)

#### Test 4c: Offset
1. `list_tasks` with `search: "LT-", limit: 2, offset: 2`
2. PASS if: exactly 2 items returned; items are different from test 4b (second page)

#### Test 4d: Offset without limit — error
Run INDIVIDUALLY (will error):
1. `list_tasks` with `offset: 2, limit: null`
2. PASS if: error message contains "offset requires limit"

#### Test 4e: Total count consistency
1. Compare `total` from test 4a (no limit) with `total` from test 4b (limit: 2)
2. PASS if: both `total` values are identical — limit and offset do not affect the total count

#### Test 4f: limit=0 — count only
1. `list_tasks` with `search: "LT-", limit: 0`
2. PASS if: `items` is empty array; `total` > 0 (reflects all matching tasks)

### 5. Filter Combinations (AND Logic)

#### Test 5a: Project + flagged
1. `list_tasks` with `project: "<proj-a-name>", flagged: true, search: "LT-"`
2. PASS if: only LT-ProjTask2 appears (the only task both in proj-a AND flagged)

#### Test 5b: Tag + lifecycle date filter (completed auto-inclusion)
1. `list_tasks` with `tags: ["<tag-a-name>"], completed: "all", search: "LT-"`
2. PASS if: LT-Tagged-A, LT-Tagged-AB, AND LT-Completed all appear (LT-Completed has tag-a and is made visible by the `completed` date filter's auto-inclusion of COMPLETED availability)

#### Test 5c: Search + project
1. `list_tasks` with `project: "<proj-a-name>", search: "ProjTask1"`
2. PASS if: only LT-ProjTask1 appears (both project filter AND search narrow the results)

#### Test 5d: inInbox + flagged + search
1. `list_tasks` with `inInbox: true, flagged: true, search: "LT-"`
2. PASS if: only LT-Flagged appears (the only inbox task that is also flagged)

### 6. Edge Cases

#### Test 6a: Empty result set
1. `list_tasks` with `search: "xyzzy_definitely_no_match_99"`
2. PASS if: `items` is empty array; `total: 0`; `hasMore: false`

#### Test 6b: No filters at all
1. `list_tasks` with `limit: 2`
2. PASS if: returns 2 items; `total` > 0; only available+blocked tasks (default availability applied)

#### Test 6c: estimatedMinutesMax excludes no-estimate tasks
1. `list_tasks` with `estimatedMinutesMax: 999, search: "LT-"`
2. PASS if: LT-Est30, LT-Est120, and LT-ProjTask1 appear (all have estimates ≤ 999); LT-NoEstimate does NOT appear (tasks without an estimate are excluded by this filter, not treated as 0)

#### Test 6d: Response shape and camelCase
1. Use the result from any previous test (e.g., test 4a)
2. PASS if: response has top-level fields `items` (array), `total` (number), `hasMore` (boolean — not `has_more`); task objects use camelCase field names (`estimatedMinutes`, `dueDate`, `inheritedFlagged` or `inheritedDueDate` if present — no snake_case leaks); `parent` is a tagged wrapper with exactly one key (`project` or `task`), each containing `{id, name}`; `project` is always present as `{id, name}` (inbox tasks show `{id: "$inbox", name: "Inbox"}`); there is NO `inInbox` field

#### Test 6e: Tags partial resolution — one resolves, one doesn't
1. `list_tasks` with `tags: ["<tag-a-name>", "xyzzy_nonexistent_99"], search: "LT-"`
2. PASS if: warning for "xyzzy_nonexistent_99" (no tag match); BUT tag-a filter IS still applied — only tasks with tag-a appear (LT-Tagged-A, LT-Tagged-AB); tasks without tag-a (LT-Inbox1, LT-Flagged, etc.) do NOT appear

### 7. $inbox System Location

#### Test 7a: $inbox — filter by system location
1. `list_tasks` with `project: "$inbox", search: "LT-"`
2. PASS if: inbox tasks appear (LT-Inbox1, LT-Flagged, LT-Tagged-*, etc.); project tasks (LT-ProjTask1-3) do NOT appear; returned tasks have `project: {id: "$inbox", name: "Inbox"}`

#### Test 7b: $inbox — equivalence with inInbox: true
1. Compare results from test 7a with results from test 1e
2. PASS if: same task set returned (same IDs, same count); `total` values match

#### Test 7c: $inbox + inInbox: true — redundant accepted
1. `list_tasks` with `project: "$inbox", inInbox: true, search: "LT-"`
2. PASS if: same results as 7a; NO warning about redundancy or contradiction

#### Test 7d: $inbox + inInbox: false — contradiction error
Run INDIVIDUALLY:
1. `list_tasks` with `project: "$inbox", inInbox: false, search: "LT-"`
2. PASS if: error mentions "Contradictory filters" and explains that `$inbox` selects inbox tasks while `inInbox=false` excludes them

#### Test 7e: inInbox: true + project — contradiction error
Run INDIVIDUALLY:
1. `list_tasks` with `inInbox: true, project: "<proj-a-name>", search: "LT-"`
2. PASS if: error mentions "Contradictory filters" and explains that combining `inInbox=true` with a project filter always yields nothing

### 8. Null/Empty Filter Rejection

Run each INDIVIDUALLY (they will error):

#### Test 8a: project: null
1. `list_tasks` with `project: null`
2. PASS if: error says "'project' cannot be null" and suggests omitting the field

#### Test 8b: flagged: null
1. `list_tasks` with `flagged: null`
2. PASS if: error says "'flagged' cannot be null" and suggests omitting the field

#### Test 8c: tags: []
1. `list_tasks` with `tags: []`
2. PASS if: error says "'tags' cannot be empty" and suggests omitting the field

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Project: single match | Filter by project name; only project tasks returned | |
| 1b | Project: by ID | Filter by project ID; same results, bypasses resolution | |
| 1c | Tag: single tag | Filter by one tag; only tasks with that tag returned | |
| 1d | Tag: multiple (OR) | Filter by 2 tags; tasks with ANY of those tags returned | |
| 1e | inInbox: true | Only inbox tasks returned; project tasks excluded; inbox tasks have `project.id == "$inbox"` | |
| 1f | inInbox: false | Only project tasks returned; inbox tasks excluded; project tasks have real `project.id` | |
| 1g | Flagged filter | flagged: true returns only flagged tasks | |
| 1h | estimatedMinutesMax | Ceiling filter; tasks above max excluded | |
| 1i | Search: name match | Substring match on task name finds the task | |
| 1j | Search: note match | Substring match on note content finds the task | |
| 2a | Availability: default | Completed and dropped excluded by default | |
| 2e | Availability: AVAILABLE only | Blocked/deferred task excluded when only AVAILABLE requested | |
| 2f | Availability: REMAINING shorthand | `["remaining"]` equals default (available + blocked); completed/dropped excluded | |
| 2g | Availability: empty list | `availability: []` returns 0 items; valid input for exclusive lifecycle queries | |
| 2h | Availability: exclusive lifecycle | `availability: [], completed: "all"` → only LT-Completed; no remaining tasks | |
| 2i | Availability: REMAINING + available redundancy | W-004 — "'remaining' already includes 'available'"; results still correct | |
| 2j | Availability: REMAINING + blocked redundancy | W-005 — "'remaining' already includes 'blocked'"; results still correct | |
| 3a | Resolution: project multi-match | Ambiguous project → warning with candidates, filter applied to all matches | |
| 3b | Resolution: project did-you-mean | Misspelled project → "Did you mean?" with suggestions | |
| 3c | Resolution: project no match | Random project name → no-match warning, no suggestions | |
| 3d | Resolution: tag no-match | Random tag name → no-match warning, filter skipped | |
| 3e | Resolution: tag multi-match | Ambiguous tag → warning with candidates, filter applied to all matches | |
| 3f | Resolution: inbox name warning | `project: "Inbox"` → warning about virtual location, suggests `$inbox` | |
| 4a | Pagination: default limit | No limit → all test tasks returned, total accurate | |
| 4b | Pagination: custom limit | limit: 2 → exactly 2 items, hasMore: true | |
| 4c | Pagination: offset | limit: 2, offset: 2 → second page, different items | |
| 4d | Pagination: offset w/o limit | offset + limit: null → "offset requires limit" error | |
| 4e | Pagination: total consistency | total identical with and without limit/offset | |
| 4f | Pagination: limit=0 | Count-only; empty items, total > 0 | |
| 5a | Combo: project + flagged | AND logic; only task matching both filters returned | |
| 5b | Combo: tag + lifecycle auto-inclusion | Tag filter + `completed: "all"` reveals completed tagged task via auto-inclusion | |
| 5c | Combo: search + project | Both filters narrow; single task matches | |
| 5d | Combo: inbox + flagged + search | Triple AND filter; single matching task | |
| 6a | Edge: empty result | Impossible search → items [], total 0, hasMore false | |
| 6b | Edge: no filters | No parameters → default availability, returns tasks | |
| 6c | Edge: estimatedMinutesMax vs no-estimate | Tasks with no estimate excluded, not treated as 0 | |
| 6d | Edge: response shape + camelCase | `parent` tagged wrapper, `project` as `{id, name}`, no `inInbox` field, camelCase throughout | |
| 6e | Edge: tags partial resolution | One tag resolves, one doesn't; resolved filter still applied | |
| 7a | $inbox: filter | `project: "$inbox"` returns inbox tasks with `project.id == "$inbox"` | |
| 7b | $inbox: equivalence | Same results as `inInbox: true` (test 1e) | |
| 7c | $inbox: redundant accepted | `$inbox` + `inInbox: true` succeeds silently, no warning | |
| 7d | $inbox: contradiction (false) | `$inbox` + `inInbox: false` → contradictory filters error | |
| 7e | $inbox: contradiction (project) | `inInbox: true` + real project → contradictory filters error | |
| 8a | Null: project | `project: null` → cannot be null, suggests omitting | |
| 8b | Null: flagged | `flagged: null` → cannot be null, suggests omitting | |
| 8c | Empty: tags | `tags: []` → cannot be empty, suggests omitting | |
