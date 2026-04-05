"""Shared utilities for agent-message consolidation tests."""

import inspect


def get_upper_snake_constants(module: object) -> set[str]:
    """Return all UPPER_SNAKE_CASE names exported from a module."""
    return {name for name in dir(module) if name.isupper() and not name.startswith("_")}


def get_consumer_sources(consumers: list[object]) -> str:
    """Return combined source of all consumer modules."""
    return "\n".join(inspect.getsource(m) for m in consumers)
