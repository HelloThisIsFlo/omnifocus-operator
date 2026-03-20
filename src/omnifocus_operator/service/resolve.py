"""Input resolution -- verify and normalize raw user identifiers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from omnifocus_operator.agent_messages.errors import (
    AMBIGUOUS_TAG,
    PARENT_NOT_FOUND,
    PROJECT_NOT_FOUND,
    TAG_NOT_FOUND,
    TASK_NOT_FOUND,
)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.protocols import Repository
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task

logger = logging.getLogger("omnifocus_operator")

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
        all_data = await self._repo.get_all()
        resolved: list[str] = []
        for name in tag_names:
            tag_id = self._match_tag(name, all_data.tags)
            resolved.append(tag_id)
        return resolved

    def _match_tag(self, name: str, tags: list[Tag]) -> str:
        """Find a single tag by name (case-insensitive) or ID."""
        matches = [t for t in tags if t.name.lower() == name.lower()]
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            ids = ", ".join(m.id for m in matches)
            msg = AMBIGUOUS_TAG.format(name=name, ids=ids)
            raise ValueError(msg)
        # No name match -- try as ID fallback
        logger.debug("Resolver.resolve_tags: '%s' no name match, trying as ID", name)
        id_match = next((t for t in tags if t.id == name), None)
        if id_match is not None:
            return id_match.id
        msg = TAG_NOT_FOUND.format(name=name)
        raise ValueError(msg)
