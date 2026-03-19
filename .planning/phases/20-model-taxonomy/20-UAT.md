---
status: complete
phase: 20-model-taxonomy
source: 20-01-SUMMARY.md, 20-02-SUMMARY.md
started: 2026-03-18T16:00:00Z
updated: 2026-03-19T10:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Package Layout
expected: contracts/ has 5 files across 2 levels. models/__init__.py exports read-side only. Directory structure feels navigable.
result: pass

### 2. Three-Layer Naming
expected: Command/Result at agent boundary, RepoPayload/RepoResult at repo boundary. Naming is self-documenting — you'd reach for the right class without looking it up.
result: pass

### 3. Protocols & Boundary Signatures
expected: Three protocols in one file. Parameter names (command/payload/params) reinforce which layer you're at. Consolidated file reads well.
result: pass

### 4. Import Hygiene
expected: Service imports Commands/Results. Repos import RepoPayloads/RepoResults. Both read from models/ for domain entities. Import path tells you the role.
result: pass

### 5. Null-Means-Clear Pipeline
expected: UNSET sentinel in Command → service filters to plain dict → model_validate on RepoPayload → exclude_unset in repos. Three mechanisms, same semantic, architecturally sound.
result: pass

### 6. No Traces of the Past
expected: No docstrings or comments referencing old model names (TagActionSpec, MoveToSpec, etc.). Current code should read as if designed this way from the start.
result: pass
reported: "common.py docstring referenced old names TagActionSpec and MoveToSpec"
severity: cosmetic
fix: "Removed in 390ad16 during UAT"

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none — issue found in Test 6 was fixed inline during UAT]
