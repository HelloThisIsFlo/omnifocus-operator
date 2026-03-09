---
created: 2026-03-08T11:51:37.290Z
title: Extract validation and pre-checks from service into dedicated layer
area: service
priority: medium
files:
  - src/omnifocus_operator/service.py
---

## Problem

The service layer is accumulating validation, guard checks, and pre-processing logic alongside its core business logic. As more checks get added (mutually exclusive tags, tag set computation for always-replace, no-op detection, etc.), the service methods risk becoming cluttered with concerns that aren't core orchestration.

## Proposal

Extract validation and pre-check logic into a dedicated class or module (e.g., a `Validator`, `Guard`, or `PreProcessor`) that the service delegates to. The service stays focused on business orchestration — "what to do" — while the new layer handles "is this valid / what needs adjusting before we do it."

### Candidates for extraction:
- Input validation (field constraints, mutually exclusive fields)
- Tag set computation (if we move to always-replace mode)
- No-op detection (computed state == current state → skip bridge call)
- ID resolution / existence checks
- Any future guard rails (e.g., preventing edits to completed tasks)

### Benefits:
- Service methods stay readable and focused on the happy path
- Validation logic is testable in isolation
- New checks don't bloat service methods
- Clear separation: validation layer says "this is safe to proceed," service layer says "here's what we do"

### Open questions:
- Single class vs module with functions?
- Decorator/middleware pattern vs explicit delegation?
- Where does it sit — `service/validation.py`, `service/guards.py`, or a peer to service?
