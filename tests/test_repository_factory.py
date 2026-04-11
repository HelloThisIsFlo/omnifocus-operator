"""Tests for the repository factory -- create_repository()."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from omnifocus_operator.repository import BridgeOnlyRepository, HybridRepository
from omnifocus_operator.repository.factory import create_repository
from tests.doubles import SimulatorBridge

if TYPE_CHECKING:
    from pathlib import Path


def _make_bridge(tmp_path: Path) -> SimulatorBridge:
    return SimulatorBridge(ipc_dir=tmp_path)


class TestCreateRepositoryHybridMode:
    """Tests for hybrid repository creation."""

    def test_hybrid_returns_hybrid_repository(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        db_file = tmp_path / "OmniFocusDatabase.db"
        db_file.touch()
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(db_file))

        repo = create_repository(_make_bridge(tmp_path), "hybrid")
        assert isinstance(repo, HybridRepository)

    def test_none_defaults_to_hybrid(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        db_file = tmp_path / "OmniFocusDatabase.db"
        db_file.touch()
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(db_file))
        monkeypatch.delenv("OPERATOR_REPOSITORY", raising=False)

        repo = create_repository(_make_bridge(tmp_path), None)
        assert isinstance(repo, HybridRepository)

    def test_env_var_selects_repo_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        ofocus_bundle = tmp_path / "OmniFocus.ofocus"
        ofocus_bundle.mkdir()
        monkeypatch.setenv("OPERATOR_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OPERATOR_OFOCUS_PATH", str(ofocus_bundle))

        repo = create_repository(_make_bridge(tmp_path))
        assert isinstance(repo, BridgeOnlyRepository)

    def test_omnifocus_sqlite_path_overrides_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        custom_db = tmp_path / "custom.db"
        custom_db.touch()
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(custom_db))

        repo = create_repository(_make_bridge(tmp_path), "hybrid")
        assert repo._db_path == str(custom_db)


class TestCreateRepositoryBridgeMode:
    """Tests for bridge repository creation."""

    def test_bridge_only_returns_bridge_repository(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        ofocus_bundle = tmp_path / "OmniFocus.ofocus"
        ofocus_bundle.mkdir()
        monkeypatch.setenv("OPERATOR_OFOCUS_PATH", str(ofocus_bundle))

        repo = create_repository(_make_bridge(tmp_path), "bridge-only")
        assert isinstance(repo, BridgeOnlyRepository)

    def test_bridge_only_logs_degraded_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        ofocus_bundle = tmp_path / "OmniFocus.ofocus"
        ofocus_bundle.mkdir()
        monkeypatch.setenv("OPERATOR_OFOCUS_PATH", str(ofocus_bundle))

        with caplog.at_level(logging.WARNING):
            create_repository(_make_bridge(tmp_path), "bridge-only")

        assert any("bridge mode" in r.message.lower() for r in caplog.records)


class TestCreateRepositoryErrors:
    """Tests for error handling."""

    def test_unknown_type_raises_value_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="unknown"):
            create_repository(_make_bridge(tmp_path), "unknown")

    def test_hybrid_missing_db_raises_file_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(missing_path))

        with pytest.raises(FileNotFoundError):
            create_repository(_make_bridge(tmp_path), "hybrid")

    def test_file_not_found_contains_expected_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(missing_path))

        with pytest.raises(FileNotFoundError, match=str(missing_path)):
            create_repository(_make_bridge(tmp_path), "hybrid")

    def test_file_not_found_contains_sqlite_path_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(missing_path))

        with pytest.raises(FileNotFoundError, match="OPERATOR_SQLITE_PATH"):
            create_repository(_make_bridge(tmp_path), "hybrid")

    def test_file_not_found_contains_bridge_workaround(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(missing_path))

        with pytest.raises(FileNotFoundError, match="OPERATOR_REPOSITORY=bridge-only"):
            create_repository(_make_bridge(tmp_path), "hybrid")

    def test_file_not_found_distinguishes_fix_vs_workaround(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(missing_path))

        with pytest.raises(FileNotFoundError) as exc_info:
            create_repository(_make_bridge(tmp_path), "hybrid")

        msg = str(exc_info.value)
        fix_pos = msg.index("To fix")
        workaround_pos = msg.index("workaround")
        assert fix_pos < workaround_pos
