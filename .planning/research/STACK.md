# Technology Stack

**Project:** v1.3.1 First-Class References
**Researched:** 2026-04-05

## Verdict: No New Dependencies

Everything v1.3.1 needs is already in the stack. Pydantic v2.12.5 (current) supports every pattern required. No new libraries, no version bumps, no new dev dependencies.

## Existing Stack (unchanged)

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Runtime |
| fastmcp | >=3.1.1 | MCP server framework (pulls in pydantic) |
| Pydantic | 2.12.5 (transitive) | Model validation, serialization, JSON Schema |
| sqlite3 | stdlib | Read path (~46ms) |

## Pydantic Patterns for v1.3.1 Features

### Tagged Object Discriminator for `parent` field

**Pattern:** Wrapper model with optional fields + `@model_validator`, NOT `Discriminator`/`Tag` or `Literal` discriminator.

**Why this pattern:**
- `Literal` discriminator fields get stripped by `exclude_defaults=True` -- this has burned the project before (DL-12 in spec)
- `Discriminator(callable)` + `Tag` is the Pydantic v2 "modern" approach but produces opaque JSON Schema (`anyOf` with `tag` metadata) that MCP clients may not interpret correctly
- The wrapper model pattern is already proven in the codebase: `MoveAction` uses the same "exactly one key" validation

**Implementation:**

```python
class TaggedParent(OmniFocusBaseModel):
    project: ProjectRef | None = None
    task: TaskRef | None = None

    @model_validator(mode="after")
    def _exactly_one_key(self) -> TaggedParent:
        keys_set = sum(1 for v in (self.project, self.task) if v is not None)
        if keys_set != 1:
            raise ValueError("Exactly one of 'project' or 'task' must be set")
        return self
```

**Verified behaviors (Pydantic 2.12.5):**
- `exclude_defaults=True` correctly drops the `None` field, keeping only the set key -- **tested locally**
- `by_alias=True` does NOT rename `project`/`task` (single-word keys, `to_camel` is identity) -- **tested locally**
- JSON Schema shows both fields as optional with `$ref` to their respective models -- clean, interpretable by MCP clients
- `OmniFocusBaseModel` alias config (`alias_generator=to_camel, validate_by_name=True`) works without issues -- **tested locally**
- Construction: `TaggedParent(project=ProjectRef(id="pXyz", name="Work"))` -- natural
- Validation from dict: `TaggedParent.model_validate({"project": {"id": "pXyz", "name": "Work"}})` -- works

**Confidence:** HIGH -- tested against installed Pydantic 2.12.5

### Reference Models (`ProjectRef`, `TaskRef`, `FolderRef`)

**Pattern:** Same as existing `TagRef(id, name)` -- minimal `OmniFocusBaseModel` subclass.

```python
class ProjectRef(OmniFocusBaseModel):
    id: str
    name: str

class TaskRef(OmniFocusBaseModel):
    id: str
    name: str

class FolderRef(OmniFocusBaseModel):
    id: str
    name: str
```

**Why not a generic `EntityRef`:** Each ref type is semantically distinct. Type checkers catch misuse (`Project.folder` can't accidentally receive a `TaskRef`). The cost is 3 lines per class -- negligible.

**Where they live:** `models/common.py` alongside existing `TagRef` and `ParentRef` (which gets removed).

### `PatchOrNone` Elimination

**Current state:** `PatchOrNone` in `contracts/base.py` is `Union[T, None, _Unset]` -- semantically identical to `PatchOrClear` but with a docstring saying "None carries domain meaning."

**After v1.3.1:**
- `MoveAction.beginning` / `MoveAction.ending`: change from `PatchOrNone[str]` to `Patch[str]` (no more null-as-inbox)
- `TagAction.replace`: stays `PatchOrNone[list[str]]` -- null means "clear all tags", which is domain meaning not inbox
- Wait -- re-checking... `replace: null` means "clear all tags" which is `PatchOrClear` semantics. After v1.3.1, `PatchOrNone` should be removable if `TagAction.replace` is retyped to `PatchOrClear`.

**Action:** Remove `PatchOrNone` from `contracts/base.py` and `contracts/__init__.py`. Retype `MoveAction.beginning`/`ending` to `Patch[str]`. Audit `TagAction.replace` -- if "null = clear all" then `PatchOrClear` is the correct alias.

### System Location Constants in `config.py`

**Current `config.py`** has `DEFAULT_LIST_LIMIT` and fuzzy match params. Add:

```python
SYSTEM_LOCATION_PREFIX: str = "$"
INBOX_ID: str = "$inbox"
INBOX_DISPLAY_NAME: str = "Inbox"
```

**Why constants, not enum:** These are configuration values referenced across layers (resolver, service, mappers). An enum adds ceremony for three strings. Constants are greppable, importable, and match the existing `config.py` style.

### Resolver Precedence Extension

**Current resolver** has two patterns:
1. `resolve_filter()` -- ID match then substring match (for list filters)
2. `resolve_parent()` / `resolve_task()` etc. -- ID-only lookup

**v1.3.1 adds step 0:** `$`-prefix check before any resolution. Implementation is a simple `if value.startswith(SYSTEM_LOCATION_PREFIX):` guard at the top of resolution methods.

**No new abstractions needed.** The three-step precedence ($-prefix -> ID match -> name substring) is a sequential check, not a strategy pattern or chain-of-responsibility. It fits in the existing `Resolver` class methods.

**Name resolution for writes** extends the existing `_match_by_name()` pattern (already used for tags) to projects, folders, and tasks. The method signature already supports any entity type via the `_HasIdAndName` protocol.

## What NOT to Add

| Temptation | Why Not |
|------------|---------|
| `typing.Discriminator` + `Tag` | Produces JSON Schema with `tag` metadata that MCP clients may not parse. Wrapper model is simpler and proven. |
| Generic `EntityRef[T]` base class | Three concrete classes are clearer than generic + type parameter. 9 lines total. |
| New dependency for name matching | `difflib.SequenceMatcher` (stdlib) already powers fuzzy matching in `config.py` constants. |
| Pydantic version pin | `fastmcp>=3.1.1` manages pydantic transitively. Pinning creates maintenance burden. |
| Abstract resolver strategy | Three-step precedence is a simple if-elif, not a pluggable strategy. |
| `$inbox` as an enum member | It's a string constant. Enum membership adds ceremony (`.value` access) for no type safety gain -- the field is `str`. |

## Integration Notes

### Output Schema Tests

After changing `parent` from `ParentRef` to `TaggedParent`, and enriching reference fields to `{id, name}`:
- `tests/test_output_schema.py` will need updated expected schemas
- The `jsonschema` validation tests catch structural drift automatically
- Run `uv run pytest tests/test_output_schema.py -x -q` after any model change (per CLAUDE.md convention)

### Golden Master Impact

- `parent` field shape changes in output -- golden master normalization may need updating
- `inInbox` removal from output -- golden master expectations must drop this field
- Rich references (`Project.folder`, etc.) -- golden master captures will show new `{id, name}` shape

### Cross-Path Equivalence

- 32 existing parametrized tests compare SQL and bridge paths
- Both paths must produce identical `TaggedParent` and `ProjectRef` shapes
- Row mappers in both `sqlite_repo.py` and bridge path need parallel updates

## Sources

- Pydantic v2 Unions docs: https://docs.pydantic.dev/latest/concepts/unions/
- Pydantic key-based discriminated union discussion: https://github.com/pydantic/pydantic/discussions/4180
- Local testing against Pydantic 2.12.5 (installed via `fastmcp>=3.1.1`)
- Existing codebase patterns: `MoveAction` exactly-one-key validation, `TagRef` reference model, `_match_by_name()` resolver
