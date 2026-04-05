# Simple List Tools Test Suite

Tests `list_tags`, `list_folders`, and `list_perspectives` — three tools sharing identical architecture (fetch-all + Python filter + paginate), combined into one suite because their individual coverage would be thin and repetitive.

## Conventions

- **Discovery-based setup.** This suite uses real tags, folders, and perspectives from the user's OmniFocus database. Tags, folders, and perspectives cannot be created via MCP tools. Setup discovers existing entities and maps them to test profiles.
- **Response size control.** Every call MUST include `limit` to cap response size. Use `limit: 0` for count-only checks, `limit: 1–5` for presence/absence verification.
- **Approximate counts.** `total` assertions use expected counts from discovered entities. If the user's database changes between setup and testing, adjust expectations.
- **Read-only suite.** All three tools are idempotent. No cleanup is needed.

## Setup

### Step 1 — Discover Entities

Run these calls to survey the user's database:

1. `list_tags` with `limit: 10` — scan available+blocked tags (default availability)
2. `list_tags` with `availability: ["DROPPED"], limit: 5` — check for dropped tags
3. `list_folders` with `availability: ["AVAILABLE", "DROPPED"], limit: 20` — all folders, scan for parent-child pairs and dropped folders
4. `list_folders` with `limit: 0` — count of available-only (default)
5. `list_perspectives` with `limit: 10` — scan custom perspectives

Build these profiles:

**Tag profiles:**

| Profile | Requirements | Stored As |
|---------|-------------|-----------|
| **tag-a** | Available, recognizable searchable name | Name, ID |
| **tag-blocked** | `availability: "blocked"` (if one exists) | Name, ID |
| **tag-dropped** | `availability: "dropped"` (if one exists) | Name, ID |

**Folder profiles:**

| Profile | Requirements | Stored As |
|---------|-------------|-----------|
| **folder-a** | Available, recognizable searchable name | Name, ID |
| **folder-nested** | A folder with a non-null `parent` field (child of another folder) | Name, ID, parent ID |
| **folder-dropped** | `availability: "dropped"` (if one exists) | Name, ID |

**Perspective profiles:**

| Profile | Requirements | Stored As |
|---------|-------------|-----------|
| **persp-a** | A custom perspective with a searchable name | Name, ID |

Also record:
- **tag-default-total**: `total` from call 1 (available+blocked count)
- **folder-avail-only-total**: `total` from call 4 (available-only count)
- **folder-all-total**: `total` from call 3 (available+dropped count)

Present discoveries to the user in a table and confirm before proceeding.

### Manual Actions

If any profile is missing:

- **tag-blocked**: If no blocked tags exist, ask the user to put a tag "on hold" in OmniFocus (Tags perspective → right-click → Status → On Hold). Wait for confirmation.
- **tag-dropped**: If no dropped tags exist, ask the user to drop a tag in OmniFocus (Tags perspective → right-click → Status → Dropped). Wait for confirmation.
- **folder-dropped**: If no dropped folders exist, ask the user to drop a folder in OmniFocus. Wait for confirmation.
- **folder-nested**: If no nested folders exist, ask the user to create a folder inside another folder. Wait for confirmation.
- **persp-a**: If no custom perspectives exist, ask the user to create one (Perspectives → + button). Wait for confirmation.

After manual actions, re-run the relevant discovery call to confirm the entity is now visible.

## Tests

### 1. list_tags

#### Test 1a: No filters — default availability
1. `list_tags` with `limit: 5`
2. PASS if: tag-a appears in results; tag-dropped does NOT appear; `total` equals **tag-default-total** (available + blocked tags only — default excludes dropped)

#### Test 1b: Search
1. `list_tags` with `search: "<unique-substring-of-tag-a-name>", limit: 5`
2. PASS if: tag-a appears in results; unrelated tags excluded; `total` reflects only search matches

#### Test 1c: Availability — include DROPPED
1. `list_tags` with `availability: ["AVAILABLE", "BLOCKED", "DROPPED"], limit: 5, search: "<tag-dropped-name-substring>"`
2. PASS if: tag-dropped appears in results (now visible because DROPPED is included)

#### Test 1d: Availability — AVAILABLE only
1. `list_tags` with `availability: ["AVAILABLE"], limit: 0`
2. Store `total` as **avail-only-count**
3. PASS if: avail-only-count ≤ **tag-default-total** (fewer or equal — blocked tags now excluded)
4. If tag-blocked was found: `list_tags` with `availability: ["AVAILABLE"], search: "<tag-blocked-name-substring>", limit: 1`
5. PASS if: `total: 0` — blocked tag is excluded when only AVAILABLE requested

#### Test 1e: Pagination — limit + offset
1. `list_tags` with `limit: 2`
2. PASS if: exactly 2 items returned; `hasMore: true` (assuming > 2 tags exist); `total` equals **tag-default-total**
3. `list_tags` with `limit: 2, offset: 2`
4. PASS if: exactly 2 items returned; items are different from step 1 (second page); `total` unchanged

#### Test 1f: limit=0 — count only
1. `list_tags` with `limit: 0`
2. PASS if: `items` is empty array; `total` equals **tag-default-total** (> 0); `hasMore: true` (correct — more items exist beyond the zero requested)

### 2. list_folders

#### Test 2a: No filters — AVAILABLE only default
1. `list_folders` with `limit: 5`
2. PASS if: folder-a appears; folder-dropped does NOT appear; `total` equals **folder-avail-only-total**
3. Compare with **folder-all-total**: PASS if **folder-avail-only-total** < **folder-all-total** (confirming the restrictive default excludes dropped folders)

#### Test 2b: Include DROPPED
1. `list_folders` with `availability: ["AVAILABLE", "DROPPED"], search: "<folder-dropped-name-substring>", limit: 5`
2. PASS if: folder-dropped appears in results (now visible with DROPPED included)
3. `list_folders` with `availability: ["AVAILABLE", "DROPPED"], limit: 0`
4. PASS if: `total` equals **folder-all-total**

#### Test 2c: Search
1. `list_folders` with `search: "<unique-substring-of-folder-a-name>", limit: 5`
2. PASS if: folder-a appears; unrelated folders excluded

#### Test 2d: Parent hierarchy
1. `list_folders` with `search: "<folder-nested-name-substring>", limit: 3`
2. PASS if: folder-nested appears with `parent` field set to a non-null folder ID; that parent ID corresponds to a real folder (cross-reference with discovery data)

#### Test 2e: Pagination — limit + offset
1. `list_folders` with `limit: 2`
2. PASS if: exactly 2 items returned; `hasMore: true` (assuming > 2 available folders); `total` equals **folder-avail-only-total**
3. `list_folders` with `limit: 2, offset: 2`
4. PASS if: items differ from step 1 (second page); `total` unchanged

### 3. list_perspectives

#### Test 3a: No filters
1. `list_perspectives` with `limit: 5`
2. PASS if: returns custom perspectives; persp-a appears in results; `total` > 0

#### Test 3b: Search
1. `list_perspectives` with `search: "<unique-substring-of-persp-a-name>", limit: 3`
2. PASS if: persp-a appears; unrelated perspectives excluded

#### Test 3c: Builtin flag
1. Use results from test 3a (or any previous list_perspectives call)
2. PASS if: every returned perspective has `builtin: false` and a non-null `id` — custom perspectives only, no built-in perspectives leak through

#### Test 3d: Pagination — limit + offset
1. `list_perspectives` with `limit: 1`
2. PASS if: exactly 1 item returned; if `total` > 1 then `hasMore: true`
3. If `total` > 1: `list_perspectives` with `limit: 1, offset: 1`
4. PASS if: 1 item returned; different from step 1; `total` unchanged

### 4. Cross-Tool Consistency

#### Test 4a: Availability default comparison
1. Use **tag-default-total** from test 1a and **folder-avail-only-total** from test 2a
2. Verify: list_tags default includes AVAILABLE + BLOCKED (tag-blocked was not excluded in test 1a)
3. Verify: list_folders default includes AVAILABLE only (folder-dropped was excluded in test 2a, and **folder-avail-only-total** < **folder-all-total**)
4. PASS if: both defaults behave as documented — tags are more permissive (2-state default) than folders (1-state default)

### 5. Edge Cases

#### Test 5a: Empty result — search no match
1. `list_tags` with `search: "xyzzy_definitely_no_match_99", limit: 5`
2. PASS if: `items` is empty array; `total: 0`; `hasMore: false`

#### Test 5b: Response shape + camelCase
1. Use a tag result from test 1a, a folder result from test 2a, and a perspective result from test 3a
2. PASS if:
   - All responses have top-level fields `items` (array), `total` (number), `hasMore` (boolean — not `has_more`)
   - Tag objects include: `id`, `name`, `availability`, `childrenAreMutuallyExclusive` (not `children_are_mutually_exclusive`), `parent`
   - Folder objects include: `id`, `name`, `availability`, `parent`
   - Perspective objects include: `id`, `name`, `builtin`
   - No snake_case field names appear anywhere in any response

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Tags: no filters | Default availability returns available + blocked; dropped excluded | |
| 1b | Tags: search | Substring match on tag name finds the tag | |
| 1c | Tags: +DROPPED | Dropped tags appear when DROPPED included in availability | |
| 1d | Tags: AVAILABLE only | Blocked tags excluded when only AVAILABLE requested | |
| 1e | Tags: pagination | limit + offset; second page has different items | |
| 1f | Tags: limit=0 | Count-only; empty items, total > 0 | |
| 2a | Folders: no filters | Default returns AVAILABLE only (more restrictive than tags) | |
| 2b | Folders: +DROPPED | Dropped folders appear when DROPPED included | |
| 2c | Folders: search | Substring match on folder name finds the folder | |
| 2d | Folders: parent hierarchy | Nested folder shows non-null parent ID | |
| 2e | Folders: pagination | limit + offset; second page has different items | |
| 3a | Perspectives: no filters | Returns custom perspectives, total > 0 | |
| 3b | Perspectives: search | Substring match on perspective name finds it | |
| 3c | Perspectives: builtin flag | All returned perspectives have builtin: false, non-null id | |
| 3d | Perspectives: pagination | limit + offset; different items per page | |
| 4a | Cross-tool: availability defaults | Tags default to avail+blocked; folders default to avail only | |
| 5a | Edge: empty result | Impossible search → items [], total 0, hasMore false | |
| 5b | Edge: response shape + camelCase | All three tools use camelCase fields, correct top-level shape | |
