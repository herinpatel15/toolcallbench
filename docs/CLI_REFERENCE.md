# CLI reference

Install with `pip install toolcallbench` (Python 3.10 or newer). The command is `toolcallbench`;
`python -m toolcallbench` does the same. `toolcallbench --version` prints the version and
`toolcallbench <command> --help` lists every option of a command.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | A check failed (`doctor`, `validate-tasks`), the server was unreachable, `init` would overwrite files, or `compare` / `export` could not find the sessions |
| 2 | Bad input: invalid config or task files, no task files found, or a session id that already exists without `--resume` |
| 130 | Interrupted with Ctrl+C (use `--resume` to continue) |

## Typical session

```bash
mkdir my-bench && cd my-bench
toolcallbench init
toolcallbench doctor --probe --config configs/my-models.yaml
toolcallbench run --config configs/my-models.yaml
toolcallbench sessions
toolcallbench report --session latest
toolcallbench compare            # previous session vs latest
toolcallbench export --format csv
```

## Where files go

| What | Where |
| --- | --- |
| Tasks and sample repository | Built into the package. A folder that has its own `tasks/` and `fixtures/repo/` uses those instead (create them with `toolcallbench init --with-tasks`) |
| Example configs | `toolcallbench init` copies them to `./configs/` |
| Results database | `./results/results.sqlite` |
| Raw logs | `./results/logs/` |
| Reports | `./results/reports/<session>.md` and `.html` |
| Comparisons | `./results/reports/compare-<A>-vs-<B>.md` |
| Exports | `./results/exports/<session>.json` or `.csv` |

"`./`" is the folder you run the command in, or `--root` / `--results-dir` if you give them.

## Commands

### `init [DIR] [--with-tasks]`

Copies the example config files into `DIR/configs/` (default: the current folder). With
`--with-tasks` it also copies `tasks/` and `fixtures/repo/` so you can edit them. It stops
without changing anything if a target folder already exists.

### `list-tasks [--markdown]`

Prints all 24 tasks (20 core, 4 optional `nested`; optional ones are marked). `--markdown` prints a table.

### `validate-tasks [--tasks IDS] [--groups NAMES]`

Replays each task's reference solution through the checker. `24/24 reference solutions pass`
means the tasks and the sample repository are intact. Exit code 1 if any fail.

### `doctor [--config FILE] [--model NAME]... [--probe] [--backend KIND] [--host URL]`

Checks Python, the task files, the sample repository, the server, and each `--model`
(installed, reports tool support). With `--probe` it also runs the task `read-01` once per model.

Pass `--config` so the probe uses the same context size, temperature, seed, `think` setting and
timeout as `run`. Without it the server's own defaults apply (temperature 0.8, context 4096),
and probe results will vary between runs. Exit code 0 if every check passed, otherwise 1.

### `run [options]`

Runs every selected task for every model, `repeats` times, and stores each result. Options
override the config file.

| Option | Meaning | Default |
| --- | --- | --- |
| `--config FILE` | YAML config file | none |
| `--backend ollama\|openai-compat\|scripted` | Server type | `ollama` |
| `--host URL` | Server address | `http://localhost:11434` (ollama), `http://localhost:8080` (openai-compat) |
| `--model NAME` | Model; repeat for several. Replaces the models in the config | none |
| `--think on\|off\|default` | Ollama thinking mode (only for models that have one) | `default` |
| `--num-ctx N` | Context length | 16384 |
| `--temperature X` | Sampling temperature | 0.0 |
| `--seed N` | Random seed; repeat `k` uses `seed + k - 1` | 42 |
| `--repeats N` | Runs per task and model | 3 |
| `--max-calls N` | Tool calls allowed per task | 12 |
| `--max-turns N` | Model turns allowed per task | 10 |
| `--tasks IDS` | Comma-separated task ids, e.g. `read-01,edit-02` | all |
| `--groups NAMES` | Comma-separated groups: `read,edit,run,chain,failure,nested` | the 20 core tasks (naming `nested` or a nested task id adds the optional tasks) |
| `--tools-offered all\|task` | `all` offers the core tools to every task; `task` offers only the tools the task needs (a hint, so an ablation) | `all` |
| `--max-calls-per-turn N` | Run only the first N tool calls of each reply; 0 means no limit | 0 |
| `--api-key-env NAME` | Name of an environment variable that holds the API key (`openai-compat` only). The key itself is never given here | none (`TOOLCALLBENCH_API_KEY` is used if set) |
| `--session ID` | Name of this run | start time |
| `--resume` | Continue a session and skip runs already stored | off |
| `--kv-cache-type T` | KV cache type your server uses (recorded only) | `f16` |
| `--flash-attention` | Record that the server uses flash attention | off |
| `--profile P` | Behavior of the `scripted` backend (for testing) | `oracle` |
| `--root`, `--tasks-dir`, `--fixture`, `--results-dir` | Paths, see above | |

If the session id already exists and `--resume` is not given, `run` prints an error and exits
with code 2. If the server cannot be reached it exits with code 1.

### `compare [SESSION_A] [SESSION_B]`

Compares two sessions. With no arguments it compares the previous session with the latest. It shows which settings differ (so you know whether the comparison is fair), the pass-rate change per model with a verdict (better, worse, or no clear difference based on the 95% ranges), tasks that flipped, and failure-family changes. It warns when the two sessions ran different task sets. Writes `results/reports/compare-A-vs-B.md`. Exit code 1 if fewer than two sessions exist or an id is unknown.

### `export [--session ID|latest] [--format json|csv] [--output FILE|-]`

Writes every run of a session as JSON (session settings plus runs) or CSV (one row per run: model, task, passed, failure type, tokens, timings). Default file: `results/exports/<session>.<format>`; `-` prints to the terminal.

### `report [--session ID|latest] [--print]`

Builds the Markdown and HTML report from stored results. `--print` also prints the Markdown.

### `sessions`

Lists stored sessions.

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
api_key_env: OPENAI_API_KEY        # NAME of an environment variable (openai-compat only), never the key
declared_server:                   # recorded in the report, not enforced
  kv_cache_type: q8_0
  flash_attention: true
models:
  - name: qwen3:8b
    think: false                   # per model; leave out for models without a thinking mode
  - llama3.1:8b                    # a plain string is enough
```

Unknown keys are rejected with a message that lists the allowed ones. A command-line option
always wins over the same setting in the file.

## Example configs (`toolcallbench init`)

| File | Purpose |
| --- | --- |
| `my-models.yaml` | Starting point: edit the model names |
| `m4-16gb.yaml` | Plan for a MacBook M4 with 16 GB |
| `quant-sweep-qwen3-8b.yaml` | Same model at two quantization levels |
| `smoke-scripted.yaml` | No model needed; proves the pipeline works |

## Failure types

`invalid_json`, `invalid_args`, `unknown_tool`, `text_tool_call`, `no_call`, `unneeded_call`,
`call_limit`, `not_parallel`, `wrong_tool`, `too_few_calls`, `no_confirm_run`, `patch_failed`,
`wrong_args`, and `outcome_mismatch` (14). `TECH_SPEC.md` defines each one and the order they are checked in.
