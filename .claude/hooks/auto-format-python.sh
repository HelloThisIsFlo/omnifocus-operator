#!/usr/bin/env bash
# PostToolUse hook: auto-format Python files after Write/Edit
#
# Reads the tool result JSON from stdin, extracts the file path,
# and runs ruff check --fix + ruff format if it's a .py file.
#
# Unfixable lint issues are silently ignored — they'll surface
# at commit time via pre-commit hooks.

set -euo pipefail

file_path=$(jq -r '.tool_response.filePath // .tool_input.file_path')

if [[ "$file_path" == *.py ]]; then
    uv run ruff check --fix --quiet "$file_path" 2>/dev/null || true
    uv run ruff format --quiet "$file_path" 2>/dev/null || true
fi
