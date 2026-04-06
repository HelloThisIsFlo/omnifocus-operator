"""Unit tests for the fuzzy matching module (service.fuzzy)."""

from omnifocus_operator.service.fuzzy import suggest_close_matches


class TestSuggestCloseMatches:
    """Fuzzy matching for did-you-mean suggestions."""

    def test_close_match_found(self) -> None:
        result = suggest_close_matches("Wrok", ["Work", "Home", "Errand"])
        assert "Work" in result

    def test_close_match_personl(self) -> None:
        """'Personl' against ['Personal', 'Work', 'Errands'] -> ['Personal']."""
        result = suggest_close_matches("Personl", ["Personal", "Work", "Errands"])
        assert result == ["Personal"]

    def test_close_match_wrk(self) -> None:
        """'Wrk' against ['Personal', 'Work', 'Errands'] -> ['Work']."""
        result = suggest_close_matches("Wrk", ["Personal", "Work", "Errands"])
        assert result == ["Work"]

    def test_no_match(self) -> None:
        result = suggest_close_matches("zzzzz", ["Work", "Home"])
        assert result == []

    def test_returns_up_to_3(self) -> None:
        """Returns up to 3 matches by default."""
        names = ["Aaa", "Aab", "Aac", "Aad", "Zzz"]
        result = suggest_close_matches("Aaa", names)
        assert len(result) <= 3
