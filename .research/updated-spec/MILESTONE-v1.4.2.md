# Milestone v1.4.2 -- TaskPaper Output Format

## Goal

Agents can request output in TaskPaper format for ~5x token reduction. Same data, different shape. After this milestone, read tools can return TaskPaper-formatted strings instead of JSON, dramatically reducing context window usage for large result sets.

## What to Build

### TaskPaper Output Format

Alternative serialization format offering ~5x token reduction compared to JSON.

**Configuration:** Server-level setting (env var or config flag -- TBD). When active, all read tools return TaskPaper-formatted strings instead of JSON.

**Important:** TaskPaper must carry hierarchy information by default. The format naturally does this via indentation — ensure this is preserved so agents can see parent/child structure without extra queries. This complements the `order` integer field (v1.3.2) which provides programmatic ordering.

**Note:** Existing research on TaskPaper format lives in the co-work folder. Refer to that research during planning -- do not re-spec from scratch.

**Interaction with field selection (v1.4):**
- When `fields` parameter is used alongside TaskPaper output, only selected fields appear in the TaskPaper tags
- `id` and `name` are always included (TaskPaper needs a task line + identifier)

**Unknowns:**
- Exact TaskPaper format specification (refer to existing research)
- How field selection interacts with TaskPaper output
- Whether TaskPaper should be per-tool or server-wide

## Key Acceptance Criteria

- TaskPaper output is valid TaskPaper format (parseable by TaskPaper-aware tools)
- Hierarchy is preserved via indentation
- Token count is measurably lower (~5x reduction vs JSON)
- Field selection works with TaskPaper output
- Default JSON output is unchanged (backward compatible)
- All read tools support TaskPaper output when configured

## Tools After This Milestone

Fourteen (unchanged from v1.4.1 -- no new tools, new output format).
