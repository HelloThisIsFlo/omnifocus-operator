"""Spec-to-core model conversion at service boundary.

Pure functions that convert write-side contract specs (FrequencyAddSpec,
EndConditionSpec) into read-side core models (Frequency, EndCondition).
Called by the add and edit pipelines before any downstream processing,
enforcing the type boundary documented in model-taxonomy.md.
"""

from __future__ import annotations

from omnifocus_operator.contracts.shared.repetition_rule import (
    EndByDateSpec,
    EndByOccurrencesSpec,
    EndConditionSpec,
    FrequencyAddSpec,
)
from omnifocus_operator.models.repetition_rule import (
    EndByDate,
    EndByOccurrences,
    EndCondition,
    Frequency,
)

__all__ = ["end_condition_from_spec", "frequency_from_spec"]


def frequency_from_spec(spec: FrequencyAddSpec) -> Frequency:
    """Convert a FrequencyAddSpec (contract) to a Frequency (core model).

    Field mapping is trivial -- identical names, widening types.
    """
    return Frequency.model_validate(spec.model_dump())


def end_condition_from_spec(spec: EndConditionSpec | None) -> EndCondition | None:
    """Convert an EndConditionSpec (contract) to an EndCondition (core model).

    Returns None if spec is None. Uses isinstance dispatch to construct
    the corresponding core type.
    """
    if spec is None:
        return None
    if isinstance(spec, EndByDateSpec):
        return EndByDate.model_validate(spec.model_dump())
    if isinstance(spec, EndByOccurrencesSpec):
        return EndByOccurrences.model_validate(spec.model_dump())
    msg = f"Unknown end condition spec type: {type(spec)}"
    raise TypeError(msg)
