"""Input resolution -- verify and normalize raw user identifiers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from omnifocus_operator.agent_messages.errors import (
    INVALID_SYSTEM_LOCATION,
    NAME_NOT_FOUND,
    PROJECT_NOT_FOUND,
    RESERVED_PREFIX,
    TAG_NOT_FOUND,
    TASK_NOT_FOUND,
)
from omnifocus_operator.config import SYSTEM_LOCATION_INBOX, SYSTEM_LOCATION_PREFIX
from omnifocus_operator.models.enums import EntityType, TagAvailability
from omnifocus_operator.service.errors import AmbiguousNameError, EntityTypeMismatchError
from omnifocus_operator.service.fuzzy import format_suggestions, suggest_close_matches

if TYPE_CHECKING:
    from collections.abc import Sequence

    from omnifocus_operator.contracts.protocols import Repository
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task

from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery


@runtime_checkable
class _HasIdAndName(Protocol):
    """Duck-typed protocol for entities with .id and .name attributes."""

    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...


logger = logging.getLogger(__name__)

__all__ = ["Resolver"]

# -- System location routing ---------------------------------------------------

_SYSTEM_LOCATIONS: dict[str, str] = {
    SYSTEM_LOCATION_INBOX: SYSTEM_LOCATION_INBOX,  # "$inbox" -> "$inbox"
}


class Resolver:
    """Resolves user-facing identifiers against the repository."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    # -- Private: system location resolution -----------------------------------

    def _resolve_system_location(self, value: str) -> str:
        """Resolve a $-prefixed value to a system location ID.

        Raises ValueError if the system location is not recognized.
        """
        if value in _SYSTEM_LOCATIONS:
            return _SYSTEM_LOCATIONS[value]
        valid = ", ".join(_SYSTEM_LOCATIONS.keys())
        msg = INVALID_SYSTEM_LOCATION.format(value=value, valid_locations=valid)
        raise ValueError(msg)

    # -- Private: entity fetching ----------------------------------------------

    async def _fetch_entities(self, accept: list[EntityType]) -> list[_HasIdAndName]:
        """Fetch entities from the repository based on accepted types."""
        entities: list[_HasIdAndName] = []
        if EntityType.PROJECT in accept or EntityType.TASK in accept:
            all_data = await self._repo.get_all()
            if EntityType.PROJECT in accept:
                entities.extend(all_data.projects)
            if EntityType.TASK in accept:
                entities.extend(all_data.tasks)
        if EntityType.TAG in accept:
            tags_result = await self._repo.list_tags(
                ListTagsRepoQuery(availability=list(TagAvailability), limit=None)
            )
            entities.extend(tags_result.items)
        return entities

    # -- Private: resolution cascade -------------------------------------------

    async def _resolve(
        self,
        value: str,
        *,
        accept: list[EntityType],
        entities: Sequence[_HasIdAndName] | None = None,
    ) -> str:
        """Three-step resolution cascade: $-prefix -> substring match -> ID fallback.

        Parameters
        ----------
        value:
            The user-provided string to resolve (name, ID, or $-location).
        accept:
            Which entity types to search among.
        entities:
            Pre-fetched entities to search. If None, fetches from repository.
        """
        assert accept, "accept must not be empty, please provide at least one entity type"

        entity_type_label = "/".join(t.value for t in accept)

        # Step 1: $-prefix detection
        if value.startswith(SYSTEM_LOCATION_PREFIX):
            # System locations only valid in container context (PROJECT in accept)
            if EntityType.PROJECT in accept:
                return self._resolve_system_location(value)

            # Known system location in wrong context → typed exception
            if value in _SYSTEM_LOCATIONS:
                raise EntityTypeMismatchError(
                    value,
                    resolved_type=EntityType.PROJECT,
                    accepted_types=list(accept),
                )

            # Unknown $-prefix → reserved prefix error
            valid = ", ".join(_SYSTEM_LOCATIONS.keys())
            msg = RESERVED_PREFIX.format(
                value=value,
                prefix=SYSTEM_LOCATION_PREFIX,
                valid_locations=valid,
            )
            raise ValueError(msg)

        # Step 2: Fetch entities if not provided
        if entities is None:
            entities = await self._fetch_entities(accept)

        # Step 3: Substring match (case-insensitive)
        lower = value.lower()
        matches = [e for e in entities if lower in e.name.lower()]
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            raise AmbiguousNameError(
                value,
                accepted_types=list(accept),
                matches=[(m.id, m.name) for m in matches],
            )

        # Step 4: ID fallback
        id_match = next((e for e in entities if e.id == value), None)
        if id_match is not None:
            return id_match.id

        # Step 5: No match -- fuzzy suggestions
        entity_names = [e.name for e in entities]
        suggestions = suggest_close_matches(value, entity_names)
        entity_type = entity_type_label
        if suggestions:
            formatted = format_suggestions(suggestions, entities)
            suffix = f" Did you mean: {formatted}?"
        else:
            suffix = ""
        msg = NAME_NOT_FOUND.format(
            entity_type=entity_type,
            name=value,
            suggestions=suffix,
        )
        raise ValueError(msg)

    # -- Public: write-side resolution -----------------------------------------

    async def resolve_container(self, value: str) -> str | None:
        """Resolve a container reference (project or task) by name, ID, or $-location.

        Returns None for $inbox (inbox = no parent in bridge payload).
        """
        result = await self._resolve(value, accept=[EntityType.PROJECT, EntityType.TASK])
        return None if result == SYSTEM_LOCATION_INBOX else result

    async def resolve_anchor(self, value: str) -> str:
        """Resolve an anchor reference (task only) by name or ID."""
        return await self._resolve(value, accept=[EntityType.TASK])

    async def resolve_tags(self, tag_names: list[str]) -> list[str]:
        """Resolve tag names to IDs using substring matching.

        Pre-fetches the tag list once and reuses for all resolutions.
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
        return [
            await self._resolve(n, accept=[EntityType.TAG], entities=all_tags) for n in tag_names
        ]

    # -- Public: lookup methods (return full entities) -------------------------

    async def lookup_task(self, task_id: str) -> Task:
        """Verify task exists. Returns the Task. Raises ValueError if not found."""
        logger.debug("Resolver.lookup_task: id=%s", task_id)
        task = await self._repo.get_task(task_id)
        if task is None:
            msg = TASK_NOT_FOUND.format(id=task_id)
            raise ValueError(msg)
        return task

    async def lookup_project(self, project_id: str) -> Project:
        """Verify project exists. Returns the Project. Raises ValueError if not found."""
        logger.debug("Resolver.lookup_project: id=%s", project_id)
        project = await self._repo.get_project(project_id)
        if project is None:
            msg = PROJECT_NOT_FOUND.format(id=project_id)
            raise ValueError(msg)
        return project

    async def lookup_tag(self, tag_id: str) -> Tag:
        """Verify tag exists by ID. Returns the Tag. Raises ValueError if not found."""
        logger.debug("Resolver.lookup_tag: id=%s", tag_id)
        tag = await self._repo.get_tag(tag_id)
        if tag is None:
            msg = TAG_NOT_FOUND.format(name=tag_id)
            raise ValueError(msg)
        return tag

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
