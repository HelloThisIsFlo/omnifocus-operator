"""RealBridge -- file-based IPC bridge to OmniFocus."""

from __future__ import annotations

import asyncio
import errno
import importlib.resources
import json
import logging
import os
import re
import subprocess
import urllib.parse
import uuid
from pathlib import Path
from typing import Any

from omnifocus_operator.bridge.errors import (
    BridgeConnectionError,
    BridgeProtocolError,
    BridgeTimeoutError,
)
from omnifocus_operator.contracts.protocols import Bridge

logger = logging.getLogger("omnifocus_operator")

OMNIFOCUS_CONTAINER: Path = Path.home() / "Library" / "Containers" / "com.omnigroup.OmniFocus4"
"""Root of the OmniFocus 4 sandboxed container on macOS.

Both the IPC directory and the ``.ofocus`` database bundle live under
this container.  A single shared root means path changes only need
updating in one place.
"""

DEFAULT_IPC_DIR: Path = OMNIFOCUS_CONTAINER / "Data" / "Documents" / "omnifocus-operator" / "ipc"
"""Default IPC directory for OmniFocus 4.

This path must be under OmniFocus's ``URL.documentsDirectory``
(``~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/``)
because URL scheme scripts can only write files within that sandbox
location via ``FileWrapper.write()``.
"""

DEFAULT_OFOCUS_PATH: Path = (
    OMNIFOCUS_CONTAINER
    / "Data"
    / "Library"
    / "Application Support"
    / "OmniFocus"
    / "OmniFocus.ofocus"
)
"""Default path to the OmniFocus 4 ``.ofocus`` database bundle.

Used by ``FileMtimeSource`` to detect when the database has changed.
Override via the ``OMNIFOCUS_OFOCUS_PATH`` environment variable.
"""

_IPC_FILE_RE: re.Pattern[str] = re.compile(r"^(\d+)_[0-9a-f-]+\.(request|response)\.json(\.tmp)?$")
"""Matches IPC files: ``<pid>_<uuid>.(request|response).json[.tmp]``."""


def _is_pid_alive(pid: int) -> bool:
    """Check whether a process with the given *pid* is alive.

    Uses ``os.kill(pid, 0)`` to probe without sending a signal.
    Returns ``False`` for *pid* <= 0 or if the process does not exist.
    Returns ``True`` if the process exists (even if owned by another user).
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        if exc.errno == errno.EPERM:
            return True
        raise
    return True


async def sweep_orphaned_files(ipc_dir: Path) -> None:
    """Remove IPC files left behind by dead processes.

    Iterates *ipc_dir*, matches filenames against :data:`_IPC_FILE_RE`,
    extracts the PID, and deletes files whose owning process is no longer
    alive.  Files that do not match the IPC naming convention are left
    untouched.

    Safe to call when *ipc_dir* does not exist or is empty.
    """

    def _sweep() -> None:
        if not ipc_dir.exists():
            return
        for entry in ipc_dir.iterdir():
            match = _IPC_FILE_RE.match(entry.name)
            if match is None:
                continue
            pid = int(match.group(1))
            if not _is_pid_alive(pid):
                entry.unlink(missing_ok=True)

    await asyncio.to_thread(_sweep)


class RealBridge(Bridge):
    """File-based IPC bridge to OmniFocus.

    Communicates with OmniFocus via the filesystem: writes a request file,
    triggers OmniFocus via URL scheme, and polls for a response file.

    Explicitly implements the ``Bridge`` protocol.
    """

    def __init__(self, ipc_dir: Path, *, timeout: float = 10.0) -> None:
        self._ipc_dir = ipc_dir
        self._pid = os.getpid()
        self._timeout = timeout
        ipc_dir.mkdir(parents=True, exist_ok=True)
        # Load and cache bridge script (no placeholder replacement needed;
        # bridge.js derives IPC dir from URL.documentsDirectory at runtime)
        self._script = (
            importlib.resources.files("omnifocus_operator.bridge")
            .joinpath("bridge.js")
            .read_text(encoding="utf-8")
        )

    @property
    def ipc_dir(self) -> Path:
        """IPC directory path (read-only)."""
        return self._ipc_dir

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a command to OmniFocus and return the parsed response data."""
        request_id = uuid.uuid4()
        file_prefix = f"{self._pid}_{request_id}"
        logger.debug(
            "RealBridge.send_command: operation=%s, params=%r, request_id=%s",
            operation,
            params,
            request_id,
        )

        await self._write_request(request_id, operation, params)
        self._trigger_omnifocus(file_prefix)
        logger.debug("RealBridge.send_command: waiting for response (timeout=%.1fs)", self._timeout)

        try:
            raw = await asyncio.wait_for(
                self._wait_response(request_id),
                timeout=self._timeout,
            )
        except TimeoutError:
            logger.debug(
                "RealBridge.send_command: TIMEOUT after %.1fs for %s", self._timeout, operation
            )
            await self._cleanup_request(request_id)
            raise BridgeTimeoutError(
                operation=operation,
                timeout_seconds=self._timeout,
            ) from None

        logger.debug("RealBridge.send_command: response received for %s", operation)
        result = self._validate_response(raw, operation)
        await self._cleanup_files(request_id)
        return result

    def _trigger_omnifocus(self, file_prefix: str) -> None:  # pragma: no cover
        """Trigger OmniFocus to process the current IPC request.

        Opens the ``omnifocus:///omnijs-run`` URL scheme via macOS ``open -g``
        (background, no focus steal).  The full bridge script is passed as the
        ``script=`` parameter.  The script derives its IPC directory from
        ``URL.documentsDirectory`` at runtime.  The ``arg=`` parameter carries
        the file prefix so the script can locate request/response files.

        The ``arg`` value is JSON-encoded (``json.dumps``) because OmniFocus
        JSON-parses the ``&arg=`` URL parameter before making it available as
        ``argument`` in the script.  Without JSON encoding, bare strings like
        ``123_uuid`` cause a ``SyntaxError: JSON Parse error``.

        .. note::

           Excluded from coverage -- SAFE-01 prevents automated testing of
           the production trigger.  Validated manually via UAT (Plan 08-02).
        """
        encoded_script = urllib.parse.quote(self._script, safe="")
        encoded_arg = urllib.parse.quote(json.dumps(file_prefix), safe="")
        url = f"omnifocus:///omnijs-run?script={encoded_script}&arg={encoded_arg}"

        try:
            subprocess.run(["open", "-g", url], check=True, capture_output=True)
        except FileNotFoundError:
            raise BridgeConnectionError(
                operation="trigger",
                reason="'open' command not found. This server requires macOS.",
            ) from None
        except subprocess.CalledProcessError as exc:
            raise BridgeConnectionError(
                operation="trigger",
                reason=(
                    f"Failed to trigger OmniFocus (exit code {exc.returncode}). "
                    "Is OmniFocus installed?"
                ),
            ) from None

    async def _write_request(
        self, request_id: uuid.UUID, operation: str, params: dict[str, Any] | None = None
    ) -> None:
        """Write request file atomically via .tmp + os.replace()."""
        filename = f"{self._pid}_{request_id}.request.json"
        final_path = self._ipc_dir / filename
        tmp_path = self._ipc_dir / f"{filename}.tmp"
        content = json.dumps({"operation": operation, "params": params or {}})

        def _write() -> None:
            tmp_path.write_text(content, encoding="utf-8")
            os.replace(tmp_path, final_path)

        await asyncio.to_thread(_write)

    async def _wait_response(self, request_id: uuid.UUID) -> dict[str, Any]:
        """Poll for response file and return parsed JSON."""
        filename = f"{self._pid}_{request_id}.response.json"
        response_path = self._ipc_dir / filename

        while True:
            exists = await asyncio.to_thread(response_path.exists)
            if exists:
                content = await asyncio.to_thread(response_path.read_text, "utf-8")
                result: dict[str, Any] = json.loads(content)
                return result
            await asyncio.sleep(0.05)

    def _validate_response(self, raw: dict[str, Any], operation: str) -> dict[str, Any]:
        """Validate response envelope and extract data."""
        if not isinstance(raw, dict):
            raise BridgeProtocolError(
                operation=operation,
                detail=f"Response is not a JSON object: {type(raw).__name__}",
            )
        if raw.get("success") is True:
            data: dict[str, Any] = raw.get("data", {})
            return data
        error_msg = raw.get("error", "Unknown error from OmniFocus")
        raise BridgeProtocolError(
            operation=operation,
            detail=f"OmniFocus reported error: {error_msg}",
        )

    async def _cleanup_request(self, request_id: uuid.UUID) -> None:
        """Delete request file (missing_ok)."""
        request_path = self._request_path(request_id)

        def _delete() -> None:
            request_path.unlink(missing_ok=True)

        await asyncio.to_thread(_delete)

    async def _cleanup_files(self, request_id: uuid.UUID) -> None:
        """Delete both request and response files (missing_ok)."""
        request_path = self._request_path(request_id)
        response_path = self._response_path(request_id)

        def _delete() -> None:
            request_path.unlink(missing_ok=True)
            response_path.unlink(missing_ok=True)

        await asyncio.to_thread(_delete)

    def _request_path(self, request_id: uuid.UUID) -> Path:
        """Build the request file path."""
        return self._ipc_dir / f"{self._pid}_{request_id}.request.json"

    def _response_path(self, request_id: uuid.UUID) -> Path:
        """Build the response file path."""
        return self._ipc_dir / f"{self._pid}_{request_id}.response.json"
