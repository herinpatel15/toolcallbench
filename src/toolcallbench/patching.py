"""Minimal unified-diff applier used by the apply_patch tool.

Context and removed lines must match the file exactly. The line counts in hunk
headers are not enforced, and trailing blank lines at the end of the patch text
are ignored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(Exception):
    """The patch is malformed or does not match the file."""


@dataclass
class Hunk:
    old_start: int
    lines: list[tuple[str, str]] = field(default_factory=list)  # (marker, text)


@dataclass
class FilePatch:
    path: str
    hunks: list[Hunk] = field(default_factory=list)


def _clean_path(path: str) -> str:
    path = path.split("\t")[0].strip()
    if path in ("/dev/null", "dev/null"):
        raise PatchError("creating or deleting files with a patch is not supported")
    if path.startswith(("a/", "b/")):
        path = path[2:]
    return path


def parse_patch(text: str) -> list[FilePatch]:
    lines = text.replace("\r\n", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    patches: list[FilePatch] = []
    current: FilePatch | None = None
    hunk: Hunk | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            current = FilePatch(path=_clean_path(lines[i + 1][4:]))
            patches.append(current)
            hunk = None
            i += 2
            continue
        match = HUNK_RE.match(line)
        if match:
            if current is None:
                raise PatchError("found a @@ hunk before any ---/+++ file header")
            hunk = Hunk(old_start=int(match.group(1)))
            current.hunks.append(hunk)
        elif hunk is not None:
            if line.startswith("\\"):
                pass  # "\ No newline at end of file"
            elif line[:1] in (" ", "-", "+"):
                hunk.lines.append((line[0], line[1:]))
            elif line == "":
                hunk.lines.append((" ", ""))  # a blank context line whose space was stripped
        i += 1
    if not patches:
        raise PatchError("no ---/+++ file headers found; expected a unified diff")
    for patch in patches:
        if not patch.hunks:
            raise PatchError(f"no @@ hunks found for {patch.path}")
    return patches


def _locate(file_lines: list[str], old: list[str], guess: int) -> int | None:
    if not old:
        return max(0, min(guess, len(file_lines)))
    size = len(old)
    candidates = [i for i in range(len(file_lines) - size + 1) if file_lines[i : i + size] == old]
    if not candidates:
        return None
    return min(candidates, key=lambda i: abs(i - guess))


def apply_hunks(original: str, hunks: list[Hunk], path: str) -> str:
    had_newline = original.endswith("\n")
    file_lines = original.split("\n")
    if had_newline:
        file_lines.pop()
    offset = 0
    for number, hunk in enumerate(hunks, 1):
        old = [text for marker, text in hunk.lines if marker in (" ", "-")]
        new = [text for marker, text in hunk.lines if marker in (" ", "+")]
        if not any(marker in ("+", "-") for marker, _ in hunk.lines):
            raise PatchError(f"hunk {number} for {path} changes nothing")
        guess = (hunk.old_start - 1 + offset) if old else (hunk.old_start + offset)
        position = _locate(file_lines, old, guess)
        if position is None:
            raise PatchError(
                f"hunk {number} does not match {path}: the context or removed lines differ from the file"
            )
        file_lines[position : position + len(old)] = new
        offset += len(new) - len(old)
    result = "\n".join(file_lines)
    return result + "\n" if had_newline else result


def apply_unified_diff(text: str, resolve: Callable[[str], Path]) -> list[str]:
    """Apply a unified diff. `resolve` maps a patch path to a safe absolute path or raises PatchError.

    All files are computed before any is written, so a bad hunk never leaves a half-applied patch.
    """
    patches = parse_patch(text)
    updates: list[tuple[Path, str, str]] = []
    for patch in patches:
        target = resolve(patch.path)
        if not target.is_file():
            raise PatchError(f"file not found: {patch.path}")
        original = target.read_text(encoding="utf-8")
        updates.append((target, apply_hunks(original, patch.hunks, patch.path), patch.path))
    messages = []
    for target, new_text, shown in updates:
        target.write_text(new_text, encoding="utf-8")
        messages.append(f"patched {shown}")
    return messages
