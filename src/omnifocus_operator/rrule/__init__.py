"""RRULE parser and builder for OmniFocus repetition rules.

Public API:
    parse_rrule(rule_string) -> dict[str, Any]  -- parse RRULE to frequency dict
    parse_end_condition(rule_string) -> dict[str, Any] | None  -- extract end condition
    build_rrule(frequency, end=None) -> str  -- build RRULE string from frequency dict
"""

from omnifocus_operator.rrule.builder import build_rrule
from omnifocus_operator.rrule.parser import parse_end_condition, parse_rrule

__all__ = ["build_rrule", "parse_end_condition", "parse_rrule"]
