#!/usr/bin/env python3
"""Prove that BUILD_FROM_SCRATCH.md is complete.

1. Extract every `<!-- file: PATH -->` block into an empty folder.
2. Check that the set of files and their contents equal the repository.
3. Create a virtual environment there, install the package and run validate-tasks and the tests.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_build_guide import MARKER, OUTPUT, ROOT, collect_files  # noqa: E402


def extract(guide: Path, target: Path) -> dict[str, str]:
    lines = guide.read_text(encoding="utf-8").splitlines()
    files: dict[str, str] = {}
    i = 0
    while i < len(lines):
        m = MARKER.match(lines[i])
        i += 1
        if not m:
            continue
        path = m.group("path")
        while not re.match(r"^`{3,}\S*$", lines[i]):
            i += 1
        fence = re.match(r"^(`{3,})", lines[i]).group(1)
        i += 1
        body = []
        while lines[i] != fence:
            body.append(lines[i])
            i += 1
        i += 1
        if path in files:
            raise SystemExit(f"file embedded twice: {path}")
        files[path] = "\n".join(body) + "\n"
        out = target / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(files[path], encoding="utf-8")
    return files


def run(cmd: list[str], cwd: Path) -> None:
    print("$", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd)
    if proc.returncode != 0:
        raise SystemExit(f"command failed with exit code {proc.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="do not delete the extracted folder")
    args = parser.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="tcb-verify-"))
    target = tmp / "toolcallbench"
    target.mkdir()
    files = extract(OUTPUT, target)
    expected = set(collect_files())
    if set(files) != expected:
        raise SystemExit(f"file sets differ.\n  only in guide: {sorted(set(files) - expected)}\n  only in repo: {sorted(expected - set(files))}")
    for rel, text in files.items():
        if (ROOT / rel).read_text(encoding="utf-8") != text:
            raise SystemExit(f"content differs from the repository: {rel}")
    print(f"{len(files)} files extracted and identical to the repository")
    run([sys.executable, "-m", "venv", ".venv"], target)
    py = str(target / ".venv" / "bin" / "python")
    run([py, "-m", "pip", "install", "-q", "-e", ".[dev]"], target)
    run([py, "scripts/make_task_catalog.py"], target)
    run([py, "-m", "toolcallbench", "validate-tasks"], target)
    run([py, "-m", "pytest"], target)
    print(f"\nOK: the guide rebuilds a working project ({target})")
    if not args.keep:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
