UV ?= uv

.PHONY: dev sync hooks lint typecheck test check

sync:
	$(UV) sync --extra dev

hooks: sync
	$(UV) run prek install --overwrite --hook-type pre-commit --hook-type pre-push

lint:
	$(UV) run ruff format --check .
	$(UV) run ruff check .

typecheck:
	$(UV) run mypy src tests

test:
	$(UV) run pytest -q

check: lint typecheck test

dev: hooks check
