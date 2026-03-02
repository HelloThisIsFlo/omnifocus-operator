"""Mock OmniFocus simulator -- standalone process for integration testing.

Run via::

    python -m omnifocus_operator.simulator --ipc-dir /tmp/sim-ipc

The simulator watches *--ipc-dir* for ``*.request.json`` files, reads
the request envelope, and writes a corresponding ``*.response.json``
with realistic OmniFocus data from :data:`SIMULATOR_SNAPSHOT`.

CLI flags allow injecting failures (``--fail-mode``) and delays
(``--delay``) to exercise error-handling paths in
:class:`~omnifocus_operator.bridge._simulator.SimulatorBridge`.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from omnifocus_operator.simulator._data import SIMULATOR_SNAPSHOT

logger = logging.getLogger("omnifocus_operator.simulator")

_REQUEST_RE: re.Pattern[str] = re.compile(r"^(\d+)_[0-9a-f-]+\.request\.json$")
"""Matches request files: ``<pid>_<uuid>.request.json`` (NOT ``.tmp``)."""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="omnifocus_operator.simulator",
        description="Mock OmniFocus simulator for integration testing.",
    )
    parser.add_argument(
        "--ipc-dir",
        type=Path,
        required=True,
        help="Directory to watch for IPC request files",
    )
    parser.add_argument(
        "--fail-mode",
        choices=("timeout", "error", "malformed"),
        default=None,
        help="Failure simulation mode (default: none)",
    )
    parser.add_argument(
        "--fail-after",
        type=int,
        default=None,
        help="First N requests succeed, then fail mode activates",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Seconds to delay before writing each response",
    )
    return parser.parse_args(argv)


def _write_atomic(path: Path, content: str) -> None:
    """Write *content* to *path* atomically via .tmp + os.replace()."""
    tmp_path = path.parent / f"{path.name}.tmp"
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _handle_request(
    ipc_dir: Path,
    filename: str,
    request_count: int,
    *,
    fail_mode: str | None,
    fail_after: int | None,
    delay: float,
) -> None:
    """Process a single request file and write the response."""
    request_path = ipc_dir / filename
    content = request_path.read_text(encoding="utf-8")
    envelope: dict[str, Any] = json.loads(content)
    _operation: str = envelope["operation"]
    _params: dict[str, Any] = envelope.get("params", {})

    # File prefix is everything before ".request.json"
    file_prefix = filename.replace(".request.json", "")
    response_filename = f"{file_prefix}.response.json"
    response_path = ipc_dir / response_filename

    if delay > 0:
        logger.debug("Delaying %.2fs before response", delay)
        time.sleep(delay)

    should_fail = fail_mode is not None and (fail_after is None or request_count > fail_after)

    if should_fail:
        if fail_mode == "timeout":
            logger.info("Simulating timeout -- NOT writing response")
            return
        if fail_mode == "error":
            logger.info("Simulating error response")
            _write_atomic(
                response_path,
                json.dumps({"success": False, "error": "simulated error"}),
            )
            return
        if fail_mode == "malformed":
            logger.info("Simulating malformed response")
            _write_atomic(response_path, "not valid json {{{")
            return

    # Normal success response
    _write_atomic(
        response_path,
        json.dumps({"success": True, "data": SIMULATOR_SNAPSHOT}),
    )
    logger.info("Response: %s", response_filename)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the mock simulator."""
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    ipc_dir: Path = args.ipc_dir
    ipc_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Config: ipc_dir=%s fail_mode=%s fail_after=%s delay=%s",
        ipc_dir,
        args.fail_mode,
        args.fail_after,
        args.delay,
    )
    # Readiness marker -- fixtures wait for this line on stderr
    sys.stderr.write(f"Ready: watching {ipc_dir}\n")
    sys.stderr.flush()

    seen: set[str] = set()
    request_count = 0

    try:
        while True:
            time.sleep(0.1)
            if not ipc_dir.exists():
                continue
            for entry in ipc_dir.iterdir():
                name = entry.name
                if name in seen:
                    continue
                if not _REQUEST_RE.match(name):
                    continue
                seen.add(name)
                request_count += 1
                logger.info("Request #%d: %s", request_count, name)
                _handle_request(
                    ipc_dir,
                    name,
                    request_count,
                    fail_mode=args.fail_mode,
                    fail_after=args.fail_after,
                    delay=args.delay,
                )
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
