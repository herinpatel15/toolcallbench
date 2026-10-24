# ToolCallBench

Find out which local language model calls tools reliably **on your own machine**.

ToolCallBench gives a model six tools (read, list, search, edit, patch, run a command) and 20
small tasks on a sample Python project. It checks the results with plain code, not with
another model, and writes a report that compares models and quantization levels.

It is tuned for a **MacBook M4 with 16 GB of memory** running Ollama, and works with any
OpenAI-compatible local server (llama.cpp, LM Studio, vLLM).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

toolcallbench validate-tasks                        # 20/20 reference solutions pass
python -m pytest                                    # the automated tests
toolcallbench run --backend scripted --repeats 1    # whole pipeline, no model needed
```

With a real model:

```bash
./scripts/serve_ollama.sh                           # terminal 1 (quit the Ollama menu-bar app first)
ollama pull qwen3:8b                                # terminal 2
toolcallbench doctor --model qwen3:8b --probe
toolcallbench run --config configs/m4-16gb.yaml
open results/reports/*.html
```

## What a report tells you

- Pass rate overall and for read, edit, run, chain and failure tasks
- Why runs failed (13 failure types, such as `invalid_json`, `text_tool_call`, `patch_failed`)
- Tokens per second, seconds per task, and calls compared with a reference solution
- Every setting that affects the result (context length, seed, KV cache type, versions)

## Status

Version 0.1.0. The harness, tasks, scoring, backends (checked against mock servers) and
reports are covered by automated tests. **No real model has been benchmarked yet**; run it on
your Mac to get the first numbers (`docs/TEST_PLAN.md` lists exactly what was and was not tested).

## Documentation

| Document | Purpose |
| --- | --- |
| [BUILD_FROM_SCRATCH.md](BUILD_FROM_SCRATCH.md) | Day-by-day guide to build this project yourself, with all code |
| [docs/PRD.md](docs/PRD.md) | Why it exists, who it is for, requirements |
| [docs/TECH_SPEC.md](docs/TECH_SPEC.md) | Exact behavior: tools, scoring, config, storage |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Diagrams: context, components, data flow, sequence, states, storage |
| [docs/TEST_PLAN.md](docs/TEST_PLAN.md) | What is tested and how requirements map to tests |
| [docs/SECURITY.md](docs/SECURITY.md) | What protects you and what does not |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why it is built this way |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Install, run, read the report, troubleshoot |
| [docs/MODEL_GUIDE_M4_16GB.md](docs/MODEL_GUIDE_M4_16GB.md) | Memory budget and model choices for 16 GB |
| [docs/TASK_CATALOG.md](docs/TASK_CATALOG.md) | All 20 tasks (generated) |
| [docs/ROADMAP.md](docs/ROADMAP.md), [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md) | Project housekeeping |

## License

MIT
