---
created: 2026-11-11T19:39:51.104Z
title: Update website install guide for Claude Desktop Full Disk Access
area: docs
severity: major
files:
  - docs/index.html (landing page + setup wizard)
  - README.md (temporary note under Quick Start)
  - .planning/todos/pending/2026-05-20-fix-recurring-macos-permission-prompt-on-claude-desktop-laun.md
---

## Problem

On recent macOS (confirmed 27.2.1), a Claude Desktop user who follows the published install steps gets a server that fails to start (`PermissionError: [Errno 1] Operation not permitted: …/com.omnigroup.OmniFocus4/…`), and nothing on the landing page or in the setup wizard explains it. The only working fix today is granting Full Disk Access to the real `uvx` binary.

A temporary note was added to `README.md` on 2026-11-11. The website (`docs/index.html`) was deliberately left alone.

## Solution

- Add the Full Disk Access step to the landing page / setup wizard for the Claude Desktop path; say plainly that the grant covers everything run through `uvx`, and that terminal clients (Claude Code CLI) are unaffected.
- Decide timing against the permission todo: the steps change again once the lazy-defer + teaching error ships, and again with the signed `.app` installer. Options: update now with the interim `uvx` step, or wait and write the guide once around the signed app.
- Remove the temporary README note when the real guide lands.
