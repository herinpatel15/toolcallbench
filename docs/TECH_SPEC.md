# Technical Specification

Version 0.1.0. This document is the reference for how ToolCallBench behaves. The code is the
final authority; tests in `tests/` check the statements below.

## 1. Conversation protocol

The runner sends this to the backend, in this order:

1. `system`: a fixed prompt (hash recorded in the report as `system_prompt_sha`).
2. `user`: the task prompt.

After each assistant message with tool calls, the runner appends one message per call:

```json
{"role": "tool", "tool_name": "read_file", "content": "   1| ..."}
```

The loop ends when the assistant replies **without** tool calls (the reply is the final
answer), or when a limit is reached: `max_calls` (default 12 tool calls in total) or
`max_turns` (default 10 model replies). Reaching a limit is the failure type `call_limit`.

For OpenAI-compatible servers the runner converts messages: tool call arguments become JSON
strings and each tool result gets a `tool_call_id`.

## 2. Tools

| Tool | Required arguments | Optional | Notes |
| --- | --- | --- | --- |
| `read_file` | `path` | `start_line`, `end_line` | Output has `NNNN| ` line prefixes; 1-based |
| `list_dir` | none | `path` | Folder names end with `/` |
| `grep` | `pattern` | `path` | Python regular expression; at most 50 matches |
| `edit_file` | `path`, `old_text`, `new_text` | none | `old_text` must occur exactly once |
| `apply_patch` | `patch` | none | Unified diff; existing files only; line numbers in `@@` headers are not enforced |
| `run_command` | `command` | none | No shell; allow-list below |

All schemas set `additionalProperties: false`, so an unexpected argument is an
`invalid_args` failure.

**Command allow-list:** `python`, `python3`, `pytest`, `ls`, `cat`, `echo`, `grep`, `head`,
`tail`, `wc`, `touch`, `mkdir`. `python` may run only a `.py` file inside the repository or
`-m pytest`. Arguments that start with `/` or `~`, or contain `..`, are rejected. The
command is split with `shlex` and run without a shell, so `ls | wc` passes `|` and `wc` to
`ls` as plain arguments. Timeout 20 s. Output is cut at 6000 characters.

## 3. Validation of a tool call

Order of checks (first failure wins):

| Check | Error kind |
| --- | --- |
| Tool name not in the six names | `unknown_tool` |
| Arguments are a string that is not valid JSON, or not an object | `invalid_json` |
| Arguments do not match the JSON Schema | `invalid_args` |

An invalid call is **not executed**. The model receives `error: ...` text and may try again;
the call still counts toward `max_calls` and the run's Parse score fails.

A call that is valid but fails when executed (file not found, patch does not match) has
`error_kind = tool_error` and does not fail Parse by itself.

## 4. Scoring

Each run produces four booleans and one ratio.

| Part | Passes when |
| --- | --- |
| **Parse** | every call is valid, and the final reply is not a tool call written as text |
| **Tool** | the right tools were used in the right amount (details below) |
| **Args** | each expected call has a matching valid call with the expected argument values |
| **Outcome** | answer checks and repository checks all hold |
| **Efficiency** | calls made divided by the reference solution's calls (1.00 is ideal; reported, not scored) |

**A run passes when Parse, Tool and Outcome all pass.** Args is reported separately because
a model can reach the right outcome with different arguments (for example, reading a file in
two ranges).

### Tool part

Evaluated in this order; the first failing rule gives the failure type.

1. Limit reached → `call_limit`
2. `no_tool_calls: true` and any call was made → `unneeded_call`
3. No calls but at least `min_calls` required → `no_call`
4. More calls than `max_calls` → `call_limit`
5. Fewer calls than `min_calls` (default: number of expected calls) → `too_few_calls`
6. A call to a `forbidden_tools` tool → `wrong_tool`
7. Expected calls cannot be matched to distinct valid calls by tool name (in order when `ordered: true`) → `wrong_tool`
8. `parallel: true` and the expected calls are not all in one turn → `not_parallel`

### Outcome part

- `answer_contains`: case-insensitive substrings in the final answer.
- `answer_regex`: case-insensitive regular expressions.
- `files_exist`, `final_files` (`contains`, `not_contains`, `unchanged`): checked on the working copy.
- `command`: an argv list run in the working copy; exit code must equal `exit_code` (default 0). The command is part of the task, not chosen by the model.

### Failure type priority

A failed run gets exactly one type:

| Order | Type | Meaning |
| --- | --- | --- |
| 1 | `invalid_json` | arguments were not parseable JSON |
| 1 | `invalid_args` | arguments broke the schema |
| 1 | `unknown_tool` | called a tool that does not exist |
| 1 | `text_tool_call` | wrote a tool call as text instead of calling it |
| 2 | `call_limit` | too many calls or turns |
| 2 | `unneeded_call` | called a tool when none was needed |
| 2 | `no_call` | answered without calling a needed tool |
| 2 | `too_few_calls` | stopped before enough calls |
| 2 | `wrong_tool` | wrong or forbidden tool |
| 2 | `not_parallel` | needed calls were made one at a time |
| 3 | `patch_failed` | outcome wrong and an edit call was rejected |
| 3 | `wrong_args` | outcome wrong and expected arguments were not found |
| 3 | `outcome_mismatch` | everything else that left the wrong outcome |
| - | `ok` | passed |
| - | `backend_error` | stored for server errors; excluded from pass rates |

Text tool calls are detected with a regular expression on the final reply: `<tool_call>`,
`<function=`, or `"name": "<tool>"`.

## 5. Task file format

```yaml
id: read-01                 # group-NN, group must match the prefix
group: read                 # read | edit | run | chain | failure
title: Read one config value
tools_named: true           # does the prompt name the tool?
prompt: |
  ...
expect:                     # see section 4
  calls:
    - tool: read_file       # or a list of acceptable tools
      args: {path: config/settings.json}   # values, or {contains|regex|one_of: ...}
  answer_regex: ['\b14\b']
reference:                  # a solution that must pass; last step is "final"
  - calls:
      - {tool: read_file, args: {path: config/settings.json}}
  - final: loan_days is 14.
```

Files are validated with a JSON Schema plus extra rules (id prefix, known `expect` keys,
last reference step is a final answer). `toolcallbench validate-tasks` replays every
reference through the real tools and checker.

## 6. Configuration

Precedence: command-line flag > config file > default.

| Setting | Default | Meaning |
| --- | --- | --- |
| `backend` | `ollama` | `ollama`, `openai-compat`, `scripted` |
| `host` | backend default | `http://localhost:11434` (Ollama), `http://localhost:8080` (others) |
| `num_ctx` | 16384 | sent to Ollama as `options.num_ctx` |
| `temperature` | 0.0 | |
| `seed` | 42 | repeat *k* uses `seed + k - 1` |
| `repeats` | 3 | runs per task and model |
| `max_calls`, `max_turns` | 12, 10 | limits per run |
| `request_timeout` | 300 s | per HTTP request |
| `declared_server.kv_cache_type` | `f16` | what you started the server with (recorded only) |
| `declared_server.flash_attention` | false | recorded only |

Server-side variables (`OLLAMA_KV_CACHE_TYPE`, `OLLAMA_FLASH_ATTENTION`,
`OLLAMA_CONTEXT_LENGTH`) cannot be changed through the API; `scripts/serve_ollama.sh` sets
them and the "declared" fields record them.

## 7. Backends

**Ollama**: `POST /api/chat` with `{model, messages, tools, stream:false, options, keep_alive, think?}`.
Tool call arguments arrive as objects. Speed comes from `eval_count` / `eval_duration`.
`GET /api/version`, `GET /api/tags` and `POST /api/show` supply the version, installed models,
quantization (`details.quantization_level`) and capabilities.

**OpenAI-compatible**: `POST /v1/chat/completions`; arguments arrive as JSON **strings**, so
this backend exercises the `invalid_json` path. Speed uses `timings.predicted_ms` when the
server provides it (llama.cpp), otherwise wall time.

**Scripted**: replays each task's reference solution. Profiles `invalid_json`, `unknown_tool`,
`wrong_tool`, `text_call`, `no_call`, `call_limit`, `bad_edit` each imitate one failure so the
checker can be tested.

## 8. Storage

SQLite file `results/results.sqlite` (tables in `ARCHITECTURE.md`, section 6) plus one JSONL
file per run at `results/logs/<session>/<model>/<task>_<repeat>.jsonl`. Each JSONL file has
one line per message and a final `summary` line with the verdict and calls.

## 9. Error handling

| Situation | Behavior |
| --- | --- |
| Server unreachable at start | `run` exits with code 1 and the fix |
| Model not installed | message with `ollama pull NAME` |
| HTTP error during a run | run stored with `status=error`; three errors in a row stop that model |
| Ctrl+C | exit code 130; continue with `--resume` |
| Invalid task or config file | exit code 2 with the file and reason |

## 10. Determinism and limits

- Scoring is a pure function of the transcript and the final repository state.
- Model output is only as repeatable as the server: temperature 0 and a fixed seed help but do not guarantee identical text across versions or hardware.
- The benchmark measures **this** system prompt, **these** six tools and **these** 20 tasks. Results do not transfer automatically to other agent designs.
