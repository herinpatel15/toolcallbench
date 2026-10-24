# User guide

## Install

```bash
git clone <your repo> toolcallbench && cd toolcallbench
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Check the install without any model:

```bash
toolcallbench validate-tasks      # 20/20 reference solutions pass
python -m pytest                  # full test suite
toolcallbench run --backend scripted --repeats 1    # whole pipeline with a fake model
```

## Run on your Mac with Ollama

1. Install Ollama from <https://ollama.com> and **quit the menu-bar app** (so it does not hold the port with default settings).
2. Terminal 1: `./scripts/serve_ollama.sh`
3. Terminal 2: pull the models, then check:

```bash
ollama pull qwen3:8b
toolcallbench doctor --model qwen3:8b --probe
```

`--probe` runs one real task. If it fails, read the message before going further.

4. Run:

```bash
toolcallbench run --config configs/m4-16gb.yaml
```

Or a single model with options:

```bash
toolcallbench run --model qwen3:8b --think off --repeats 3 --kv-cache-type q8_0 --flash-attention
```

5. Open `results/reports/<session>.html`.

## Commands

| Command | Purpose |
| --- | --- |
| `list-tasks [--markdown]` | Show the 20 tasks |
| `validate-tasks [--tasks ids] [--groups names]` | Replay reference solutions |
| `doctor [--model NAME] [--probe] [--backend K] [--host URL]` | Check setup; probe a model |
| `run` | Run the benchmark; key options below |
| `report [--session ID] [--print]` | Rebuild a report from stored results |
| `sessions` | List stored sessions |

Key `run` options: `--config FILE`, `--backend ollama|openai-compat|scripted`, `--host URL`,
`--model NAME` (repeat for several), `--think on|off`, `--num-ctx N`, `--temperature X`,
`--seed N`, `--repeats N`, `--max-calls N`, `--max-turns N`, `--tasks ids`, `--groups names`,
`--session ID`, `--resume`, `--kv-cache-type`, `--flash-attention`, `--fixture PATH`.

## Reading the report

- **Settings** table: compare two reports only if these match.
- **Summary**: pass rate overall and per group, median tokens per second, median seconds per task, and calls versus the reference (1.00 is ideal; 2.00 means twice as many calls).
- **Errors**: runs where the server failed. They are not in the pass rate.
- **Failure types**: why runs failed. A model with many `invalid_json` failures has a formatting problem; many `no_call` means it answers from memory instead of using tools; many `outcome_mismatch` means it calls tools but reaches wrong results.
- **Per-task results**: cells are passed/scored. With 3 repeats, `1/3` is a flaky task, not a hard failure.

## Compare quantization levels

```bash
ollama pull qwen3:8b-q4_K_M && ollama pull qwen3:8b-q8_0
toolcallbench run --config configs/quant-sweep-qwen3-8b.yaml
```

Check the tag names on the model's Ollama page first; names change between releases.

## Resume

If a run stops (Ctrl+C, sleep, crash), run the same command with `--session NAME --resume`.
Without `--session`, the id is the start time, so look it up with `toolcallbench sessions`.

## Use your own repository

```bash
toolcallbench run --fixture ~/code/my-project-copy --tasks-dir my-tasks --model qwen3:8b
```

Copy the project first and remove secrets (see `SECURITY.md`). Write tasks in
`my-tasks/*.yaml` using the format in `TECH_SPEC.md`, then run `validate-tasks` with the same
`--fixture` and `--tasks-dir` to prove each task is passable.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `cannot reach http://localhost:11434` | Start the server: `./scripts/serve_ollama.sh` |
| `model 'x' is not installed` | `ollama pull x` |
| `doctor` says the model does not report tool support | Choose a model whose Ollama page lists "tools" |
| Every run fails with `no_call` | The model may not support tools, or the template is wrong; check `doctor --probe` |
| Very slow runs with Qwen3 | Add `--think off` (or `think: false` for that model in the config file) |
| `HTTP 400 ... does not support thinking` | That model has no thinking mode; remove `--think`, and set `think` only on models that have it (per model in the config file) |
| Mac becomes slow, fans loud | Lower `--num-ctx` to 8192, use a smaller model, close other apps; see `MODEL_GUIDE_M4_16GB.md` |
| `fixture repo: 0 failing test(s)` in doctor | The fixture was modified; restore `fixtures/repo` |
| Session exists | Add `--resume` or choose a new `--session` |
