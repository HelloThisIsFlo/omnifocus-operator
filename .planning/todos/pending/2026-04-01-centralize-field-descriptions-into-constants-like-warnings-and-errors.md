---
created: 2026-04-01T12:41:26.600Z
title: Centralize field descriptions into constants like warnings and errors
area: models
files:
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
---

## Problem

Field `description=` strings on Pydantic models are currently inline — repeated across core models and contract specs (e.g., `on_days` description appears on `Frequency`, `FrequencyAddSpec`, and `FrequencyEditSpec`). This means:

- Descriptions can silently drift between the core model and its contract counterpart
- There's no single place to review all agent-facing descriptions at a glance
- It's inconsistent with how we handle warnings and errors, which already live in centralized constant files under `agent_messages/`

## Solution

Follow the existing `agent_messages/errors.py` and `agent_messages/warnings.py` pattern:

- Create a descriptions constants file (likely under `agent_messages/`) where all `Field(description=...)` strings are defined as named constants
- Replace inline description strings with references to these constants across both `models/` and `contracts/`
- Add tests mirroring the existing error/warning constant tests — verify constants exist, are non-empty, and are used consistently
- The file should read as a reviewable catalogue of every description an agent might see
