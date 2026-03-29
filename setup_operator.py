"""Install/uninstall OmniFocus Operator in Claude Code and Claude Desktop MCP configs.

Usage:
    uv run python setup_operator.py              # Interactive install (Enter = defaults)
    uv run python setup_operator.py --uninstall   # Remove from both configs
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

SERVER_KEY = "omnifocus-operator"
PROJECT_ROOT = Path(__file__).resolve().parent


# ── Config targets ──────────────────────────────────────────────────────────


@dataclass
class ConfigTarget:
    path: Path
    label: str
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
        path=Path.home()
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json",
        label="Claude Desktop",
        may_create=False,
        may_delete=False,
        absolute_command=True,
    ),
]


# ── Config file helpers ─────────────────────────────────────────────────────


def _load(target: ConfigTarget) -> dict | None:
    if target.path.exists():
        return json.loads(target.path.read_text())
    if target.may_create:
        return {"mcpServers": {}}
    return None


def _save(target: ConfigTarget, data: dict) -> None:
    target.path.write_text(json.dumps(data, indent=2) + "\n")


# ── Interactive prompts ─────────────────────────────────────────────────────


def _prompt_choice(label: str, choices: list[str], default: str) -> str:
    options = "/".join(choices)
    while True:
        value = input(f"  {label} ({options}) [{default}]: ").strip() or default
        if value in choices:
            return value
        print(f"    Invalid choice. Options: {options}")


def _prompt_value(label: str, default: str) -> str:
    return input(f"  {label} [{default}]: ").strip() or default


def _gather_config() -> dict[str, str]:
    print("Configuration (Enter = default):")
    return {
        "OPERATOR_REPOSITORY": _prompt_choice("Repository", ["hybrid", "bridge-only"], "hybrid"),
        "OPERATOR_LOG_LEVEL": _prompt_choice(
            "Log level", ["DEBUG", "INFO", "WARNING", "ERROR"], "DEBUG"
        ),
        "OPERATOR_BRIDGE_TIMEOUT": _prompt_value("Bridge timeout in seconds", "10"),
    }


# ── Install / Uninstall ────────────────────────────────────────────────────


def install() -> None:
    print()
    print("OmniFocus Operator — MCP Setup")
    print("=" * 34)
    env = _gather_config()
    print()

    for target in TARGETS:
        data = _load(target)
        if data is None:
            print(f"  [{target.label}] Skipped — {target.path} not found")
            continue

        command = "uv"
        if target.absolute_command:
            resolved = shutil.which("uv")
            if not resolved:
                print(f"  [{target.label}] Skipped — 'uv' not found on PATH")
                continue
            command = resolved

        data.setdefault("mcpServers", {})
        data["mcpServers"][SERVER_KEY] = {
            "command": command,
            "args": ["run", "--directory", str(PROJECT_ROOT), "python", "-m", "omnifocus_operator"],
            "env": env,
        }
        _save(target, data)
        print(f"  [{target.label}] Updated {target.path}")

    print()
    print("Restart Claude Code / Claude Desktop to connect.")


def uninstall() -> None:
    print(f"Removing '{SERVER_KEY}':")
    for target in TARGETS:
        if not target.path.exists():
            print(f"  [{target.label}] Skipped — {target.path} not found")
            continue

        data = json.loads(target.path.read_text())
        if SERVER_KEY not in data.get("mcpServers", {}):
            print(f"  [{target.label}] '{SERVER_KEY}' not present — nothing to remove")
            continue

        del data["mcpServers"][SERVER_KEY]
        if not data["mcpServers"]:
            del data["mcpServers"]

        if not data and target.may_delete:
            target.path.unlink()
            print(f"  [{target.label}] Removed {target.path} (was empty)")
        else:
            _save(target, data)
            print(f"  [{target.label}] Removed '{SERVER_KEY}' from {target.path}")


# ── CLI ─────────────────────────────────────────────────────────────────────


def main() -> None:
    if "--uninstall" in sys.argv:
        uninstall()
    elif "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
    else:
        install()


if __name__ == "__main__":
    main()
