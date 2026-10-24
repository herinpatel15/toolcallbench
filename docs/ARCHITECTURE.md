# Architecture

ToolCallBench is a single Python program that talks to a model server over HTTP. It has no
web server, no background service and no cloud dependency. This document shows the system
from five angles: context, components, data flow, run sequence, and storage.

## 1. System context

```mermaid
flowchart LR
    user([You, on a MacBook M4 16 GB])
    subgraph mac[Your Mac]
        cli[toolcallbench CLI]
        server[Model server<br/>Ollama or llama-server]
        files[(results/<br/>SQLite, JSONL, reports)]
        repo[fixtures/repo<br/>sample project]
        tasks[tasks/*.yaml<br/>20 tasks]
    end
    user -->|run, report| cli
    cli -->|HTTP chat + tools| server
    cli -->|reads| tasks
    cli -->|copies for every run| repo
    cli -->|writes| files
    user -->|reads report| files
```

Everything stays on the Mac. The only network traffic is `localhost` HTTP to the model server.

## 2. Components

```mermaid
flowchart TB
    cli[cli.py<br/>commands, config merge]
    cfg[config.py<br/>RunConfig, ModelSpec]
    tsk[tasks.py<br/>load + validate YAML]
    run[runner.py<br/>conversation loop]
    be[backends/<br/>ollama, openai_compat, scripted]
    tools[tools.py<br/>6 tool specs, validation, sandbox executor]
    patch[patching.py<br/>unified diff applier]
    chk[checks.py<br/>deterministic scoring]
    st[store.py<br/>SQLite + JSONL]
    rep[report.py<br/>Markdown + HTML]
    mod[models.py<br/>dataclasses]

    cli --> cfg
    cli --> tsk
    cli --> run
    cli --> st
    cli --> rep
    run --> be
    run --> tools
    run --> chk
    tools --> patch
    chk --> tools
    st --> run
    rep --> st
    run --> mod
    chk --> mod
```

| Module | Responsibility | Knows about |
| --- | --- | --- |
| `cli.py` | Parse arguments, merge config file and flags, drive a session | everything |
| `config.py` | Defaults and YAML config loading | nothing else |
| `tasks.py` | Load task files, validate them against a JSON Schema | `models` |
| `runner.py` | Run one task: talk to the backend, execute tool calls, then score | backends, tools, checks |
| `backends/` | One class per server type; return a uniform `BackendResponse` | `models` |
| `tools.py` | Tool JSON schemas, argument validation, sandboxed execution | `patching` |
| `checks.py` | Turn a transcript and the final repo state into a verdict | `tools` (to run check commands) |
| `store.py` | Persist sessions, runs and calls; write transcripts | `runner` (for `RunRecord`) |
| `report.py` | Aggregate runs and render Markdown and HTML | `store`, `checks` |

## 3. Data flow

```mermaid
flowchart LR
    y[tasks/*.yaml] -->|load_tasks| T[Task objects]
    T --> R[run_once]
    F[fixtures/repo] -->|copytree| W[temp working copy]
    R -->|messages + tool specs| B[Backend]
    B -->|assistant message,<br/>tool calls| R
    R -->|raw call| V[validate_arguments]
    V -->|valid| X[ToolExecutor on W]
    V -->|invalid| E[error text to model]
    X -->|result text| R
    E --> R
    R -->|Transcript + W| C[evaluate]
    C -->|CheckResult| S[(SQLite runs, calls)]
    R -->|messages| L[(JSONL transcript)]
    S --> P[report.py]
    P --> M[report.md + report.html]
```

Key point: the model never touches your real files. Every run gets a new copy of
`fixtures/repo`, and the copy is deleted after scoring.

## 4. Sequence of one run

```mermaid
sequenceDiagram
    autonumber
    participant CLI as cli.cmd_run
    participant RUN as runner.run_once
    participant BE as Backend (Ollama)
    participant TL as ToolExecutor
    participant CK as checks.evaluate
    participant DB as Store

    CLI->>RUN: task, backend, fixture dir
    RUN->>RUN: copy fixture to temp dir
    loop until the model answers, or a limit is hit
        RUN->>BE: chat(messages, tool specs)
        BE-->>RUN: content + tool calls + eval_count/eval_duration
        alt no tool calls
            RUN->>RUN: final answer saved, stop
        else tool calls present
            loop each call
                RUN->>TL: validate, then execute
                TL-->>RUN: ok flag + result text
                RUN->>RUN: append role=tool message
            end
        end
    end
    RUN->>CK: transcript, temp dir
    CK->>CK: run check commands in temp dir
    CK-->>RUN: CheckResult
    RUN-->>CLI: RunRecord
    CLI->>DB: add_run + JSONL log
    Note over RUN: temp dir removed here
```

If the backend raises `BackendError` (server down, HTTP error), the run is stored with
status `error` and is **not** counted as a model failure.

## 5. Run state machine

```mermaid
stateDiagram-v2
    [*] --> Prepared: copy fixture
    Prepared --> Talking: send prompt
    Talking --> Executing: model returned tool calls
    Executing --> Talking: results sent back
    Talking --> Answered: reply without tool calls
    Executing --> LimitHit: call or turn limit
    Talking --> LimitHit: turn limit
    Talking --> BackendError: server failed
    Answered --> Scored
    LimitHit --> Scored
    BackendError --> [*]: stored as error
    Scored --> [*]: stored as pass or fail
```

## 6. Storage model

```mermaid
erDiagram
    SESSIONS ||--o{ RUNS : contains
    RUNS ||--o{ CALLS : made
    SESSIONS {
        text session_id PK
        text started_at
        text finished_at
        text settings_json
    }
    RUNS {
        int id PK
        text session_id FK
        text model
        text quant
        text task_id
        int repeat
        text status
        int passed
        text failure_type
        real efficiency
        real tok_per_s
        text log_path
    }
    CALLS {
        int run_id FK
        int idx
        int turn
        text tool
        text arguments_json
        int valid
        int ok
        text error_kind
    }
```

`UNIQUE (session_id, model, task_id, repeat)` on `runs` is what makes `--resume` safe: a run
that is already stored is skipped and can never be stored twice.

## 7. Deployment on a MacBook M4 with 16 GB

```mermaid
flowchart LR
    subgraph terminal1[Terminal 1]
        o[scripts/serve_ollama.sh<br/>ollama serve]
    end
    subgraph terminal2[Terminal 2]
        t[toolcallbench run<br/>.venv Python]
    end
    subgraph memory[16 GB unified memory]
        m[Model weights ~5 GB<br/>KV cache ~1-2 GB<br/>macOS and apps]
    end
    t -- "http://localhost:11434" --> o
    o --- m
```

One model is loaded at a time (`OLLAMA_MAX_LOADED_MODELS=1`). When the benchmark moves to the
next model, Ollama unloads the old one. See `MODEL_GUIDE_M4_16GB.md` for the budget.

## 8. Extension points

| To add | Touch |
| --- | --- |
| A new task | one YAML file in `tasks/`; run `validate-tasks` |
| A new tool | `tools.py` (spec + handler), the system prompt if needed, tests |
| A new backend | a class in `backends/`, one line in `make_backend` |
| A new failure type | `checks.py`, `FAILURE_TYPES`, `TECH_SPEC.md`, a scripted profile and a test |
| Your own repository | pass `--fixture PATH` and write tasks for it |
