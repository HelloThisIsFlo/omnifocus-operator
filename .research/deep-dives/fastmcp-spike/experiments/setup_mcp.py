"""Helper to connect Claude Code AND Claude Desktop to a spike experiment server.

Usage:
    uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 02
    uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py remove
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

SPIKE_KEY = "fastmcp-spike"
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # up from experiments/ → spike/ → deep-dives/ → .research/ → root
EXPERIMENTS_DIR = Path(__file__).resolve().parent

# Map experiment numbers to their script filenames
EXPERIMENT_SCRIPTS = {
    "02": "02_client_logging.py",
    "03": "03_server_logging.py",
    "05": "05_middleware.py",
    "07": "07_progress.py",
    "09": "09_elicitation.py",
}


@dataclass
class ConfigTarget:
    """A config file that may contain an mcpServers entry for the spike."""

    path: Path
    label: str  # human-readable name for print output
    may_create: bool  # create file if missing?
    may_delete: bool  # delete file when empty?
    absolute_command: bool  # resolve command to absolute path? (GUI apps lack shell PATH)


TARGETS = [
    ConfigTarget(
        path=PROJECT_ROOT / ".mcp.json",
        label="Claude Code",
        may_create=True,
        may_delete=True,
        absolute_command=False,
    ),
    ConfigTarget(
        path=Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        label="Claude Desktop",
        may_create=False,
        may_delete=False,
        absolute_command=True,
    ),
]


def _load(target: ConfigTarget) -> dict | None:
    """Load config JSON, or None if the file doesn't exist and we can't create it."""
    if target.path.exists():
        return json.loads(target.path.read_text())
    if target.may_create:
        return {"mcpServers": {}}
    return None


def _save(target: ConfigTarget, data: dict) -> None:
    target.path.write_text(json.dumps(data, indent=2) + "\n")


def _add_to_target(target: ConfigTarget, server_entry: dict) -> None:
    data = _load(target)
    if data is None:
        print(f"  [{target.label}] Skipped — {target.path} not found")
        return

    data.setdefault("mcpServers", {})
    data["mcpServers"][SPIKE_KEY] = server_entry
    _save(target, data)
    print(f"  [{target.label}] Updated {target.path}")


def _remove_from_target(target: ConfigTarget) -> None:
    if not target.path.exists():
        print(f"  [{target.label}] Skipped — {target.path} not found")
        return

    data = json.loads(target.path.read_text())

    if SPIKE_KEY not in data.get("mcpServers", {}):
        print(f"  [{target.label}] '{SPIKE_KEY}' not present — nothing to remove")
        return

    del data["mcpServers"][SPIKE_KEY]

    # Clean up empty mcpServers
    if not data["mcpServers"]:
        del data["mcpServers"]

    # Delete the file if empty and allowed, otherwise save
    if not data and target.may_delete:
        target.path.unlink()
        print(f"  [{target.label}] Removed {target.path} (was empty)")
    else:
        _save(target, data)
        print(f"  [{target.label}] Removed '{SPIKE_KEY}' from {target.path}")


def add(experiment_num: str) -> None:
    num = experiment_num.zfill(2)
    if num not in EXPERIMENT_SCRIPTS:
        server_experiments = ", ".join(sorted(EXPERIMENT_SCRIPTS.keys()))
        print(f"Error: Experiment {num} is not a server-interactive experiment.")
        print(f"Server-interactive experiments: {server_experiments}")
        print(f"(Code-interactive experiments run directly with uv run python ...)")
        sys.exit(1)

    script = EXPERIMENTS_DIR / EXPERIMENT_SCRIPTS[num]
    if not script.exists():
        print(f"Error: Script not found: {script}")
        sys.exit(1)

    print(f"Adding '{SPIKE_KEY}' → Experiment {num}: {EXPERIMENT_SCRIPTS[num]}")
    for target in TARGETS:
        command = "uv"
        if target.absolute_command:
            resolved = shutil.which("uv")
            if not resolved:
                print(f"  [{target.label}] Skipped — 'uv' not found on PATH")
                continue
            command = resolved
        server_entry = {
            "command": command,
            "args": ["run", "--directory", str(PROJECT_ROOT), "python", str(script)],
        }
        _add_to_target(target, server_entry)
    print("Restart Claude Code / Claude Desktop to connect.")


def remove() -> None:
    print(f"Removing '{SPIKE_KEY}':")
    for target in TARGETS:
        _remove_from_target(target)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "add":
        if len(sys.argv) < 3:
            print("Usage: setup_mcp.py add <experiment_number>")
            print(f"Server-interactive experiments: {', '.join(sorted(EXPERIMENT_SCRIPTS.keys()))}")
            sys.exit(1)
        add(sys.argv[2])

    elif command == "remove":
        remove()

    else:
        print(f"Unknown command: {command}")
        print("Usage: setup_mcp.py add <num> | setup_mcp.py remove")
        sys.exit(1)


if __name__ == "__main__":
    main()
