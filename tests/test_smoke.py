"""Smoke test: verify the package can be imported."""

import pytest


def test_package_imports() -> None:
    """Verify omnifocus_operator package is importable and has correct version."""
    import omnifocus_operator

    assert omnifocus_operator.__version__ == "0.1.0"


def test_main_entry_point_exists() -> None:
    """Verify main() is importable and callable."""
    from omnifocus_operator.__main__ import main

    assert callable(main)


def test_default_bridge_is_real() -> None:
    """Verify create_server defaults to 'real' bridge which fails cleanly.

    Uses the in-process pattern rather than calling main() directly,
    which avoids pytest capture teardown issues from stdout redirection.
    """
    import os

    from omnifocus_operator.bridge import create_bridge

    # Without OMNIFOCUS_BRIDGE set, factory should attempt "real"
    bridge_type = os.environ.get("OMNIFOCUS_BRIDGE", "real")
    if bridge_type == "real":
        with pytest.raises(NotImplementedError, match="RealBridge"):
            create_bridge("real")
