# Issue: show why runs failed before the pass rate

Reported on the dev.to post about v1.0.1 (comment).

## What was said
Split the failures before the pass rate for local tool calling: wrong tool name, malformed arguments, or no call at all. Each needs a different fix, so one pass-or-fail number hides the cause.

## Is it right?
Yes. The tool already records a failure type for every failed run (13 types), but the report put the pass-rate table first and the failure table further down, so the breakdown was easy to miss. The blog and Reddit posts also led with the pass rate.

## How the 13 types map to the three cases
| Case | Failure types |
|---|---|
| Wrong tool name | `unknown_tool` (no such tool), `wrong_tool` (real tool, wrong one for the task) |
| Malformed arguments | `invalid_json`, `invalid_args`, and `wrong_args` (valid call, wrong values) |
| No call | `no_call`, and `text_tool_call` (the call is written out as text) |

Two big groups are not in those three cases: `call_limit` (over the call or turn budget) and `outcome_mismatch` / `patch_failed` (the repo ended up wrong). In the demo run (4 models, 1 run each) these were the largest: `call_limit` 7 runs, `outcome_mismatch` 5 runs.

## Fix (v1.0.3)
- The report has a "Why runs failed" section right after the summary.
- Failure types are grouped into five families: wrong tool, bad arguments, no real call, over budget, wrong result. The full per-type table follows it.
- A test makes sure every failure type belongs to exactly one family.

Files: `src/toolcallbench/report.py`, `tests/test_timing.py`, `docs/USER_GUIDE.md`, `CHANGELOG.md`.

## Status
Fixed in v1.0.3. Reply to the commenter once 1.0.3 is on PyPI.
