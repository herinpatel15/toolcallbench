# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.

## [1.0.3] - 2026-10-29

### Changed
- The report now shows "Why runs failed" right after the pass-rate summary. It groups the 13 failure types into five families (wrong tool, bad arguments, no real call, over budget, wrong result), followed by the full per-type table. A pass rate alone hides which kind of fix a model needs.

## [1.0.2] - 2026-10-29

### Added
- Each run now records prompt tokens, time spent reading the prompt and model load time (Ollama; llama.cpp servers report prompt time when they send `timings`). Older result databases are upgraded in place.
- The report has a "Where the time went" table: seconds per task split into generating, reading the prompt and loading, plus output and prompt tokens. It shows whether a model is slow because it writes a lot or because the context grows.
- When a run fails with `call_limit`, its log now says how many calls and turns were used, what the task allows, and whether the final repository was correct. This separates "too many calls" from "wrong fix".
- Each run log now ends with `final_diff`, the unified diff of the repository the model left behind. Failed runs can be inspected after the fact, for example to run the tests against what a model produced.

## [1.0.1] - 2026-10-24

### Fixed
- Package metadata: author, project URLs (now the lowercase `toolcallbench` repository) and the SPDX license expression.
- `pyproject.toml` had a duplicate `[build-system]` table that broke `python -m build`.

## [1.0.0] - 2026-10-24

### Added
- `pip install toolcallbench`: tasks, fixture repository and example configs now ship inside the package (`toolcallbench/data`).
- `toolcallbench init [DIR] [--with-tasks]` creates a working folder with example configs.
- `toolcallbench doctor --config FILE` probes models with the same settings `run` uses.
- PyPI publish workflow and `make release`.

### Fixed
- `doctor --probe` ignored temperature, seed, context size and timeout, so probe results varied between runs and slow models timed out.

## [0.1.0] - 2026-10-24

### Added
- Six tools (`read_file`, `list_dir`, `grep`, `edit_file`, `apply_patch`, `run_command`) with JSON Schemas and a sandboxed executor.
- 20 tasks in five groups, each with a reference solution, and the `shelf` fixture repository with two known bugs.
- Deterministic scoring with 13 failure types.
- Ollama, OpenAI-compatible and scripted backends.
- SQLite results, JSONL transcripts, Markdown and HTML reports, `--resume`.
- Commands `list-tasks`, `validate-tasks`, `doctor`, `run`, `report`, `sessions`.
- Configs for a MacBook M4 with 16 GB and for a Q4/Q8 sweep; `scripts/serve_ollama.sh`; `scripts/estimate_memory.py`.
- Documentation set: PRD, technical specification, architecture, test plan, security notes, decision records, user guide, model guide, task catalog, and `BUILD_FROM_SCRATCH.md`.
