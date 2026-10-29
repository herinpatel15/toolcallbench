# Issue: why do edits fail, and is chain-04 caused by stale line offsets?

Reported on the dev.to post about v1.0.1 (comment).

## What was said
1. Models pass command runs because stdout feedback is immediate, but file editing needs matching indentation and exact line anchors. When small models write unified diffs, off-by-one line counts cause patch rejects that cascade into outcome mismatches.
2. For chain-04 failing across every model, check whether the harness evaluates intermediate test runs. If an agent fixes two bugs in one turn without running pytest between them, the second patch relies on stale line offsets from the first edit.

## What the code does
- `edit_file` needs `old_text` to match the file exactly. `apply_patch` needs the context and removed lines to match exactly.
- **Hunk line counts are not enforced.** `patching.py` locates each hunk by its content (it tries the stated line first, then searches). Off-by-one counts and stale offsets do not cause rejects. Only a text mismatch (for example wrong indentation) does.
- chain-04's two fixes are in different files (`catalog.py`, `fees.py`), so one edit cannot shift the other's lines.

## What the demo data shows
28 failures in the demo run (4 models, 1 run each). `patch_failed` was 3 of them (qwen3:8b 1, llama3.1:8b 2). The larger edit-related groups were `outcome_mismatch` (qwen3.5:0.8b, 5: valid calls, wrong final repo) and `wrong_args` (llama3.1:8b, 3). So a reject cascade does not explain most failures. Transcripts were not all read.

Check with your own data:
```bash
sqlite3 results/results.sqlite "select r.model, c.tool, c.error_kind, count(*) from calls c join runs r on r.id=c.run_id where c.tool in ('edit_file','apply_patch') and c.ok=0 group by 1,2,3;"
```

## Real gap found
chain-04 requires a `run_command` containing `pytest`, but the order is not enforced. A pytest run before any edit satisfies it. The final repo is still judged by running the real tests, so scores are correct, but "run the suite at the end to confirm" is not checked.

## Decision
- No code change now. Making the check stricter changes the task, so old and new results would not be comparable.
- Added to the roadmap: check that a test run happens after the last edit (chain-01 and chain-04), as a new task version.
- v1.0.2 already saves each run's final repo diff (`final_diff`) and has `scripts/replay_final_repo.py`, so chain-04 can be triaged properly. See `docs/TRIAGE_chain-04_and_timing.md`.

## Status
Documented. Roadmap item open.
