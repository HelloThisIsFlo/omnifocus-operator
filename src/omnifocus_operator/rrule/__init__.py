"""RRULE parser and builder for OmniFocus repetition rules.

Public API:
    parse_rrule(rule_string) -> Frequency  -- parse RRULE to frequency model
    parse_end_condition(rule_string) -> EndByDate | EndByOccurrences | None
    build_rrule(frequency, end=None) -> str  -- build RRULE string from frequency model
"""

from omnifocus_operator.rrule.builder import build_rrule
from omnifocus_operator.rrule.parser import parse_end_condition, parse_rrule

__all__ = ["build_rrule", "parse_end_condition", "parse_rrule"]
