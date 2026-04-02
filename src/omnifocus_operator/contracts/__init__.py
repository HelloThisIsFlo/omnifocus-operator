"""Contracts package -- typed boundaries, commands, payloads, results.

Re-exports all contracts models and protocols for convenient importing.
Calls model_rebuild() to resolve forward references from
``from __future__ import annotations``.
"""

from pydantic import AwareDatetime

from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
    PatchOrNone,
    QueryModel,
    StrictModel,
    _Unset,
)
from omnifocus_operator.contracts.protocols import Bridge, Repository, Service
from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction
from omnifocus_operator.contracts.shared.repetition_rule import (
    EndByDateSpec,
    EndByOccurrencesSpec,
    EndConditionSpec,
    RepetitionRuleAddSpec,
    RepetitionRuleEditSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.contracts.use_cases.add.tasks import (
    AddTaskCommand,
    AddTaskRepoPayload,
    AddTaskRepoResult,
    AddTaskResult,
)
from omnifocus_operator.contracts.use_cases.edit.tasks import (
    EditTaskActions,
    EditTaskCommand,
    EditTaskRepoPayload,
    EditTaskRepoResult,
    EditTaskResult,
    MoveToRepoPayload,
)
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult, ListResult
from omnifocus_operator.contracts.use_cases.list.folders import (
    ListFoldersQuery,
    ListFoldersRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.projects import (
    ListProjectsQuery,
    ListProjectsRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.tags import (
    ListTagsQuery,
    ListTagsRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.tasks import (
    ListTasksQuery,
    ListTasksRepoQuery,
)
from omnifocus_operator.models.repetition_rule import EndCondition, Frequency

# Resolve forward references now that all modules are imported.
# Models using ``from __future__ import annotations`` need explicit
# type resolution for AwareDatetime and cross-model references.
_ns: dict[str, type | object] = {
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
    "EndByDateSpec": EndByDateSpec,
    "EndByOccurrencesSpec": EndByOccurrencesSpec,
    "EndConditionSpec": EndConditionSpec,
    "RepetitionRuleAddSpec": RepetitionRuleAddSpec,
    "RepetitionRuleEditSpec": RepetitionRuleEditSpec,
    "RepetitionRuleRepoPayload": RepetitionRuleRepoPayload,
    "Frequency": Frequency,
    "EndCondition": EndCondition,
    "ListResult": ListResult,
    "ListRepoResult": ListRepoResult,
    "ListTasksQuery": ListTasksQuery,
    "ListTasksRepoQuery": ListTasksRepoQuery,
    "ListProjectsQuery": ListProjectsQuery,
    "ListProjectsRepoQuery": ListProjectsRepoQuery,
    "ListTagsQuery": ListTagsQuery,
    "ListTagsRepoQuery": ListTagsRepoQuery,
    "ListFoldersQuery": ListFoldersQuery,
    "ListFoldersRepoQuery": ListFoldersRepoQuery,
    "QueryModel": QueryModel,
    "StrictModel": StrictModel,
}

# Base and common models
StrictModel.model_rebuild(_types_namespace=_ns)
CommandModel.model_rebuild(_types_namespace=_ns)
QueryModel.model_rebuild(_types_namespace=_ns)
TagAction.model_rebuild(_types_namespace=_ns)
MoveAction.model_rebuild(_types_namespace=_ns)

# List-entity models
ListResult.model_rebuild(_types_namespace=_ns)
ListRepoResult.model_rebuild(_types_namespace=_ns)
ListTasksQuery.model_rebuild(_types_namespace=_ns)
ListTasksRepoQuery.model_rebuild(_types_namespace=_ns)
ListProjectsQuery.model_rebuild(_types_namespace=_ns)
ListProjectsRepoQuery.model_rebuild(_types_namespace=_ns)
ListTagsQuery.model_rebuild(_types_namespace=_ns)
ListTagsRepoQuery.model_rebuild(_types_namespace=_ns)
ListFoldersQuery.model_rebuild(_types_namespace=_ns)
ListFoldersRepoQuery.model_rebuild(_types_namespace=_ns)

# Create-task models
AddTaskCommand.model_rebuild(_types_namespace=_ns)
AddTaskResult.model_rebuild(_types_namespace=_ns)
AddTaskRepoPayload.model_rebuild(_types_namespace=_ns)
AddTaskRepoResult.model_rebuild(_types_namespace=_ns)

# Repetition rule spec models
EndByDateSpec.model_rebuild(_types_namespace=_ns)
EndByOccurrencesSpec.model_rebuild(_types_namespace=_ns)
RepetitionRuleAddSpec.model_rebuild(_types_namespace=_ns)
RepetitionRuleEditSpec.model_rebuild(_types_namespace=_ns)
RepetitionRuleRepoPayload.model_rebuild(_types_namespace=_ns)

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
    "ListFoldersQuery",
    "ListFoldersRepoQuery",
    "ListProjectsQuery",
    "ListProjectsRepoQuery",
    "ListRepoResult",
    "ListTagsQuery",
    "ListTagsRepoQuery",
    "ListTasksQuery",
    "ListTasksRepoQuery",
    "MoveAction",
    "MoveToRepoPayload",
    "Patch",
    "PatchOrClear",
    "PatchOrNone",
    "QueryModel",
    "RepetitionRuleAddSpec",
    "RepetitionRuleEditSpec",
    "RepetitionRuleRepoPayload",
    "Repository",
    "Service",
    "StrictModel",
    "TagAction",
    "_Unset",
]
