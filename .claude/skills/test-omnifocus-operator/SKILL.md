---
name: test-omnifocus-operator
description: >
  Test the OmniFocus Operator MCP server end-to-end. Calls list_all against the
  live database, builds a minimal coverage snapshot in .sandbox/, and reports
  field/boolean/enum gaps. Use this after any model change, bridge change, or
  schema migration to confirm the live output matches expectations. Also use when
  the user says "test the operator", "check if list_all works", "update the
  snapshot", or "verify the MCP server".
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__omnifocus-operator__list_all
---

# Test OmniFocus Operator

## What this skill does

Tests the `list_all` MCP tool against the user's live OmniFocus database, then
builds a minimal snapshot file that covers every field value at least once. The
snapshot serves as a compact reference for what the real data looks like — useful
for debugging, testing model changes, and verifying schema migrations.

The key insight is **coverage**: rather than grabbing random items, we select the
fewest items that together exercise every null/non-null field, every boolean
true/false, and every enum value. Gaps that can't be covered (because the value
doesn't exist anywhere in the database) are flagged for manual investigation.

## Prerequisites

- OmniFocus must be running
- The `mcp__omnifocus-operator__list_all` MCP tool must be available

## Workflow

### Step 1 — Call list_all and report counts

Call `mcp__omnifocus-operator__list_all` with no arguments. The result will be
large (millions of characters) and gets saved to a temp file automatically. Note
the file path — it's the input for subsequent steps.

Report item counts so the user can sanity-check:
```
tasks: N, projects: N, tags: N, folders: N, perspectives: N
```

### Step 2 — Build the covering snapshot

Use the bundled script to automatically select the minimum covering set:

```bash
python .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py \
  "$RESULT_FILE" \
  --build-cover
```

The output file is automatically timestamped (e.g.,
`snapshot-sample-live-20260307-110400.json`) so it never overwrites previous
snapshots. You can override with `--output <path>` if needed.

The script handles everything: greedy set-cover for null fields, boolean
true/false coverage, and enum value coverage. It prints per-entity selection
counts and a verification report.

### Step 3 — Review the report with the user

The script's output distinguishes:

- **OK** — all coverable values are represented
- **Uncoverable nulls** — a field is null across the entire database (no item
  can cover it). This may indicate a bridge bug or a field OmniFocus never
  populates for this entity type.
- **Uncoverable booleans** — a boolean value (true or false) never appears in
  the entire database
- **MISSED gaps** — a value exists in the database but wasn't selected. This
  means the script has a bug — report it.

Walk the user through any gaps. Uncoverable gaps are worth investigating:
- Could be a bridge serialization bug (field always emits null)
- Could be a field that OmniFocus structurally never populates for that entity
- Could be a boolean that's always one value by design

### Step 4 — Compare with previous snapshots (if they exist)

Check `.sandbox/` for existing snapshots (`snapshot-sample.json`,
`snapshot-sample-live.json`). If found, briefly compare schemas:

- New fields added?
- Fields removed?
- Field type changes? (e.g., `status` replaced by `urgency`/`availability`)
- Different enum values?

Note differences for the user — these confirm that a migration worked or
highlight unexpected changes.

### Step 5 — Analyze the snapshot independently (optional)

If the user wants to verify an existing snapshot without rebuilding, or check a
snapshot against the full database:

```bash
# Analyze a snapshot on its own (no full-DB comparison)
python .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py \
  .sandbox/snapshot-sample-live.json

# Analyze with full-DB reference (shows uncoverable vs missed)
python .claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py \
  .sandbox/snapshot-sample-live.json \
  --full-db "$RESULT_FILE"
```

## Script reference

The analysis script lives at:
```
.claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py
```

**Modes:**
- `analyze_snapshot.py <file>` — analyze coverage of a snapshot
- `analyze_snapshot.py <file> --full-db <full.json>` — analyze with uncoverable detection
- `analyze_snapshot.py <full.json> --build-cover --output <out.json>` — build minimal covering set

**How enum detection works:** A string field is classified as an "enum" only if
it has <= 20 distinct values AND a low uniqueness ratio (< 5%). This prevents
dates and IDs from being treated as enums — only fields like `status`,
`urgency`, `availability` qualify.

**How the covering algorithm works:**
1. Greedy null coverage — repeatedly pick the item that covers the most remaining null fields
2. Boolean coverage — for each boolean field, ensure both true and false appear
3. Enum coverage — for each enum field, ensure every distinct value appears
