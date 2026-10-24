# Contributing

## Set up

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test
```

## Add a task

1. Copy a file in `src/toolcallbench/data/tasks/` and change the id (`group-NN`).
2. Write the prompt, the `expect` block and a `reference` solution.
3. `toolcallbench validate-tasks --tasks your-id` must pass.
4. `python scripts/make_task_catalog.py` to refresh `docs/TASK_CATALOG.md`.
5. If the fixture repository changed, update tests in `tests/` that depend on it (for example the failing-test count in `doctor`).

Rules for good tasks: one clear goal, an outcome that code can check, a prompt that does not
leak the answer, and a reference that uses the fewest calls a sensible model would make.

## Change the checker

Add a scripted profile or a hand-built transcript in `tests/test_checks.py` that shows the
new behavior, and update `docs/TECH_SPEC.md` section 4 in the same change.

## Style

- Python 3.10+, type hints, short functions, standard library first.
- Error messages say what to do next.
- No new runtime dependency without a decision record in `docs/DECISIONS.md`.

## Before you open a pull request

```bash
make check      # tests, task validation, generated docs are current
```
