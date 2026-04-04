"""Input resolution -- verify and normalize raw user identifiers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from omnifocus_operator.agent_messages.errors import (
    AMBIGUOUS_ENTITY,
    PARENT_NOT_FOUND,
    PROJECT_NOT_FOUND,
    TAG_NOT_FOUND,
    TASK_NOT_FOUND,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from omnifocus_operator.contracts.protocols import Repository
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task

from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery
from omnifocus_operator.models.enums import TagAvailability


@runtime_checkable
class _HasIdAndName(Protocol):
    """Duck-typed protocol for entities with .id and .name attributes."""

    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...


logger = logging.getLogger(__name__)

__all__ = ["Resolver"]


class Resolver:
    """Resolves user-facing identifiers against the repository."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    async def resolve_parent(self, parent_id: str) -> str:
        """Verify parent exists as project or task.

        Returns the ID. Raises ValueError if not found.
        """
        logger.debug("Resolver.resolve_parent: id=%s", parent_id)
        project = await self._repo.get_project(parent_id)
        if project is not None:
            logger.debug("Resolver.resolve_parent: resolved as project")
            return parent_id

        task = await self._repo.get_task(parent_id)
        if task is not None:
            logger.debug("Resolver.resolve_parent: resolved as task")
            return parent_id

        msg = PARENT_NOT_FOUND.format(id=parent_id)
        raise ValueError(msg)

    async def resolve_task(self, task_id: str) -> Task:
        """Verify task exists. Returns the Task. Raises ValueError if not found."""
        logger.debug("Resolver.resolve_task: id=%s", task_id)
        task = await self._repo.get_task(task_id)
        if task is None:
            msg = TASK_NOT_FOUND.format(id=task_id)
            raise ValueError(msg)
        return task

    async def resolve_project(self, project_id: str) -> Project:
        """Verify project exists. Returns the Project. Raises ValueError if not found."""
        logger.debug("Resolver.resolve_project: id=%s", project_id)
        project = await self._repo.get_project(project_id)
        if project is None:
            msg = PROJECT_NOT_FOUND.format(id=project_id)
            raise ValueError(msg)
        return project

    async def resolve_tag(self, tag_id: str) -> Tag:
        """Verify tag exists by ID. Returns the Tag. Raises ValueError if not found."""
        logger.debug("Resolver.resolve_tag: id=%s", tag_id)
        tag = await self._repo.get_tag(tag_id)
        if tag is None:
            msg = TAG_NOT_FOUND.format(name=tag_id)
            raise ValueError(msg)
        return tag

    async def resolve_tags(self, tag_names: list[str]) -> list[str]:
        """Resolve tag names to IDs (case-insensitive).

        Falls back to ID lookup if name doesn't match.
        """
        logger.debug(
            "Resolver.resolve_tags: resolving %d tags: %s",
            len(tag_names),
            tag_names,
        )
        tags_result = await self._repo.list_tags(
            ListTagsRepoQuery(availability=list(TagAvailability), limit=None)
        )
        all_tags = tags_result.items
        resolved: list[str] = []
        for name in tag_names:
            tag_id = self._match_by_name(name, all_tags, "tag")
            resolved.append(tag_id)
        return resolved

    def _match_by_name(self, name: str, entities: Sequence[_HasIdAndName], entity_type: str) -> str:
        """Find a single entity by name (case-insensitive) or ID."""
        matches = [e for e in entities if e.name.lower() == name.lower()]
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            ids = ", ".join(m.id for m in matches)
            msg = AMBIGUOUS_ENTITY.format(entity_type=entity_type, name=name, ids=ids)
            raise ValueError(msg)
        # No name match -- try as ID fallback
        logger.debug("Resolver._match_by_name: '%s' no name match, trying as ID", name)
        id_match = next((e for e in entities if e.id == name), None)
        if id_match is not None:
            return id_match.id
        msg = TAG_NOT_FOUND.format(name=name)
        raise ValueError(msg)

    # -- Read-side resolution (filter cascade) --------------------------------

    def resolve_filter(self, value: str, entities: Sequence[_HasIdAndName]) -> list[str]:
        """Resolve a single filter value to entity IDs via the cascade.

        Steps:
        1. ID match: if value matches any entity's .id exactly, return [value]
        2. Substring match: case-insensitive substring check, return all matching IDs
        3. No match: return []
        """
        # Step 1: exact ID match
        if any(e.id == value for e in entities):
            logger.debug("Resolver.resolve_filter: '%s' matched as ID", value)
            return [value]

        # Step 2: case-insensitive substring match
        lower_value = value.lower()
        matches = [e.id for e in entities if lower_value in e.name.lower()]
        if matches:
            logger.debug(
                "Resolver.resolve_filter: '%s' substring matched %d entities",
                value,
                len(matches),
            )
            return matches

        # Step 3: no match
        logger.debug("Resolver.resolve_filter: '%s' no match found", value)
        return []

    def resolve_filter_list(
        self, values: list[str], entities: Sequence[_HasIdAndName]
    ) -> list[str]:
        """Resolve multiple filter values, accumulating all matched IDs.

        Each value is resolved independently through the cascade.
        Returns a flat deduplicated list of all resolved IDs.
        Values that don't resolve are simply not included.
        """
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            for eid in self.resolve_filter(value, entities):
                if eid not in seen:
                    seen.add(eid)
                    result.append(eid)
        return result

    def find_unresolved(self, values: list[str], entities: Sequence[_HasIdAndName]) -> list[str]:
        """Return values that did not resolve to any entity ID."""
        return [v for v in values if not self.resolve_filter(v, entities)]
