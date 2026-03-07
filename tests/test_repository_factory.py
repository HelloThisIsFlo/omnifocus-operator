"""Tests for the repository factory -- create_repository()."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


class TestCreateRepositorySqliteMode:
    """Tests for sqlite/hybrid repository creation."""

    def test_sqlite_returns_hybrid_repository(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        db_file = tmp_path / "OmniFocusDatabase.db"
        db_file.touch()
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(db_file))

        from omnifocus_operator.repository import HybridRepository
        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository("sqlite")
        assert isinstance(repo, HybridRepository)

    def test_hybrid_alias_returns_hybrid_repository(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        db_file = tmp_path / "OmniFocusDatabase.db"
        db_file.touch()
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(db_file))

        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository("hybrid")
        from omnifocus_operator.repository import HybridRepository

        assert isinstance(repo, HybridRepository)

    def test_none_defaults_to_sqlite(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        db_file = tmp_path / "OmniFocusDatabase.db"
        db_file.touch()
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(db_file))
        monkeypatch.delenv("OMNIFOCUS_REPOSITORY", raising=False)

        from omnifocus_operator.repository import HybridRepository
        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository(None)
        assert isinstance(repo, HybridRepository)

    def test_env_var_selects_repo_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")

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

        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository("sqlite")
        assert repo._db_path == str(custom_db)


class TestCreateRepositoryBridgeMode:
    """Tests for bridge repository creation."""

    def test_bridge_returns_bridge_repository(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")

        from omnifocus_operator.repository import BridgeRepository
        from omnifocus_operator.repository.factory import create_repository

        repo = create_repository("bridge")
        assert isinstance(repo, BridgeRepository)

    def test_bridge_logs_degraded_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")

        from omnifocus_operator.repository.factory import create_repository

        with caplog.at_level(logging.WARNING):
            create_repository("bridge")

        assert any("bridge mode" in r.message.lower() for r in caplog.records)


class TestCreateRepositoryErrors:
    """Tests for error handling."""

    def test_unknown_type_raises_value_error(self) -> None:
        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(ValueError, match="unknown"):
            create_repository("unknown")

    def test_sqlite_missing_db_raises_file_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError):
            create_repository("sqlite")

    def test_file_not_found_contains_expected_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError, match=str(missing_path)):
            create_repository("sqlite")

    def test_file_not_found_contains_sqlite_path_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError, match="OMNIFOCUS_SQLITE_PATH"):
            create_repository("sqlite")

    def test_file_not_found_contains_bridge_workaround(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError, match="OMNIFOCUS_REPOSITORY=bridge"):
            create_repository("sqlite")

    def test_file_not_found_distinguishes_fix_vs_workaround(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing_path = tmp_path / "nonexistent.db"
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(missing_path))

        from omnifocus_operator.repository.factory import create_repository

        with pytest.raises(FileNotFoundError) as exc_info:
            create_repository("sqlite")

        msg = str(exc_info.value)
        fix_pos = msg.index("To fix")
        workaround_pos = msg.index("workaround")
        assert fix_pos < workaround_pos
