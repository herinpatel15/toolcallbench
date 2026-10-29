# Two reader questions: chain-04 and gemma's speed

A reader on dev.to read the first results post and asked two things. This note records what they said, what is true, what the code does, and what changed in v1.0.2.

## What the comment said

1. Scoring on the end state of the repo is the right call. Since all four models failed chain-04, take each model's final repo and run the shelf tests on it.
   - If some pass the tests but are marked `outcome_mismatch`, the check is too strict (it compares against one expected diff).
   - If none pass, the task is genuinely hard, or the two bugs interact.
2. gemma4:e4b is slowest per task although its tok/s is higher than the 8B models. tok/s is only the generation rate. Per-task time also depends on how many tokens are generated and on prompt processing, which grows as tool results pile up. Log `eval_count` and `prompt_eval_duration` per task.

## Question 1: chain-04

### What is true
- **The outcome check is not a diff comparison.** For chain-04 it runs `python -m pytest -q` on the final repository (`expect.command` in `tasks/chain-04.yaml`). Any valid fix passes that part. So the "too strict diff" worry does not apply to the outcome check.
- **There is a second, separate check on the tool calls** (`expect.calls`): an edit to `catalog.py`, an edit to `fees.py`, and a `run_command` containing `pytest`, with `max_calls: 10`. A model can fix the bugs and still fail this check.
- **The report's own numbers point at the call budget.** gemma4:e4b failed exactly one task in the whole run: chain-04. Its only failure type was `call_limit`. So for gemma, chain-04 was not a wrong fix and not an outcome mismatch.

### What was not known (and still is, until you run the query)
Whether the other three models also hit the limit, or really did not fix the code.

### Two details that make `call_limit` easy to misread
- `call_limit` is reported when a run hits **either** the call limit **or** the turn limit (`hit_limit` covers both).
- Three different numbers apply: the run-wide `max_calls` (12 by default), `max_turns` (10 by default), and the task's own `max_calls` (10 for chain-04). The task value overrides the command-line value in the check, so `--max-calls 20` does **not** loosen chain-04. You have to change `src/toolcallbench/data/tasks/chain-04.yaml`.
- The reference solution needs about 6 calls (run, read, read, edit, edit, run). A model that also lists the directory or searches first gets close to 10 quickly.

### A real gap the comment exposed
The runner deleted its temporary repository after each run, so "take each model's final repo" was not possible. Fixed in v1.0.2 (below).

### How to triage, step by step
1. Ask the database what happened to each model:
   ```bash
   sqlite3 results/results.sqlite \
     "select model, failure_type, outcome_ok, calls_made, turns from runs where task_id='chain-04';"
   ```
   - `call_limit` and `outcome_ok = 1`: the model fixed the code but used too many calls. The budget is too tight.
   - `call_limit` and `outcome_ok = 0`: it ran out of calls before finishing. Look at its call list in the log to see whether it wandered.
   - `outcome_mismatch` or `patch_failed`: it did not fix the code.
2. For runs made with v1.0.2 or later, rebuild what the model left behind and run the tests on it:
   ```bash
   python scripts/replay_final_repo.py results/logs/<session>/<model>/chain-04_1.jsonl
   ```
   It prints the recorded failure reason and then `tests PASS` or `tests FAIL` for the model's final repo.
   Runs from older versions have no saved diff; rerun chain-04 (`--tasks chain-04`).
3. Decide:
   - Tests pass but the run is marked failed: the check is too strict. Loosen `expect.calls` or the budget.
   - Tests fail for every model: the task is hard, or the two bugs interact. Read the transcripts.

### What to do about the task (after step 1)
Do not change the task before looking at the data. If the cause is the budget, raise `max_calls` for chain-04 (and check chain-01, which also failed for three models), note it in the changelog, and rerun. A changed task is a new task version, so old and new results should not be compared as if they were the same.

## Question 2: why is gemma slow per task?

### What is true
tok/s is generation speed only. Wall time per task = generating + reading the prompt + model load + tool execution. A model that writes more before each call, or that makes more calls so the context grows, takes longer even with a higher tok/s.

### What the tool recorded before v1.0.2
Output tokens and generation seconds per run (`eval_tokens`, `eval_seconds`). It did **not** record prompt tokens, prompt-reading time or load time. So you could see output length but not prompt cost.

### What changed in v1.0.2
- Per run, the database now stores `prompt_tokens`, `prompt_seconds` and `load_seconds` (Ollama; llama.cpp servers report prompt time if they send `timings`). Old databases are upgraded in place.
- The report has a **"Where the time went"** table: s/task, generating s, reading prompt s, loading s, output tokens, prompt tokens (medians).

### How to read it
- Large "Output tokens" for gemma: it reasons or writes a lot before each call.
- Large "Reading prompt s": the growing context is the cost.
- Large "Loading s": the model was reloaded between runs; check `keep_alive` and memory pressure.
Do not guess the cause until the table is filled from a real run.

## Suggested reply to the commenter

> Thanks, this is really useful.
>
> On chain-04: the outcome check doesn't compare against one expected diff. It runs the real test suite on the final repo, so any valid fix passes that part. There's also a separate tool-call check (edits to both files, a pytest run, max 10 calls). gemma's only failure in my whole run was a `call_limit`, so I suspect chain-04 is hitting the call budget, not a wrong fix. I haven't confirmed that for all four models yet, and I'll check each model's final repo before I change the task.
>
> On speed: agreed, tok/s is only the generation rate. The DB already stored output tokens per run; I've now added prompt tokens, prompt-reading time and load time (v1.0.2), plus a "where the time went" table in the report. I'll share the numbers after a rerun with 3 repeats.

Edit the last paragraph so it matches what you have actually published and run when you post it.

## Checklist
- [ ] Run the sqlite query above on your existing results.
- [ ] Apply the v1.0.2 patch, run the tests, publish 1.0.2.
- [ ] Rerun with `repeats: 3` (at least chain-01 and chain-04, plus the full run for the table).
- [ ] Use `replay_final_repo.py` on the chain-04 logs.
- [ ] Decide on the chain-04 budget from the data; record it in the changelog.
- [ ] Reply to the comment with the real numbers.
