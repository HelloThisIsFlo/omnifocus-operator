# Milestone v1.4.1 -- Fuzzy Search

## Goal

Agents can find tasks despite typos and partial recall. After this milestone, the `search` parameter on `list_tasks` and `count_tasks` supports fuzzy matching in addition to the existing substring search (SQL LIKE) from v1.3. No new tools -- enhances existing search parameter.

## What to Build

### Fuzzy Matching Engine

- Index-based fuzzy matching for task names and notes
- In-memory index built from snapshot, refreshed on snapshot change
- Substring (SQL LIKE) matches rank higher than fuzzy matches
- Builds on v1.3 filtering infrastructure (`list_tasks`, `count_tasks`)

### Edge Cases

- Emoji in task names
- Unicode normalization (e.g., accented characters: é vs e)
- Very short queries (1-2 characters) -- likely too ambiguous for fuzzy, fall back to substring only

### Integration

- Same `search` parameter on `list_tasks` and `count_tasks` -- fuzzy is additive, not a separate mode
- Fuzzy results appended after exact/substring matches (ranking: exact > substring > fuzzy)
- Bridge fallback: fuzzy matching runs in Python against the snapshot (same as SQLite path uses the in-memory index)

## Key Acceptance Criteria

- Fuzzy search finds tasks despite typos (e.g., "reveiw" matches "Review Q3 roadmap")
- Substring matches always rank above fuzzy matches
- Index refreshes automatically when snapshot changes
- No performance regression on non-fuzzy searches
- No new tools -- same tool count as v1.4

## Tools After This Milestone

Eighteen (unchanged from v1.4).
