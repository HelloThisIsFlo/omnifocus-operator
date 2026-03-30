"""Add-task contracts: command, repo payload, repo result, result.

Re-exports all public names from submodules for convenient imports.
"""

from omnifocus_operator.contracts.use_cases.add.tasks import (
    AddTaskCommand,
    AddTaskRepoPayload,
    AddTaskRepoResult,
    AddTaskResult,
)

__all__ = [
    "AddTaskCommand",
    "AddTaskRepoPayload",
    "AddTaskRepoResult",
    "AddTaskResult",
]
