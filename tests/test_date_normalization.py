"""RED tests for EndByDate date type normalization (str -> datetime.date)."""

from __future__ import annotations

from datetime import date

from omnifocus_operator.models.repetition_rule import EndByDate
from omnifocus_operator.repository.rrule.parser import parse_end_condition


class TestEndByDateTypeNormalization:
    """EndByDate.date must be datetime.date, not str."""

    def test_date_field_is_date_type(self):
        e = EndByDate(date=date(2026, 12, 31))
        assert isinstance(e.date, date)

    def test_model_dump_returns_date_object(self):
        e = EndByDate(date=date(2026, 12, 31))
        assert e.model_dump() == {"date": date(2026, 12, 31)}

    def test_json_dump_returns_iso_date_string(self):
        e = EndByDate(date=date(2026, 12, 31))
        assert e.model_dump(mode="json") == {"date": "2026-12-31"}

    def test_json_schema_has_date_format(self):
        schema = EndByDate.model_json_schema()
        assert schema["properties"]["date"]["format"] == "date"

    def test_parser_returns_date_object(self):
        result = parse_end_condition("FREQ=MONTHLY;UNTIL=20261231T000000Z")
        assert isinstance(result, EndByDate)
        assert result.date == date(2026, 12, 31)
        assert isinstance(result.date, date)
