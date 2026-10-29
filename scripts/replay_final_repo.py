#!/usr/bin/env python3
"""Rebuild the repository a model left behind and run its tests.

Usage:  python scripts/replay_final_repo.py results/logs/<session>/<model>/chain-04_1.jsonl [--fixture DIR]

It copies the fixture repository, applies the `final_diff` saved at the end of the run log, then runs
`python -m pytest -q` in the copy. Use it to tell "the model fixed it but the check was too strict"
(tests pass) from "the model did not fix it" (tests fail).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def default_fixture() -> Path:
    here = Path(__file__).resolve().parents[1]
    for candidate in (here / "src" / "toolcallbench" / "data" / "fixtures" / "repo", here / "fixtures" / "repo"):
        if candidate.is_dir():
            return candidate
    raise SystemExit("could not find the fixture repository; pass --fixture")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("log", type=Path, help="a run log (.jsonl) written by toolcallbench")
    parser.add_argument("--fixture", type=Path, help="fixture repository (default: the one shipped with the package)")
    args = parser.parse_args()

    summary = json.loads(args.log.read_text(encoding="utf-8").splitlines()[-1])
    if summary.get("type") != "summary" or "final_diff" not in summary:
        raise SystemExit("this log has no final_diff; it was written by an older version. Rerun the task with toolcallbench >= 1.0.2.")
    print(f"task {summary['task']}: recorded result = {summary['failure_type']}")
    for line in summary.get("details", []):
        print(f"  {line}")

    fixture = args.fixture or default_fixture()
    with tempfile.TemporaryDirectory(prefix="tcb-replay-") as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(fixture, repo, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
        diff = summary["final_diff"]
        if diff.strip():
            applied = subprocess.run(["patch", "-p1", "--quiet"], input=diff, text=True, cwd=repo, capture_output=True)
            if applied.returncode != 0:
                print("could not apply the saved diff:\n" + applied.stdout + applied.stderr)
                return 2
        else:
            print("the model did not change any file")
        tests = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=repo, text=True, capture_output=True)
        print(tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else tests.stderr.strip())
        print("tests PASS on the model's final repo" if tests.returncode == 0 else "tests FAIL on the model's final repo")
        return 0 if tests.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
