# CLI reference

Install with `pip install toolcallbench` (Python 3.10 or newer). The command is `toolcallbench`;
`python -m toolcallbench` does the same. `toolcallbench --version` prints the version and
`toolcallbench <command> --help` lists every option of a command.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | A check failed (`doctor`, `validate-tasks`), the server was unreachable, or `init` would overwrite files |
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
```

## Where files go

| What | Where |
| --- | --- |
| Tasks and sample repository | Built into the package. A folder that has its own `tasks/` and `fixtures/repo/` uses those instead (create them with `toolcallbench init --with-tasks`) |
| Example configs | `toolcallbench init` copies them to `./configs/` |
| Results database | `./results/results.sqlite` |
| Raw logs | `./results/logs/` |
| Reports | `./results/reports/<session>.md` and `.html` |

"`./`" is the folder you run the command in, or `--root` / `--results-dir` if you give them.

## Commands

### `init [DIR] [--with-tasks]`

Copies the example config files into `DIR/configs/` (default: the current folder). With
`--with-tasks` it also copies `tasks/` and `fixtures/repo/` so you can edit them. It stops
without changing anything if a target folder already exists.

### `list-tasks [--markdown]`

Prints the 20 tasks. `--markdown` prints a table.

### `validate-tasks [--tasks IDS] [--groups NAMES]`

Replays each task's reference solution through the checker. `20/20 reference solutions pass`
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
| `--groups NAMES` | Comma-separated groups: `read,edit,run,chain,failure` | all |
| `--session ID` | Name of this run | start time |
| `--resume` | Continue a session and skip runs already stored | off |
| `--kv-cache-type T` | KV cache type your server uses (recorded only) | `f16` |
| `--flash-attention` | Record that the server uses flash attention | off |
| `--profile P` | Behavior of the `scripted` backend (for testing) | `oracle` |
| `--root`, `--tasks-dir`, `--fixture`, `--results-dir` | Paths, see above | |

If the session id already exists and `--resume` is not given, `run` prints an error and exits
with code 2. If the server cannot be reached it exits with code 1.

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
`call_limit`, `not_parallel`, `wrong_tool`, `too_few_calls`, `patch_failed`, `wrong_args`, and
`outcome_mismatch`. `TECH_SPEC.md` defines each one and the order they are checked in.
