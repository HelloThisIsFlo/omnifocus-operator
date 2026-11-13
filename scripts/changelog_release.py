"""Turn a git tag into its GitHub Release title and notes, straight from CHANGELOG.md.

Two modes:

- **classify**: is the tag a patch (``vX.Y.Z``, Z > 0) or a milestone
  (``vX.Y.0`` / ``vX.Y``)? CI only automates Releases for patches.
- **extract**: find the ``## [X.Y.Z] - <Title>`` section for the tag, print the
  Release title and write the Release body to a notes file.

Usage:
    python3 scripts/changelog_release.py v1.4.7 --classify
    python3 scripts/changelog_release.py v1.4.7 --notes-file notes.md
    python3 scripts/changelog_release.py v1.4.7 --notes-file notes.md --changelog CHANGELOG.md

Standard library only: CI runs it on the runner's preinstalled ``python3``.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

FOOTER = (
    "\n\n---\n\n"
    "Full CHANGELOG: https://github.com/HelloThisIsFlo/omnifocus-operator/blob/main/CHANGELOG.md\n"
)
EXPECTED_HEADING = "## [X.Y.Z] - <Title>"

_TAG_RE = re.compile(r"^v(\d+)\.(\d+)(?:\.(\d+))?$")
# Only dotted-numeric versions are candidates, so [Unreleased] never matches.
_HEADING_RE = re.compile(r"^## \[(?P<version>\d+(?:\.\d+)*)\] - (?P<title>.+)$", re.MULTILINE)
_NEXT_SECTION_RE = re.compile(r"^## ", re.MULTILINE)
_LINK_REFERENCE_RE = re.compile(r"^\[[^\]]+\]:\s", re.MULTILINE)


class ChangelogError(Exception):
    """A tag or CHANGELOG problem; the message is the user-facing explanation."""


@dataclass(frozen=True)
class ReleaseNotes:
    title: str
    body: str


def _parse_tag(tag: str) -> tuple[int, ...]:
    """Parse ``vX.Y`` or ``vX.Y.Z`` into an integer tuple; anything else is an error."""
    match = _TAG_RE.match(tag)
    if match is None:
        raise ChangelogError(
            f"tag {tag!r} is not a release tag: expected 'v' plus two or three "
            "dot-separated numbers (e.g. v1.4 or v1.4.7)"
        )
    return tuple(int(part) for part in match.groups() if part is not None)


def classify_tag(tag: str) -> Literal["patch", "milestone"]:
    """Patch = three parts with the third > 0; milestone = two parts or a zero third part."""
    parts = _parse_tag(tag)
    if len(parts) == 3 and parts[2] > 0:
        return "patch"
    return "milestone"


def _normalize(parts: Sequence[int]) -> tuple[int, ...]:
    """Drop trailing zeros so 1.4, 1.4.0 and v1.4 compare equal (but never 1.4.1 or 1.40)."""
    normalized = list(parts)
    while normalized and normalized[-1] == 0:
        normalized.pop()
    return tuple(normalized)


def _clean_body(section: str) -> str:
    """Strip Keep a Changelog footers: link-reference definitions and a trailing ``---``."""
    link_reference = _LINK_REFERENCE_RE.search(section)
    if link_reference:
        section = section[: link_reference.start()]
    lines = section.strip().split("\n")
    if lines[-1].strip() == "---":
        lines.pop()
    return "\n".join(lines).strip()


def release_for_tag(changelog: str, tag: str) -> ReleaseNotes:
    """Build the Release title and body for ``tag`` from the CHANGELOG text.

    Independent of :func:`classify_tag`: milestone tags extract just like patches.
    """
    wanted = _normalize(_parse_tag(tag))
    version = tag.removeprefix("v")
    expected = f"expected a heading like '{EXPECTED_HEADING}' for {version}"

    matches = [
        heading
        for heading in _HEADING_RE.finditer(changelog)
        if _normalize([int(part) for part in heading["version"].split(".")]) == wanted
    ]
    if not matches:
        raise ChangelogError(f"no CHANGELOG section for tag {tag}: {expected}")
    if len(matches) > 1:
        found = ", ".join(f"[{heading['version']}]" for heading in matches)
        raise ChangelogError(
            f"ambiguous CHANGELOG sections for tag {tag}: {found} all match; "
            f"keep exactly one ({expected})"
        )

    heading = matches[0]
    start = heading.end()
    next_section = _NEXT_SECTION_RE.search(changelog, start)
    end = next_section.start() if next_section else len(changelog)
    body = _clean_body(changelog[start:end])
    if not body:
        raise ChangelogError(
            f"CHANGELOG section [{heading['version']}] for tag {tag} is empty: "
            f"{expected} followed by release notes"
        )

    title = f"{tag} \u2014 {heading['title'].rstrip()}"
    return ReleaseNotes(title=title, body=body + FOOTER)


def _milestone_line(tag: str) -> str:
    parts = _parse_tag(tag)
    three_part = ".".join(str(part) for part in (*parts, 0, 0)[:3])
    return (
        f"Milestone release ({three_part}): GitHub Release is created by the "
        "release-milestone skill after the CHANGELOG is written; skipping."
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify a release tag, or extract its GitHub Release notes from CHANGELOG.md."
        ),
    )
    parser.add_argument("tag", help="release tag as pushed, e.g. v1.4.7")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--notes-file",
        type=Path,
        help="extract mode: write the Release body here and print the title",
    )
    mode.add_argument(
        "--classify",
        action="store_true",
        help="classify mode: print 'patch' or 'milestone'",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        default=Path("CHANGELOG.md"),
        help="CHANGELOG path for extract mode (default: CHANGELOG.md)",
    )
    args = parser.parse_args(argv)

    if args.classify:
        try:
            kind = classify_tag(args.tag)
        except ChangelogError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(kind)
        if kind == "milestone":
            print(_milestone_line(args.tag), file=sys.stderr)
        return 0

    changelog_path: Path = args.changelog
    try:
        text = changelog_path.read_text(encoding="utf-8")
        notes = release_for_tag(text, args.tag)
    except OSError as exc:
        print(f"error: cannot read {changelog_path}: {exc}", file=sys.stderr)
        return 1
    except ChangelogError as exc:
        print(f"error: {exc} (in {changelog_path})", file=sys.stderr)
        return 1

    notes_path: Path = args.notes_file
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(notes.body, encoding="utf-8")
    print(notes.title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
