---
status: resolved
trigger: "Note field encoding artifacts in hybrid/SQLite read path"
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T02:00:00Z
---

## Current Focus

hypothesis: HybridRepository reads `noteXMLData` (BLOB) and does naive regex tag-stripping, which leaves font artifacts, swallows newlines, and preserves HTML entities. A `plainTextNote` TEXT column exists in the same table and is unused.
test: Confirmed by reading SQLite schema + hybrid.py source
expecting: n/a -- root cause confirmed
next_action: Report diagnosis

## Symptoms

expected: Notes from the SQLite/hybrid read path should contain clean plain text with proper newlines (matching bridge output)
actual: Notes contain `.AppleSystemUIFont` artifacts (from NSAttributedString XML), newlines are swallowed, `&` appears as `&amp;`, `>` as `&gt;`
errors: No errors -- data quality issue
reproduction: Read any task with a multi-line note or special characters via the hybrid repository
started: Since HybridRepository was implemented (v1.1)

## Eliminated

(none -- root cause found on first hypothesis)

## Evidence

- timestamp: 2026-03-08
  checked: SQLite schema (`sqlite_schema.sql` line 14-15)
  found: Task table has TWO note columns -- `plainTextNote` (TEXT) and `noteXMLData` (BLOB)
  implication: A plain-text column exists and is likely maintained by OmniFocus alongside the XML version

- timestamp: 2026-03-08
  checked: `hybrid.py` `_extract_note_text()` (lines 104-114)
  found: Function reads `noteXMLData` (BLOB), decodes UTF-8, then does `re.sub(r"<[^>]+>", "", text)` -- a naive regex strip of XML tags
  implication: This regex approach has three problems: (1) it leaves text content from XML attributes like font names (`.AppleSystemUIFont`), (2) it strips `<p>` tags without inserting newlines, (3) it doesn't decode HTML entities (`&amp;`, `&gt;`)

- timestamp: 2026-03-08
  checked: `hybrid.py` `_map_task_row()` (line 269) and `_map_project_row()` (line 312)
  found: Both call `_extract_note_text(row["noteXMLData"])` -- reading the XML blob column
  implication: The fix would be to read `row["plainTextNote"]` instead, or fall back to it

- timestamp: 2026-03-08
  checked: Bridge path (`bridge.js` line 117)
  found: Bridge reads `t.note` which is the OmniJS API's built-in plain-text accessor -- OmniJS handles the XML-to-text conversion internally
  implication: Bridge path works correctly because OmniJS does proper conversion

- timestamp: 2026-03-08
  checked: Verification script (`verify_field_coverage.py` lines 243, 273-282)
  found: The v1.1 field coverage analysis explicitly investigated both `plainTextNote` and `noteXMLData`, confirming both exist. The note field mapping (line 243) says "Check if plainTextNote or noteXMLData"
  implication: The plain-text column was known to exist during research but `noteXMLData` was chosen (or defaulted to) during implementation

- timestamp: 2026-03-08
  checked: Folder and Context (Tag) tables in schema
  found: Folder (line 114) and Context (line 129) only have `noteXMLData` -- no `plainTextNote` column
  implication: `plainTextNote` is Task-table-only. If notes are ever exposed for Folders/Tags, the XML parsing issue would need a proper fix for those entities

## Resolution

root_cause: |
  `HybridRepository._extract_note_text()` reads the `noteXMLData` BLOB column and applies a naive regex tag-strip (`re.sub(r"<[^>]+>", "", text)`). This approach fails in three ways:
  1. **Font artifacts**: XML attributes like `.AppleSystemUIFont` from `<style>` elements are text content after tag stripping
  2. **Swallowed newlines**: `<p>` paragraph tags are stripped without inserting `\n` replacements
  3. **HTML entities**: `&amp;` and `&gt;` are not decoded back to `&` and `>`

  The Task table has a `plainTextNote` TEXT column (line 14 of schema) that OmniFocus maintains alongside `noteXMLData`. This column contains clean plain text and is the correct column to read.

fix: (not applied -- diagnosis only)
verification: (not applied -- diagnosis only)
files_changed: []
