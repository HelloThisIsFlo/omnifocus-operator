"""Contracts package -- typed boundaries, commands, payloads, results.

Re-exports all contracts models and protocols for convenient importing.
Calls model_rebuild() to resolve forward references from
``from __future__ import annotations``.
"""

from pydantic import AwareDatetime

from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    _Unset,
)
from omnifocus_operator.contracts.common import MoveAction, TagAction
from omnifocus_operator.contracts.protocols import Bridge, Repository, Service
from omnifocus_operator.contracts.use_cases.add_task import (
    AddTaskCommand,
    AddTaskRepoPayload,
    AddTaskRepoResult,
    AddTaskResult,
)
from omnifocus_operator.contracts.use_cases.edit_task import (
    EditTaskActions,
    EditTaskCommand,
    EditTaskRepoPayload,
    EditTaskRepoResult,
    EditTaskResult,
    MoveToRepoPayload,
)

# Resolve forward references now that all modules are imported.
# Models using ``from __future__ import annotations`` need explicit
# type resolution for AwareDatetime and cross-model references.
_ns: dict[str, type] = {
    "AwareDatetime": AwareDatetime,
    "TagAction": TagAction,
    "MoveAction": MoveAction,
    "EditTaskActions": EditTaskActions,
    "AddTaskCommand": AddTaskCommand,
    "AddTaskResult": AddTaskResult,
    "AddTaskRepoPayload": AddTaskRepoPayload,
    "AddTaskRepoResult": AddTaskRepoResult,
    "EditTaskCommand": EditTaskCommand,
    "EditTaskResult": EditTaskResult,
    "EditTaskRepoPayload": EditTaskRepoPayload,
    "MoveToRepoPayload": MoveToRepoPayload,
    "EditTaskRepoResult": EditTaskRepoResult,
}

# Base and common models
CommandModel.model_rebuild(_types_namespace=_ns)
TagAction.model_rebuild(_types_namespace=_ns)
MoveAction.model_rebuild(_types_namespace=_ns)

# Create-task models
AddTaskCommand.model_rebuild(_types_namespace=_ns)
AddTaskResult.model_rebuild(_types_namespace=_ns)
AddTaskRepoPayload.model_rebuild(_types_namespace=_ns)
AddTaskRepoResult.model_rebuild(_types_namespace=_ns)

# Edit-task models
EditTaskActions.model_rebuild(_types_namespace=_ns)
EditTaskCommand.model_rebuild(_types_namespace=_ns)
EditTaskResult.model_rebuild(_types_namespace=_ns)
MoveToRepoPayload.model_rebuild(_types_namespace=_ns)
EditTaskRepoPayload.model_rebuild(_types_namespace=_ns)
EditTaskRepoResult.model_rebuild(_types_namespace=_ns)

__all__ = [
    "UNSET",
    "AddTaskCommand",
    "AddTaskRepoPayload",
    "AddTaskRepoResult",
    "AddTaskResult",
    "Bridge",
    "CommandModel",
    "EditTaskActions",
    "EditTaskCommand",
    "EditTaskRepoPayload",
    "EditTaskRepoResult",
    "EditTaskResult",
    "MoveAction",
    "MoveToRepoPayload",
    "Repository",
    "Service",
    "TagAction",
    "_Unset",
]
