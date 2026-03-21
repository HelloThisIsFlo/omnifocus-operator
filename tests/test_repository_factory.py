"""Tests for the repository factory -- create_repository()."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _stub_real_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Monkeypatch _create_real_bridge so factory never touches the real Bridge."""
    from tests.doubles import SimulatorBridge

    monkeypatch.setattr(
        "omnifocus_operator.repository.factory._create_real_bridge",
        lambda: SimulatorBridge(ipc_dir=tmp_path),
    )


class TestCreateRepositoryHybridMode:
    """Tests for hybrid repository creation."""

    def test_hybrid_returns_hybrid_repository(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        db_file = tmp_path / "OmniFocusDatabase.db"
        db_file.touch()
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(db_file))
        _stub_real_bridge(monkeypatch, tmp_path)

        from omnifocus_operator.repository import HybridRepository
        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository("hybrid")
        assert isinstance(repo, HybridRepository)

    def test_none_defaults_to_hybrid(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        db_file = tmp_path / "OmniFocusDatabase.db"
        db_file.touch()
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(db_file))
        _stub_real_bridge(monkeypatch, tmp_path)
        monkeypatch.delenv("OMNIFOCUS_REPOSITORY", raising=False)

        from omnifocus_operator.repository import HybridRepository
        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository(None)
        assert isinstance(repo, HybridRepository)

    def test_env_var_selects_repo_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        ofocus_bundle = tmp_path / "OmniFocus.ofocus"
        ofocus_bundle.mkdir()
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_OFOCUS_PATH", str(ofocus_bundle))
        _stub_real_bridge(monkeypatch, tmp_path)

        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository()
        from omnifocus_operator.repository import BridgeRepository

        assert isinstance(repo, BridgeRepository)

    def test_omnifocus_sqlite_path_overrides_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        custom_db = tmp_path / "custom.db"
        custom_db.touch()
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(custom_db))
        _stub_real_bridge(monkeypatch, tmp_path)

        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository("hybrid")
        assert repo._db_path == str(custom_db)


class TestCreateRepositoryBridgeMode:
    """Tests for bridge repository creation."""

    def test_bridge_only_returns_bridge_repository(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        ofocus_bundle = tmp_path / "OmniFocus.ofocus"
        ofocus_bundle.mkdir()
        monkeypatch.setenv("OMNIFOCUS_OFOCUS_PATH", str(ofocus_bundle))
        _stub_real_bridge(monkeypatch, tmp_path)

        from omnifocus_operator.repository import BridgeRepository
        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository("bridge-only")
        assert isinstance(repo, BridgeRepository)

    def test_bridge_only_logs_degraded_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        ofocus_bundle = tmp_path / "OmniFocus.ofocus"
        ofocus_bundle.mkdir()
        monkeypatch.setenv("OMNIFOCUS_OFOCUS_PATH", str(ofocus_bundle))
        _stub_real_bridge(monkeypatch, tmp_path)

        from omnifocus_operator.repository.factory import create_repository

        with caplog.at_level(logging.WARNING):
            create_repository("bridge-only")

        assert any("bridge mode" in r.message.lower() for r in caplog.records)


class TestCreateRepositoryErrors:
    """Tests for error handling."""

    def test_unknown_type_raises_value_error(self) -> None:
        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(ValueError, match="unknown"):
            create_repository("unknown")

    def test_hybrid_missing_db_raises_file_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError):
            create_repository("hybrid")

    def test_file_not_found_contains_expected_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError, match=str(missing_path)):
            create_repository("hybrid")

    def test_file_not_found_contains_sqlite_path_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError, match="OMNIFOCUS_SQLITE_PATH"):
            create_repository("hybrid")

    def test_file_not_found_contains_bridge_workaround(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError, match="OMNIFOCUS_REPOSITORY=bridge-only"):
            create_repository("hybrid")

    def test_file_not_found_distinguishes_fix_vs_workaround(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError) as exc_info:
            create_repository("hybrid")

        msg = str(exc_info.value)
        fix_pos = msg.index("To fix")
        workaround_pos = msg.index("workaround")
        assert fix_pos < workaround_pos
