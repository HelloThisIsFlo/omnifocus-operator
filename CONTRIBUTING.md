# Contributing

## Setup

```bash
just setup
```

## CI Checks

Run `just --list` for all available recipes. Key ones:

- `just check-all` — full suite (test + lint + typecheck)
- `just ci` — replicate CI pipeline locally
- `just fix` — auto-fix lint and formatting

Pre-commit hooks run lint, format, and type checks locally before each commit.
