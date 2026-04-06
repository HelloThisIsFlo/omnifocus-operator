"""Tests for service-layer error classes — message formatting and structured data."""

from __future__ import annotations

from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.service.errors import AmbiguousNameError, EntityTypeMismatchError


class TestEntityTypeMismatchError:
    """EntityTypeMismatchError formats a readable message from structured data."""

    def test_single_accepted_type(self) -> None:
        err = EntityTypeMismatchError(
            "$inbox",
            resolved_type=EntityType.PROJECT,
            accepted_types=[EntityType.TASK],
        )
        assert str(err) == "'$inbox' resolved to project, but only task is accepted here"

    def test_multiple_accepted_types(self) -> None:
        err = EntityTypeMismatchError(
            "some-tag",
            resolved_type=EntityType.TAG,
            accepted_types=[EntityType.PROJECT, EntityType.TASK],
        )
        assert str(err) == "'some-tag' resolved to tag, but only project/task is accepted here"


class TestAmbiguousNameError:
    """AmbiguousNameError formats entity type label and match list from structured data."""

    def test_single_accepted_type(self) -> None:
        err = AmbiguousNameError(
            "Beta",
            accepted_types=[EntityType.TASK],
            matches=[("t-1", "Beta"), ("t-2", "Beta Task A")],
        )
        assert str(err) == (
            "Ambiguous task 'Beta': multiple matches: t-1 (Beta), t-2 (Beta Task A). "
            "Use the ID to specify which one."
        )

    def test_multiple_accepted_types(self) -> None:
        err = AmbiguousNameError(
            "Review",
            accepted_types=[EntityType.PROJECT, EntityType.TASK],
            matches=[("p-1", "Review Q3"), ("t-1", "Review notes")],
        )
        assert str(err) == (
            "Ambiguous project/task 'Review': multiple matches: "
            "p-1 (Review Q3), t-1 (Review notes). "
            "Use the ID to specify which one."
        )
