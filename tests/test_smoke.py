"""Smoke test: verify the package can be imported."""

import pytest

from omnifocus_operator.__main__ import main


def test_package_imports() -> None:
    """Verify omnifocus_operator package is importable and has correct version."""
    import omnifocus_operator

    assert omnifocus_operator.__version__ == "0.1.0"


def test_main_raises_not_implemented() -> None:
    """Verify main() raises NotImplementedError until server is implemented."""
    with pytest.raises(NotImplementedError, match="Server not yet implemented"):
        main()
