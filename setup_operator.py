"""Install/uninstall OmniFocus Operator in Claude Code and Claude Desktop MCP configs.

Usage:
    uv run python setup_operator.py              # Interactive install (Enter = defaults)
    uv run python setup_operator.py --uninstall   # Remove from both configs
"""

from __future__ import annotations

import json
import shutil
import sys
import termios
import tty
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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


# ── Source selection ────────────────────────────────────────────────────────


@dataclass
class Source:
    kind: Literal["uvx", "local"]
    project_dir: Path  # used when kind == "local"
    version: str  # used when kind == "uvx"; empty = latest


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


def _getch() -> str:
    """Read a single character from stdin without waiting for Enter."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _prompt_choice(label: str, choices: list[str], default: str) -> str:
    key_map: dict[str, str] = {}
    display_parts: list[str] = []
    for choice in choices:
        key = choice[0].lower()
        key_map[key] = choice
        bracket_display = f"[{choice[0]}]{choice[1:]}"
        display_parts.append(bracket_display)
    default_key = default[0].lower()
    options = " / ".join(display_parts)

    sys.stdout.write(f"  {label} ({options}) [{default_key}]: ")
    sys.stdout.flush()

    while True:
        ch = _getch()
        if ch in ("\r", "\n"):
            sys.stdout.write(f"{default}\n")
            sys.stdout.flush()
            return default
        if ch.lower() in key_map:
            result = key_map[ch.lower()]
            sys.stdout.write(f"{result}\n")
            sys.stdout.flush()
            return result
        # Ignore invalid keys, wait for a valid one


def _prompt_value(label: str, default: str) -> str:
    return input(f"  {label} [{default}]: ").strip() or default


def _detect_worktrees() -> list[Path]:
    """Return sorted list of worktree directories under .claude/worktrees/."""
    worktrees_dir = PROJECT_ROOT / ".claude" / "worktrees"
    if not worktrees_dir.is_dir():
        return []
    return sorted(p for p in worktrees_dir.iterdir() if p.is_dir() and not p.name.startswith("."))


def _prompt_worktree(worktrees: list[Path]) -> Path:
    """Prompt user to pick a worktree. Returns the project directory to use."""
    key_map: dict[str, Path] = {}
    display_lines: list[str] = []

    display_lines.append("    Enter  main")
    for wt in worktrees:
        suffix = wt.name.removeprefix("agent-") if wt.name.startswith("agent-") else wt.name
        key = suffix[0].lower()
        if key in key_map:
            # Collision — fall back to full suffix, user types first unique char
            # For now, skip duplicates (extremely unlikely with hex IDs)
            continue
        key_map[key] = wt
        display_lines.append(f"       {key}   {wt.name}")

    sys.stdout.write("  Worktree:\n")
    for line in display_lines:
        sys.stdout.write(f"{line}\n")
    sys.stdout.write("  Select [main]: ")
    sys.stdout.flush()

    while True:
        ch = _getch()
        if ch in ("\r", "\n"):
            sys.stdout.write("main\n")
            sys.stdout.flush()
            return PROJECT_ROOT
        if ch.lower() in key_map:
            selected = key_map[ch.lower()]
            sys.stdout.write(f"{selected.name}\n")
            sys.stdout.flush()
            return selected
        # Ignore invalid keys


def _gather_config() -> tuple[Source, dict[str, str]]:
    """Return (source, env_vars) for the install."""
    print("Configuration (Enter = default):")

    kind = _prompt_choice("Source", ["uvx", "local"], "local")
    if kind == "uvx":
        version = _prompt_value("Version (empty = latest)", "")
        source = Source(kind="uvx", project_dir=PROJECT_ROOT, version=version)
    else:
        worktrees = _detect_worktrees()
        project_dir = PROJECT_ROOT
        if worktrees:
            project_dir = _prompt_worktree(worktrees)
        source = Source(kind="local", project_dir=project_dir, version="")

    env = {
        "OPERATOR_REPOSITORY": _prompt_choice("Repository", ["hybrid", "bridge-only"], "hybrid"),
        "OPERATOR_LOG_LEVEL": _prompt_choice(
            "Log level", ["DEBUG", "INFO", "WARNING", "ERROR"], "DEBUG"
        ),
        "OPERATOR_BRIDGE_TIMEOUT": _prompt_value("Bridge timeout in seconds", "30"),
    }
    return source, env


# ── Install / Uninstall ────────────────────────────────────────────────────


def install() -> None:
    print()
    print("OmniFocus Operator — MCP Setup")
    print("=" * 34)
    source, env = _gather_config()
    print()

    base_command = "uvx" if source.kind == "uvx" else "uv"

    for target in TARGETS:
        data = _load(target)
        if data is None:
            print(f"  [{target.label}] Skipped — {target.path} not found")
            continue

        command = base_command
        if target.absolute_command:
            resolved = shutil.which(base_command)
            if not resolved:
                print(f"  [{target.label}] Skipped — '{base_command}' not found on PATH")
                continue
            command = resolved

        if source.kind == "uvx":
            package_spec = (
                f"omnifocus-operator@{source.version}" if source.version else "omnifocus-operator"
            )
            args = [package_spec]
        else:
            args = [
                "run",
                "--directory",
                str(source.project_dir),
                "python",
                "-m",
                "omnifocus_operator",
            ]

        data.setdefault("mcpServers", {})
        data["mcpServers"][SERVER_KEY] = {
            "command": command,
            "args": args,
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
