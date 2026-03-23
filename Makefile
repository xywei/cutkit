UV ?= uv

.PHONY: dev sync hooks lint typecheck architecture docs evals test check

sync:
	$(UV) sync --extra dev

hooks: sync
	$(UV) run prek install --overwrite --hook-type pre-commit --hook-type pre-push

lint:
	$(UV) run ruff format --check .
	$(UV) run ruff check .

typecheck:
	$(UV) run mypy src tests

architecture:
	$(UV) run python scripts/check_architecture.py

docs:
	$(UV) run python scripts/check_docs_freshness.py

evals:
	$(UV) run python scripts/run_cutpanel_eval.py

test:
	$(UV) run pytest -q

check: lint typecheck architecture docs test evals

dev: hooks check
