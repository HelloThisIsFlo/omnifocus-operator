"""List-entity contracts: query models, repo queries, and result containers.

Re-exports all public names from submodules for convenient imports.
"""

from omnifocus_operator.contracts.use_cases.list._enums import (
    AvailabilityFilter,
    FolderAvailabilityFilter,
    TagAvailabilityFilter,
)
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult, ListResult
from omnifocus_operator.contracts.use_cases.list.folders import (
    ListFoldersQuery,
    ListFoldersRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.perspectives import (
    ListPerspectivesQuery,
    ListPerspectivesRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.projects import (
    DurationUnit,
    ListProjectsQuery,
    ListProjectsRepoQuery,
    ReviewDueFilter,
)
from omnifocus_operator.contracts.use_cases.list.tags import (
    ListTagsQuery,
    ListTagsRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.tasks import (
    ListTasksQuery,
    ListTasksRepoQuery,
)

__all__ = [
    "AvailabilityFilter",
    "DurationUnit",
    "FolderAvailabilityFilter",
    "ListFoldersQuery",
    "ListFoldersRepoQuery",
    "ListPerspectivesQuery",
    "ListPerspectivesRepoQuery",
    "ListProjectsQuery",
    "ListProjectsRepoQuery",
    "ListRepoResult",
    "ListResult",
    "ListTagsQuery",
    "ListTagsRepoQuery",
    "ListTasksQuery",
    "ListTasksRepoQuery",
    "ReviewDueFilter",
    "TagAvailabilityFilter",
]
