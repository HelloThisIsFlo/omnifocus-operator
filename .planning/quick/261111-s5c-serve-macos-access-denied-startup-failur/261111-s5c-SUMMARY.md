---
phase: 261111-s5c
plan: 01
status: complete
subsystem: server-startup / error-mode
tags: [startup, error-mode, macos, tcc, agent-messages]
requires: []
provides:
  - "No startup failure escapes error mode (IPC sweep now inside the lifespan try)"
  - "macOS privacy block (EPERM) recognised at the ErrorOperatorService boundary and answered with a teaching message"
  - "Repository factory tells a refused path apart from a missing one (hybrid DB + bridge-only .ofocus)"
  - "Real uvx path discovery via uv's UV variable"
affects:
  - "Later work: defer OmniFocus folder access to first tool call (todo 2026-05-20, sequence step 1 follow-ups)"
tech-stack:
  added: []
  patterns:
    - "Error classification once, at the error-mode boundary (exception + __cause__ chain)"
    - "Metadata-only existence check (os.stat) instead of os.path.exists"
key-files:
  created: []
  modified:
    - src/omnifocus_operator/server/lifespan.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/repository/factory.py
    - tests/conftest.py
    - tests/test_server.py
    - tests/test_service.py
    - tests/test_repository_factory.py
decisions:
  - "macOS privacy block = PermissionError with errno EPERM on the error or its __cause__ chain; EACCES stays generic"
  - "Teaching message replaces both {error} and the generic 'Restart the server after fixing.' line; lead-in 'OmniFocus Operator failed to start:' kept"
  - "Generic startup template moved verbatim into agent_messages/errors.py as STARTUP_FAILED"
  - "uvx discovery reads UV, resolves symlinks, takes sibling uvx; never resolves from PATH (mise shims)"
  - "Fallback FDA wording adds the mise hint: if realpath ends in mise, use `mise which uvx`"
  - "Bridge-only .ofocus check gets the same refused-vs-missing fix (accepted by orchestrator)"
metrics:
  duration: "~10 min"
  started: 2026-11-11T20:28:42Z
  completed: 2026-11-11T20:38:48Z
  tasks: 3
  files: 8
actuals:
  tokens: 8100
  tasks: 3
  commits: 3
plan_head_before: 50d9792fc2c152e97773c407ed1063a8e869a6f6
plan_head_after: 1ebedd6078e02a302b324bd85529c1b66c17320f
---

# Quick Task 261111-s5c: Serve macOS access-denied startup failures through error mode — Summary

**One-liner:** A macOS 27 privacy denial at startup no longer kills the server; every tool call now returns a teaching message naming the blocked path, the click-Allow route, and the Full Disk Access route with the resolved real `uvx` path.

## ✅ Result

- 🧯 **Crash fixed** — the IPC sweep runs inside the lifespan's error-mode `try`, first step, function-local import kept (tests patch it on `bridge.real`).
- 🎓 **Teaching message** — built once in `ErrorOperatorService.__init__` via `_startup_error_message()` in `service/service.py`.
- 🔍 **Refused ≠ missing** — `repository/factory.py::_path_exists()` uses `os.stat`; missing → existing `FileNotFoundError` text byte-identical, refused → `PermissionError` propagates with `errno`/`filename`.
- 🧭 **uvx discovery** — `service/service.py::_discover_real_uvx()` (used by `_fda_target()`).
- `bridge/real.py` untouched.

## 🧩 Design decisions as implemented

- **DD-1** — `_find_macos_access_denial()` walks the error and its explicit `__cause__` chain (cycle-safe) for `PermissionError` with `errno.EPERM`. EACCES → generic text.
- **DD-2** — `STARTUP_FAILED` (verbatim move) + `STARTUP_MACOS_ACCESS_DENIED` in a new `# --- Startup (error mode) ---` section of `agent_messages/errors.py`; sub-constants `STARTUP_MACOS_BLOCKED_PATH`, `STARTUP_FDA_TARGET_UVX_PATH`, `STARTUP_FDA_TARGET_FALLBACK`. Arrow escaped as `→`. All referenced from `service/service.py` (already in `_ERROR_CONSUMERS`), so `tests/test_errors.py` unchanged.
- **DD-3** — `_path_exists()` guards both the hybrid DB and the bridge-only `.ofocus` bundle. `FileNotFoundError`, `NotADirectoryError` and `ValueError` (embedded null byte, which `os.path.exists` also treated as missing) → missing. Never opens the file.
- **DD-4** — `UV` → `Path.resolve(strict=True)` → sibling `uvx` `is_file()` → resolved path. Catches `OSError`, `ValueError`, `RuntimeError`. Only runs for a macOS block.
- **DD-5** — blocked path from `filename` (`os.fsdecode` for str/bytes/PathLike); clause dropped when absent.

## 💬 Final message (as an agent receives it via MCP, UV set)

```
Error calling tool 'get_all': OmniFocus Operator failed to start: macOS is blocking this server from reading OmniFocus's data (blocked path: /Users/flo/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/ipc).

The user needs to fix this on their Mac. There are two ways:

1. If macOS shows a prompt asking whether "uvx" may access data from other apps, click Allow. macOS asks again every time the server launches.
2. To stop being asked, or if no prompt appears: open System Settings → Privacy & Security → Full Disk Access, click +, and add the program that launches this server: /Users/flo/.local/share/mise/installs/uv/0.13.7/uv-aarch64-apple-darwin/uvx (in the file picker, press Cmd+Shift+G and paste the path).

Granting Full Disk Access to Claude itself does not help: Claude Desktop launches MCP servers as their own responsible process, so macOS checks the launching program, not Claude.

After either step, fully quit and reopen the MCP client (for example Claude Desktop) so the server starts again.
```

Fallback step 2 target (UV unset or no sibling `uvx`):

```
... add the program that launches this server: uvx. To find its real path, run `realpath "$(which uvx)"` in Terminal (if the printed path ends in "mise", use the output of `mise which uvx` instead). In the file picker, press Cmd+Shift+G and paste that path.
```

The `Error calling tool '…': ` prefix is added by FastMCP, not by the server.

## 🧪 New tests (22; suite 2561 → 2583)

- `tests/test_service.py`
  - `TestErrorOperatorServiceMacOSAccessDenied`: `test_eperm_gives_teaching_message_in_order`, `test_eperm_names_blocked_path`, `test_eperm_without_filename_drops_path_clause`, `test_eperm_as_cause_gives_teaching_message`, `test_eacces_keeps_generic_message`, `test_generic_message_text_is_unchanged`, `test_fallback_names_realpath_command_and_mise_hint`
  - `TestErrorOperatorServiceUvxDiscovery`: `test_sibling_uvx_is_named`, `test_symlinked_uv_names_resolved_real_uvx`, `test_uv_without_sibling_uvx_falls_back`, `test_uv_pointing_nowhere_falls_back`, `test_uv_unset_falls_back`, `test_both_variants_share_parts_and_order`, `test_discovery_skipped_for_generic_errors`
- `tests/test_server.py`
  - `TestIPC06OrphanSweepWiring::test_sweep_runs_before_repository_creation`
  - `TestStartupMacOSAccessDenied`: `test_blocked_ipc_sweep_serves_teaching_message`, `test_blocked_bridge_construction_serves_teaching_message`, `test_blocked_database_serves_teaching_message_not_missing`
  - `test_sqlite_mode_missing_db_enters_error_mode` now also asserts no "Full Disk Access"
- `tests/test_repository_factory.py`
  - `TestCreateRepositoryErrors::test_hybrid_missing_db_message_is_unchanged` (byte-identical guard)
  - `TestCreateRepositoryAccessRefused`: `test_hybrid_refused_db_raises_eperm_permission_error`, `test_bridge_only_refused_ofocus_raises_eperm_permission_error`, `test_bridge_only_missing_ofocus_raises_file_not_found`
- Shared helper `refuse_stat(monkeypatch, path)` in `tests/conftest.py` — path-scoped EPERM `os.stat`, delegates otherwise.

## 🔁 Deviations from Plan

- **[Rule 3 - Blocking] Shared test helper placed in `tests/conftest.py`** (file not in `files_modified`). The path-scoped EPERM `os.stat` seam is needed by both `test_repository_factory.py` and `test_server.py`; conftest already exports plain helpers (`make_task_dict` …). Commit `bb5689c3`.
- **[Rule 2] `ValueError` treated as "missing" in `_path_exists`** — keeps parity with `os.path.exists` for null-byte paths instead of newly routing them to the generic error. Commit `bb5689c3`.
- **Orchestrator-directed addition:** mise hint in the fallback wording.
- The sweep-order assertion lives in a new test in `TestIPC06OrphanSweepWiring` rather than inside an existing one (cleaner; same guarantee).

## 📌 Notes

- Known limits from the plan stand (uv run contributors get the `uvx` sibling named; stat-allowed-but-read-denied surfaces at first read).
- Gates: `uv run pytest -q` → 2583 passed, coverage 97.57%; `just ci` → lint, format, mypy, safety, JS (85) + web (44) tests, pytest 2583 passed — "CI pipeline passed."

## Self-Check: PASSED

- Files exist: all 8 modified files present.
- Commits on HEAD: `f5eda3b3`, `bb5689c3`, `1ebedd60`.
