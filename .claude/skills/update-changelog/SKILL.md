---
name: update-changelog
description: Update CHANGELOG.md with the latest completed milestone. Reads milestone specs and audit reports, generates a changelog entry in Keep a Changelog format. Trigger on "update changelog", "changelog", "update the changelog".
---

# Update Changelog

Add the latest completed milestone(s) to `CHANGELOG.md`.

## Execution Flow

### Step 1: Determine what's missing

1. Read `CHANGELOG.md` — note the highest versioned entry (e.g., `[1.3.3]`)
2. Read `.planning/STATE.md` — note the current milestone
3. List `.planning/milestones/` — find any milestone audits between the last changelog entry and the current milestone
4. If nothing is missing, tell the user the changelog is up to date and stop

### Step 2: Check for milestone audit

For each missing milestone version:

1. Check if `.planning/milestones/v{VERSION}-MILESTONE-AUDIT.md` exists
2. If it exists and `status: passed`, proceed to Step 3
3. If it doesn't exist or didn't pass, tell the user:
   > "Milestone v{VERSION} doesn't have a passing audit yet. Run `/gsd-audit-milestone` first, then come back."

   Stop here — don't generate changelog entries for unaudited milestones.

### Step 3: Generate the entry

For each audited milestone, read these sources:
- `.research/updated-spec/MILESTONE-v{VERSION}.md` — the spec (what was planned)
- `.planning/milestones/v{VERSION}-MILESTONE-AUDIT.md` — the audit (what was verified)
- `.planning/milestones/v{VERSION}-REQUIREMENTS.md` — the requirements (what was delivered)

Generate a changelog entry following the existing format in `CHANGELOG.md`:
- Use [Keep a Changelog](https://keepachangelog.com/) categories: **Added**, **Changed**, **Fixed**
- Only include categories that apply
- Focus on user-facing changes (new tools, new filters, new fields, behavioral changes)
- Include breaking changes under **Changed** with clear description of what changed
- Keep entries concise — one bullet per feature, not per implementation detail
- Use the milestone subtitle as the section title (e.g., `## [1.3.3] - Ordering & Move Fix`)

### Step 4: Insert into CHANGELOG.md

1. Insert the new entry after `## [Unreleased]` and before the previous version
2. If `[Unreleased]` has items that belong to this version, move them into the new entry
3. Show the user the new entry for review before committing
4. Commit with message: `docs: update CHANGELOG for v{VERSION}`

## Format Reference

```markdown
## [1.3.3] - Ordering & Move Fix

### Added
- `order` field on task responses — 1-based integer reflecting outline order

### Fixed
- `moveTo beginning/ending` on same container no longer silently ignored
```

## Rules

- Never invent changes — everything must trace to the audit or spec
- Don't include internal refactors unless they're breaking (changed public API)
- Match the tone and density of existing entries in the file
- One milestone per entry — don't combine multiple milestones into one section
