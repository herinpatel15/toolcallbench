# Roadmap

Ideas are ordered by value for the owner's goal: choosing and tuning a local model for
agent work. None are promised.

## Delivered in 1.1.0

Run history compare, pass-rate ranges, JSON/CSV export, nested-argument tasks, one-call-per-turn
and tools-offered ablations, test-run-after-edit check, hosted API keys. See `CHANGELOG.md`.

## Next

- **More tasks**: grow from 24 to about 40, with longer chains and more multi-file edits.
- **Context stress tasks**: a large file that forces the model to use `start_line` / `end_line`.
- **Sampling variants**: run at temperature 0.0 and 0.7 and report the gap.
- **Static HTML charts** with per-run drill-down to the transcript.

## Later

- **llama.cpp direct**: tuned config for `llama-server` with `--jinja`, including grammar-constrained tool calls.
- **MLX backend** for Apple silicon.
- **Container sandbox**: run `run_command` inside a container for untrusted models.
- **Task packs**: community packs for other languages (JavaScript, Go).

## Not planned

- A hosted leaderboard.
- An AI judge.
