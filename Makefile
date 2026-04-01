.PHONY: check-all test test-python test-js lint typecheck

check-all: test lint typecheck

test: test-python test-js
	@echo "All tests passed."

test-python:
	uv run pytest tests/ -x

test-js:
	cd bridge && npm test

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

typecheck:
	uv run mypy src/
