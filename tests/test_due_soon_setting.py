"""Tests for get_due_soon_setting() on both repository implementations."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from omnifocus_operator.config import Settings, get_settings
from omnifocus_operator.contracts.protocols import Repository
from omnifocus_operator.contracts.use_cases.list._enums import DueSoonSetting
from omnifocus_operator.repository.bridge_only.bridge_only import BridgeOnlyRepository
from omnifocus_operator.repository.hybrid.hybrid import HybridRepository
from tests.doubles import ConstantMtimeSource

if TYPE_CHECKING:
    from pathlib import Path

# -- HybridRepository tests --


@pytest.fixture()
def _setting_db(tmp_path: Path) -> Path:
    """Create a temporary SQLite database with a Setting table."""
    db_path = tmp_path / "OmniFocusDatabase.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE Setting (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()
    return db_path


def _insert_settings(db_path: Path, interval: str, granularity: str) -> None:
    """Insert DueSoonInterval and DueSoonGranularity into the Setting table."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT OR REPLACE INTO Setting (key, value) VALUES ('DueSoonInterval', ?)",
        (interval,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO Setting (key, value) VALUES ('DueSoonGranularity', ?)",
        (granularity,),
    )
    conn.commit()
    conn.close()


def _make_hybrid_repo(db_path: Path):
    """Create a HybridRepository pointing at a temp database."""

    bridge = AsyncMock()
    return HybridRepository(db_path=db_path, bridge=bridge)


class TestHybridGetDueSoonSetting:
    """HybridRepository.get_due_soon_setting() reads from SQLite Setting table."""

    @pytest.mark.asyncio()
    async def test_returns_today(self, _setting_db: Path) -> None:
        _insert_settings(_setting_db, "86400", "1")
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.TODAY

    @pytest.mark.asyncio()
    async def test_returns_twenty_four_hours(self, _setting_db: Path) -> None:
        _insert_settings(_setting_db, "86400", "0")
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.TWENTY_FOUR_HOURS

    @pytest.mark.asyncio()
    async def test_returns_two_days(self, _setting_db: Path) -> None:
        _insert_settings(_setting_db, "172800", "1")
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.TWO_DAYS

    @pytest.mark.asyncio()
    async def test_returns_three_days(self, _setting_db: Path) -> None:
        _insert_settings(_setting_db, "259200", "1")
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.THREE_DAYS

    @pytest.mark.asyncio()
    async def test_returns_four_days(self, _setting_db: Path) -> None:
        _insert_settings(_setting_db, "345600", "1")
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.FOUR_DAYS

    @pytest.mark.asyncio()
    async def test_returns_five_days(self, _setting_db: Path) -> None:
        _insert_settings(_setting_db, "432000", "1")
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.FIVE_DAYS

    @pytest.mark.asyncio()
    async def test_returns_one_week(self, _setting_db: Path) -> None:
        _insert_settings(_setting_db, "604800", "1")
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.ONE_WEEK

    @pytest.mark.asyncio()
    async def test_returns_none_for_unknown_pair(self, _setting_db: Path) -> None:
        _insert_settings(_setting_db, "999999", "1")
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_when_no_rows(self, _setting_db: Path) -> None:
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_when_only_interval(self, _setting_db: Path) -> None:
        conn = sqlite3.connect(str(_setting_db))
        conn.execute("INSERT INTO Setting (key, value) VALUES ('DueSoonInterval', '86400')")
        conn.commit()
        conn.close()
        repo = _make_hybrid_repo(_setting_db)
        result = await repo.get_due_soon_setting()
        assert result is None


class TestRepositoryProtocolIncludesGetDueSoonSetting:
    """Structural check that the Repository protocol includes get_due_soon_setting."""

    def test_protocol_has_method(self) -> None:

        assert hasattr(Repository, "get_due_soon_setting")


# -- BridgeOnlyRepository tests --


def _make_bridge_only_repo():
    """Create a BridgeOnlyRepository with mock bridge and mtime source."""

    bridge = AsyncMock()
    return BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())


class TestBridgeOnlyGetDueSoonSetting:
    """BridgeOnlyRepository.get_due_soon_setting() reads from
    OPERATOR_DUE_SOON_THRESHOLD env var via Settings."""

    @pytest.mark.asyncio()
    async def test_returns_two_days(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPERATOR_DUE_SOON_THRESHOLD", "TWO_DAYS")
        repo = _make_bridge_only_repo()
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.TWO_DAYS

    @pytest.mark.asyncio()
    async def test_returns_today(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPERATOR_DUE_SOON_THRESHOLD", "TODAY")
        repo = _make_bridge_only_repo()
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.TODAY

    @pytest.mark.asyncio()
    async def test_returns_none_when_not_set(self) -> None:
        repo = _make_bridge_only_repo()
        result = await repo.get_due_soon_setting()
        assert result is None

    @pytest.mark.asyncio()
    async def test_raises_for_invalid_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPERATOR_DUE_SOON_THRESHOLD", "INVALID")
        with pytest.raises(ValidationError, match="Invalid OPERATOR_DUE_SOON_THRESHOLD"):
            get_settings()

    @pytest.mark.asyncio()
    async def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPERATOR_DUE_SOON_THRESHOLD", "one_week")
        repo = _make_bridge_only_repo()
        result = await repo.get_due_soon_setting()
        assert result is DueSoonSetting.ONE_WEEK


# -- Settings field_validator tests --


class TestSettingsDueSoonValidation:
    """Direct tests for the field_validator on Settings.due_soon_threshold."""

    def test_none_accepted(self) -> None:
        settings = Settings(due_soon_threshold=None)
        assert settings.due_soon_threshold is None

    def test_valid_value_accepted(self) -> None:
        settings = Settings(due_soon_threshold="TWO_DAYS")
        assert settings.due_soon_threshold is DueSoonSetting.TWO_DAYS

    def test_case_insensitive(self) -> None:
        settings = Settings(due_soon_threshold="one_week")
        assert settings.due_soon_threshold is DueSoonSetting.ONE_WEEK

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValidationError, match="Invalid OPERATOR_DUE_SOON_THRESHOLD"):
            Settings(due_soon_threshold="INVALID")
