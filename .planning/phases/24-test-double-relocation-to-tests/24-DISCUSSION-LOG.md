# Phase 24: Test Double Relocation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-20
**Phase:** 24-test-double-relocation-to-tests
**Areas discussed:** Directory layout, Mixed-file handling, Enforcement strategy

---

## Directory layout

### Where should test doubles live inside tests/?

| Option | Description | Selected |
|--------|-------------|----------|
| tests/doubles/ (Recommended) | Dedicated package with __init__.py. Clean separation. Import: from tests.doubles.bridge import InMemoryBridge | ✓ |
| tests/doubles/ mirroring src/ | Mirror the src/ package structure inside doubles/. More directories but matches mental model. | |
| tests/support/ | Generic name for test utilities. Same flat layout but different name. | |

**User's choice:** tests/doubles/ — flat package
**Notes:** None

### Should doubles re-export from tests/doubles/__init__.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Re-export from __init__.py (Recommended) | from tests.doubles import InMemoryBridge — convenient, one import line. Test-only, no production leakage risk. | ✓ |
| Direct module imports only | from tests.doubles.bridge import InMemoryBridge — explicit, mirrors Phase 19/23 pattern. | |

**User's choice:** Re-export from __init__.py
**Notes:** None

### conftest.py factory functions — move or stay?

| Option | Description | Selected |
|--------|-------------|----------|
| Leave in conftest.py (Recommended) | Pytest fixtures/factories, not test doubles. Standard pytest location. | ✓ |
| Move to tests/doubles/ | Consolidate all test infrastructure in one place. | |

**User's choice:** Leave in conftest.py
**Notes:** None

---

## Mixed-file handling

### How should ConstantMtimeSource be extracted from mtime.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete from mtime.py, recreate in tests/doubles/mtime.py (Recommended) | Surgical extract. Production mtime.py becomes purely production. Clean cut. | ✓ |
| Move entire mtime.py, re-import production classes | Breaks src/tests boundary — not viable. | |
| Keep ConstantMtimeSource in mtime.py | Pragmatic but doesn't satisfy INFRA-08. | |

**User's choice:** Surgical extract — delete from production, recreate in tests/doubles
**Notes:** "Both ConstantMtimeSource and FileMtimeSource should explicitly implement MtimeSource protocol — it's just one line." User specifically requested protocol conformance on both the existing and relocated class.

### mtime.py __all__ cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| You decide | Claude audits current __all__ lists and cleans up whatever references ConstantMtimeSource. | ✓ |
| Just remove from mtime.py __all__ | Only touch module-level __all__. | |

**User's choice:** Claude's discretion
**Notes:** None

---

## Enforcement strategy

### How to enforce src/ never imports from tests/doubles/?

| Option | Description | Selected |
|--------|-------------|----------|
| Structural only (Recommended) | Python's import system already prevents this. tests/ not on sys.path for installed packages. No CI grep needed. | ✓ |
| Structural + CI grep | Belt and suspenders. CI check greps for cross-boundary imports. | |
| CI grep only | Rely on CI check rather than structural guarantees. | |

**User's choice:** Structural only
**Notes:** None

### Negative import tests?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, for package-level imports (Recommended) | Prove old paths are broken. Mirrors Phase 19/23 pattern. | ✓ |
| No negative tests | Module files physically gone — imports fail naturally. | |

**User's choice:** Yes, negative import tests
**Notes:** None

---

## Claude's Discretion

- Commit strategy (single vs multi-commit)
- Order of operations
- __all__ cleanup details
- Negative import test file placement

## Deferred Ideas

None — discussion stayed within phase scope
