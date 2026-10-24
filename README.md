# ToolCallBench

Find out which local language model calls tools reliably **on your own machine**.

ToolCallBench gives a model six tools (read, list, search, edit, patch, run a command) and 20
small tasks on a sample Python project. It checks the results with plain code, not with
another model, and writes a report that compares models and quantization levels.

It is tuned for a **MacBook M4 with 16 GB of memory** running Ollama, and works with any
OpenAI-compatible local server (llama.cpp, LM Studio, vLLM).

## Install and run

```bash
pip install toolcallbench

mkdir my-bench && cd my-bench
toolcallbench init                                  # creates configs/ with example settings
```

Edit `configs/my-models.yaml` and list the models you have pulled in Ollama, then:

```bash
toolcallbench doctor --probe --config configs/my-models.yaml   # check Ollama, models, tool calling
toolcallbench run --config configs/my-models.yaml              # run the 20 tasks
toolcallbench sessions                                         # list past runs
toolcallbench report --session <id>                            # Markdown + HTML report in ./results/reports
```

Every setting can also be given as an argument, and arguments override the config file:

```bash
toolcallbench run --model qwen3:8b --model gemma4:e4b --repeats 3 --num-ctx 16384 --groups read,edit
toolcallbench run --help
```

Other commands: `toolcallbench list-tasks`, `toolcallbench validate-tasks`, `toolcallbench init --with-tasks`
(copies the tasks and sample repo so you can edit them; a folder with its own `tasks/` and
`fixtures/repo/` uses them instead of the built-in ones). Results are written to `./results`.

No model yet? `toolcallbench run --backend scripted --repeats 1` runs the whole pipeline without one.

Ollama must be running (`ollama serve`) with the models pulled (`ollama pull qwen3:8b`).
On a 16 GB Mac, start from the `m4-16gb.yaml` example config. See [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

### Develop

```bash
git clone <repo> && cd toolcallbench
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```

## What a report tells you

- Pass rate overall and for read, edit, run, chain and failure tasks
- Why runs failed (13 failure types, such as `invalid_json`, `text_tool_call`, `patch_failed`)
- Tokens per second, seconds per task, and calls compared with a reference solution
- Every setting that affects the result (context length, seed, KV cache type, versions)

## Status

Version 1.0.0. The harness, tasks, scoring, backends (checked against mock servers) and
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
| [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) | Every command, option and config key |
| [docs/MODEL_GUIDE_M4_16GB.md](docs/MODEL_GUIDE_M4_16GB.md) | Memory budget and model choices for 16 GB |
| [docs/TASK_CATALOG.md](docs/TASK_CATALOG.md) | All 20 tasks (generated) |
| [docs/ROADMAP.md](docs/ROADMAP.md), [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md) | Project housekeeping |

## License

MIT
