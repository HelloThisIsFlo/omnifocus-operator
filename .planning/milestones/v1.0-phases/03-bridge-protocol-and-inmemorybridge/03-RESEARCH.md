# Phase 3: Bridge Protocol and InMemoryBridge - Research

**Researched:** 2026-03-01
**Domain:** Python Protocol (structural typing), async bridge abstraction, error hierarchies, test doubles
**Confidence:** HIGH

## Summary

Phase 3 introduces the bridge abstraction layer -- a `Protocol` class defining `send_command(operation, params) -> dict` as the single contract between the OmniFocus data source and all upstream code (Repository, Service, MCP layers). The `InMemoryBridge` is the first concrete implementation, purpose-built for testing with built-in call tracking and configurable error simulation.

The technical domain is well-understood Python: `typing.Protocol` for structural subtyping, `async def` methods for the async event loop, a standard exception hierarchy for error classification, and `dataclasses` for call tracking records. All patterns were verified against mypy strict mode, ruff with the project's lint rules (`TCH`, `RUF`, etc.), and pytest-asyncio with `asyncio_mode = "auto"`.

**Primary recommendation:** Use `typing.Protocol` (not ABC) with a single `async def send_command` method returning `dict[str, Any]`. Keep the bridge deliberately simple -- it shuttles raw data, not domain objects. The error hierarchy should be defined from day one with `BridgeError` as the base and subclasses for timeout, connection, and protocol errors.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use Python `Protocol` (structural typing), not ABC -- implementations don't need to inherit from a base class
- `send_command` is async-only -- the MCP server runs in an async event loop, and file IPC (Phases 6-8) is inherently async
- Include an optional `params` argument from day one -- `dump_all` ignores it, but future operations (create_task, complete_task) can use it without protocol signature changes
- Returns raw `dict[str, Any]` payload -- the caller (Repository) is responsible for parsing into DatabaseSnapshot or other models. Keeps the bridge simple: it shuttles data, not domain objects
- Error hierarchy from the start: base `BridgeError` with subclasses for distinct failure modes (timeout, connection, protocol)
- Errors include structured context: the operation that failed + optional chained cause exception
- InMemoryBridge has configurable error simulation -- can be set up to raise specific BridgeError subclasses on demand
- InMemoryBridge has built-in call tracking -- records each `send_command` call (operation + params)

### Claude's Discretion
- Operation identifier style (string literals vs typed enum vs command objects)
- Return type details beyond raw dict
- Data injection approach (constructor injection vs builder vs other)
- Whether InMemoryBridge provides a sensible default snapshot or requires explicit data

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BRDG-01 | Bridge protocol defines `send_command(operation, params) -> response` | Protocol pattern verified with mypy strict, async method signature validated, `dict[str, Any]` return type confirmed compatible |
| BRDG-02 | InMemoryBridge returns test data from memory for unit testing | Call tracking via `dataclass(frozen=True)`, error simulation via `set_error()`/`clear_error()`, constructor injection of snapshot data -- all verified with mypy strict + ruff |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing.Protocol` | stdlib (3.12) | Structural subtyping for bridge contract | PEP 544, built into Python 3.8+, no runtime overhead, mypy-native |
| `dataclasses` | stdlib (3.12) | Immutable call tracking records (`BridgeCall`) | stdlib, frozen=True for immutability, mypy strict compatible |
| `pydantic` | >=2.0 (already in project) | NOT used in bridge module directly -- Repository does `DatabaseSnapshot.model_validate()` | Bridge returns raw dict; Pydantic stays at the Repository layer |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | >=1.3.0 (already in project) | Testing async `send_command` | All bridge tests -- `asyncio_mode = "auto"` already configured |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Protocol` | `ABC` | ABC requires explicit inheritance (`class InMemoryBridge(Bridge):`), violating the user's decision for structural typing. Protocol enables duck typing -- any class with the right method signature satisfies the contract. |
| `dataclass` for `BridgeCall` | `NamedTuple` | NamedTuple is also immutable but has positional semantics. Dataclass is more readable for keyword construction: `BridgeCall(operation="dump_all", params=None)` |
| Raw `dict` return | TypedDict | TypedDict would add type safety to the return value but couples the bridge to the response schema. The user explicitly chose raw dict -- parsing belongs in the Repository. |

**Installation:** No new dependencies needed. Everything uses stdlib + existing project deps.

## Architecture Patterns

### Recommended Project Structure
```
src/omnifocus_operator/
├── bridge/
│   ├── __init__.py        # Public API: Bridge, InMemoryBridge, errors
│   ├── _protocol.py       # Bridge Protocol definition
│   ├── _errors.py         # BridgeError hierarchy
│   └── _in_memory.py      # InMemoryBridge implementation
├── models/                # Existing (Phase 2)
│   └── ...
```

### Pattern 1: Protocol with async method

**What:** Define the bridge contract as a `typing.Protocol` with a single `async def send_command` method.
**When to use:** Always -- this is the sole interface all bridge implementations must satisfy.
**Example:**
```python
# Source: Verified against mypy --strict and ruff (project config)
from __future__ import annotations

from typing import Any, Protocol


class Bridge(Protocol):
    """Protocol for OmniFocus bridge implementations."""

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a command to OmniFocus and return the raw response."""
        ...
```

**Key details:**
- The `...` body is idiomatic for Protocol methods (not `pass`, not `raise NotImplementedError`)
- `async def` in Protocol means implementations MUST also be `async def` -- mypy strict catches sync implementations
- No `@runtime_checkable` needed: the user said "no isinstance checks", and structural subtyping is compile-time only
- `from __future__ import annotations` enables `dict[str, Any]` syntax on Python 3.12 (though 3.12 supports it natively, it's consistent with the project pattern)

### Pattern 2: Error hierarchy with structured context

**What:** Base `BridgeError` with operation context and chained cause; subclasses for distinct failure modes.
**When to use:** Every bridge error -- callers catch `BridgeError` for generic handling, specific subclasses for targeted recovery.
**Example:**
```python
# Source: Verified against mypy --strict
from __future__ import annotations


class BridgeError(Exception):
    """Base error for all bridge operations."""

    def __init__(
        self,
        operation: str,
        message: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.operation = operation
        super().__init__(message)
        self.__cause__ = cause


class BridgeTimeoutError(BridgeError):
    """Bridge operation timed out."""

    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            operation,
            f"Operation '{operation}' timed out after {timeout_seconds}s",
            cause=cause,
        )


class BridgeConnectionError(BridgeError):
    """Cannot connect to OmniFocus."""

    def __init__(
        self,
        operation: str,
        reason: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.reason = reason
        super().__init__(
            operation,
            f"Cannot connect to OmniFocus: {reason}",
            cause=cause,
        )


class BridgeProtocolError(BridgeError):
    """Response from OmniFocus was malformed or unparseable."""

    def __init__(
        self,
        operation: str,
        detail: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.detail = detail
        super().__init__(
            operation,
            f"Protocol error on '{operation}': {detail}",
            cause=cause,
        )
```

**Key details:**
- `__cause__` is Python's standard exception chaining mechanism (`raise X from Y`)
- Using keyword-only `cause` parameter avoids confusion with positional args
- Each subclass stores its specific context (`timeout_seconds`, `reason`, `detail`) as attributes
- All subclasses call `super().__init__()` with the same `(operation, message)` signature

### Pattern 3: InMemoryBridge with call tracking

**What:** Test double that returns data from memory, records calls, and can simulate errors.
**When to use:** All automated tests that need a bridge (Repository, Service, MCP layer tests in future phases).
**Example:**
```python
# Source: Verified against mypy --strict + runtime
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BridgeCall:
    """Record of a single send_command invocation."""

    operation: str
    params: dict[str, Any] | None


class InMemoryBridge:
    """Test bridge: returns data from memory with call tracking."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data or {}
        self._calls: list[BridgeCall] = []
        self._error: Exception | None = None

    @property
    def calls(self) -> list[BridgeCall]:
        """Copy of recorded calls (prevents mutation)."""
        return list(self._calls)

    @property
    def call_count(self) -> int:
        """Number of send_command invocations."""
        return len(self._calls)

    def set_error(self, error: Exception) -> None:
        """Configure error to raise on next send_command."""
        self._error = error

    def clear_error(self) -> None:
        """Remove configured error."""
        self._error = None

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record call, optionally raise error, return data."""
        self._calls.append(BridgeCall(operation=operation, params=params))
        if self._error is not None:
            raise self._error
        return self._data
```

### Pattern 4: Module `__init__.py` re-exports

**What:** Public API surface from `bridge/__init__.py`, following the existing `models/__init__.py` pattern.
**When to use:** Always -- this is the established project convention for package-level imports.
**Example:**
```python
"""OmniFocus bridge protocol and implementations."""

from omnifocus_operator.bridge._errors import (
    BridgeConnectionError,
    BridgeError,
    BridgeProtocolError,
    BridgeTimeoutError,
)
from omnifocus_operator.bridge._in_memory import BridgeCall, InMemoryBridge
from omnifocus_operator.bridge._protocol import Bridge

__all__ = [
    "Bridge",
    "BridgeCall",
    "BridgeConnectionError",
    "BridgeError",
    "BridgeProtocolError",
    "BridgeTimeoutError",
    "InMemoryBridge",
]
```

### Anti-Patterns to Avoid

- **isinstance checks on Bridge:** The user explicitly chose Protocol (structural typing). Never use `isinstance(x, Bridge)` -- it defeats the purpose. Don't add `@runtime_checkable` to the Protocol.
- **Bridge returning domain objects:** The bridge returns `dict[str, Any]`. Don't import `DatabaseSnapshot` or any Pydantic models into bridge modules. The Repository (Phase 4) does the parsing.
- **Inheriting from Bridge Protocol:** Implementations like `InMemoryBridge` must NOT inherit from `Bridge`. They satisfy the protocol structurally. Adding `(Bridge)` to the class definition would work but contradicts the structural typing decision.
- **Mutable BridgeCall records:** Use `frozen=True` on the dataclass. Call records are historical facts and should not be modified after creation.
- **Catching generic Exception in tests:** When testing error simulation, always catch the specific `BridgeError` subclass to verify the right error type is raised.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structural typing interface | Custom metaclass or registration system | `typing.Protocol` | PEP 544 is the standard, mypy validates it statically |
| Exception chaining | Custom `cause` attribute on errors | `__cause__` (PEP 3134) | Python's built-in mechanism, works with `raise X from Y`, shown in tracebacks |
| Immutable records | Manual `__eq__`/`__hash__` on call records | `@dataclass(frozen=True)` | stdlib, handles equality/hashing/repr automatically |
| Async test infrastructure | Custom event loop setup | `pytest-asyncio` with `asyncio_mode = "auto"` | Already configured in pyproject.toml, auto-detects async tests |

**Key insight:** This phase is almost entirely stdlib Python patterns. The only third-party dependency involved is pytest-asyncio for testing, which is already configured. There is no need to install anything new.

## Common Pitfalls

### Pitfall 1: Sync method satisfying async Protocol
**What goes wrong:** Defining `def send_command()` (sync) on an implementation that's supposed to satisfy an `async def` Protocol. Python won't raise a runtime error, but mypy will.
**Why it happens:** The method name and parameters match, so it looks correct. The sync/async distinction is invisible without type checking.
**How to avoid:** Always run `mypy --strict` as part of the dev workflow. The project already has `strict = true` in `pyproject.toml`.
**Warning signs:** Tests pass but mypy reports `Argument has incompatible type` with a note about `Coroutine[Any, Any, ...]`.

### Pitfall 2: Forgetting `from __future__ import annotations` in bridge modules
**What goes wrong:** Without it, `dict[str, Any] | None` syntax requires Python 3.10+ at parse time. While 3.12 supports it natively, the project uses `from __future__ import annotations` consistently for ruff `TCH` compliance when TYPE_CHECKING imports are present.
**Why it happens:** New modules are created without copying the project pattern.
**How to avoid:** Every `.py` file in the bridge package should start with `from __future__ import annotations` to match the existing convention.
**Warning signs:** ruff TC errors or inconsistent import style across modules.

### Pitfall 3: InMemoryBridge error simulation leaking across tests
**What goes wrong:** One test calls `bridge.set_error(...)` and a subsequent test gets unexpected errors because the bridge instance is shared.
**Why it happens:** Using a module-level or session-scoped bridge fixture.
**How to avoid:** Either create a fresh `InMemoryBridge` per test (factory function pattern, matching the existing `make_*_dict()` approach) or always call `bridge.clear_error()` in test teardown. The project uses factory functions, not fixtures -- follow this pattern.
**Warning signs:** Tests that pass in isolation but fail when run together.

### Pitfall 4: Not recording call before raising error
**What goes wrong:** If `InMemoryBridge.send_command()` raises an error before appending to `_calls`, test assertions on `bridge.call_count` don't reflect the failed attempt.
**Why it happens:** Early-return pattern: check error, raise, then record. Logic order matters.
**How to avoid:** Always append to `_calls` BEFORE checking `_error`. The call happened -- it just failed.
**Warning signs:** `bridge.call_count == 0` after a test that called `send_command` (which raised).

### Pitfall 5: Returning a mutable reference from `calls` property
**What goes wrong:** If `calls` returns `self._calls` directly, test code could mutate the internal list (e.g., `bridge.calls.clear()`).
**Why it happens:** Python properties don't prevent mutation of the returned object.
**How to avoid:** Return `list(self._calls)` (a copy) from the `calls` property.
**Warning signs:** Mysterious test interactions where call counts change unexpectedly.

## Code Examples

Verified patterns from official sources and local validation:

### Async test with InMemoryBridge
```python
# Source: Verified with pytest-asyncio (asyncio_mode="auto" in pyproject.toml)
import pytest

from omnifocus_operator.bridge import Bridge, BridgeCall, InMemoryBridge


async def test_send_command_returns_data() -> None:
    """InMemoryBridge returns configured data."""
    data = {"tasks": [], "projects": []}
    bridge = InMemoryBridge(data=data)

    result = await bridge.send_command("dump_all")

    assert result == data
    assert bridge.call_count == 1
    assert bridge.calls[0] == BridgeCall(operation="dump_all", params=None)


async def test_send_command_with_params() -> None:
    """InMemoryBridge records params."""
    bridge = InMemoryBridge(data={})
    params = {"task_id": "abc-123"}

    await bridge.send_command("complete_task", params=params)

    assert bridge.calls[0].params == {"task_id": "abc-123"}
```

### Error simulation test
```python
# Source: Verified with mypy --strict
import pytest

from omnifocus_operator.bridge import (
    BridgeError,
    BridgeTimeoutError,
    InMemoryBridge,
)


async def test_error_simulation() -> None:
    """InMemoryBridge raises configured error."""
    bridge = InMemoryBridge(data={})
    bridge.set_error(BridgeTimeoutError("dump_all", timeout_seconds=10.0))

    with pytest.raises(BridgeTimeoutError) as exc_info:
        await bridge.send_command("dump_all")

    assert exc_info.value.operation == "dump_all"
    assert exc_info.value.timeout_seconds == 10.0
    assert bridge.call_count == 1  # Call recorded before error raised


async def test_clear_error() -> None:
    """clear_error removes configured error."""
    bridge = InMemoryBridge(data={"ok": True})
    bridge.set_error(BridgeError("test", "fail"))
    bridge.clear_error()

    result = await bridge.send_command("dump_all")
    assert result == {"ok": True}
```

### Protocol satisfaction test (structural typing)
```python
# Source: Verified with mypy --strict
from omnifocus_operator.bridge import Bridge, InMemoryBridge


def test_in_memory_bridge_satisfies_protocol() -> None:
    """InMemoryBridge structurally satisfies the Bridge protocol."""
    bridge: Bridge = InMemoryBridge(data={})
    # If this line type-checks with mypy --strict, the protocol is satisfied.
    # No isinstance check needed -- structural typing is static.
    assert bridge is not None
```

### Error hierarchy test
```python
# Source: Verified with mypy --strict
import pytest

from omnifocus_operator.bridge import (
    BridgeConnectionError,
    BridgeError,
    BridgeProtocolError,
    BridgeTimeoutError,
)


def test_all_bridge_errors_are_bridge_error() -> None:
    """All specific errors inherit from BridgeError."""
    assert issubclass(BridgeTimeoutError, BridgeError)
    assert issubclass(BridgeConnectionError, BridgeError)
    assert issubclass(BridgeProtocolError, BridgeError)


def test_bridge_error_has_operation() -> None:
    """BridgeError exposes the operation that failed."""
    err = BridgeError("dump_all", "something broke")
    assert err.operation == "dump_all"
    assert str(err) == "something broke"


def test_bridge_error_chaining() -> None:
    """BridgeError supports exception chaining via __cause__."""
    original = OSError("disk full")
    err = BridgeConnectionError("dump_all", "write failed", cause=original)
    assert err.__cause__ is original
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ABC` with abstract methods | `typing.Protocol` (PEP 544) | Python 3.8 (2019) | No inheritance required; structural subtyping |
| `raise NotImplementedError` in protocol body | `...` (ellipsis) | Convention, not version-gated | Cleaner, idiomatic, mypy-preferred |
| `Optional[X]` | `X \| None` | Python 3.10+ (PEP 604) | More readable union syntax |
| `Dict[str, Any]` | `dict[str, Any]` | Python 3.9+ (PEP 585) | Lowercase generics |

**Deprecated/outdated:**
- `@abstractmethod` on Protocol methods: Not needed. Protocol methods are abstract by definition. Adding `@abstractmethod` only matters if a class explicitly inherits from the Protocol (which we don't do here).
- `runtime_checkable`: Not needed for this project. The user explicitly said no isinstance checks.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_bridge.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRDG-01 | Bridge protocol defines `send_command(operation, params) -> response` as typed interface | unit | `uv run pytest tests/test_bridge.py::TestBridgeProtocol -x` | No -- Wave 0 |
| BRDG-01 | Protocol rejects sync implementations (mypy check) | type-check | `uv run mypy src/omnifocus_operator/bridge/` | No -- Wave 0 |
| BRDG-02 | InMemoryBridge returns test data from memory | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge -x` | No -- Wave 0 |
| BRDG-02 | InMemoryBridge records calls with operation + params | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge::test_call_tracking -x` | No -- Wave 0 |
| BRDG-02 | InMemoryBridge simulates configurable errors | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge::test_error_simulation -x` | No -- Wave 0 |
| BRDG-02 | Error hierarchy: BridgeError base with timeout/connection/protocol subclasses | unit | `uv run pytest tests/test_bridge.py::TestBridgeErrors -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_bridge.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_bridge.py` -- covers BRDG-01, BRDG-02 (protocol, in-memory bridge, errors)
- [ ] No new conftest fixtures needed -- InMemoryBridge IS the test fixture; existing `make_snapshot_dict()` in `tests/conftest.py` provides data

## Open Questions

1. **Operation identifier style: string literals vs enum**
   - What we know: The user left this to Claude's discretion. `dump_all` is the only operation needed now; future operations include `create_task`, `complete_task`.
   - What's unclear: Whether to use plain string literals (`"dump_all"`) or a `StrEnum` class.
   - Recommendation: Use plain string literals for now. The bridge protocol accepts `str`, so any calling code can pass any string. If operation names proliferate in future phases, a `StrEnum` can be introduced at the caller side without changing the bridge protocol. This follows YAGNI -- the Protocol signature is `operation: str`, which is maximally flexible.

2. **InMemoryBridge default data: empty dict vs sensible snapshot**
   - What we know: The user left this to Claude's discretion. Constructor takes `data: dict[str, Any] | None = None`.
   - What's unclear: Should `data=None` produce an empty dict, or a default snapshot matching `make_snapshot_dict()` format?
   - Recommendation: Default to empty dict (`{}`). Tests should explicitly construct the data they need using the existing `make_snapshot_dict()` factory. This makes tests self-documenting -- you can see exactly what data the bridge will return. A "magic default" would hide test setup and make failures harder to diagnose.

3. **Data injection: constructor vs setter vs builder**
   - What we know: Constructor injection is simplest and most Pythonic.
   - What's unclear: Whether a `set_data()` method is needed for tests that want to change data mid-test.
   - Recommendation: Start with constructor-only. If a mid-test data swap is needed, create a new `InMemoryBridge` instance. This is simpler and avoids mutable state confusion. Add `set_data()` only if Phase 4 (Repository caching tests) demonstrates a clear need.

## Sources

### Primary (HIGH confidence)
- mypy docs: Protocols and structural subtyping (https://mypy.readthedocs.io/en/latest/protocols) -- Protocol definition patterns, async method typing, runtime_checkable semantics
- mypy docs: Async types (https://mypy.readthedocs.io/en/latest/more_types) -- Async Protocol method signatures, Coroutine type inference
- Local verification: All code examples tested against `mypy --strict`, `ruff check` (project config), `ruff format`, and `pytest-asyncio` runtime

### Secondary (MEDIUM confidence)
- Python docs: PEP 544 (Protocols: Structural subtyping) -- Design rationale for Protocol
- Python docs: PEP 3134 (Exception chaining) -- `__cause__` semantics
- Python docs: dataclasses (frozen=True) -- Immutable record pattern

### Tertiary (LOW confidence)
None -- all findings verified with local tooling.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, no new deps, verified with project toolchain
- Architecture: HIGH -- Protocol + error hierarchy + dataclass are well-established Python patterns, all verified against mypy strict + ruff
- Pitfalls: HIGH -- each pitfall was discovered during local testing (e.g., call recording order, mutable property return)

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable domain -- stdlib Python patterns don't churn)
