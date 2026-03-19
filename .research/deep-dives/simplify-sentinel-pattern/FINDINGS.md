# Simplify Sentinel Pattern — Findings

## Question

Can we simplify the `_Unset` / `UNSET` sentinel pattern used for patch semantics in command models?

## Background

Two external reports proposed changes:
1. **Replace sentinel entirely** with `model_fields_set` — drop `_Unset`, use plain `None` defaults
2. **Refine sentinel** — swap `_Unset` class for Enum, add `Patch[T]`/`PatchOrClear[T]` aliases, add `changed_fields()` helper

## What we tested

### Phase 1 (original investigation)
- `explore_patch_aliases.py` — Enum sentinel + Python 3.12 `type` aliases (`Patch[T]`, `PatchOrClear[T]`)
- `explore_enum_plain_unions.py` — Enum sentinel + plain union annotations (no aliases)

### Phase 2 (alias investigation)
Systematic test of every reasonable approach to define `Patch[T]` / `PatchOrClear[T]` type aliases.

- `00_baseline_current_unset.py` — Baseline: current `_Unset` class with plain unions
- `01_typealias_from_typing.py` — `TypeAlias` from typing (concrete + generic attempt)
- `02_typevar_union.py` — `TypeVar` + `Union` (pre-3.12 generic approach)
- `03_annotated_metadata.py` — `Annotated` with metadata markers
- `04_concrete_typealias_no_generics.py` — Concrete `TypeAlias` per type (no generics)
- `05_newtype.py` — `NewType` wrapping unions
- `06_type_statement_with_schema_customization.py` — Python 3.12 `type` + schema customization
- `06b_json_schema_extra_fix.py` — Deeper dive on `json_schema_extra` limitations
- `07_other_approaches.py` — `__class_getitem__` returning Union
- `08_mypy_check.py` — Mypy compatibility for passing approaches
- `08b_mypy_failing_approaches.py` — Mypy failure documentation
- `09_forward_refs_and_rebuild.py` — Forward reference + `model_rebuild()` tests
- `10_cross_module_test.py` — Full model hierarchy (mirrors real codebase)

## Key findings

### 1. `model_fields_set` replacement: rejected

- Fails silently — forgetting a check passes `None` downstream, which silently clears fields
- Current sentinel fails loudly — an unhandled `UNSET` value can't serialize, so it blows up immediately
- `model_fields_set` is instance metadata that doesn't survive model copies/transformations
- Significant refactor churn for no new functionality

### 2. Enum sentinel: worse schema output

The current `_Unset` class produces no `default` in JSON schema (Pydantic can't serialize the singleton, silently drops it). The Enum produces `"default": "UNSET"` on every optional field — agents might send the literal string `"UNSET"` thinking it's valid.

| | Current (`_Unset` class) | Enum (`_UnsetType`) |
|---|---|---|
| `default` in schema | No (dropped) | Yes — `"UNSET"` leaks |
| Singleton guarantee | Manual `__new__` | Free (Enum) |
| `bool(UNSET)` | `False` (trap) | `True` (safer) |

The truthiness improvement doesn't justify the schema regression.

### 3. `Patch[T]` / `PatchOrClear[T]` alias investigation (NEW)

#### Results table

| # | Approach | Schema clean? | `$defs` noise? | Default leak? | Mypy? | Generic? | Notes |
|---|----------|:---:|:---:|:---:|:---:|:---:|-------|
| 0 | **Baseline** (plain unions) | PASS | No | No | PASS | N/A | Reference point |
| 1a | `TypeAlias` + `TypeVar` (generic) | PASS | No | No | FAIL | Yes | mypy can't resolve `TypeAlias = T \| _Unset` with subscripting |
| 1b | Concrete `TypeAlias` | PASS | No | No | PASS | No | Same as approach 4 |
| 2 | **`TypeVar` + `Union`** | **PASS** | **No** | **No** | **PASS** | **Yes** | **Winner.** `Patch = Union[T, _Unset]` |
| 3a | `Annotated` (concrete) | PASS | No | No | PASS | No | Metadata invisible, works but not generic |
| 3b | `Annotated` (function-based) | PASS | No | No | FAIL | Sort of | `Patch(str)` — mypy can't resolve function call as type |
| 4 | Concrete `TypeAlias` | PASS | No | No | PASS | No | `PatchStr`, `PatchOrClearStr` etc. — works but verbose |
| 5 | `NewType` | PASS | No | No | N/T | No | Works at runtime but conceptually wrong (wraps union, not new type) |
| 6-base | Python 3.12 `type` statement | **FAIL** | **Yes** | No | PASS | Yes | `$defs`: `Patch_str_`, `PatchOrClear_str_` with `$ref` indirection |
| 6a | `type` + `json_schema_extra` | **FAIL** | **Yes** | No | PASS | Yes | `json_schema_extra` mutation doesn't affect `$defs`/`$ref` |
| 6b | `type` + `GenerateJsonSchema` | PASS | No | No | PASS | Yes | Works but requires custom schema_generator on every call — MCP framework calls `model_json_schema()` internally |
| 7a | `__class_getitem__` | PASS | No | No | **FAIL** | Yes | Mypy sees class name, not resolved union. Needs `type: ignore` everywhere |

#### Detailed notes on key approaches

**Approach 2 (`TypeVar` + `Union`) — THE WINNER:**
```python
T = TypeVar("T")
Patch = Union[T, _Unset]
PatchOrClear = Union[T, None, _Unset]

# Usage:
name: Patch[str] = UNSET       # schema: {"type": "string"}
note: PatchOrClear[str] = UNSET   # schema: {"anyOf": [{"type": "string"}, {"type": "null"}]}
```
- Pydantic resolves `Patch[str]` to `Union[str, _Unset]`, then drops `_Unset` via `is_instance_schema` — identical to writing `str | _Unset` directly
- Mypy resolves `Patch[str]` to `Union[str, _Unset]` — full type narrowing works
- No `$defs`, no default leak, no alias names in schema
- Works with `from __future__ import annotations` (string eval)
- Works with `model_rebuild()` for forward references
- Works with nested models (`Patch[TagAction]`, `Patch[MoveAction]`)
- Tested with full model hierarchy mirroring real codebase (`10_cross_module_test.py`)

**Why Python 3.12 `type` statement fails:**
- `type Patch[T] = T | _Unset` creates a `TypeAliasType` object that Pydantic treats as a named schema definition
- Pydantic generates a `$defs` entry for each specialization (`Patch_str_`, `Patch_bool_`, `PatchOrClear_str_`, etc.)
- Properties use `$ref` to reference these definitions instead of inlining
- `json_schema_extra` cannot fix this — Pydantic adds `$defs`/`$ref` after the callback runs
- `GenerateJsonSchema` subclass CAN fix it, but requires passing `schema_generator=` on every `model_json_schema()` call — impractical since the MCP framework controls schema generation

**Why `__class_getitem__` (7a) fails:**
- At runtime: `Patch[str]` calls `__class_getitem__` which returns `Union[str, _Unset]` — Pydantic sees the union, clean schema
- At type-check time: mypy sees `Patch[str]` as the class `Patch` subscripted — it doesn't know about the runtime `__class_getitem__` return. Every usage needs `type: ignore`

### 4. `changed_fields()` helper: keep

No downside. Checks values (not metadata), survives transformations, gives the service layer a named method instead of manual isinstance loops.

```python
def changed_fields(self) -> dict[str, Any]:
    return {
        name: value
        for name, value in self.__dict__.items()
        if not isinstance(value, _UnsetType)
    }
```

### 5. `_clean_unset_from_schema` was dead code (already removed)

`is_instance_schema` in `__get_pydantic_core_schema__` already excludes `_Unset` from JSON schema. The 40-line schema cleaner and 4 `model_json_schema` overrides were no-ops. Removed in `e0532c3` with 5 schema shape tests covering the behavior.

### 6. Baseline confirmed: current `_Unset` class does NOT leak defaults

Verified in `00_baseline_current_unset.py`. Pydantic emits a `PydanticJsonSchemaWarning` ("Default value UNSET is not JSON serializable; excluding default from JSON schema") and silently drops the default. This is the correct behavior. No `"default"` key appears in the JSON schema for any field.

## Recommendation

| Change | Verdict | Why |
|--------|---------|-----|
| Drop sentinel for `model_fields_set` | **No** | Silent failure, fragile metadata, big churn |
| Swap class for Enum | **No** | `default: "UNSET"` schema leak |
| `Patch[T]` / `PatchOrClear[T]` aliases | **Yes** | Use `Union[T, _Unset]` approach — clean schema, clean mypy, generic |
| `changed_fields()` helper | **Yes** | Low risk, useful, no schema impact |
| Remove `_clean_unset_from_schema` | **Done** | Was dead code, already removed |

## Implementation plan for aliases

Add to `contracts/base.py`:
```python
from typing import TypeVar, Union

T = TypeVar("T")
Patch = Union[T, _Unset]
PatchOrClear = Union[T, None, _Unset]
```

Then migrate field annotations across command models:
```python
# Before
name: str | _Unset = UNSET
note: str | None | _Unset = UNSET
tags: TagAction | _Unset = UNSET

# After
name: Patch[str] = UNSET
note: PatchOrClear[str] = UNSET
tags: Patch[TagAction] = UNSET
```

The change is mechanical — `Patch[X]` replaces `X | _Unset`, `PatchOrClear[X]` replaces `X | None | _Unset`. Schema output is byte-for-byte identical.
