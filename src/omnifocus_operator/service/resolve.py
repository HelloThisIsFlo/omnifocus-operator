"""Input resolution -- verify and normalize raw user identifiers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Never, Protocol, runtime_checkable

from omnifocus_operator.agent_messages.errors import (
    CONTRADICTORY_INBOX_FALSE,
    CONTRADICTORY_INBOX_PROJECT,
    GET_PROJECT_INBOX_ERROR,
    NAME_NOT_FOUND,
    PROJECT_NOT_FOUND,
    RESERVED_PREFIX,
    TAG_NOT_FOUND,
    TASK_NOT_FOUND,
)
from omnifocus_operator.config import SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATIONS
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


class Resolver:
    """Resolves user-facing identifiers against the repository."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    # -- Private: entity fetching ----------------------------------------------

    async def _fetch_all_by_type(self) -> dict[EntityType, list[_HasIdAndName]]:
        """Fetch all entity types from the repository, grouped by type."""
        by_type: dict[EntityType, list[_HasIdAndName]] = {}
        all_data = await self._repo.get_all()
        by_type[EntityType.PROJECT] = list(all_data.projects)
        by_type[EntityType.TASK] = list(all_data.tasks)
        tags_result = await self._repo.list_tags(
            ListTagsRepoQuery(availability=list(TagAvailability), limit=None)
        )
        by_type[EntityType.TAG] = list(tags_result.items)
        return by_type

    # -- Private: resolution cascade -------------------------------------------

    async def _resolve(self, value: str, *, accept: list[EntityType]) -> str:
        """Resolution cascade: $-prefix → ID match → name match → mismatch → not found."""
        assert accept, "accept must not be empty, please provide at least one entity type"

        if value.startswith(SYSTEM_LOCATION_PREFIX):
            return self._resolve_system_location(value, accept)

        by_type = await self._fetch_all_by_type()

        # Exact ID match in accepted types (IDs are unambiguous — always wins)
        for entity_type in accept:
            if any(e.id == value for e in by_type.get(entity_type, [])):
                return value

        # Substring name match across all accepted types
        matches = [e for t in accept for e in by_type.get(t, []) if value.lower() in e.name.lower()]
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            raise AmbiguousNameError(
                value,
                accepted_types=list(accept),
                matches=[(m.id, m.name) for m in matches],
            )

        # Cross-type mismatch detection
        for entity_type in EntityType:
            if entity_type in accept:
                continue
            others = by_type.get(entity_type, [])
            if any(value.lower() in e.name.lower() or e.id == value for e in others):
                raise EntityTypeMismatchError(
                    value,
                    resolved_type=entity_type,
                    accepted_types=list(accept),
                )

        # Not found — fuzzy suggestions from accepted types only
        accepted_entities = [e for t in accept for e in by_type.get(t, [])]
        self._raise_not_found(value, accepted_entities, accept)

    # -- Private: system location resolution -----------------------------------

    @staticmethod
    def _resolve_system_location(value: str, accept: list[EntityType]) -> str:
        """Resolve a $-prefixed value to a system location ID.

        Raises ValueError for unknown locations, EntityTypeMismatchError
        if the location exists but its type is not in accept.
        """
        location = next((loc for loc in SYSTEM_LOCATIONS.values() if loc.id == value), None)
        if location is None:
            valid = ", ".join(loc.id for loc in SYSTEM_LOCATIONS.values())
            msg = RESERVED_PREFIX.format(
                value=value,
                prefix=SYSTEM_LOCATION_PREFIX,
                valid_locations=valid,
            )
            raise ValueError(msg)
        if location.type in accept:
            return location.id
        raise EntityTypeMismatchError(
            value,
            resolved_type=location.type,
            accepted_types=list(accept),
        )

    # -- Private: error helpers ------------------------------------------------

    @staticmethod
    def _raise_not_found(
        value: str,
        entities: Sequence[_HasIdAndName],
        accept: list[EntityType],
    ) -> Never:
        entity_type = "/".join(t.value for t in accept)
        suggestions = suggest_close_matches(value, [e.name for e in entities])
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
        return None if result == SYSTEM_LOCATIONS["inbox"].id else result

    async def resolve_anchor(self, value: str) -> str:
        """Resolve an anchor reference (task only) by name or ID."""
        return await self._resolve(value, accept=[EntityType.TASK])

    async def resolve_tags(self, tag_names: list[str]) -> list[str]:
        """Resolve tag names to IDs using substring matching."""
        logger.debug(
            "Resolver.resolve_tags: resolving %d tags: %s",
            len(tag_names),
            tag_names,
        )
        return [await self._resolve(n, accept=[EntityType.TAG]) for n in tag_names]

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
        if project_id.startswith(SYSTEM_LOCATION_PREFIX):
            raise ValueError(GET_PROJECT_INBOX_ERROR)
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

    # -- Read-side resolution (inbox normalization) ----------------------------

    def resolve_inbox(
        self,
        in_inbox: bool | None,
        project: str | None,
        parent: str | None,
    ) -> tuple[bool | None, str | None, str | None]:
        """Resolve inbox filter state from (in_inbox, project, parent) filter params.

        Returns (effective_in_inbox, remaining_project, remaining_parent).

        Phase 57-02 (D-09): single consolidation point for all ``$inbox``
        semantics across both surface filters.

        Consumption rules:
        - ``project`` is ``"$inbox"`` -> project consumed (returns ``None``);
          ``in_inbox`` becomes ``True``.
        - ``parent`` is ``"$inbox"`` -> parent consumed (returns ``None``);
          ``in_inbox`` becomes ``True``.
        - Both ``"$inbox"`` is allowed (both consume independently).

        Contradiction rules:
        - Either side's ``"$inbox"`` + ``in_inbox=False`` -> CONTRADICTORY_INBOX_FALSE.
        - After consumption, ``in_inbox=True`` with any non-None real (non-"$inbox")
          ref on either side -> CONTRADICTORY_INBOX_PROJECT.

        Unknown $-prefix on either side raises via ``_resolve_system_location``.
        The parent-side lookup accepts both PROJECT and TASK (parent is a
        two-type filter); the ``$inbox`` sentinel is registered as PROJECT
        and resolves successfully against either accept set.
        """
        # Consume $inbox from project (legacy 2-arg path -- accept=[PROJECT]).
        if project is not None and project.startswith(SYSTEM_LOCATION_PREFIX):
            self._resolve_system_location(project, [EntityType.PROJECT])
            if in_inbox is False:
                raise ValueError(CONTRADICTORY_INBOX_FALSE)
            in_inbox = True
            project = None

        # Consume $inbox from parent (accept=[PROJECT, TASK] since parent
        # accepts both entity types; the $inbox sentinel is type=PROJECT
        # and resolves successfully against either set).
        if parent is not None and parent.startswith(SYSTEM_LOCATION_PREFIX):
            self._resolve_system_location(parent, [EntityType.PROJECT, EntityType.TASK])
            if in_inbox is False:
                raise ValueError(CONTRADICTORY_INBOX_FALSE)
            in_inbox = True
            parent = None

        # Post-consumption: in_inbox=True with any real ref remaining is contradictory.
        # Note the semantic shift vs the old 2-arg form: before, $inbox consumption
        # returned (True, None) directly without a post-check; now we flow through a
        # unified gate so e.g. project="$inbox", parent="SomeTask" raises correctly.
        if in_inbox is True and (project is not None or parent is not None):
            raise ValueError(CONTRADICTORY_INBOX_PROJECT)

        return (in_inbox, project, parent)

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
