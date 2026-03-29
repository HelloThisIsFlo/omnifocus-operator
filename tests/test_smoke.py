"""Smoke tests: package import and SAFE-01 enforcement."""

from pathlib import Path

import pytest


def test_package_imports() -> None:
    """Verify omnifocus_operator package is importable and has correct version."""
    import omnifocus_operator

    assert omnifocus_operator.__version__ == "0.1.0"


def test_main_entry_point_exists() -> None:
    """Verify main() is importable and callable."""
    from omnifocus_operator.__main__ import main

    assert callable(main)


def test_default_bridge_refused_during_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SAFE-01: RealBridge() is refused during automated testing."""
    from omnifocus_operator.bridge.real import RealBridge

    monkeypatch.setenv("OPERATOR_IPC_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="PYTEST_CURRENT_TEST"):
        RealBridge(ipc_dir=tmp_path)


def test_no_test_removes_pytest_current_test() -> None:
    """SAFE-01: No test file may remove PYTEST_CURRENT_TEST.

    Removing this env var bypasses the RealBridge safety guard, allowing
    tests to trigger real OmniFocus. Scan all test files for delenv/unsetenv
    patterns targeting PYTEST_CURRENT_TEST.

    Exception: test_ipc_engine.py contains the SAFE-01 enforcement test
    that verifies RealBridge *can* be created when PYTEST_CURRENT_TEST is
    absent. It only instantiates the object -- never calls send_command.
    """
    import re

    tests_dir = Path(__file__).parent
    pattern = re.compile(r"""(delenv|unsetenv)\s*\(\s*["']PYTEST_CURRENT_TEST["']""")

    # The enforcement test in test_ipc_engine.py is the sole allowed exception.
    allowed = {"test_ipc_engine.py"}

    violations: list[str] = []
    for py_file in tests_dir.rglob("*.py"):
        if py_file.name in allowed:
            continue
        text = py_file.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{py_file.name}:{i}: {line.strip()}")

    assert not violations, (
        "SAFE-01 VIOLATION: test code must never remove PYTEST_CURRENT_TEST.\n"
        "This env var prevents RealBridge from triggering real OmniFocus.\n"
        "Allowed exception: test_ipc_engine.py (SAFE-01 enforcement test).\n"
        + "\n".join(violations)
    )
