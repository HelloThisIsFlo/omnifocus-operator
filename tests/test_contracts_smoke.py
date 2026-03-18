"""Smoke tests for the contracts/ package.

Validates:
- All contracts/ exports are importable and schema-generatable
- Old files (models/write.py, bridge/protocol.py, repository/protocol.py) are deleted
"""

import importlib

import pytest


class TestContractsImportSmoke:
    """Verify every public export from contracts/ is importable and usable."""

    def test_all_exports_importable(self) -> None:
        from omnifocus_operator import contracts

        for name in contracts.__all__:
            obj = getattr(contracts, name)
            assert obj is not None, f"contracts.{name} resolved to None"

    @pytest.mark.parametrize(
        "model_name",
        [
            "CreateTaskCommand",
            "CreateTaskRepoPayload",
            "EditTaskCommand",
            "EditTaskRepoPayload",
        ],
    )
    def test_schema_generation(self, model_name: str) -> None:
        """model_rebuild resolved forward refs — schema generation must succeed."""
        from omnifocus_operator import contracts

        model_cls = getattr(contracts, model_name)
        schema = model_cls.model_json_schema()
        assert "properties" in schema


class TestOldFileDeletionGuards:
    """Regression guards: old files must not be re-created."""

    def test_models_write_deleted(self) -> None:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("omnifocus_operator.models.write")

    def test_bridge_protocol_deleted(self) -> None:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("omnifocus_operator.bridge.protocol")

    def test_repository_protocol_deleted(self) -> None:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("omnifocus_operator.repository.protocol")
