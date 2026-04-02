"""RRULE parser and builder for OmniFocus repetition rules.

Public API:
    parse_rrule(rule_string) -> Frequency  -- parse RRULE to frequency model
    parse_end_condition(rule_string) -> EndByDate | EndByOccurrences | None
    build_rrule(frequency, end=None) -> str  -- build RRULE string from frequency model
"""

from omnifocus_operator.repository.rrule.builder import build_rrule
from omnifocus_operator.repository.rrule.parser import parse_end_condition, parse_rrule
from omnifocus_operator.repository.rrule.schedule import derive_schedule

__all__ = ["build_rrule", "derive_schedule", "parse_end_condition", "parse_rrule"]
