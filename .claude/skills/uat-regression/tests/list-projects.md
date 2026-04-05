# List Projects Test Suite

Tests `list_projects` tool — filtering by folder, review due date, flagged, availability, search, pagination, folder name resolution warnings, and filter combinations.

## Conventions

- **Discovery-based setup.** This suite uses real projects from the user's OmniFocus database — projects cannot be created via `add_tasks`. Setup discovers existing entities and maps them to test profiles.
- **Response size control.** `list_projects` returns full project objects (~200 tokens each). Every call MUST include `limit` to cap response size. Use `limit: 0` for count-only checks, `limit: 1–3` for presence/absence verification, and larger limits only when testing pagination. Combine with `search` to narrow results further. Multi-step verification (presence check + absence check) is preferred over broad queries.
- **Approximate counts.** `total` assertions use expected counts from discovered projects. If the user's database changes between setup and testing, adjust expectations.
- **Read-only suite.** `list_projects` is idempotent. No cleanup is needed between tests — only after the suite completes (consolidate any setup tasks under cleanup umbrella).
- **Review date dependency.** Tests 4a–4c require projects with `nextReviewDate` set. OmniFocus manages review dates via its review system — the user may need to configure review schedules manually on test projects.

## Setup

### Step 1 — Discover Entities

Call `get_all` and scan projects and folders. Build the following profiles:

**Project profiles** (find one project per profile):

| Profile | Requirements | Stored As |
|---------|-------------|-----------|
| **proj-a** | Active (available), in a folder, recognizable name | Name, ID, folder name |
| **proj-flagged** | `flagged: true` | Name, ID |
| **proj-completed** | `availability: "completed"` | Name, ID |
| **proj-dropped** | `availability: "dropped"` | Name, ID |
| **proj-review-soon** | `nextReviewDate` within the next 2 weeks | Name, ID, nextReviewDate |

**Folder profiles:**

| Profile | Requirements | Stored As |
|---------|-------------|-----------|
| **folder-a** | The folder containing proj-a | Name, ID |
| **folder-with-multiple** | A folder containing 2+ active projects | Name, ID, project count |

**Resolution candidates:**

- **Ambiguous folder substring**: A short substring matching 2+ folder names (e.g., if "Work" and "Workout" folders exist, substring "Work" is ambiguous). Store as **ambig-folder** if found.
- **Close folder name**: Note folder-a's full name. During test 3d, craft a misspelling (swap/add a letter) — NOT a prefix/suffix that could substring-match.

Present discoveries to the user in a table and confirm before proceeding.

### Manual Actions

Follow the **Project Discovery** procedure (SKILL.md). If any profile is missing, tell the user exactly what to create or configure and wait for confirmation before proceeding.

## Tests

### 1. Basic Filtering

#### Test 1a: No filters — existence + default exclusion
1. `list_projects` with `limit: 2`
2. PASS if: returns 2 items; `total` > 2 (more projects exist than returned)
3. `list_projects` with `search: "<proj-completed-name>", limit: 0`
4. PASS if: `total: 0` — completed project excluded by default availability
5. `list_projects` with `search: "<proj-dropped-name>", limit: 0`
6. PASS if: `total: 0` — dropped project excluded by default availability

#### Test 1b: Search
1. `list_projects` with `search: "<unique-substring-of-proj-a-name>", limit: 3`
2. PASS if: proj-a appears in results; unrelated projects excluded

#### Test 1c: Flagged filter
1. `list_projects` with `flagged: true, search: "<proj-flagged-name-substring>", limit: 3`
2. PASS if: proj-flagged appears; unflagged projects do NOT appear

### 2. Availability

#### Test 2a: Default availability
1. `list_projects` with `search: "<proj-a-name-substring>", limit: 3`
2. PASS if: proj-a appears (active project included by default)
3. `list_projects` with `search: "<proj-completed-name>", limit: 0`
4. PASS if: `total: 0` — completed excluded by default
5. `list_projects` with `search: "<proj-dropped-name>", limit: 0`
6. PASS if: `total: 0` — dropped excluded by default

#### Test 2b: Include COMPLETED
1. `list_projects` with `availability: ["AVAILABLE", "BLOCKED", "COMPLETED"], search: "<proj-completed-name-substring>", limit: 3`
2. PASS if: proj-completed appears in results
3. `list_projects` with `availability: ["AVAILABLE", "BLOCKED", "COMPLETED"], search: "<proj-dropped-name>", limit: 0`
4. PASS if: `total: 0` — dropped still excluded

#### Test 2c: Include DROPPED
1. `list_projects` with `availability: ["AVAILABLE", "BLOCKED", "DROPPED"], search: "<proj-dropped-name-substring>", limit: 3`
2. PASS if: proj-dropped appears in results
3. `list_projects` with `availability: ["AVAILABLE", "BLOCKED", "DROPPED"], search: "<proj-completed-name>", limit: 0`
4. PASS if: `total: 0` — completed still excluded

#### Test 2d: All four states
1. `list_projects` with `availability: ["AVAILABLE", "BLOCKED", "COMPLETED", "DROPPED"], search: "<proj-completed-name-substring>", limit: 3`
2. PASS if: proj-completed appears
3. `list_projects` with `availability: ["AVAILABLE", "BLOCKED", "COMPLETED", "DROPPED"], search: "<proj-dropped-name-substring>", limit: 3`
4. PASS if: proj-dropped appears

#### Test 2e: AVAILABLE only
1. `list_projects` with `availability: ["AVAILABLE"], limit: 0`
2. Store `total` as **available-only-count**
3. PASS if: available-only-count ≤ total from test 1a (fewer or equal — blocked projects excluded)

### 3. Folder Resolution

#### Test 3a: Folder filter — single match
1. `list_projects` with `folder: "<folder-a-name>", limit: 3`
2. PASS if: only projects in folder-a returned; projects in other folders or without a folder do NOT appear

#### Test 3b: Folder filter — by ID
1. `list_projects` with `folder: "<folder-a-id>", limit: 3`
2. PASS if: same results as 3a — ID bypasses name resolution entirely, no warnings

#### Test 3c: Folder multi-match
1. `list_projects` with `folder: "<ambig-folder>", limit: 1`
2. PASS if: warning contains "matched" with candidate folder names and IDs, and "For exact results, filter by ID"; filter IS applied to ALL matched folders (`total` reflects projects from every matching folder)

#### Test 3d: Folder no-match — did you mean?
1. `list_projects` with `folder: "<misspelling-of-folder-a>", limit: 1`
2. PASS if: warning contains "Did you mean:" with suggestions including the real folder name; warning ends with "This filter was skipped."

#### Test 3e: Folder no-match — no suggestions
1. `list_projects` with `folder: "xyzzy_nonexistent_folder_99", limit: 1`
2. PASS if: warning says "No folder found matching 'xyzzy_nonexistent_folder_99'. This filter was skipped."; does NOT contain "Did you mean"

### 4. Review Due Within

#### Test 4a: Valid duration "1w"
1. `list_projects` with `reviewDueWithin: "1w", search: "<proj-review-soon-name-substring>", limit: 3`
2. PASS if: proj-review-soon appears (its nextReviewDate is within 1 week)

#### Test 4b: Valid duration "now"
1. `list_projects` with `reviewDueWithin: "now", limit: 3`
2. PASS if: only projects with nextReviewDate at or before the current moment returned. If proj-review-soon is in the future, it should NOT appear here (only overdue reviews match "now"). If no reviews are currently overdue, `items` may be empty — that's a valid PASS.

#### Test 4c: Valid duration "2m"
1. `list_projects` with `reviewDueWithin: "2m", limit: 0`
2. Store `total` as **review-2m-count**
3. `list_projects` with `reviewDueWithin: "1w", limit: 0`
4. PASS if: review-2m-count ≥ the 1w total (wider window captures at least as many)

#### Test 4d: Invalid format — error
Run INDIVIDUALLY (will error):
1. `list_projects` with `reviewDueWithin: "abc"`
2. PASS if: error message contains "Invalid review_due_within" and shows valid format examples ("'now', or a number followed by d/w/m/y"); no pydantic internals in the message

#### Test 4e: Zero amount "0w" — error
Run INDIVIDUALLY (will error):
1. `list_projects` with `reviewDueWithin: "0w"`
2. PASS if: error message contains "Invalid review_due_within" with format examples

### 5. Pagination

#### Test 5a: Custom limit + hasMore
1. `list_projects` with `limit: 2`
2. PASS if: exactly 2 items returned; `hasMore: true` (assuming > 2 projects exist); `total` reflects all matching projects

#### Test 5b: Total count consistency
1. `list_projects` with `limit: 0`
2. Store `total` as **count-only-total**
3. PASS if: count-only-total equals `total` from test 5a — limit does not affect the total count

#### Test 5c: Offset without limit — error
Run INDIVIDUALLY (will error):
1. `list_projects` with `offset: 2, limit: null`
2. PASS if: error message contains "offset requires limit"

#### Test 5d: limit=0 — count only
1. Use the result from test 5b (which already called `limit: 0`)
2. PASS if: `items` is empty array; `total` > 0 (reflects all matching projects)

### 6. Filter Combinations (AND Logic)

#### Test 6a: Folder + flagged
1. `list_projects` with `folder: "<folder-a-name>", flagged: true, limit: 3`
2. PASS if: only projects that are BOTH in folder-a AND flagged returned. If no project matches both, `items` is empty — that's a valid PASS showing AND logic works.

#### Test 6b: Folder + reviewDueWithin
1. `list_projects` with `folder: "<folder-with-multiple-name>", reviewDueWithin: "2m", limit: 3`
2. PASS if: results include only projects that are in the folder AND have review due within 2 months. May be empty if no projects match both — valid PASS.

#### Test 6c: Search + availability (COMPLETED)
1. `list_projects` with `search: "<substring-of-proj-completed-name>", availability: ["COMPLETED"], limit: 3`
2. PASS if: proj-completed appears; active projects do NOT appear

### 7. Edge Cases

#### Test 7a: Empty result set
1. `list_projects` with `search: "xyzzy_definitely_no_match_99", limit: 3`
2. PASS if: `items` is empty array; `total: 0`; `hasMore: false`

#### Test 7b: Response shape + camelCase
1. Use the result from any previous test (e.g., test 3a)
2. PASS if: response has top-level fields `items` (array), `total` (number), `hasMore` (boolean — not `has_more`); project objects use camelCase: `lastReviewDate`, `nextReviewDate`, `reviewInterval`, `nextTask`, `dueDate`, `deferDate`, `effectiveFlagged`, `effectiveDueDate`, `effectiveDeferDate` — no snake_case leaks

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Basic: no filters | No parameters → default availability, returns projects | |
| 1b | Basic: search | Substring match on project name finds the project | |
| 1c | Basic: flagged | flagged: true returns only flagged projects | |
| 2a | Availability: default | Completed and dropped excluded by default | |
| 2b | Availability: +COMPLETED | Completed projects appear when explicitly included | |
| 2c | Availability: +DROPPED | Dropped projects appear when explicitly included | |
| 2d | Availability: all four | All availability states; everything returned | |
| 2e | Availability: AVAILABLE only | Blocked projects excluded when only AVAILABLE requested | |
| 3a | Folder: single match | Filter by folder name; only projects in that folder returned | |
| 3b | Folder: by ID | Filter by folder ID; same results, bypasses resolution | |
| 3c | Folder: multi-match | Ambiguous folder → warning with candidates, filter applied to all | |
| 3d | Folder: did-you-mean | Misspelled folder → "Did you mean?" with suggestions | |
| 3e | Folder: no match | Random folder name → no-match warning, no suggestions | |
| 4a | Review due: 1w | Projects with review due within 1 week returned | |
| 4b | Review due: now | Only overdue reviews (nextReviewDate ≤ now) returned | |
| 4c | Review due: 2m | Wider window; total ≥ 1w total | |
| 4d | Review due: invalid format | "abc" → clean error with format examples | |
| 4e | Review due: zero amount | "0w" → clean error, zero not allowed | |
| 5a | Pagination: custom limit | limit: 2 → exactly 2 items, hasMore: true | |
| 5b | Pagination: total consistency | total identical with and without limit | |
| 5c | Pagination: offset w/o limit | offset + limit: null → "offset requires limit" error | |
| 5d | Pagination: limit=0 | Count-only; empty items, total > 0 | |
| 6a | Combo: folder + flagged | AND logic; only projects matching both filters | |
| 6b | Combo: folder + reviewDueWithin | Projects in folder with review due soon | |
| 6c | Combo: search + COMPLETED | Search across completed projects only | |
| 7a | Edge: empty result | Impossible search → items [], total 0, hasMore false | |
| 7b | Edge: response shape + camelCase | Top-level and project fields use correct camelCase names | |
