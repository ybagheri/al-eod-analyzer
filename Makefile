.PHONY: check test lint typecheck
check:
	python -m tasks check
test:
	pytest -q --cov=src --cov-fail-under=85
lint:
	ruff check . && ruff format --check .
typecheck:
	mypy --strict src
