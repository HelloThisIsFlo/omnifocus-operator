---
phase: 08-realbridge-and-end-to-end-validation
plan: 02
subsystem: safety, uat
tags: [safe-01, safe-02, ci, uat, coverage, test-audit]

# Dependency graph
requires:
  - phase: 08-realbridge-and-end-to-end-validation
    plan: 01
    provides: SAFE-01 factory guard, refactored test suite
provides:
  - CI safety grep step (SAFE-01 enforcement in pipeline)
  - pytest testpaths exclusion for uat/
  - Coverage omit for simulator/__main__.py and __main__.py
  - CLAUDE.md SAFE-01/SAFE-02 documentation for AI agents
  - UAT directory structure with read-only validation script
affects: [ci-pipeline, developer-experience, agent-safety]

# Tech tracking
tech-stack:
  added: []
  patterns: [CI grep safety enforcement, testpaths exclusion, coverage omit for subprocess-tested modules]

key-files:
  created:
    - uat/README.md
    - uat/test_read_only.py
  modified:
    - .github/workflows/ci.yml
    - pyproject.toml
    - CLAUDE.md
---

# Plan 08-02 Summary

## What was built

**Task 1 — CI safety, pytest config, coverage, CLAUDE.md (COMPLETE):**
- Added `Safety check (SAFE-01)` step to CI pipeline that greps test files for `RealBridge` references and fails the build
- Configured `testpaths = ["tests"]` in pyproject.toml to exclude `uat/` from pytest discovery
- Added coverage omit for `simulator/__main__.py` and `__main__.py` (subprocess-tested, not importable)
- Documented SAFE-01 and SAFE-02 rules in CLAUDE.md for AI agent awareness
- Verified TEST-02 (full pipeline via InMemoryBridge) and TEST-03 (all 5 layers have tests)
- 165 tests passing, 98.35% coverage

**Task 2 — UAT framework (FILES CREATED, CHECKPOINT FAILED):**
- Created `uat/README.md` with UAT philosophy and safety documentation
- Created `uat/test_read_only.py` with read-only dump validation script
- Verified `uv run pytest --collect-only` does NOT discover uat/ files

## Checkpoint: FAILED

**Type:** human-verify
**Reason:** The UAT script cannot work because the OmniFocus-side bridge script does not exist yet.

### Root cause

`_trigger_omnifocus()` builds a URL with only `arg=` but no `script=` parameter:
```python
url = f"omnifocus:///omnijs-run?arg={encoded_arg}"
```

The `omnifocus:///omnijs-run` URL scheme requires a `script=` parameter containing the JavaScript to execute inside OmniFocus. Without it, OmniFocus receives the URL but has no code to run.

Additionally, the research-phase bridge script (`.research/operatorBridgeScript.js`) uses a different IPC protocol (different directory, different filename convention) than what `RealBridge` implements. A new bridge script must be authored from scratch to match `RealBridge`'s IPC protocol.

### What's needed (separate phase)

1. Author the OmniFocus-side JavaScript bridge script matching RealBridge's IPC protocol
2. JavaScript tests for the bridge script logic
3. Integration into `_trigger_omnifocus()` (inline from a reviewable file)
4. End-to-end UAT against live OmniFocus

## Self-Check: PARTIAL

- [x] CI safety grep step added
- [x] pytest testpaths configured
- [x] Coverage omit configured
- [x] CLAUDE.md updated with SAFE-01/02
- [x] UAT files created
- [ ] UAT script validated against real OmniFocus (BLOCKED — bridge script missing)

## Deviations

| What | Expected | Actual | Impact |
|------|----------|--------|--------|
| UAT checkpoint | Pass after human runs script | Failed — bridge script missing | Phase cannot fully complete; needs inserted phase for bridge script |

## Stats

- Commits: 2 (6a97d91, 8aab526)
- Tests: 165 passing, 98.35% coverage
- Duration: Task 1 + Task 2 files committed; checkpoint failed at human verification
