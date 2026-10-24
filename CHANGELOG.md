# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.

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
