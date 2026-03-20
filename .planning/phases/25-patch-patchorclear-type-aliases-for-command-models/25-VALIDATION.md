---
phase: 25
slug: patch-patchorclear-type-aliases-for-command-models
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-20
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_contracts_type_aliases.py -x -v` |
| **Full suite command** | `uv run python -m pytest -x --timeout=60` |
| **Estimated runtime** | ~11 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_contracts_type_aliases.py -x -v`
- **After every plan wave:** Run `uv run python -m pytest -x --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 11 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | TYPE-01 | unit | `uv run python -m pytest tests/test_contracts_type_aliases.py -k "SchemaIdentical or NoAliasLeakage" -v` | ✅ | ✅ green |
| 25-01-02 | 01 | 1 | TYPE-02 | unit | `uv run python -m pytest tests/test_contracts_type_aliases.py -k "SchemaIdentical or NoAliasLeakage" -v` | ✅ | ✅ green |
| 25-01-03 | 01 | 1 | TYPE-03 | unit | `uv run python -m pytest tests/test_contracts_type_aliases.py -k "SchemaIdentical" -v` | ✅ | ✅ green |
| 25-01-04 | 01 | 1 | TYPE-04 | unit | `uv run python -m pytest tests/test_contracts_type_aliases.py -k "ChangedFields" -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement Coverage Detail

### TYPE-01: Patchable fields annotated with `Patch[T]`

**Direct tests (13 in `test_contracts_type_aliases.py`):**
- `TestSchemaIdentical` (4 tests) — proves Patch[T] annotations produce identical JSON schema to raw unions
- `TestNoAliasLeakage` (4 tests) — proves no `Patch_` names leak into schema `$defs`
- `TestChangedFields::test_tag_action_add` — exercises `Patch[list[str]]` field

**Indirect coverage (343 references across 5 test files):**
- `test_service.py` (241 occurrences) — exercises EditTaskCommand, TagAction, MoveAction through service layer
- `test_service_domain.py` (34 occurrences) — exercises domain logic with aliased models
- `test_models.py` (36 occurrences) — exercises model construction and validation

### TYPE-02: Clearable fields annotated with `PatchOrClear[T]`

- `TestSchemaIdentical` (4 tests) — proves PatchOrClear[T] annotations produce identical schema
- `TestChangedFields::test_required_plus_optional_fields` — exercises `PatchOrClear[str]` with `note=None`
- Service tests exercise `due_date`, `defer_date`, `planned_date`, `estimated_minutes` PatchOrClear fields

### TYPE-03: JSON schema identical before/after migration

- `TestSchemaIdentical` (4 tests) — byte-for-byte comparison for EditTaskCommand, EditTaskActions, TagAction, MoveAction
- `TestNoAliasLeakage` (4 tests) — no alias type names in schema output

### TYPE-04: `changed_fields()` returns only explicitly set fields

- `TestChangedFields` (5 tests):
  - `test_only_required_field` — `EditTaskCommand(id="t1")` → `{"id": "t1"}`
  - `test_required_plus_optional_fields` — `EditTaskCommand(id="t1", name="x", note=None)` → includes None
  - `test_tag_action_add` — `TagAction(add=["urgent"])` → `{"add": ["urgent"]}`
  - `test_move_action_ending_none_is_inbox` — `MoveAction(ending=None)` → `{"ending": None}` (None = inbox)
  - `test_edit_task_actions_lifecycle` — `EditTaskActions(lifecycle="complete")` → `{"lifecycle": "complete"}`

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 11s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-20

---

## Validation Audit 2026-03-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 4 requirements (TYPE-01 through TYPE-04) have full automated coverage via 13 dedicated tests in `tests/test_contracts_type_aliases.py`, plus 343 indirect references across 5 test files. Full suite: 610 passed.
