"""Helper to connect Claude Code to a spike experiment server.

Usage:
    uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 02
    uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py remove
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SPIKE_KEY = "fastmcp-spike"
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # up from experiments/ → spike/ → deep-dives/ → .research/ → root
MCP_JSON = PROJECT_ROOT / ".mcp.json"
EXPERIMENTS_DIR = Path(__file__).resolve().parent

# Map experiment numbers to their script filenames
EXPERIMENT_SCRIPTS = {
    "02": "02_client_logging.py",
    "03": "03_server_logging.py",
    "05": "05_middleware.py",
    "07": "07_progress.py",
    "09": "09_elicitation.py",
}


def load_mcp_json() -> dict:
    if MCP_JSON.exists():
        return json.loads(MCP_JSON.read_text())
    return {"mcpServers": {}}


def save_mcp_json(data: dict) -> None:
    MCP_JSON.write_text(json.dumps(data, indent=2) + "\n")


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

    data = load_mcp_json()
    data.setdefault("mcpServers", {})

    data["mcpServers"][SPIKE_KEY] = {
        "command": "uv",
        "args": ["run", "python", str(script)],
    }

    save_mcp_json(data)
    print(f"Added '{SPIKE_KEY}' to {MCP_JSON}")
    print(f"  -> Experiment {num}: {EXPERIMENT_SCRIPTS[num]}")
    print(f"  -> Restart Claude Code (or reload MCP servers) to connect")


def remove() -> None:
    data = load_mcp_json()

    if SPIKE_KEY not in data.get("mcpServers", {}):
        print(f"'{SPIKE_KEY}' not found in {MCP_JSON} — nothing to remove")
        return

    del data["mcpServers"][SPIKE_KEY]

    # Clean up empty mcpServers
    if not data["mcpServers"]:
        del data["mcpServers"]

    if data:
        save_mcp_json(data)
    else:
        MCP_JSON.unlink()
        print(f"Removed {MCP_JSON} (was empty)")
        return

    save_mcp_json(data)
    print(f"Removed '{SPIKE_KEY}' from {MCP_JSON}")


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
