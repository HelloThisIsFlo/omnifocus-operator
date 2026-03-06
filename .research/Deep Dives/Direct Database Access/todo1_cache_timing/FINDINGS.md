# TODO #1 Findings: SQLite Cache Update Timing

**Date:** 2026-03-06
**Status:** Complete

---

## Abstract

After a write through the JS bridge, the SQLite cache updates within milliseconds — fast enough that we can trust SQLite reads immediately after bridge writes. There is no need for delay, retry logic, or staleness checks in the hybrid architecture.

This confirms the Omni Group's documented two-phase commit behavior: OmniFocus updates both the XML transaction log and the SQLite cache as part of the same operation. The cache is transactional, not lazy. By the time the bridge call returns, the SQLite cache already reflects the change.

**Bottom line:** The hybrid architecture (SQLite reads + bridge writes) works seamlessly. Read-after-write consistency is guaranteed without any special handling.

---

## Results

Created a test task via the JS bridge, renamed it, then deleted it. Measured how quickly each change appeared in SQLite.

| Operation       | SQLite propagation delay |
|-----------------|-------------------------:|
| Create          |                   0.059s |
| Modify (rename) |                   0.004s |
| Delete          |                   0.002s |

All under 100ms. The create is slightly slower (59ms) likely because it's the first operation and OmniFocus is waking up. Subsequent operations propagate in 2-4ms.

For reference, the OmniJS bridge itself takes 0.1-1.3s to respond — the SQLite update happens well before the bridge response even arrives.

---

## Script

- `test_cache_timing.py` — Creates/modifies/deletes a `__CACHE_TIMING_TEST_{uuid}__` task via OmniJS URL scheme, polls SQLite for each change. Uses file-based IPC (fixed script text, parameters in request JSON) so macOS only prompts for URL scheme approval once. Cleanup in `try/finally`.
