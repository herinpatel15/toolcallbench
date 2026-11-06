<h1 align="center">ToolCallBench</h1>

<p align="center">
  <b>Does your local model really call tools right? Find out on your own machine, with your own repo.</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/toolcallbench/"><img src="https://img.shields.io/pypi/v/toolcallbench" alt="PyPI"/></a>
  <a href="https://pypi.org/project/toolcallbench/"><img src="https://img.shields.io/pypi/pyversions/toolcallbench" alt="Python versions"/></a>
  <a href="https://github.com/herinpatel15/toolcallbench/actions/workflows/ci.yml"><img src="https://github.com/herinpatel15/toolcallbench/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="License: MIT"/></a>
</p>

Run `toolcallbench run` and any local model gets **six coding tools** (read, list, search, edit, patch, run a command) and **20 small tasks** on a sample Python project. The result is a report that tells you which model to trust with tool calls and, when one fails, *how* it failed.

- **Any model, any server.** Ollama, or any OpenAI-compatible server: llama.cpp, LM Studio, vLLM, or a hosted API. The models in the examples are only a demo.
- **Scored by code, not by another model.** The outcome check runs the real `pytest` on the repository the model left behind. No AI judge.
- **Shows why it failed.** 14 failure types (`invalid_json`, `wrong_args`, `patch_failed`, `no_confirm_run`, ...) grouped into families, so you can tell a formatting problem from a wrong-tool problem.
- **Honest numbers.** Every pass rate comes with a 95% range, and `compare` says when two runs cannot be told apart.
- **Local by default.** Your files and results stay on your machine. Nothing is uploaded.

> [!NOTE]
> The built-in tasks measure how a model uses *these* tools with *this* system prompt. They do not rank models in general. To test your own project, point `--fixture` at a copy of it and write your own tasks ([Use your own repo](#use-your-own-repo-and-tasks)).

## Quickstart

```bash
pip install toolcallbench          # Python 3.10 or newer

mkdir my-bench && cd my-bench
toolcallbench init                 # creates ./configs with example settings
```

Edit `configs/my-models.yaml`, list the models you have pulled, then:

```bash
toolcallbench doctor --probe --config configs/my-models.yaml   # is the server up, do the models support tools?
toolcallbench run --config configs/my-models.yaml              # 20 tasks x your models x 3 repeats
toolcallbench report --session latest                          # Markdown + HTML in ./results/reports
```

No model installed yet? `toolcallbench run --backend scripted --repeats 1` runs the whole pipeline without one.

Ollama must be running (`ollama serve`) with the models pulled, for example `ollama pull qwen3:8b`.

## What you get

| Output | Where |
| --- | --- |
| All runs and settings (SQLite) | `results/results.sqlite` |
| Full transcript of every run, with the final diff of the repo | `results/logs/` |
| Report for a session (Markdown and HTML) | `results/reports/<session>.md`, `.html` |
| Comparison of two sessions | `results/reports/compare-<A>-vs-<B>.md` |
| JSON or CSV export of a session | `results/exports/<session>.json`, `.csv` |

## See it in action

A report starts with a summary table. This one is a **demo** (one run per task, 20 tasks, four models), shown only to explain the columns:

| Model | Passed | 95% range |
| --- | --- | --- |
| gemma4:e4b | 95% (19/20) | 76-99% |
| qwen3:8b | 75% (15/20) | 53-89% |
| llama3.1:8b | 60% (12/20) | 39-78% |
| qwen3.5:0.8b | 55% (11/20) | 34-74% |

The ranges are wide because 20 tasks is a small sample: `qwen3:8b` and `llama3.1:8b` are not clearly different here, and the report says so. That is what the range is for. Use `--repeats 3` or more before you trust a ranking. These numbers show the report format; they are not a verdict on those models. The real report also has columns per task group, tokens per second, seconds per task and calls versus the reference solution.

Right under the summary, **Why runs failed** groups the failures:

| Family | Failure types | Meaning |
| --- | --- | --- |
| Wrong tool or step | `wrong_tool`, `unneeded_call`, `too_few_calls`, `not_parallel`, `no_confirm_run` | the model chose or ordered the calls badly |
| Bad arguments | `invalid_json`, `invalid_args`, `wrong_args`, `patch_failed` | the call was malformed, or the arguments did not apply |
| No real call | `no_call`, `text_tool_call`, `unknown_tool` | the model answered from memory, wrote the call as text, or invented a tool |
| Over budget | `call_limit` | too many calls or turns; the log says whether the final repo was correct |
| Wrong result | `outcome_mismatch` | the calls were fine, the change was wrong |

## How scoring works

A run passes when three things are true:

1. **Parse**: every tool call is valid JSON and matches the tool's schema.
2. **Tool**: the right tools were called, in the right order, within the call limit.
3. **Outcome**: the final answer matches, and for edit tasks the real `pytest` passes on the final repository. A diff is never compared, so any correct fix passes.

"Args" (did the model pass the exact expected arguments) is reported but does not decide pass or fail. Server errors are stored as errors and never counted as model failures. A failed run gets exactly one failure type, checked in a fixed order (`docs/TECH_SPEC.md`).

## Commands

| Command | What it does |
| --- | --- |
| `toolcallbench init [DIR] [--with-tasks]` | Create example configs; with `--with-tasks` also copy the tasks and sample repo so you can edit them |
| `toolcallbench doctor [--config FILE] [--probe]` | Check Python, tasks, server and models; `--probe` runs one task per model |
| `toolcallbench run [options]` | Run the benchmark |
| `toolcallbench report [--session ID\|latest] [--print]` | Rebuild the report from stored results |
| `toolcallbench sessions` | List stored sessions |
| `toolcallbench compare [A] [B]` | Compare two sessions (default: previous vs latest) |
| `toolcallbench export [--session ID] [--format json\|csv] [--output FILE\|-]` | Write a session's runs to a file |
| `toolcallbench list-tasks [--markdown]` | Show all 24 tasks |
| `toolcallbench validate-tasks` | Replay every reference solution; `24/24 reference solutions pass` means everything is intact |

`toolcallbench <command> --help` lists every option. Exit codes: `0` ok, `1` a check failed or the server is unreachable, `2` bad input, `130` Ctrl+C (continue with `--resume`).

```bash
toolcallbench run --model qwen3:8b --model gemma4:e4b --repeats 3 --num-ctx 16384 --groups read,edit
toolcallbench run --config configs/my-models.yaml --session nightly --resume
```

Options for `run` (a command-line option always beats the config file):

| Option | Meaning | Default |
| --- | --- | --- |
| `--backend ollama\|openai-compat\|scripted` | Server type | `ollama` |
| `--host URL` | Server address | `http://localhost:11434` / `:8080` |
| `--model NAME` | Model; repeat for several | from config |
| `--think on\|off\|default` | Ollama thinking mode | `default` |
| `--num-ctx N` | Context length | 16384 |
| `--temperature X`, `--seed N` | Sampling; repeat `k` uses `seed + k - 1` | 0.0, 42 |
| `--repeats N` | Runs per task and model | 3 |
| `--max-calls N`, `--max-turns N` | Budget per task | 12, 10 |
| `--tasks IDS`, `--groups NAMES` | Pick tasks (groups: `read,edit,run,chain,failure,nested`) | the 20 core tasks |
| `--tools-offered all\|task` | Offer all tools, or only those a task needs | `all` |
| `--max-calls-per-turn N` | Run only the first N calls of each reply (0 = no limit) | 0 |
| `--api-key-env NAME` | Environment variable holding an API key | none |
| `--session ID`, `--resume` | Name a run; continue and skip stored runs | start time |
| `--kv-cache-type T`, `--flash-attention` | Record how your server is set up (not enforced) | `f16`, off |
| `--fixture PATH`, `--tasks-dir PATH` | Use your own repo / tasks | built in |

## Config file

```yaml
backend: ollama                    # ollama | openai-compat | scripted
host: http://localhost:11434       # optional
settings:                          # all optional
  num_ctx: 16384
  temperature: 0.0
  seed: 42
  repeats: 3
  max_calls: 12
  max_turns: 10
  request_timeout: 600             # seconds per request; raise it for slow or thinking models
  tools_offered: all               # all | task
  max_calls_per_turn: 0            # 0 = no limit
api_key_env: OPENAI_API_KEY        # NAME of an environment variable, never the key itself
declared_server:                   # recorded in the report, not enforced
  kv_cache_type: q8_0
  flash_attention: true
models:
  - name: qwen3:8b
    think: false                   # per model; leave out for models without a thinking mode
  - llama3.1:8b                    # a plain string is enough
```

Unknown keys are rejected with a message that lists the allowed ones. `toolcallbench init` also writes `m4-16gb.yaml` (a plan for a 16 GB Mac), `quant-sweep-qwen3-8b.yaml` (one model at two quantization levels) and `smoke-scripted.yaml` (no model needed).

## Backends

| Backend | Use it for | Notes |
| --- | --- | --- |
| `ollama` | Ollama on this machine | Uses the server's token counts and timings for tokens per second |
| `openai-compat` | llama.cpp (`llama-server --jinja`), LM Studio, vLLM, hosted APIs | Uses `/v1/chat/completions`; reads `usage` and `timings` when the server sends them |
| `scripted` | Testing the pipeline | Replays reference solutions or imitates a failure; no model needed |

**Hosted APIs.** Put the key in an environment variable and pass its *name*:

```bash
export OPENAI_API_KEY=...
toolcallbench run --backend openai-compat --host https://api.example.com --model some-model --api-key-env OPENAI_API_KEY
```

The key is sent as a `Bearer` header. It is never accepted on the command line or in YAML (a value that looks like a key is rejected) and is never written to results, logs or reports. **A hosted API receives every prompt, file content and tool result**, so use a private repo only with a provider you trust.

## Tasks

20 core tasks run by default. Each has a reference solution that `validate-tasks` replays through the real tools.

| Group | Tasks | What it tests |
| --- | --- | --- |
| `read` (5) | read a config value, list a folder, find a definition with grep, read a CSV, count members | picking the right read tool and arguments |
| `edit` (5) | change a value, bump a version, apply a unified diff, add a function, fix the late-fee cap with no tool named | edits that really change the repo |
| `run` (3) | run the tests and count failures, run a script, run a listing | `run_command` and its allow-list |
| `chain` (4) | fix a search bug and confirm with tests, read the README and run what it says, locate a class then read it, fix two failing tests | dependent steps; `chain-04` must run the tests after its last edit |
| `failure` (3) | answer without tools, two independent reads in one step, recover from a missing file | not calling tools when none is needed, parallel calls, recovery |

**4 optional `nested` tasks** (`--groups nested`) test arguments that contain lists of objects, where smaller models often slip on format:

| Task | Tool | What it asks |
| --- | --- | --- |
| `nested-01` | `apply_edits` | fix two bugs in two files with one call, then run the tests |
| `nested-02` | `set_json_values` | change two settings with one call |
| `nested-03` | either | change JSON settings with no tool named |
| `nested-04` | `apply_edits` | add a function and its test across two files |

`apply_edits` applies all of its edits or none. Nested tasks are opt-in so the default run stays comparable with earlier versions. `docs/TASK_CATALOG.md` lists every task's prompt and expectations.

## Reading the report

- **Settings**: compare two reports only if these match (`compare` checks for you).
- **Summary**: pass rate overall and per group, the **95% range**, median tokens per second, median seconds per task, and calls versus the reference solution (1.00 is ideal, 2.00 is twice as many).
- **Why runs failed**: failure families, then every exact type.
- **Run-to-run consistency** (with `--repeats` above 1): tasks that always passed, sometimes passed or never passed. Many "sometimes" means the result is noisy.
- **Where the time went**: seconds per task split into generating, reading the prompt and loading. It shows whether a model is slow because it writes a lot or because its context grows.
- **Per-task results**: `1/3` is a flaky task, not a hard failure.

A `call_limit` log says how many calls and turns were used and whether the final repository was correct, which separates "too many calls" from "wrong fix".

## Compare two runs

```bash
toolcallbench compare                  # previous session vs latest
toolcallbench compare run-a run-b
```

It prints which settings differ, the pass-rate change per model with a verdict (**better**, **worse** or **no clear difference**, based on the 95% ranges), tasks that flipped, and failure-family changes. It warns when the two sessions ran different task sets. Change one thing between runs (context length, quantization, temperature, `--think`) to learn what it does.

## Ablations

| Question | Run |
| --- | --- |
| Does the model do better one call at a time? | `--max-calls-per-turn 1` |
| Does a smaller tool menu help? | `--tools-offered task` (also a hint, so keep these results separate) |
| Is it the context size? | `--num-ctx 8192` vs `16384` |
| Is it the quantization? | `configs/quant-sweep-qwen3-8b.yaml` |
| Is it the thinking mode? | `--think off` vs `--think on` |
| Is it luck? | `--repeats 5` and read the consistency table |

## Use your own repo and tasks

```bash
toolcallbench init --with-tasks        # copies tasks/ and fixtures/repo/ so you can edit them
toolcallbench validate-tasks --fixture ~/code/my-project-copy --tasks-dir my-tasks
toolcallbench run --fixture ~/code/my-project-copy --tasks-dir my-tasks --model qwen3:8b
```

A task is one YAML file:

```yaml
id: read-01                 # group-NN, must match the group
group: read                 # read | edit | run | chain | failure | nested
title: Read one config value
tools_named: true           # does the prompt name the tool?
optional: false             # true: only run when named
version: 1                  # raise it when the task changes meaning
prompt: |
  What is loan_days in config/settings.json?
expect:
  calls:
    - tool: read_file
      args: {path: config/settings.json}
  answer_regex: ['\b14\b']
  # after_last_edit: {tool: run_command, contains: pytest}   # require a test run after the last edit
reference:                  # a solution that must pass
  - calls:
      - {tool: read_file, args: {path: config/settings.json}}
  - final: loan_days is 14.
```

Run `validate-tasks` with the same `--fixture` and `--tasks-dir` first: it proves each task can be passed. Each session stores a fingerprint of the task set, so `compare` can warn when it changed.

## Choosing models on a 16 GB Mac

The project is tuned for a MacBook M4 with 16 GB, but nothing in it is Mac-only. Plan for about 12 GB of usable model memory: weights plus a KV cache that grows with context length. An 8B model at Q4 with a 16k context and a `q8_0` cache needs about 7 GB; a 14B model is tight at about 11 GB.

| Setting | Recommended |
| --- | --- |
| `num_ctx` | 16384 (8192 for Q8 or 14B) |
| `OLLAMA_FLASH_ATTENTION` | `1` (needed for a quantized KV cache) |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` |
| `OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_NUM_PARALLEL` | `1` |
| `--think off` | for Qwen3 and other thinking models; compare once with it on |

Sizes are approximate; check `ollama ps`. `docs/MODEL_GUIDE_M4_16GB.md` has the table.

## Privacy and safety

- **Local by default.** Nothing is sent anywhere except to the model server you configure. With a hosted API, prompts and file contents go to that provider.
- **Throwaway workspace.** Every run works in a fresh copy of the repository in a temp folder. File tools reject paths outside it (`..`, absolute paths, escaping symlinks).
- **No shell.** Commands are split and run directly; `|`, `>`, `;`, `&&` and `$()` have no special meaning. Only 12 programs are allowed, 20 s per command, 6000 characters of output.
- **This is a safety net, not a sandbox.** A model can edit a `.py` file and then run it, with your user's permissions. If you use your own repo: use a copy without secrets, never run with `sudo`, and put untrusted models in a VM or container with no network.
- **Logs contain prompts and file contents.** Do not publish `results/logs/` from a private fixture. `results/` is git-ignored.

Details: `docs/SECURITY.md`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `cannot reach http://localhost:11434` | Start the server (`ollama serve`). In a probe, a timeout can also mean the model is still loading: use `--config` and raise `request_timeout` |
| Probe results change between runs | Run `doctor --probe` with `--config` so temperature and seed are fixed |
| `no task files (*.yaml) found` | The current folder has its own empty `tasks/` and `fixtures/repo/`, which replace the built-in ones. Run from another folder or delete them |
| `model 'x' is not installed` | `ollama pull x` |
| Every run fails with `no_call` | The model may not support tools, or its template is wrong; run `doctor --probe` |
| Very slow runs with Qwen3 | Add `--think off` |
| `HTTP 400 ... does not support thinking` | That model has no thinking mode; remove `--think` for it |
| Mac slow, fans loud | Lower `--num-ctx` to 8192, use a smaller model, close other apps |
| `X is not set` | `export X=...` in the same shell, then pass `--api-key-env X` |
| Session exists | Add `--resume` or choose a new `--session` |

## Development

```bash
git clone https://github.com/herinpatel15/toolcallbench && cd toolcallbench
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
toolcallbench validate-tasks
python -m pytest
```

Dependencies are `pyyaml`, `jsonschema` and `pytest` (the outcome check runs it); HTTP uses the standard library. Tests use mock Ollama and OpenAI-compatible servers and scripted failure profiles, so they need no model. See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

**Not covered by automated tests:** real models and real hosted APIs. The mock servers check request and response formats; run a real model on your machine for real numbers.

## More documentation

Everything above is enough to use the tool. For depth, the `docs/` folder has the product requirements, the exact specification (`TECH_SPEC.md`), architecture diagrams, the test plan, security notes, design decisions, the generated task catalog and the roadmap. `BUILD_FROM_SCRATCH.md` is a day-by-day guide to building a version of this project yourself.

## Roadmap

Next: about 40 tasks, context-stress tasks, a temperature 0.0 vs 0.7 comparison, static HTML charts. Later: direct llama.cpp tuning, an MLX backend, a container sandbox, task packs for other languages. Not planned: a hosted leaderboard or an AI judge.

## License

MIT
