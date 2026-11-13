"""Tests for scripts/changelog_release.py: tag classification and CHANGELOG -> Release notes."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.changelog_release import (
    FOOTER,
    ChangelogError,
    ReleaseNotes,
    classify_tag,
    main,
    release_for_tag,
)

JUNK_TAGS = ["vfoo", "1.4.7", "v1", "v1.2.3.4", "v1.5.0rc1"]

SYNTHETIC = """\
# Changelog

## [Unreleased]

## [1.4.7] - FastMCP 4

### Changed
- Runs on FastMCP 4

## [1.4] - Response Shaping

### Added
- Field selection
"""


class TestClassifyTag:
    @pytest.mark.parametrize(
        ("tag", "kind"),
        [
            ("v1.4.7", "patch"),
            ("v0.0.1", "patch"),
            ("v1.5.0", "milestone"),
            ("v1.4", "milestone"),
            ("v1.3", "milestone"),
        ],
    )
    def test_kind(self, tag: str, kind: str) -> None:
        assert classify_tag(tag) == kind

    @pytest.mark.parametrize("tag", JUNK_TAGS)
    def test_junk_tag_raises(self, tag: str) -> None:
        with pytest.raises(ChangelogError, match=re.escape(tag)):
            classify_tag(tag)

    @pytest.mark.parametrize("tag", JUNK_TAGS)
    def test_junk_tag_raises_in_extraction_too(self, tag: str) -> None:
        with pytest.raises(ChangelogError, match=re.escape(tag)):
            release_for_tag(SYNTHETIC, tag)


class TestClassifyCli:
    def test_patch(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["v1.4.7", "--classify"]) == 0
        out, err = capsys.readouterr()
        assert out == "patch\n"
        assert err == ""

    def test_milestone_logs_skip_line(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["v1.4", "--classify"]) == 0
        out, err = capsys.readouterr()
        assert out == "milestone\n"
        assert "Milestone release (1.4.0)" in err
        assert "release-milestone skill" in err

    def test_three_part_milestone_skip_line(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["v1.5.0", "--classify"]) == 0
        out, err = capsys.readouterr()
        assert out == "milestone\n"
        assert err == (
            "Milestone release (1.5.0): GitHub Release is created by the "
            "release-milestone skill after the CHANGELOG is written; skipping.\n"
        )

    def test_junk_fails(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["vfoo", "--classify"]) == 1
        out, err = capsys.readouterr()
        assert out == ""
        assert err.startswith("error: ")
        assert "vfoo" in err

    def test_classify_never_reads_changelog(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "nope.md"
        assert main(["v1.4.7", "--classify", "--changelog", str(missing)]) == 0
        assert capsys.readouterr().out == "patch\n"


class TestExtraction:
    def test_happy_path(self) -> None:
        notes = release_for_tag(SYNTHETIC, "v1.4.7")
        assert notes == ReleaseNotes(
            title="v1.4.7 — FastMCP 4",
            body=(
                "### Changed\n- Runs on FastMCP 4\n\n---\n\n"
                "Full CHANGELOG: "
                "https://github.com/HelloThisIsFlo/omnifocus-operator/blob/main/CHANGELOG.md\n"
            ),
        )

    def test_body_ends_with_footer_and_one_newline(self) -> None:
        body = release_for_tag(SYNTHETIC, "v1.4.7").body
        assert body.endswith(FOOTER)
        assert body.endswith("CHANGELOG.md\n")
        assert not body.endswith("\n\n")

    def test_last_section_runs_to_end_of_file(self) -> None:
        notes = release_for_tag(SYNTHETIC, "v1.4")
        assert notes.title == "v1.4 — Response Shaping"
        assert notes.body == "### Added\n- Field selection" + FOOTER

    def test_title_uses_tag_as_given_and_strips_trailing_space(self) -> None:
        changelog = "## [2.1.3] - Spaced Out   \n\n- fix\n"
        assert release_for_tag(changelog, "v2.1.3").title == "v2.1.3 — Spaced Out"

    def test_extraction_works_for_milestone_tags(self) -> None:
        # Extraction never consults the classification: the release-milestone
        # skill will call it for milestone tags.
        assert classify_tag("v1.4") == "milestone"
        assert release_for_tag(SYNTHETIC, "v1.4").body.startswith("### Added")

    def test_missing_section_names_tag_and_heading(self) -> None:
        with pytest.raises(ChangelogError) as exc_info:
            release_for_tag(SYNTHETIC, "v9.9.9")
        message = str(exc_info.value)
        assert "v9.9.9" in message
        assert "## [X.Y.Z] - <Title>" in message


class TestExtractCli:
    def test_writes_notes_and_prints_title(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(SYNTHETIC, encoding="utf-8")
        notes_file = tmp_path / "out" / "notes.md"

        code = main(["v1.4.7", "--notes-file", str(notes_file), "--changelog", str(changelog)])

        assert code == 0
        assert capsys.readouterr().out == "v1.4.7 — FastMCP 4\n"
        assert notes_file.read_text(encoding="utf-8") == release_for_tag(SYNTHETIC, "v1.4.7").body

    def test_missing_tag_fails_without_writing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(SYNTHETIC, encoding="utf-8")
        notes_file = tmp_path / "notes.md"

        code = main(["v9.9.9", "--notes-file", str(notes_file), "--changelog", str(changelog)])

        assert code == 1
        out, err = capsys.readouterr()
        assert out == ""
        assert err.startswith("error: ")
        assert "v9.9.9" in err
        assert str(changelog) in err
        assert not notes_file.exists()

    def test_missing_changelog_fails_without_writing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        notes_file = tmp_path / "notes.md"
        missing = tmp_path / "nope.md"

        code = main(["v1.4.7", "--notes-file", str(notes_file), "--changelog", str(missing)])

        assert code == 1
        err = capsys.readouterr().err
        assert err.startswith("error: ")
        assert str(missing) in err
        assert not notes_file.exists()

    def test_mode_is_required(self) -> None:
        with pytest.raises(SystemExit):
            main(["v1.4.7"])


def _section(version: str, title: str, content: str = "- change") -> str:
    return f"## [{version}] - {title}\n\n{content}\n\n"


class TestVersionMatching:
    @pytest.mark.parametrize(
        ("tag", "heading"),
        [
            ("v1.3", "1.3.0"),
            ("v1.4", "1.4"),
            ("v1.4.0", "1.4"),
            ("v1.0", "1.0.0"),
            ("v1.4.7", "1.4.7"),
        ],
    )
    def test_trailing_zeros_are_ignored(self, tag: str, heading: str) -> None:
        changelog = _section(heading, "Match", "- yes")
        notes = release_for_tag(changelog, tag)
        assert notes.title == f"{tag} — Match"
        assert notes.body == "- yes" + FOOTER

    @pytest.mark.parametrize("heading", ["1.4.1", "1.40", "1.4.0.1", "14"])
    def test_v1_4_does_not_match_other_versions(self, heading: str) -> None:
        with pytest.raises(ChangelogError, match=re.escape("v1.4")):
            release_for_tag(_section(heading, "Other"), "v1.4")

    def test_picks_the_matching_section_among_neighbours(self) -> None:
        changelog = (
            _section("1.4.1", "Patch", "- patch")
            + _section("1.4", "Minor", "- minor")
            + _section("1.3.0", "Older", "- older")
        )
        assert release_for_tag(changelog, "v1.4").body == "- minor" + FOOTER
        assert release_for_tag(changelog, "v1.4.1").body == "- patch" + FOOTER
        assert release_for_tag(changelog, "v1.3").body == "- older" + FOOTER


class TestUnreleased:
    def test_untitled_unreleased_is_skipped(self) -> None:
        changelog = "## [Unreleased]\n\n- wip\n\n" + _section("1.2.0", "X", "- shipped")
        notes = release_for_tag(changelog, "v1.2")
        assert notes.title == "v1.2 — X"
        assert notes.body == "- shipped" + FOOTER

    def test_titled_unreleased_is_never_a_candidate(self) -> None:
        changelog = "## [Unreleased] - Something\n\n- wip\n"
        with pytest.raises(ChangelogError, match=re.escape("v1.0")):
            release_for_tag(changelog, "v1.0")


class TestBodyCleanup:
    def test_trailing_separator_is_removed(self) -> None:
        changelog = "## [1.2.0] - X\n\n- a\n\n---\n\n## [1.1.0] - Y\n\n- b\n"
        assert release_for_tag(changelog, "v1.2.0").body == "- a" + FOOTER

    def test_link_reference_block_is_dropped(self) -> None:
        changelog = (
            "## [1.0.0] - X\n\n- a\n\n"
            "[1.0.0]: https://example.com/v1.0.0\n"
            "[Unreleased]: https://example.com/compare\n"
        )
        assert release_for_tag(changelog, "v1.0").body == "- a" + FOOTER

    def test_separator_before_link_references_is_removed_too(self) -> None:
        changelog = "## [1.0.0] - X\n\n- a\n- b\n\n---\n\n[1.0.0]: https://example.com/v1.0.0\n"
        assert release_for_tag(changelog, "v1.0").body == "- a\n- b" + FOOTER

    def test_separator_in_the_middle_is_kept(self) -> None:
        changelog = "## [1.2.0] - X\n\n- a\n\n---\n\n- b\n"
        assert release_for_tag(changelog, "v1.2.0").body == "- a\n\n---\n\n- b" + FOOTER


class TestRefusals:
    @pytest.mark.parametrize(
        "content",
        [
            "",
            "---",
            "[1.2.0]: https://example.com/v1.2.0",
            "---\n\n[1.2.0]: https://example.com/v1.2.0",
        ],
    )
    def test_empty_section_raises(self, content: str) -> None:
        changelog = _section("1.2.0", "X", content) + _section("1.1.0", "Y")
        with pytest.raises(ChangelogError, match="empty") as exc_info:
            release_for_tag(changelog, "v1.2.0")
        assert "v1.2.0" in str(exc_info.value)

    def test_empty_section_fails_cli_without_writing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(_section("1.2.1", "X", "") + _section("1.2.0", "Y"), encoding="utf-8")
        notes_file = tmp_path / "notes.md"

        code = main(["v1.2.1", "--notes-file", str(notes_file), "--changelog", str(changelog)])

        assert code == 1
        assert "empty" in capsys.readouterr().err
        assert not notes_file.exists()

    def test_ambiguous_headings_raise_naming_both(self) -> None:
        changelog = _section("1.4", "A") + _section("1.4.0", "B")
        with pytest.raises(ChangelogError) as exc_info:
            release_for_tag(changelog, "v1.4")
        message = str(exc_info.value)
        assert "v1.4" in message
        assert "[1.4]" in message
        assert "[1.4.0]" in message


REAL_CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
_VERSIONED_HEADING = re.compile(r"^## \[(\d+(?:\.\d+)*)\] - ", re.MULTILINE)


class TestRealChangelog:
    @pytest.mark.parametrize(
        ("tag", "title"),
        [
            ("v1.0", "v1.0 — Foundation"),
            ("v1.3", "v1.3 — Read Tools"),
            ("v1.4", "v1.4 — Response Shaping & Batch Processing"),
            ("v1.4.7", "v1.4.7 — FastMCP 4"),
        ],
    )
    def test_pinned_titles(self, tag: str, title: str) -> None:
        text = REAL_CHANGELOG.read_text(encoding="utf-8")
        assert release_for_tag(text, tag).title == title

    def test_every_versioned_section_has_a_body(self) -> None:
        # Guard run by `just ci` in publish.yml's test job: an empty versioned
        # section fails the job before anything reaches PyPI.
        text = REAL_CHANGELOG.read_text(encoding="utf-8")
        versions = _VERSIONED_HEADING.findall(text)
        assert versions
        for version in versions:
            notes = release_for_tag(text, f"v{version}")
            assert notes.body.removesuffix(FOOTER).strip(), version
