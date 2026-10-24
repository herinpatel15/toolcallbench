# Product Requirements Document: ToolCallBench

| | |
| --- | --- |
| Version | 0.1 |
| Owner | Herin |
| Status | Implemented (v0.1.0); real-model results pending on the owner's Mac |

## 1. Problem

Local language models are advertised with leaderboard scores, but a developer who wants to
build an agent on a laptop needs a different answer: **which model, at which quantization,
calls tools correctly on my machine?** Public benchmarks run on large GPUs, use other
prompts, and rarely report what happens when a quantized 8B model on 16 GB of memory is
asked to edit a file and run a test.

Typical failures are small and expensive: arguments that are not valid JSON, a tool call
written as plain text, a made-up tool name, an edit whose `old_text` does not match, or a
loop that never stops. Each one breaks an agent, and none show up in a general score.

## 2. Users

| Persona | Need |
| --- | --- |
| **Solo developer on a MacBook** (the owner) | Pick a model for a local coding agent; know the cost of Q4 versus Q8 |
| **Agent builder** | Compare a few models on the same tasks before committing |
| **Researcher / writer** | Reproducible numbers with all settings recorded, for a blog post or paper |

## 3. Goals

1. Measure tool-calling reliability with **deterministic** scoring (no AI judge).
2. Run on a **MacBook M4 with 16 GB** with sensible defaults, and tell the user how much memory a setup needs.
3. Compare models and **quantization levels** in one report.
4. Be **reproducible**: record every setting that affects a result.
5. Be **easy to extend**: a new task is one YAML file.
6. Be **safe to run**: the model can never change the user's real files.

## 4. Non-goals

- Measuring general intelligence, coding quality or speed benchmarks (speed is reported only as context).
- Cloud models (the code does not stop you, but nothing is tuned for them).
- A hosted leaderboard or a web UI.
- A security boundary against a hostile model (see `SECURITY.md`).

## 5. Functional requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-1 | Run a fixed suite of 20 tasks in 5 groups (read, edit, run, chain, failure) | Must |
| FR-2 | Support Ollama, OpenAI-compatible servers (llama.cpp, LM Studio, vLLM) and a scripted fake model | Must |
| FR-3 | Offer six tools with JSON Schema and validate every tool call before running it | Must |
| FR-4 | Run tools only in a throwaway copy of a sample repository; allow-list commands | Must |
| FR-5 | Score deterministically; classify every failure into one of 13 types | Must |
| FR-6 | Repeat each task N times with different seeds; record all settings | Must |
| FR-7 | Store results in SQLite and keep full JSONL transcripts | Must |
| FR-8 | Resume an interrupted session without repeating finished runs | Must |
| FR-9 | Produce Markdown and HTML reports comparing models by group and failure type | Must |
| FR-10 | Prove every task is passable by replaying a reference solution (`validate-tasks`) | Must |
| FR-11 | `doctor` command checks Python, tasks, fixture, server, models; `--probe` runs one real task | Should |
| FR-12 | Ship configs for M4 16 GB and a Q4/Q8 sweep; record the server settings the user declares | Should |
| FR-13 | Treat server errors as "not scored", never as model failures | Must |
| FR-14 | Estimate memory use of a model and context before running | Could |

## 6. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-1 | Python 3.10 or newer; runtime dependencies limited to PyYAML and jsonschema |
| NFR-2 | The full automated test suite runs offline in under two minutes |
| NFR-3 | No network access except the configured model server |
| NFR-4 | Reports must show the settings, so two reports are only compared when settings match |
| NFR-5 | Same inputs and same seed give the same task scoring (model output may still vary by server) |
| NFR-6 | Clear error messages with the command that fixes the problem |

## 7. Success metrics

| Metric | Target |
| --- | --- |
| Tasks with a passing reference solution | 20 of 20 |
| Each failure type detectable by a scripted profile | 13 of 13 (see `TEST_PLAN.md`) |
| A full run of one 8B model, 20 tasks x 3 repeats, on the owner's Mac | measured by the owner; record the time in the report |
| Owner can reproduce the repo from `BUILD_FROM_SCRATCH.md` | all tests pass |

## 8. Scope of v0.1

In: everything in section 5. Out: see `ROADMAP.md`.

## 9. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Servers differ in how they report tool calls | Two backends; `doctor --probe` checks the real behavior |
| A model reaches an unsafe command | Allow-list, path confinement, temp copy, timeout; `SECURITY.md` is honest about limits |
| Results depend on settings the tool cannot see (server env vars) | `declared_server` fields are recorded in every report |
| Thinking models are slow | `--think off` option; documented in `MODEL_GUIDE_M4_16GB.md` |
| Small task suite gives noisy numbers | 3 repeats by default; report shows per-task cells so noise is visible |

## 10. Milestones

| Milestone | Content |
| --- | --- |
| M1 | Tools, sandbox, scoring, scripted backend, tests |
| M2 | Ollama and OpenAI-compatible backends, mock servers, CLI |
| M3 | Store, report, resume, docs |
| M4 (owner) | First real run on the M4; publish the report |
