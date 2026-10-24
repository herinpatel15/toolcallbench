.PHONY: install test validate smoke docs check serve clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest

validate:
	toolcallbench validate-tasks

smoke:
	toolcallbench run --backend scripted --repeats 1 --results-dir results-smoke --session smoke --resume
	@echo "Open results-smoke/reports/smoke.html"

docs:
	python scripts/make_task_catalog.py
	python scripts/make_build_guide.py

check: test validate
	python scripts/make_task_catalog.py
	git diff --exit-code docs/TASK_CATALOG.md || (echo "TASK_CATALOG.md was out of date"; exit 1)

serve:
	./scripts/serve_ollama.sh

clean:
	rm -rf results results-smoke .pytest_cache build *.egg-info
