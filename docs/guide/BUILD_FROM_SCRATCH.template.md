# Build ToolCallBench from scratch: a day-by-day guide

This guide takes you from an empty folder to the finished project, one day at a time. Every
file is shown in full, so you can type it or paste it. After each day there is a command to
run and the output you should see.

**What you build:** a program that tests how well a local AI model calls tools. You give a
model six tools (read a file, list a folder, search, edit, apply a patch, run a command) and
20 small tasks. The program checks the result with normal code and writes a report. You will
run it on your MacBook M4 with 16 GB of memory.

**How long:** about 10 days at 2 to 3 hours each. You can go faster by pasting the code, but read
the "why" notes: they are what teaches you how the program works.

**How this guide was checked:** the code blocks below are copied from the real repository by a
script. A second script extracts them into an empty folder, installs the project and runs
every test. So if you copy the files exactly, the tests pass. The author ran these checks on
Linux with a fake model and with mock servers. **The author could not run a real model on a
Mac**, so Day 7 and Day 8 (real models on your M4) are where you do the first real
measurements. Output you see on those days will differ from anything printed here.

## How to read each day

| Part | Meaning |
| --- | --- |
| **Goal** | What works at the end of the day |
| **Why** | The idea behind the code, in simple words |
| **Create** | Files to create, shown in full |
| **Run** | A command and the output you should see |
| **Checkpoint** | A `git commit` so you can always go back |

When a path is shown, create the file at exactly that path inside your project folder, and
create missing folders as you go.

## The plan

| Day | You build | You can then |
| --- | --- | --- |
| 0 | Mac setup and the project skeleton | import the package |
| 1 | A small sample project (`shelf`) with two bugs | see two failing tests |
| 2 | Tools, a safe sandbox and a patch engine | let a program read, edit and run code safely |
| 3 | Backends (Ollama, OpenAI-style, fake) and config | talk to a model server |
| 4 | The 20 tasks, the scoring rules and the runner | score a run without any AI judge |
| 5 | Storage and reports | keep results and compare models |
| 6 | The command line and mock servers | run everything end to end with a fake model |
| 7 | Helper scripts, then your first real model | run a real benchmark on your M4 |
| 8 | Real benchmark plan: models, quantization, memory | decide which model to use |
| 9 | Documents, polish and publishing | share a finished project |
| 10 | Make it yours | add tasks, point it at your own code |

## The final project layout

{{tree}}

---

## Day 0: Set up your Mac and the project skeleton

**Goal:** Python, Git and Ollama are installed, and `import toolcallbench` works.

### Why

A Python project needs an isolated environment (a *virtual environment*) so its packages do
not mix with other projects. We use a `src/` folder layout: the code lives in `src/toolcallbench`,
and `pip install -e .` makes it importable while still letting you edit it ("editable" install).

### Install the tools

Open Terminal and run:

```bash
# 1. Homebrew (skip if you have it): see https://brew.sh for the current install command
# 2. Python and Git
brew install python@3.12 git
# 3. Ollama: download the app from https://ollama.com, or use Homebrew
brew install ollama
```

Check: `python3 --version` should show 3.10 or newer, and `ollama --version` should print a version.

### Create the project

```bash
mkdir -p ~/code/toolcallbench && cd ~/code/toolcallbench
git init
python3 -m venv .venv
source .venv/bin/activate        # run this again in every new terminal
touch README.md                  # a real README comes on Day 9
mkdir -p src/toolcallbench/data/tasks src/toolcallbench/data/configs src/toolcallbench/data/fixtures/repo tests scripts
```

### Create

`pyproject.toml` tells Python the project name, its two dependencies (PyYAML for task files,
jsonschema for checking tool arguments), and the `toolcallbench` command.

{{file:pyproject.toml}}

`.gitignore` keeps generated files out of Git.

{{file:.gitignore}}

The package files. `__init__.py` holds the version; `__main__.py` lets you run
`python -m toolcallbench`.

{{file:src/toolcallbench/__init__.py}}

{{file:src/toolcallbench/__main__.py}}

Also add a license. Copy the MIT License text from <https://choosealicense.com/licenses/mit/>
into a file named `LICENSE`.

### Run

Install the project in your virtual environment:

```bash
pip install -e ".[dev]"
python -c "import toolcallbench; print(toolcallbench.__version__)"
```

{{cmd:python -c "import toolcallbench; print(toolcallbench.__version__)"}}

### Checkpoint

```bash
git add -A && git commit -m "Day 0: project skeleton"
```

---

## Day 1: The sample project the model will work on

**Goal:** a tiny library-lending project called `shelf`, with exactly **two failing tests**.

### Why

A benchmark needs something to work on. We want a small project that is realistic (code,
config, data, tests) and has known bugs, so we can ask a model to "fix the failing tests" and
check the answer with code. It lives in `src/toolcallbench/data/fixtures/repo`. For every run, the program copies it
to a temporary folder, so the model can never break the original.

The two bugs are on purpose:

1. `search_by_title` in `catalog.py` is case-sensitive, but its docstring and test say it should ignore case.
2. `late_fee` in `fees.py` ignores its `cap` argument.

Do not fix them. The tasks need them.

### Create

Settings and data:

{{file:src/toolcallbench/data/fixtures/repo/config/settings.json}}

{{file:src/toolcallbench/data/fixtures/repo/data/books.csv}}

{{file:src/toolcallbench/data/fixtures/repo/data/members.csv}}

The package. Read `catalog.py` and `fees.py` and find the two bugs.

{{file:src/toolcallbench/data/fixtures/repo/src/shelf/__init__.py}}

{{file:src/toolcallbench/data/fixtures/repo/src/shelf/models.py}}

{{file:src/toolcallbench/data/fixtures/repo/src/shelf/settings.py}}

{{file:src/toolcallbench/data/fixtures/repo/src/shelf/catalog.py}}

{{file:src/toolcallbench/data/fixtures/repo/src/shelf/fees.py}}

{{file:src/toolcallbench/data/fixtures/repo/src/shelf/loans.py}}

{{file:src/toolcallbench/data/fixtures/repo/src/shelf/utils.py}}

A script, a README, the pytest settings (`pythonpath = src` lets the tests import `shelf`):

{{file:src/toolcallbench/data/fixtures/repo/scripts/report.py}}

{{file:src/toolcallbench/data/fixtures/repo/README.md}}

{{file:src/toolcallbench/data/fixtures/repo/pytest.ini}}

The tests:

{{file:src/toolcallbench/data/fixtures/repo/tests/test_catalog.py}}

{{file:src/toolcallbench/data/fixtures/repo/tests/test_fees.py}}

{{file:src/toolcallbench/data/fixtures/repo/tests/test_loans.py}}

{{file:src/toolcallbench/data/fixtures/repo/tests/test_utils.py}}

### Run

{{cmd:cd src/toolcallbench/data/fixtures/repo && python -m pytest -q --tb=line}}

You must see **2 failed, 11 passed**. If you see a different number, a file was copied
wrongly. The tasks later in this guide depend on these exact numbers (for example, the
report script prints 11 copies in total):

{{cmd:cd src/toolcallbench/data/fixtures/repo && python scripts/report.py}}

### Checkpoint

```bash
git add -A && git commit -m "Day 1: sample project with two bugs"
```

---

## Day 2: Tools, the sandbox and the patch engine

**Goal:** a safe way for a program to read files, search, edit, apply patches and run commands.

### Why

A model "calls a tool" by returning a name and some arguments, for example
`read_file` with `{"path": "README.md"}`. Our program must (1) check that the call is
valid, (2) run it safely, and (3) send the result back. This day builds those three parts.

- `models.py` holds small data classes shared by all other files (a `Task`, a tool call record, a check result).
- `patching.py` applies a *unified diff* (the `+` and `-` lines you see in `git diff`). Models often write these, and they often get them slightly wrong, so the engine reports clear errors.
- `tools.py` has the six tool definitions as JSON Schema (this is what the model sees), a function that validates a raw call, and a `ToolExecutor` that runs calls inside one folder.

How the safety works, in plain words:

- File tools turn the path into an absolute path and refuse anything outside the project copy.
- `run_command` does **not** use a shell. The command is split into words and only 12 programs are allowed. `python` may run only a `.py` file inside the project or `-m pytest`.
- Every command has a time limit and its output is cut at 6000 characters.

This is a safety net against mistakes, not a wall against a hostile program. `docs/SECURITY.md` explains the limits.

An invalid call is never run. The model gets an `error: ...` message instead, so it can try again,
and the run records *why* it was invalid (`invalid_json`, `invalid_args`, `unknown_tool`). This
is the heart of what we measure.

### Create

{{file:src/toolcallbench/models.py}}

{{file:src/toolcallbench/patching.py}}

{{file:src/toolcallbench/tools.py}}

Test helpers. `conftest.py` gives every test a fresh copy of the sample project:

{{file:tests/conftest.py}}

{{file:tests/test_patching.py}}

{{file:tests/test_tools.py}}

### Run

{{cmd:python -m pytest tests/test_patching.py tests/test_tools.py}}

### Checkpoint

```bash
git add -A && git commit -m "Day 2: tools, sandbox, patch engine"
```

---

## Day 3: Backends and configuration

**Goal:** code that can talk to Ollama, to OpenAI-style servers, and to a fake model.

### Why

A *backend* hides how a server speaks. The runner only asks `backend.chat(messages, tools)` and
gets a `BackendResponse` (text, tool calls, token counts). Three backends:

- **Ollama** (`ollama.py`): `POST /api/chat` with `stream: false`. Tool-call arguments come back as a real object. Speed comes from `eval_count` and `eval_duration` (nanoseconds).
- **OpenAI-compatible** (`openai_compat.py`): for llama.cpp's `llama-server`, LM Studio and vLLM. Here the arguments come back as a **JSON string**, which the model may get wrong. That makes this backend good at finding `invalid_json` problems.
- **Scripted** (`scripted.py`): a fake model that replays each task's correct solution, or fails in a chosen way (bad JSON, unknown tool, and so on). We use it to test the program and to prove the scoring detects each kind of failure. Without a fake model we could not test anything before downloading gigabytes of weights.

`base.py` has `BackendError` (the *server* failed, not the model) and a small HTTP helper that
uses only Python's standard library.

`config.py` holds the settings with their defaults. Three of them matter for your Mac:

- `num_ctx: 16384`: the context length. Ollama's own default is only 4096 on machines with less than 24 GB, which is too small for multi-step work. 16k costs about 1 to 2 GB of memory for an 8B model.
- `temperature: 0.0` and a fixed `seed`: as repeatable as a model can be. Each repeat adds 1 to the seed.
- `repeats: 3`: one run of one task proves little; models are not perfectly steady.

### Create

{{file:src/toolcallbench/backends/base.py}}

{{file:src/toolcallbench/backends/ollama.py}}

{{file:src/toolcallbench/backends/openai_compat.py}}

{{file:src/toolcallbench/backends/scripted.py}}

{{file:src/toolcallbench/backends/__init__.py}}

{{file:src/toolcallbench/config.py}}

Three ready-made config files. The first is the plan for your Mac, the second compares two
quantization levels of the same model, the third needs no model.

{{file:src/toolcallbench/data/configs/m4-16gb.yaml}}

{{file:src/toolcallbench/data/configs/quant-sweep-qwen3-8b.yaml}}

{{file:src/toolcallbench/data/configs/smoke-scripted.yaml}}

And the starter file that `toolcallbench init` gives to users:

{{file:src/toolcallbench/data/configs/my-models.yaml}}

{{file:tests/test_config.py}}

### Run

{{cmd:python -m pytest tests/test_config.py}}

### Checkpoint

```bash
git add -A && git commit -m "Day 3: backends and config"
```

---

## Day 4: The 20 tasks, the scoring rules and the runner

**Goal:** every task can be run against the fake model and scored, and every task is proven passable.

### Why

**Tasks.** Each task is a YAML file with a `prompt`, an `expect` block (what a pass looks like)
and a `reference` (a correct solution). Five groups:

| Group | Count | What it tests |
| --- | --- | --- |
| read | 5 | One tool call and a question about the result |
| edit | 5 | Changing files with `edit_file` or `apply_patch` |
| run | 3 | Running commands and reporting what they print |
| chain | 4 | Several dependent steps, no tool named in the prompt |
| failure | 3 | Answering without tools, parallel calls, recovering from a wrong path |

In 12 tasks the prompt names the tool; in 8 it does not. That separates "can call a tool" from
"can decide which tool to call".

**Scoring** (`checks.py`). No AI judge: the verdict is plain code. A run **passes** when three
parts succeed:

1. **Parse**: every call is valid JSON with the right arguments for a real tool, and the model did not just *write* a tool call as text.
2. **Tool**: the right tools in the right amount (not too many, not too few, in order when the task says so, together in one step when the task wants parallel calls).
3. **Outcome**: the final answer contains what it should, and the repository ends in the right state. The task itself can run a command (for example the tests) to check.

Two more numbers are reported but do not decide pass or fail: **Args** (did the expected
arguments appear?) and **Efficiency** (calls made divided by calls in the reference).

A failed run gets exactly one reason from a fixed priority list (for example `invalid_json`
before `wrong_tool` before `outcome_mismatch`), so the report can count them.

**The runner** (`runner.py`) is the loop: copy the sample project, send the prompt, run the
tool calls, send the results back, repeat until the model answers or a limit is hit, then score.
If the server crashes, the run is marked `error`, not "failed".

### Create

The task loader:

{{file:src/toolcallbench/tasks.py}}

The scoring rules and the runner:

{{file:src/toolcallbench/checks.py}}

{{file:src/toolcallbench/runner.py}}

Now the 20 tasks. Read two or three of them (start with `read-01` and `chain-04`) before you
paste all of them.

{{file:src/toolcallbench/data/tasks/read-01.yaml}}

{{file:src/toolcallbench/data/tasks/read-02.yaml}}

{{file:src/toolcallbench/data/tasks/read-03.yaml}}

{{file:src/toolcallbench/data/tasks/read-04.yaml}}

{{file:src/toolcallbench/data/tasks/read-05.yaml}}

{{file:src/toolcallbench/data/tasks/edit-01.yaml}}

{{file:src/toolcallbench/data/tasks/edit-02.yaml}}

{{file:src/toolcallbench/data/tasks/edit-03.yaml}}

{{file:src/toolcallbench/data/tasks/edit-04.yaml}}

{{file:src/toolcallbench/data/tasks/edit-05.yaml}}

{{file:src/toolcallbench/data/tasks/run-01.yaml}}

{{file:src/toolcallbench/data/tasks/run-02.yaml}}

{{file:src/toolcallbench/data/tasks/run-03.yaml}}

{{file:src/toolcallbench/data/tasks/chain-01.yaml}}

{{file:src/toolcallbench/data/tasks/chain-02.yaml}}

{{file:src/toolcallbench/data/tasks/chain-03.yaml}}

{{file:src/toolcallbench/data/tasks/chain-04.yaml}}

{{file:src/toolcallbench/data/tasks/failure-01.yaml}}

{{file:src/toolcallbench/data/tasks/failure-02.yaml}}

{{file:src/toolcallbench/data/tasks/failure-03.yaml}}

The tests. `test_tasks.py` replays all 20 reference solutions. `test_checks.py` makes the fake
model fail in each way and checks that the scorer names the right failure.

{{file:tests/test_tasks.py}}

{{file:tests/test_checks.py}}

### Run

This takes about half a minute because some checks run the sample project's tests.

{{cmd:python -m pytest tests/test_tasks.py tests/test_checks.py}}

### Checkpoint

```bash
git add -A && git commit -m "Day 4: tasks, scoring, runner"
```

---

## Day 5: Storage and reports

**Goal:** results are saved to a database and turned into a readable report.

### Why

- `store.py` uses **SQLite**, a database in one file with no server to install. Three tables: `sessions` (one benchmark run, with all its settings), `runs` (one task attempt) and `calls` (each tool call). A `UNIQUE (session_id, model, task_id, repeat)` rule means the same run can never be stored twice, which makes **resume** safe. It also writes one **JSONL** transcript per run (one JSON object per line), so you can read exactly what the model said.
- `report.py` turns the numbers into a Markdown table and a simple HTML page. It reports the pass rate per group, why runs failed, the median speed, and **all settings**, because two reports are only comparable when their settings match.

### Create

{{file:src/toolcallbench/store.py}}

{{file:src/toolcallbench/report.py}}

{{file:tests/test_store_report.py}}

### Run

{{cmd:python -m pytest tests/test_store_report.py}}

### Checkpoint

```bash
git add -A && git commit -m "Day 5: storage and reports"
```

---

## Day 6: The command line and mock servers

**Goal:** `toolcallbench` works end to end with a fake model, and the real HTTP backends are tested against pretend servers.

### Why

`cli.py` connects everything. Its commands:

| Command | What it does |
| --- | --- |
| `list-tasks` | Show the tasks |
| `validate-tasks` | Replay every reference solution through the real tools and scorer |
| `doctor` | Check Python, tasks, sample project, the server and the models; `--probe` runs one real task |
| `run` | Run the benchmark and write the report |
| `report` | Rebuild a report from saved results |
| `sessions` | List saved sessions |

Two ideas worth noticing in `cmd_run`:

- **Resume**: before each run it asks the database whether that run already exists. Press Ctrl+C any time; run the same command again with `--resume`.
- **Stop after three server errors in a row**: if Ollama crashes, the program stops that model instead of writing 60 fake "failures".

`tests/mock_servers.py` starts small HTTP servers on your own computer that *pretend* to be
Ollama or an OpenAI-style server. They answer by using the fake model. This lets us test the real
HTTP code (URLs, JSON shapes, headers) without any model.

### Create

{{file:src/toolcallbench/cli.py}}

{{file:tests/mock_servers.py}}

{{file:tests/test_http_backends.py}}

{{file:tests/test_cli.py}}

### Run

Everything the program can do without a real model:

{{cmd:toolcallbench list-tasks}}

{{cmd:toolcallbench validate-tasks}}

A complete benchmark with the fake model (a "perfect" model, so it passes everything). Results
go to the `results` folder:

{{cmd:toolcallbench run --backend scripted --repeats 1 --session demo}}

The beginning of the report it wrote:

{{cmd:toolcallbench report --session demo --print | sed -n 1,24p}}

The doctor with the fake backend:

{{cmd:toolcallbench doctor --backend scripted}}

And the whole test suite so far (this takes about a minute):

{{cmd:python -m pytest}}

### Checkpoint

```bash
git add -A && git commit -m "Day 6: CLI and mock-server tests"
```

---

## Day 7: Helper scripts, then your first real model

**Goal:** a model on your Mac answers one real task.

### Why

Three small scripts help you run on 16 GB:

- `serve_ollama.sh` starts Ollama with the right settings. Some settings (`OLLAMA_KV_CACHE_TYPE`, `OLLAMA_FLASH_ATTENTION`) can only be set when the server starts, not in each request. So we tell the benchmark what we used with `--kv-cache-type` and `--flash-attention`, and it prints them in the report as "declared".
- `estimate_memory.py` estimates weights plus *KV cache* (the memory a model uses to remember the conversation). Formula: `2 x layers x KV heads x head size x bytes per number x tokens`.
- `make_task_catalog.py` writes `docs/TASK_CATALOG.md` from the task files, so the documentation can never disagree with the tasks.

### Create

{{file:scripts/serve_ollama.sh}}

{{file:scripts/estimate_memory.py}}

{{file:scripts/make_task_catalog.py}}

{{file:tests/test_scripts.py}}

Make the server script runnable and generate the catalog:

```bash
chmod +x scripts/serve_ollama.sh
mkdir -p docs
python scripts/make_task_catalog.py
```

### Run

{{cmd:python scripts/estimate_memory.py}}

{{cmd:python scripts/make_task_catalog.py && python -m pytest tests/test_scripts.py}}

### Your first real model

1. **Quit the Ollama menu-bar app** (it would block the port with default settings).
2. Terminal 1: `./scripts/serve_ollama.sh` (leave it running).
3. Terminal 2 (with `source .venv/bin/activate`):

```bash
ollama pull qwen3:8b            # about 5 GB download
toolcallbench doctor --model qwen3:8b --probe
```

`doctor` prints one line per check, in this shape (your values will differ):

```text
[ OK ] Python 3.10 or newer: 3.12.x
[ OK ] task files: 20 tasks in .../tasks
[ OK ] fixture repo: 2 failing test(s); the tasks expect exactly 2
[ OK ] Ollama server: version X.Y.Z at http://localhost:11434; N model(s) installed
[ OK ] model qwen3:8b: <size> <quantization>; tools supported
[ OK ] probe qwen3:8b: read-01 passed in <seconds>s, <number> tok/s
```

If the probe fails, look at the reason in the last line before you continue. Common causes are
in the table below.

| Message | What to do |
| --- | --- |
| `cannot reach http://localhost:11434` | Start the server: `./scripts/serve_ollama.sh` |
| `model ... not installed` | Run the `ollama pull` command it prints |
| `does not report tool support` | Use a model whose Ollama page lists "tools" |
| Probe fails with `no_call` or `text_tool_call` | The model or its template does not do tool calls well. That is a result, not a bug. Try another model |
| Very slow | For Qwen3 add `--think off` |

One thing the author could not verify without a real model: the exact shape Ollama expects for a
tool result message. This program sends `{"role": "tool", "tool_name": ..., "content": ...}`. The
probe is how you find out on your machine. If the probe always ends in a second tool call
or confusion about results, check the Ollama documentation for your version.

### Checkpoint

```bash
git add -A && git commit -m "Day 7: helper scripts, first real probe"
```

---

## Day 8: The real benchmark on your M4

**Goal:** a report that tells you which model to use.

### Plan the sweep

Memory first (the estimator gives the same table as above). On 16 GB the GPU can use roughly 12
GB. An 8B model at Q4 with a 16k context and a `q8_0` cache needs about 7 GB, so you can run it
while a browser is open. A 14B model or an 8B at Q8 leaves little room.

Run in this order, from cheap to expensive:

```bash
# 1. A quick look: one repeat of the cheapest group
toolcallbench run --model qwen3:8b --think off --groups read --repeats 1 --kv-cache-type q8_0 --flash-attention

# 2. The planned sweep (three models, three repeats each)
caffeinate -i toolcallbench run --config configs/m4-16gb.yaml --session m4-first

# 3. Does thinking help? Same model, thinking on
toolcallbench run --model qwen3:8b --think on --kv-cache-type q8_0 --flash-attention --session m4-think-on

# 4. Does quantization matter?
ollama pull qwen3:8b-q4_K_M && ollama pull qwen3:8b-q8_0     # check the exact tag names on ollama.com first
caffeinate -i toolcallbench run --config configs/quant-sweep-qwen3-8b.yaml --session m4-quant
```

`caffeinate -i` keeps the Mac awake. If it sleeps anyway, run the same command again with `--resume`.

Each command ends by printing where the report is. Open the HTML file:

```bash
open results/reports/m4-first.html
```

### How to read the first report

1. Look at **Settings**. If two reports differ there, they are not a fair comparison.
2. Look at **Errors**. If it is not 0, the server had problems; fix that first.
3. Compare **Pass** per group. Chain tasks are the hardest; a model that passes `read` and `run` but fails `chain` can call tools but cannot plan.
4. Read **Failure types**. `invalid_json` or `text_tool_call` means a format problem; `no_call` means the model answered from memory; `wrong_tool` or `outcome_mismatch` means a reasoning problem.
5. Look at the per-task table for cells like `1/3`: those are flaky tasks, and the transcript in `results/logs/<session>/<model>/<task>_<repeat>.jsonl` shows what happened.
6. Compare `tok/s` and `s/task`. A model that is 5% better but three times slower may not be the better choice for you.

### Keep a log

Fill in this table with your own numbers (do not copy anyone else's):

| Session | Model | Quant | Think | KV cache | Pass % | Chain % | Top failure type | s/task |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | |

### If something goes wrong

| Problem | Fix |
| --- | --- |
| The Mac becomes slow | Lower `--num-ctx 8192`, close the browser, or use a smaller model |
| `ollama ps` shows part of the model on CPU | The model plus cache does not fit; use a smaller context or quantization |
| All runs are `no_call` | Check that the model supports tools |
| Results change between runs | Expected to a small degree; use more `--repeats` |

---

## Day 9: Documents, polish and publishing

**Goal:** a project another person can understand, run and trust.

### The documents

Software projects normally come with a standard set of documents. They are all in the `docs`
folder of the finished repository; here is what each is for and how to write your own.

| Document | Question it answers | How to write it |
| --- | --- | --- |
| `README.md` | What is this and how do I start? | What it is in 3 lines, a quick start, where the docs are, honest status |
| `docs/PRD.md` (product requirements) | Why build it, for whom, what must it do? | Problem, users, goals and non-goals, numbered requirements (FR-1, FR-2...), risks |
| `docs/TECH_SPEC.md` | Exactly how does it behave? | Protocols, formats, scoring rules, configuration, error handling |
| `docs/ARCHITECTURE.md` | How are the parts connected? | Diagrams: context, components, data flow, sequence, states, storage (Mermaid) |
| `docs/TEST_PLAN.md` | What is tested and what is not? | Strategy, a table linking each requirement to tests, results, known gaps |
| `docs/SECURITY.md` | What can go wrong? | What protects the user, and honestly, what does not |
| `docs/DECISIONS.md` | Why this way? | Short records: decision, why, cost |
| `docs/USER_GUIDE.md` | How do I use it? | Install, commands, reading output, troubleshooting |
| `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md` | What changed, how to help, what next? | Short lists |

Diagrams in `ARCHITECTURE.md` are written as text (Mermaid), so they stay in Git. GitHub draws
them automatically. To preview locally, use the Mermaid extension in VS Code.

A good habit, used here: generate documents from the source when you can (the task catalog
and this guide), so they cannot go out of date. The PRD has a requirement table; the test plan
maps each requirement to the tests that prove it.

### Create

The README, a Makefile with shortcuts, and the CI file that runs the tests on GitHub for every push:

{{file:README.md}}

{{file:Makefile}}

{{file:.github/workflows/ci.yml}}

The two scripts that build and check this guide (yes, the guide contains the scripts that
build the guide):

{{file:scripts/make_build_guide.py}}

{{file:scripts/verify_build_guide.py}}

Write the documents from the table above, using the finished repository's `docs` folder as a
model, then add `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md` in the same way.

### Run

The full test suite, one last time:

{{cmd:python -m pytest}}

### Publish

```bash
git add -A && git commit -m "Day 9: docs and polish"
git tag v0.1.0
gh repo create toolcallbench --public --source=. --push      # needs the GitHub CLI: brew install gh
git push --tags
```

---

## Day 10: Make it yours

Ideas, from easiest to hardest:

1. **Add a task.** Copy `tasks/read-01.yaml` to `tasks/read-06.yaml`, change the id, prompt and `expect`, add a reference solution, then run `toolcallbench validate-tasks --tasks read-06`. If your reference does not pass, the task is wrong.
2. **Add a failure profile** to `scripted.py` (for example, a model that calls the right tool with the wrong argument name) and a test in `test_checks.py`.
3. **Use your own project.** Copy a project of yours (without secrets), write tasks for it, and run `toolcallbench run --fixture ~/path/to/copy --tasks-dir my-tasks --model qwen3:8b`. Read `docs/SECURITY.md` first.
4. **Compare servers.** Run the same model through llama.cpp's `llama-server` with `--backend openai-compat --host http://localhost:8080` and compare the failure types. This is where `invalid_json` shows up.
5. **Write about it.** The report contains every setting. Publish your table and say which Mac you used.

## Appendix: if a test fails after you copy the code

1. Run only that test with `python -m pytest tests/test_x.py -x`.
2. Read the first error, not the last.
3. Diff the file against this guide (a missing blank line or indentation is the usual cause).
4. Files must end with exactly one newline.
5. Re-check Day 1: the sample project must show 2 failed, 11 passed.
