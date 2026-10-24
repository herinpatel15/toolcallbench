# Architecture decision records

Short records of choices that shaped the design. Each one says what was decided, why, and
what it costs.

## ADR-001: Score with code, not with an AI judge

- **Decision:** Every verdict comes from deterministic checks on the transcript and on the final repository state.
- **Why:** A judge model adds its own errors, costs memory on a 16 GB Mac, and makes runs hard to repeat.
- **Cost:** Tasks need precise expectations, and answers are matched by substring or regular expression, which can miss a correct answer in unexpected wording. Reports show per-task cells so such cases are visible.

## ADR-002: A pass needs Parse, Tool and Outcome; Args is reported only

- **Decision:** Wrong argument *values* do not fail a run on their own if the outcome is right.
- **Why:** Two valid approaches (one `read_file` call or two ranges) should both pass. What matters to an agent is that the repository and the answer are right.
- **Cost:** A model can pass by luck with unusual arguments. The Args column and the efficiency ratio expose this.

## ADR-003: Every task has a reference solution

- **Decision:** Each task file contains a solution that is replayed through the real tools and checker (`validate-tasks`).
- **Why:** A task nobody can pass tells you nothing. This also tests the checker against each task.
- **Cost:** Writing a task takes longer.

## ADR-004: Scripted failure profiles

- **Decision:** A fake backend can imitate seven failure behaviors.
- **Why:** The checker is the part that must be right. Profiles prove each failure type is detected without needing a real model to fail on purpose.
- **Cost:** Profiles only cover failures we thought of.

## ADR-005: Standard library HTTP, two small dependencies

- **Decision:** Use `urllib` for HTTP and depend only on PyYAML and jsonschema.
- **Why:** Fewer things to install and break; the Ollama API is simple JSON over HTTP.
- **Cost:** No streaming and no connection pooling. Both are unnecessary for this workload.

## ADR-006: Non-streaming requests

- **Decision:** `stream: false` for every request.
- **Why:** Tool calls arrive complete, and `eval_count` / `eval_duration` give exact speed.
- **Cost:** No live progress inside a single request; the CLI prints one line per run instead.

## ADR-007: Default context 16384 on 16 GB

- **Decision:** `num_ctx = 16384`, KV cache `q8_0` recommended.
- **Why:** About 12 GB can be used by the GPU on a 16 GB Mac. An 8B model at Q4 takes about 5 GB; 16k of context adds a little over 1 GB with a `q8_0` cache. That leaves room for macOS and a browser. Ollama's own default is only 4k, which can truncate multi-step tool conversations.
- **Cost:** Tasks stay short. Long-context behavior is not tested.

## ADR-008: Set server options outside the API; record them as "declared"

- **Decision:** KV cache type and flash attention are server environment variables, so the benchmark cannot set them; the user declares them with flags or in the config and they are printed in the report.
- **Why:** Honest reporting. Two reports with different KV cache types should not be compared as if they were equal.
- **Cost:** The user can declare something untrue. The report says "declared".

## ADR-009: SQLite plus JSONL

- **Decision:** Results in one SQLite file; full transcripts as JSONL files.
- **Why:** SQL makes the report simple, the file is portable, and `UNIQUE` constraints make resume safe. JSONL transcripts are easy to read and to grep.
- **Cost:** No concurrent writers (one benchmark process at a time).

## ADR-010: Fresh copy of the fixture repository per run

- **Decision:** `shutil.copytree` into a temp folder for each run.
- **Why:** Runs cannot affect each other or the original, and edits can be checked afterwards.
- **Cost:** About 10 ms per run; irrelevant next to model time.

## ADR-011: Backend errors are not model failures

- **Decision:** Server errors are stored as `status=error` and excluded from pass rates; three in a row stop that model.
- **Why:** A crashed server must not look like a bad model.
- **Cost:** The report needs an Errors column.
