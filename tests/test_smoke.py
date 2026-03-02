"""Smoke test: verify the package can be imported."""

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


def test_default_bridge_is_real(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify create_bridge('real') returns a RealBridge instance."""
    from omnifocus_operator.bridge import create_bridge
    from omnifocus_operator.bridge._real import RealBridge

    monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))
    bridge = create_bridge("real")
    assert isinstance(bridge, RealBridge)
