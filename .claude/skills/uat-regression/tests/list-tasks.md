---
suite: list-tasks
display: List Tasks
test_count: 67

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

  Batch C — Phase 56 presence flags + hierarchy (parent: UAT-ListTasks):
    LT-SeqParent       (type: "sequential", completesWithChildren: false)
    LT-SeqChild1       (parent: LT-SeqParent)
    LT-SeqChild2       (parent: LT-SeqParent)
    LT-Parallel        (type: "parallel" — leaf, no children)
    LT-AutoComplete    (completesWithChildren: true)
    LT-ACChild         (parent: LT-AutoComplete)
    LT-Repeating       (dueDate: "2099-06-01T12:00:00Z", repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" })
    LT-Attached        (plain — attachment added manually, see manual_actions)

  Batch D — Phase 57 parent filter (parent: UAT-ListTasks):
    LT-P57-Root        (plain — scope anchor for parent-filter tests)
    LT-P57-Child1      (parent: LT-P57-Root, tags: [tag-a] — the only tag-a-bearing descendant for AND-compose test 10e)
    LT-P57-Child2      (parent: LT-P57-Root, plain — substring "LT-P57-Child" matches Child1 AND Child2 for multi-match test 10l)
    LT-P57-Grandchild  (parent: LT-P57-Child1, plain — level-2 descendant for deep-descendants test 10d)

  ### Post-Create
  1. complete: LT-Completed
  2. drop: LT-Dropped

  ### Verify
  LT-Completed: availability=completed
  LT-Dropped: availability=dropped
  LT-Deferred: availability=blocked
  LT-SeqParent: type=sequential, completesWithChildren=false, hasChildren=true
  LT-Parallel: type=parallel, hasChildren=false
  LT-AutoComplete: completesWithChildren=true, hasChildren=true
  LT-P57-Root: hasChildren=true
  LT-P57-Child1: parent=LT-P57-Root, tag-a in tags
  LT-P57-Grandchild: parent=LT-P57-Child1

manual_actions:
  - "If no ambiguous project or tag substrings found in discovery, tell user what's needed for tests 3a and 3e (project/tag names matching multiple entities) and ask them to create duplicates."
  - "In OmniFocus, drag any file onto `LT-Attached` to add an attachment — required for test 9c (hasAttachments). The flag is cache-backed (snapshot-loaded), so ensure the attachment is in place BEFORE running the suite; a mid-suite attach may not be reflected until the next snapshot refresh."
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

### 9. Presence Flags & Hierarchy Include Group (Phase 56)

> **Phase 56 surface.** Default response now includes derived presence flags: `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential`, `dependsOnChildren` — all strip-when-false. The `hierarchy` include group exposes structural detail on demand (`hasChildren`, `type`, `completesWithChildren`). See 56-CONTEXT.md FLAG-01..05 and HIER-01..05. Assertions below are behavioral — specific field shapes, never exact warning text.

#### Test 9a: Presence flag — hasNote (T-HasNote)
1. `list_tasks` with `search: "LT-"`
2. PASS if:
   - LT-SearchNote has `hasNote: true` in its response object (it was created with `note: "unicorn_xK7_marker"`)
   - LT-Inbox1 (created plain) does NOT have a `hasNote` field at all — strip-when-false applies

#### Test 9b: Presence flag — hasRepetition (T-HasRepetition)
1. `list_tasks` with `search: "LT-"`
2. PASS if:
   - LT-Repeating has `hasRepetition: true` (a daily repetition rule was set in setup)
   - LT-Inbox1 does NOT have a `hasRepetition` field

#### Test 9c: Presence flag — hasAttachments (T-HasAttachments)
1. Precondition: the attachment manual action has been completed (any file dragged onto `LT-Attached` in OmniFocus)
2. `list_tasks` with `search: "LT-"`
3. PASS if:
   - LT-Attached has `hasAttachments: true`
   - LT-Inbox1 does NOT have a `hasAttachments` field
4. Notes: `hasAttachments` is cache-backed (batched snapshot load per CACHE-04). If the flag is missing despite an attachment being present, a snapshot refresh may be needed — retry after any other read tool call.

#### Test 9d: Presence flag — isSequential (T-IsSequential)
1. `list_tasks` with `search: "LT-"`
2. PASS if:
   - LT-SeqParent has `isSequential: true` (created with `type: "sequential"`)
   - LT-Parallel (created with `type: "parallel"`) does NOT have an `isSequential` field — strip-when-false
3. Notes: `isSequential` is an agent-behavior signal — "only the next-in-line child is available; agents reasoning about actionability must not over-count."

#### Test 9e: Presence flag — dependsOnChildren (T-DependsOnChildren)
1. `list_tasks` with `search: "LT-"`
2. PASS if:
   - LT-SeqParent has `dependsOnChildren: true` — it has children AND `completesWithChildren: false`, so the task itself is a real unit of work waiting on its children
   - LT-AutoComplete does NOT have a `dependsOnChildren` field — it has children BUT `completesWithChildren: true`, so it auto-completes when its children do (container, not waiting)
   - LT-Parallel does NOT have a `dependsOnChildren` field — leaf task, no children at all
3. Notes: Contract is `hasChildren AND NOT completesWithChildren` → flag emitted. Tasks-only; projects never emit this flag (projects are always containers — FLAG-05).

#### Test 9f: Hierarchy include group — structural fields appear on demand (T-HierarchyTask)
1. `list_tasks` with `search: "LT-SeqParent", include: ["hierarchy"]`
2. PASS if: the matched LT-SeqParent item includes all three hierarchy fields:
   - `hasChildren: true`
   - `type: "sequential"` (full enum string, not a boolean)
   - `completesWithChildren: false` (always present, including when `false`)
3. PASS also if: LT-Parallel in a separate call with the same include shows `hasChildren` absent (stripped when false), `type: "parallel"`, `completesWithChildren: <bool>` (always present).

#### Test 9g: No-suppression invariant — default flags AND hierarchy fields emit together (T-NoSuppressionInvariant)
1. `list_tasks` with `search: "LT-SeqParent", include: ["hierarchy"]`
2. PASS if: the LT-SeqParent response contains ALL FIVE fields together, no de-duplication:
   - Default-response derived flags: `isSequential: true`, `dependsOnChildren: true`
   - Hierarchy group fields: `hasChildren: true`, `type: "sequential"`, `completesWithChildren: false`
3. Notes: This is Phase 56 SC-4 — the two emission pipelines run independently. Redundancy is the contract, not a bug. If the hierarchy fields suppress the default flags (or vice versa), it's a regression.

#### Test 9h: completesWithChildren: false survives stripping (T-CompletesWithChildrenInNeverStrip)
1. `list_tasks` with `search: "LT-SeqParent", include: ["hierarchy"]`
2. PASS if: response contains `completesWithChildren: false` as a literal `false` value — the key IS present with value `false`, not absent
3. Notes: `completesWithChildren` is in `NEVER_STRIP` per PROP-08. The default stripping pipeline would normally drop `false` values, but this field is exempted because the distinction between "auto-completes" and "doesn't auto-complete" is load-bearing for agent reasoning — silence would be ambiguous.

### 10. Parent Filter & Filter Unification (Phase 57)

> **Phase 57 surface.** `list_tasks` gains a `parent` filter — single-reference (`$inbox` / exact ID / substring name match), accepts tasks AND projects, returns the resolved entity's descendant subtree at any depth. A resolved task IS the anchor (included in the result set); a resolved project is NOT (projects aren't `list_tasks` rows). `parent` and `project` share one expansion function — same entity resolved via either filter produces byte-identical task lists (UNIFY-02). Five warnings guide correct usage: FILTERED_SUBTREE (WARN-01), PARENT_RESOLVES_TO_PROJECT (WARN-02), PARENT_PROJECT_COMBINED (WARN-03), multi-match reuse (WARN-04), inbox-name-substring reuse (WARN-05). See 57-CONTEXT.md + 57-VERIFICATION.md. Warning assertions are **behavioral** — present, fluent from an agent's perspective, no internals (`type=`, `pydantic`, `input_value`, `_Unset`); never exact-string match, even for the verbatim-locked FILTERED_SUBTREE text.

> **Search isolation note.** Phase 57 tests use the parent filter itself as the scoping mechanism (the LT-P57- subtree is self-isolating). Adding `search: "LT-"` would trigger FILTERED_SUBTREE_WARNING since `search` is a dimensional filter — the warning tests do that intentionally; the other tests use the parent filter alone to keep the warning surface clean.

#### Test 10a: Parent filter — by name substring (task anchor included)
1. `list_tasks` with `parent: "LT-P57-Root"`
2. PASS if:
   - `items` contains LT-P57-Root (the resolved task IS an anchor — included in the result set even though it's not a descendant of itself)
   - `items` contains LT-P57-Child1, LT-P57-Child2, and LT-P57-Grandchild (all descendants at any depth)
   - No unrelated LT-* tasks appear (LT-SeqParent, LT-Inbox1, LT-ProjTask1, etc. are outside the subtree)
   - No filtered-subtree warning fires (scope-only query with no dimensional filters — `availability` default is explicitly excluded from the warning predicate per D-13)
3. Notes: "LT-P57-Root" is a unique substring across the test hierarchy — the single resolved match is the LT-P57-Root task. This test locks PARENT-01 + PARENT-03 + PARENT-04 (task-anchor side).

#### Test 10b: Parent filter — by task ID (resolver short-circuit)
1. `list_tasks` with `parent: "<LT-P57-Root-id>"` (use the actual OF ID from `get_all` or test 10a's response)
2. PASS if: result set is identical to test 10a — the same anchor + 3 descendants. ID bypasses name-substring resolution entirely (PARENT-02: three-step resolver, ID step wins when value is a valid OF ID)

#### Test 10c: Parent filter — `$inbox` sentinel equivalence
1. First call: `list_tasks` with `parent: "$inbox", search: "LT-"`
2. Second call: `list_tasks` with `project: "$inbox", search: "LT-"`
3. PASS if: both calls return the same task set (same IDs, same count, same order); returned inbox tasks show `project: {id: "$inbox", name: "Inbox"}`; proves `parent: "$inbox"` consumes into the same inbox-mode as `project: "$inbox"` (PARENT-07)
4. Notes: Both calls will emit FILTERED_SUBTREE_WARNING because `search` is a dimensional filter — that's expected and not the focus of this test. The contract being tested is the `$inbox` consumption equivalence, not the warning surface.

#### Test 10d: Parent filter — all descendants at any depth (PARENT-03)
1. `list_tasks` with `parent: "LT-P57-Root"`
2. PASS if: `items` contains LT-P57-Grandchild, which is a level-2 descendant (Root → Child1 → Grandchild). The expansion is BFS-unbounded — descendants at depth 1, 2, 3, etc. all included. If LT-P57-Grandchild were missing, the expansion would be shallow (regression).
3. Notes: Uses the same setup as 10a but asserts specifically on the deep-descendant contract. Locks PARENT-03.

#### Test 10e: Parent filter — AND-composes with tag filter (anchor always included, descendants filtered)
1. `list_tasks` with `parent: "LT-P57-Root", tags: ["<tag-a-name>"]`
2. PASS if:
   - LT-P57-Root appears (anchor is ALWAYS included even though it has no tag-a — this is the "resolved parent tasks are always included" clause of the filtered-subtree contract)
   - LT-P57-Child1 appears (has tag-a — survives the AND filter)
   - LT-P57-Child2 does NOT appear (descendant without tag-a — filtered out)
   - LT-P57-Grandchild does NOT appear (descendant without tag-a — filtered out)
   - FILTERED_SUBTREE_WARNING is present (scope + dimensional filter)
3. Notes: Locks PARENT-05 (AND-composition) + the nuanced anchor-vs-descendant filtering contract embedded in the FILTERED_SUBTREE_WARNING text.

#### Test 10f: Parent filter — project produces no anchor row (PARENT-04 project side)
1. `list_tasks` with `parent: "<proj-a-name>"`
2. PASS if:
   - `items` contains LT-ProjTask1, LT-ProjTask2, LT-ProjTask3 (all proj-a task descendants)
   - No row in `items` has `id` matching proj-a's project ID (projects are not `list_tasks` rows — resolved project emits no anchor)
   - No task is dropped — the project's descendants are all there, just the project itself isn't materialised as a row
3. Notes: Complements 10a's task-anchor assertion with the project-no-anchor side. Locks PARENT-04 in both directions. A PARENT_RESOLVES_TO_PROJECT_WARNING will also fire (covered separately in 10j); ignore warning diffs for this test.

#### Test 10g: Parent / project cross-filter byte-identical equivalence (UNIFY-02)
1. First call: `list_tasks` with `parent: "<proj-a-name>"`
2. Second call: `list_tasks` with `project: "<proj-a-name>"`
3. PASS if:
   - Both calls return identical `items` arrays — same IDs in the same order, same per-task fields (default projection)
   - Same `total`, same `hasMore`
   - Warnings MAY differ (parent path fires PARENT_RESOLVES_TO_PROJECT_WARNING, project path doesn't) — the byte-identicality contract is on the task payload, not the warning surface, per 57-02-SUMMARY
4. Notes: D-15 / UNIFY-02 contract gate. Proves both filters converge on the same expansion function and same repo primitive. If this ever diverges, a duplicate code path got reintroduced.

#### Test 10h: FILTERED_SUBTREE_WARNING — parent + dimensional filter (WARN-01 parent side)
1. `list_tasks` with `parent: "LT-P57-Root", flagged: true`
2. PASS if:
   - A filtered-subtree warning is present in `result.warnings`
   - Warning is fluent from an agent's perspective — communicates that resolved parent tasks are always included, descendants not matching the other filters are excluded, and returned tasks' `parent` field still points at the true parent (so fetch separately for excluded intermediates if needed)
   - Warning text contains no internals (no `type=`, `pydantic`, `input_value`, `_Unset`)
   - Results are still correct (just empty or anchor-only since no LT-P57-* task is flagged — warning is the focus, not the items)

#### Test 10i: FILTERED_SUBTREE_WARNING — project + dimensional filter, same warning (unification proof)
1. `list_tasks` with `project: "<proj-a-name>", flagged: true`
2. PASS if:
   - The SAME filtered-subtree warning fires (same text, same meaning) — proves WARN-01 is shared across both `project` and `parent` filters per D-13 (not two parallel warnings)
   - Results contain LT-ProjTask2 (the only flagged proj-a task)
   - No internals leak
3. Notes: Paired with 10h. If the two tests fire different warning texts, the "single code path" contract is broken at the warning surface.

#### Test 10j: PARENT_RESOLVES_TO_PROJECT_WARNING — all matches are projects (WARN-02)
1. `list_tasks` with `parent: "<proj-a-name>"`
2. PASS if:
   - A pedagogical warning is present advising the agent that the reference resolved to projects only (no task matched) and suggests using `project` instead for clarity
   - Warning is soft in tone (hint, not error)
   - Warning is fluent and contains no internals
   - Fires ONLY because every matched entity is a project — if any task had matched the substring, this warning would be silent (pedagogical tone, not punitive)
   - Results still include LT-ProjTask1/2/3 (the filter still works)

#### Test 10k: PARENT_PROJECT_COMBINED_WARNING — both scope filters set (WARN-03)
1. `list_tasks` with `parent: "LT-P57-Root", project: "<proj-a-name>"`
2. PASS if:
   - A soft warning about specifying both `parent` and `project` together is present
   - Warning is fluent — suggests picking one scope filter; does NOT declare the combination an error
   - Contains no internals
   - Fires independent of intersection cardinality — even though LT-P57-Root's subtree and proj-a's subtree don't overlap (empty result expected), the warning still fires on presence alone (per D-13)
   - No FILTERED_SUBTREE_WARNING fires from this call alone (no dimensional filter present — only two scope filters)

#### Test 10l: Parent multi-match warning — substring matches multiple tasks (WARN-04 reuse)
1. `list_tasks` with `parent: "LT-P57-Child"`
2. PASS if:
   - A multi-match warning is present naming the candidate matches (LT-P57-Child1 and LT-P57-Child2 both satisfy the substring)
   - Warning is fluent and suggests narrowing (e.g., filter by ID) — same shape as existing test 3a for project multi-match (reused infrastructure)
   - Results include the descendants of BOTH matched tasks: LT-P57-Child1 (anchor) + LT-P57-Grandchild (its descendant) + LT-P57-Child2 (anchor, no descendants of its own)
   - No internals leak
3. Notes: Proves `DomainLogic.check_filter_resolution` works unmodified for the new `parent` filter (D-14 / WARN-05 reuse).

#### Test 10m: Parent inbox-name-substring warning — "Inbox" substring (WARN-05 reuse)
1. `list_tasks` with `parent: "Inbox"`
2. PASS if:
   - An inbox-name-substring warning is present
   - Warning explains that the inbox is a virtual location, not a named entity, and suggests `$inbox` or `inInbox: true`
   - Warning **references the `parent` filter** that triggered it (wording adapts to the triggering filter — does NOT say `project="Inbox"` when the user wrote `parent: "Inbox"`)
   - Warning is fluent and contains no internals
3. Notes: Proves the shared warning infrastructure is parameterised so the message matches the filter the agent actually used. If the warning text still says `project="..."`, that's a regression of the fix (a prior iteration reused the constant verbatim and Flo called that out as an agent-UX wart; it has since been fixed).

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
| 9a | Presence: hasNote | Task with non-empty note emits `hasNote: true`; no-note task omits the field (strip-when-false) | |
| 9b | Presence: hasRepetition | Repeating task emits `hasRepetition: true`; non-repeating task omits | |
| 9c | Presence: hasAttachments | Task with attachment emits `hasAttachments: true` (cache-backed; requires manual attach before run) | |
| 9d | Presence: isSequential | `type: "sequential"` task emits `isSequential: true`; parallel task omits | |
| 9e | Presence: dependsOnChildren | Sequential parent w/ children + `completesWithChildren: false` emits the flag; auto-complete parent and leaf task both omit | |
| 9f | Hierarchy: include group (task) | `include: ["hierarchy"]` adds `hasChildren`, `type` (enum), `completesWithChildren` (always present) | |
| 9g | Hierarchy: no-suppression invariant | Default flags AND hierarchy fields emit together on the same task — redundancy is the contract (SC-4) | |
| 9h | Hierarchy: completesWithChildren false survives stripping | `completesWithChildren` in NEVER_STRIP — literal `false` appears in response (PROP-08) | |
| 10a | Parent: by name (task anchor) | `parent: "LT-P57-Root"` → anchor + all descendants (Root + 2 children + 1 grandchild); no warning fires (scope-only) | |
| 10b | Parent: by ID | `parent: "<Root-id>"` → same result as 10a; resolver short-circuits on ID step (PARENT-02) | |
| 10c | Parent: `$inbox` equivalence | `parent: "$inbox"` ≡ `project: "$inbox"`; same task set; same `project` wrapper on returned items (PARENT-07) | |
| 10d | Parent: deep descendants | `parent: "LT-P57-Root"` → grandchild (level-2) appears; expansion is BFS-unbounded (PARENT-03) | |
| 10e | Parent: AND-compose + anchor-kept | `parent: "LT-P57-Root", tags: [tag-a]` → anchor always included, non-matching descendants filtered out; FILTERED_SUBTREE warning fires | |
| 10f | Parent: project no-anchor | `parent: "<proj-a>"` → proj-a's task descendants but proj-a itself is NOT a row (PARENT-04 project side) | |
| 10g | Parent / project byte-identical (UNIFY-02) | Same resolved project via `parent` and `project` → byte-identical `items`/`total`/`hasMore`; warning surface may differ | |
| 10h | WARN-01 filtered-subtree (parent) | `parent: "X", flagged: true` → filtered-subtree warning present, fluent, no internals | |
| 10i | WARN-01 filtered-subtree (project, unification) | `project: "X", flagged: true` → SAME warning as 10h; proves single-warning unification | |
| 10j | WARN-02 parent-resolves-to-project | `parent: "<proj-a>"` (no tasks match substring) → pedagogical "consider `project`" hint; soft tone | |
| 10k | WARN-03 parent+project combined | `parent: "X", project: "Y"` → soft hint about specifying both scope filters; fires regardless of intersection | |
| 10l | WARN-04 parent multi-match (reuse) | `parent: "LT-P57-Child"` → multi-match warning names Child1 + Child2; results include both subtrees | |
| 10m | WARN-05 parent inbox-substring (reuse) | `parent: "Inbox"` → inbox-name-substring warning (same constant as 3f) suggesting `$inbox` / `inInbox: true` | |
