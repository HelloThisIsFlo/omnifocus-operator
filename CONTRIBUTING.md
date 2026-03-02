# Contributing

## Setup

```bash
uv sync --dev
pre-commit install
```

## CI Checks

These run on every push to `main` and on PRs:

- `uv run ruff check` — lint
- `uv run ruff format --check` — formatting
- `uv run mypy src/` — type checking
- `uv run pytest --cov-fail-under=80` — tests with 80% coverage threshold

Pre-commit hooks run lint, format, and type checks locally before each commit.
