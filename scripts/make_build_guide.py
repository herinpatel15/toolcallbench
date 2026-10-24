#!/usr/bin/env python3
"""Build BUILD_FROM_SCRATCH.md from docs/guide/BUILD_FROM_SCRATCH.template.md.

The template contains three kinds of directive, each alone on a line:

    {{file:PATH}}   embed a repository file (code can never differ from the repo)
    {{cmd:COMMAND}} run COMMAND in a clean copy of the repo and embed its real output
    {{tree}}        embed the list of embedded files

`scripts/verify_build_guide.py` extracts the embedded files into an empty folder and runs the tests there.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "guide" / "BUILD_FROM_SCRATCH.template.md"
OUTPUT = ROOT / "BUILD_FROM_SCRATCH.md"

LANGUAGES = {".py": "python", ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".toml": "toml", ".sh": "bash",
             ".md": "markdown", ".csv": "text", ".ini": "ini", ".gitignore": "text"}
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".venv", "results", "results-smoke", "results-demo", ".git", "build"}
MARKER = re.compile(r"^<!-- file: (?P<path>.+?) -->$")


def collect_files() -> list[str]:
    """Repository files that the guide teaches the reader to create, as sorted relative POSIX paths."""
    found: set[str] = set()
    for name in ("pyproject.toml", ".gitignore", "Makefile", "README.md", ".github/workflows/ci.yml"):
        if (ROOT / name).is_file():
            found.add(name)
    for folder, pattern in (("src", "*.py"), ("tests", "*.py"), ("scripts", "*")):
        for path in (ROOT / folder).rglob(pattern):
            if path.is_file() and not SKIP_PARTS & set(path.relative_to(ROOT).parts) and "egg-info" not in str(path):
                found.add(path.relative_to(ROOT).as_posix())
    for path in (ROOT / "src" / "toolcallbench" / "data").rglob("*"):
        if path.is_file() and not SKIP_PARTS & set(path.relative_to(ROOT).parts):
            found.add(path.relative_to(ROOT).as_posix())
    return sorted(found)


def fence_for(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def embed_file(rel: str) -> str:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise SystemExit(f"{rel} must end with exactly one newline")
    language = LANGUAGES.get(path.suffix) or LANGUAGES.get(path.name, "text")
    fence = fence_for(text)
    return f"<!-- file: {rel} -->\n**`{rel}`**\n\n{fence}{language}\n{text.rstrip(chr(10))}\n{fence}"


def normalize(output: str, workdir: str) -> str:
    output = output.replace(workdir, ".")
    output = re.sub(r"\bin \d+\.\d+s\b", "in N.NNs", output)
    output = re.sub(r"\b\d+\.\d+s\b", "N.Ns", output)
    output = re.sub(r"\b\d{8}-\d{6}\b", "YYYYMMDD-HHMMSS", output)
    return "\n".join(line.rstrip() for line in output.strip("\n").splitlines())


def make_workdir() -> str:
    tmp = tempfile.mkdtemp(prefix="tcb-guide-")
    target = Path(tmp) / "proj"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(*SKIP_PARTS, "*.egg-info", "__pycache__"))
    return str(target)


def run_cmd(command: str, workdir: str) -> str:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": "-p no:cacheprovider", "NO_COLOR": "1"}
    proc = subprocess.run(command, shell=True, cwd=workdir, capture_output=True, text=True, env=env, timeout=600)
    body = normalize(proc.stdout + proc.stderr, workdir)
    status = "" if proc.returncode == 0 else f"\n[exit code {proc.returncode}]"
    return f"```text\n$ {command}\n{body}{status}\n```"


def build() -> str:
    workdir = make_workdir()
    try:
        out = []
        for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
            m = re.fullmatch(r"\{\{(file|cmd|tree):?(.*)\}\}", line.strip())
            if not m:
                out.append(line)
            elif m.group(1) == "file":
                out.append(embed_file(m.group(2)))
            elif m.group(1) == "cmd":
                out.append(run_cmd(m.group(2), workdir))
            else:
                out.append("```text\n" + "\n".join(collect_files()) + "\n```")
        return "\n".join(out) + "\n"
    finally:
        shutil.rmtree(Path(workdir).parent, ignore_errors=True)


def main() -> int:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
