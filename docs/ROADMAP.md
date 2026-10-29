# Roadmap

Ideas are ordered by value for the owner's goal: choosing and tuning a local model for
agent work. None are promised.

## Next (v0.2)

- **Run history compare**: `toolcallbench compare SESSION_A SESSION_B` with a table of differences.
- **Confidence intervals**: show a range, not only a percentage, for each pass rate.
- **More tasks**: 40 tasks, including multi-file edits and longer chains.
- **Context stress tasks**: a large file that forces the model to use `start_line` / `end_line`.
- **Sampling variants**: run at temperature 0.0 and 0.7 and report the gap.
- **Check test runs after edits**: for tasks that say "run the tests to confirm" (chain-01, chain-04), require a test run after the last edit. Ship as a new task version so old results are not compared with new ones. See `docs/issues/edit-4-issue/ISSUE_edit-failures.md`.

## Later

- **llama.cpp direct**: tuned config for `llama-server` with `--jinja`, including grammar-constrained tool calls.
- **MLX backend** for Apple silicon.
- **Container sandbox**: run `run_command` inside a container for untrusted models.
- **Task packs**: community packs for other languages (JavaScript, Go).
- **Static HTML dashboard** with charts and per-run drill-down to the transcript.

## Not planned

- A hosted leaderboard.
- An AI judge.
