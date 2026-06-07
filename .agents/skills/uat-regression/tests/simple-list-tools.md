---
suite: simple-list-tools
display: Simple List Tools
test_count: 23

discovery:
  needs:
    - type: tag
      label: tag-a
      filters: [available]
    - type: tag
      label: tag-blocked
      filters: [blocked]
    - type: tag
      label: tag-dropped
      filters: [dropped]
    - type: folder
      label: folder-a
      filters: [available]
    - type: folder
      label: folder-nested
      filters: [available, has_parent]
    - type: folder
      label: folder-dropped
      filters: [dropped]
    - type: perspective
      label: persp-a
  counts:
    - label: tags-default
      type: tag
      filters: [not_dropped]
    - label: folder-avail-only
      type: folder
      filters: [available]
    - label: folder-all
      type: folder

setup: |
  No task creation needed — discovery only.

  Present all discovered entities to user in a table and confirm.

manual_actions:
  - "tag-blocked: If no blocked tags exist, ask user to put a tag 'on hold' in OmniFocus (Tags perspective > right-click > Status > On Hold)."
  - "tag-dropped: If no dropped tags exist, ask user to drop a tag in OmniFocus (Tags perspective > right-click > Status > Dropped)."
  - "folder-dropped: If no dropped folders exist, ask user to drop a folder in OmniFocus."
  - "folder-nested: If no nested folders exist, ask user to create a folder inside another folder."
  - "persp-a: If no custom perspectives exist, ask user to create one (Perspectives > + button)."
---

# Simple List Tools Test Suite

Tests `list_tags`, `list_folders`, and `list_perspectives` — three tools sharing identical architecture (fetch-all + Python filter + paginate), combined into one suite. Covers availability defaults, `ALL` shorthand, enriched parent references, search, pagination, null/empty filter rejection, and cross-tool consistency.

## Conventions

- **Discovery-based setup.** This suite uses real tags, folders, and perspectives from the user's OmniFocus database. Tags, folders, and perspectives cannot be created via MCP tools. Setup discovers existing entities and maps them to test profiles.
- **Response size control.** Every call MUST include `limit` to cap response size. Use `limit: 0` for count-only checks, `limit: 1–5` for presence/absence verification.
- **Approximate counts.** `total` assertions use expected counts from discovered entities. If the user's database changes between setup and testing, adjust expectations.
- **Read-only suite.** All three tools are idempotent. No cleanup is needed.

## Tests

### 1. list_tags

#### Test 1a: No filters — default availability
1. `list_tags` with `limit: 5`
2. PASS if: tag-a appears in results; tag-dropped does NOT appear; `total` equals **tag-default-total** (available + blocked tags only — default excludes dropped)

#### Test 1b: Search
1. `list_tags` with `search: "<unique-substring-of-tag-a-name>", limit: 5`
2. PASS if: tag-a appears in results; unrelated tags excluded; `total` reflects only search matches

#### Test 1c: Availability — include DROPPED
1. `list_tags` with `availability: ["available", "blocked", "dropped"], limit: 5, search: "<tag-dropped-name-substring>"`
2. PASS if: tag-dropped appears in results (now visible because DROPPED is included)

#### Test 1d: Availability — AVAILABLE only
1. `list_tags` with `availability: ["available"], limit: 0`
2. Store `total` as **avail-only-count**
3. PASS if: avail-only-count ≤ **tag-default-total** (fewer or equal — blocked tags now excluded)
4. If tag-blocked was found: `list_tags` with `availability: ["available"], search: "<tag-blocked-name-substring>", limit: 1`
5. PASS if: `total: 0` — blocked tag is excluded when only AVAILABLE requested

#### Test 1e: Pagination — limit + offset
1. `list_tags` with `limit: 2`
2. PASS if: exactly 2 items returned; `hasMore: true` (assuming > 2 tags exist); `total` equals **tag-default-total**
3. `list_tags` with `limit: 2, offset: 2`
4. PASS if: exactly 2 items returned; items are different from step 1 (second page); `total` unchanged

#### Test 1f: limit=0 — count only
1. `list_tags` with `limit: 0`
2. PASS if: `items` is empty array; `total` equals **tag-default-total** (> 0); `hasMore: true` (correct — more items exist beyond the zero requested)

#### Test 1g: ALL shorthand
1. `list_tags` with `availability: ["ALL"], limit: 5, search: "<tag-dropped-name-substring>"`
2. PASS if: tag-dropped appears in results (ALL expands to available + blocked + dropped — all three tag states)

### 2. list_folders

#### Test 2a: No filters — AVAILABLE only default
1. `list_folders` with `limit: 5`
2. PASS if: folder-a appears; folder-dropped does NOT appear; `total` equals **folder-avail-only-total**
3. Compare with **folder-all-total**: PASS if **folder-avail-only-total** < **folder-all-total** (confirming the restrictive default excludes dropped folders)

#### Test 2b: Include DROPPED
1. `list_folders` with `availability: ["available", "dropped"], search: "<folder-dropped-name-substring>", limit: 5`
2. PASS if: folder-dropped appears in results (now visible with DROPPED included)
3. `list_folders` with `availability: ["available", "dropped"], limit: 0`
4. PASS if: `total` equals **folder-all-total**

#### Test 2c: Search
1. `list_folders` with `search: "<unique-substring-of-folder-a-name>", limit: 5`
2. PASS if: folder-a appears; unrelated folders excluded

#### Test 2d: Parent hierarchy
1. `list_folders` with `search: "<folder-nested-name-substring>", limit: 3`
2. PASS if: folder-nested appears with `parent` as `{id, name}` (enriched FolderRef, not a bare ID string); the parent ID corresponds to a real folder (cross-reference with discovery data)

#### Test 2e: Pagination — limit + offset
1. `list_folders` with `limit: 2`
2. PASS if: exactly 2 items returned; `hasMore: true` (assuming > 2 available folders); `total` equals **folder-avail-only-total**
3. `list_folders` with `limit: 2, offset: 2`
4. PASS if: items differ from step 1 (second page); `total` unchanged

#### Test 2f: ALL shorthand
1. `list_folders` with `availability: ["ALL"], limit: 0`
2. PASS if: `total` equals **folder-all-total** (ALL expands to available + dropped — the two folder states; no "blocked" state for folders)

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

#### Test 4b: ALL mixed with other values — warning
1. `list_tags` with `availability: ["ALL", "available"], limit: 5`
2. PASS if: warning mentions "'ALL' already includes every status"; results still include tags (ALL is still expanded despite the redundancy)

### 5. Edge Cases

#### Test 5a: Empty result — search no match
1. `list_tags` with `search: "xyzzy_definitely_no_match_99", limit: 5`
2. PASS if: `items` is empty array; `total: 0`; `hasMore: false`

#### Test 5b: Response shape + camelCase
1. Use a tag result from test 1a, a folder result from test 2a, and a perspective result from test 3a
2. PASS if:
   - All responses have top-level fields `items` (array), `total` (number), `hasMore` (boolean — not `has_more`)
   - Tag objects include: `id`, `name`, `availability`, `childrenAreMutuallyExclusive` (not `children_are_mutually_exclusive`), `parent` as `{id, name}` or null (enriched TagRef, not a bare ID string)
   - Folder objects include: `id`, `name`, `availability`, `parent` as `{id, name}` or null (enriched FolderRef, not a bare ID string)
   - Perspective objects include: `id`, `name`, `builtin`
   - No snake_case field names appear anywhere in any response

### 6. Null/Empty Filter Rejection

Run each INDIVIDUALLY (they will error):

#### Test 6a: search: null
1. `list_tags` with `search: null`
2. PASS if: error says "'search' cannot be null" and suggests omitting the field

#### Test 6b: availability: []
1. `list_folders` with `availability: []`
2. PASS if: error says "'availability' cannot be empty" and mentions using `["ALL"]` as an alternative

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Tags: no filters | Default availability returns available + blocked; dropped excluded | |
| 1b | Tags: search | Substring match on tag name finds the tag | |
| 1c | Tags: +DROPPED | Dropped tags appear when DROPPED included in availability | |
| 1d | Tags: AVAILABLE only | Blocked tags excluded when only AVAILABLE requested | |
| 1e | Tags: pagination | limit + offset; second page has different items | |
| 1f | Tags: limit=0 | Count-only; empty items, total > 0 | |
| 1g | Tags: ALL shorthand | `["ALL"]` returns all 3 tag states (available + blocked + dropped) | |
| 2a | Folders: no filters | Default returns AVAILABLE only (more restrictive than tags) | |
| 2b | Folders: +DROPPED | Dropped folders appear when DROPPED included | |
| 2c | Folders: search | Substring match on folder name finds the folder | |
| 2d | Folders: parent hierarchy | Nested folder shows non-null parent ID | |
| 2e | Folders: pagination | limit + offset; second page has different items | |
| 2f | Folders: ALL shorthand | `["ALL"]` returns available + dropped (the two folder states) | |
| 3a | Perspectives: no filters | Returns custom perspectives, total > 0 | |
| 3b | Perspectives: search | Substring match on perspective name finds it | |
| 3c | Perspectives: builtin flag | All returned perspectives have builtin: false, non-null id | |
| 3d | Perspectives: pagination | limit + offset; different items per page | |
| 4a | Cross-tool: availability defaults | Tags default to avail+blocked; folders default to avail only | |
| 4b | Cross-tool: ALL mixed warning | `["ALL", "available"]` → warning about redundancy; results still complete | |
| 5a | Edge: empty result | Impossible search → items [], total 0, hasMore false | |
| 5b | Edge: response shape + camelCase | All three tools use camelCase; tag/folder `parent` is enriched `{id, name}` ref | |
| 6a | Null: search | `search: null` → cannot be null, suggests omitting | |
| 6b | Empty: availability | `availability: []` → cannot be empty, mentions `["ALL"]` | |
