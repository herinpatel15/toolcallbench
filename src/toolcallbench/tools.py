"""The tools offered to the model, their JSON schemas, and a sandboxed executor.

Six core tools are offered on every task. Two extra tools take nested arguments (a list of objects);
they are offered only to tasks that ask for them, so the core results stay comparable.

The executor works inside one directory (a fresh copy of the fixture repo). It is
a safety net against accidents, not a security boundary: see docs/SECURITY.md.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .patching import PatchError, apply_unified_diff

IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".git"}
ALLOWED_COMMANDS = {"python", "python3", "pytest", "ls", "cat", "echo", "grep", "head", "tail", "wc", "touch", "mkdir"}


def _spec(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


TOOL_SPECS: list[dict[str, Any]] = [
    _spec(
        "read_file",
        "Read a text file in the repository. Output lines are prefixed with their line number. "
        "Use start_line and end_line (1-based, inclusive) to read only part of a file.",
        {
            "path": {"type": "string", "description": "File path relative to the repository root"},
            "start_line": {"type": "integer", "minimum": 1, "description": "First line to read"},
            "end_line": {"type": "integer", "minimum": 1, "description": "Last line to read"},
        },
        ["path"],
    ),
    _spec(
        "list_dir",
        "List the files and folders in a directory. Folder names end with a slash.",
        {"path": {"type": "string", "description": "Directory path relative to the repository root; default is the root"}},
        [],
    ),
    _spec(
        "grep",
        "Search files for a regular expression. Returns up to 50 matches as path:line:text.",
        {
            "pattern": {"type": "string", "description": "Regular expression to search for"},
            "path": {"type": "string", "description": "File or directory to search; default is the whole repository"},
        },
        ["pattern"],
    ),
    _spec(
        "edit_file",
        "Replace text in a file. old_text must match the file exactly once, including whitespace "
        "and without any line-number prefix.",
        {
            "path": {"type": "string", "description": "File path relative to the repository root"},
            "old_text": {"type": "string", "description": "Exact text to replace; must occur exactly once"},
            "new_text": {"type": "string", "description": "Replacement text"},
        },
        ["path", "old_text", "new_text"],
    ),
    _spec(
        "apply_patch",
        "Apply a unified diff to existing files. The diff needs --- and +++ file headers and @@ hunks; "
        "context and removed lines must match the file exactly.",
        {"patch": {"type": "string", "description": "The unified diff text"}},
        ["patch"],
    ),
    _spec(
        "run_command",
        "Run one command in the repository root without a shell (no pipes or redirects). "
        "Allowed programs: " + ", ".join(sorted(ALLOWED_COMMANDS)) + ". "
        "Python may run only a .py script inside the repository or `-m pytest`. "
        "Returns the exit code, stdout and stderr.",
        {"command": {"type": "string", "description": "The command line, for example: python -m pytest -q"}},
        ["command"],
    ),
]

# Extra tools with nested arguments (an array of objects). Offered only to tasks that list them in `extra_tools`.
EXTRA_TOOL_SPECS: list[dict[str, Any]] = [
    _spec(
        "apply_edits",
        "Make several exact-text replacements, possibly in different files, in one call. Each edit needs path, "
        "old_text and new_text; old_text must match its file exactly once. Either every edit is applied or none is.",
        {
            "edits": {
                "type": "array",
                "minItems": 1,
                "description": "The replacements to make, in order",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path relative to the repository root"},
                        "old_text": {"type": "string", "description": "Exact text to replace; must occur exactly once"},
                        "new_text": {"type": "string", "description": "Replacement text"},
                    },
                    "required": ["path", "old_text", "new_text"],
                    "additionalProperties": False,
                },
            }
        },
        ["edits"],
    ),
    _spec(
        "set_json_values",
        "Set values in a JSON file. Each update gives key_path (the keys from the top of the file down to the value, "
        "as a list of strings) and the new value. The keys must already exist.",
        {
            "path": {"type": "string", "description": "JSON file path relative to the repository root"},
            "updates": {
                "type": "array",
                "minItems": 1,
                "description": "The values to set",
                "items": {
                    "type": "object",
                    "properties": {
                        "key_path": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                        "value": {"type": ["string", "number", "boolean", "null"]},
                    },
                    "required": ["key_path", "value"],
                    "additionalProperties": False,
                },
            },
        },
        ["path", "updates"],
    ),
]

TOOL_NAMES = [spec["function"]["name"] for spec in TOOL_SPECS]  # the six core tools
EXTRA_TOOL_NAMES = [spec["function"]["name"] for spec in EXTRA_TOOL_SPECS]
ALL_TOOL_NAMES = TOOL_NAMES + EXTRA_TOOL_NAMES
EDIT_TOOL_NAMES = {"edit_file", "apply_patch", "apply_edits", "set_json_values"}
_VALIDATORS = {
    spec["function"]["name"]: Draft202012Validator(spec["function"]["parameters"]) for spec in TOOL_SPECS + EXTRA_TOOL_SPECS
}
TOOLS_OFFERED_MODES = ("all", "task")


def tool_specs_for(task: Any, mode: str = "all") -> list[dict[str, Any]]:
    """The tools to offer for one task.

    "all": the six core tools plus the task's extra tools (the default).
    "task": only the tools the task's reference solution uses. This is an ablation that shows how much
    of the difficulty is choosing a tool; it gives the model a hint.
    """
    if mode not in TOOLS_OFFERED_MODES:
        raise ValueError(f"unknown tools-offered mode '{mode}'; choose from {', '.join(TOOLS_OFFERED_MODES)}")
    by_name = {spec["function"]["name"]: spec for spec in TOOL_SPECS + EXTRA_TOOL_SPECS}
    if mode == "task":
        used = {c["tool"] for step in task.reference for c in step.get("calls", [])}
        names = [n for n in ALL_TOOL_NAMES if n in used]
        if not names:  # a task that needs no tool still gets the core tools, so a wrong call can be seen
            names = list(TOOL_NAMES)
    else:
        names = TOOL_NAMES + [n for n in task.extra_tools if n in by_name]
    return [by_name[n] for n in names]


def validate_arguments(name: str, arguments: Any, allowed: list[str] | None = None) -> tuple[dict[str, Any] | None, str, str]:
    """Check a raw tool call. Returns (arguments, error_kind, message); error_kind is "" when valid.

    `allowed` lists the tools offered to the model for this task (default: the six core tools).
    """
    offered = TOOL_NAMES if allowed is None else allowed
    if name not in _VALIDATORS or name not in offered:
        return None, "unknown_tool", f"unknown tool '{name}'; available tools: {', '.join(offered)}"
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            return None, "invalid_json", f"arguments are not valid JSON: {exc.msg}"
    if not isinstance(arguments, dict):
        return None, "invalid_json", "arguments must be a JSON object"
    errors = sorted(_VALIDATORS[name].iter_errors(arguments), key=lambda e: [str(p) for p in e.path])
    if errors:
        return None, "invalid_args", errors[0].message
    return arguments, "", ""


class ToolError(Exception):
    """A tool could not do what was asked; the message goes back to the model."""


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[output truncated after {limit} characters]"


def run_trusted(argv: list[str], cwd: Path, timeout: float = 30.0) -> subprocess.CompletedProcess:
    """Run a command that the benchmark itself defines (checks, reference commands). `python` maps to this interpreter."""
    argv = list(argv)
    if argv and argv[0] in ("python", "python3"):
        argv[0] = sys.executable
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(cwd),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


class ToolExecutor:
    def __init__(self, root: Path, command_timeout: float = 20.0, max_output: int = 6000):
        self.root = Path(root).resolve()
        self.command_timeout = command_timeout
        self.max_output = max_output
        self._handlers = {
            "read_file": self._read_file,
            "list_dir": self._list_dir,
            "grep": self._grep,
            "edit_file": self._edit_file,
            "apply_patch": self._apply_patch,
            "run_command": self._run_command,
            "apply_edits": self._apply_edits,
            "set_json_values": self._set_json_values,
        }

    # ------------------------------------------------------------------ public

    def execute(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Run a validated call. Returns (ok, text). Failures become 'error: ...' text for the model."""
        try:
            return True, clip(self._handlers[name](**arguments), self.max_output)
        except (ToolError, PatchError) as exc:
            return False, f"error: {exc}"
        except (OSError, UnicodeError) as exc:
            return False, f"error: {exc.__class__.__name__}: {exc}"

    # ----------------------------------------------------------------- helpers

    def _resolve(self, path: str) -> Path:
        candidate = (self.root / path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ToolError(f"path '{path}' is outside the repository")
        return candidate

    def _resolve_for_patch(self, path: str) -> Path:
        try:
            return self._resolve(path)
        except ToolError as exc:
            raise PatchError(str(exc)) from exc

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    @staticmethod
    def _check_args(args: list[str]) -> None:
        for arg in args:
            value = arg.split("=", 1)[1] if arg.startswith("-") and "=" in arg else arg
            if arg.startswith("-") and "=" not in arg:
                continue
            if value.startswith(("/", "~")) or ".." in Path(value).parts:
                raise ToolError(f"argument '{arg}' points outside the repository")

    # ------------------------------------------------------------------- tools

    def _read_file(self, path: str, start_line: int | None = None, end_line: int | None = None) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"file not found: {path}")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = 1 if start_line is None else start_line
        end = len(lines) if end_line is None else end_line
        if end < start:
            raise ToolError("end_line must not be smaller than start_line")
        if lines and start > len(lines):
            raise ToolError(f"start_line {start} is beyond the end of the file ({len(lines)} lines)")
        selected = lines[start - 1 : end]
        if not selected:
            return "(empty file)"
        return "\n".join(f"{number:>4}| {text}" for number, text in enumerate(selected, start))

    def _list_dir(self, path: str = ".") -> str:
        target = self._resolve(path)
        if not target.is_dir():
            raise ToolError(f"directory not found: {path}")
        entries = sorted(p for p in target.iterdir() if p.name not in IGNORED_NAMES)
        if not entries:
            return "(empty directory)"
        return "\n".join(p.name + ("/" if p.is_dir() else "") for p in entries)

    def _grep(self, pattern: str, path: str = ".") -> str:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ToolError(f"invalid regular expression: {exc}") from exc
        target = self._resolve(path)
        if not target.exists():
            raise ToolError(f"path not found: {path}")
        if target.is_file():
            files = [target]
        else:
            files = []
            for current, dirs, names in os.walk(target):
                dirs[:] = sorted(d for d in dirs if d not in IGNORED_NAMES)
                files.extend(Path(current) / n for n in sorted(names))
        matches: list[str] = []
        for file in files:
            try:
                text = file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    matches.append(f"{self._rel(file)}:{number}:{line}")
                    if len(matches) > 50:
                        return "\n".join(matches[:50]) + "\n[more matches not shown]"
        return "\n".join(matches) if matches else "no matches"

    def _edit_file(self, path: str, old_text: str, new_text: str) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"file not found: {path}")
        if old_text == "":
            raise ToolError("old_text must not be empty")
        text = target.read_text(encoding="utf-8")
        count = text.count(old_text)
        if count == 0:
            raise ToolError(
                "old_text was not found in the file. It must match exactly, including whitespace; "
                "copy it from read_file output without the line-number prefix."
            )
        if count > 1:
            raise ToolError(f"old_text matches {count} places; include more surrounding lines so it matches once")
        target.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return f"edited {path}"

    def _apply_edits(self, edits: list[dict[str, str]]) -> str:
        """All edits are checked first and written only if every one of them is valid."""
        texts: dict[Path, str] = {}
        for number, edit in enumerate(edits, 1):
            target = self._resolve(edit["path"])
            if not target.is_file():
                raise ToolError(f"edit {number}: file not found: {edit['path']}")
            if edit["old_text"] == "":
                raise ToolError(f"edit {number}: old_text must not be empty")
            text = texts.get(target)
            if text is None:
                text = target.read_text(encoding="utf-8")
            count = text.count(edit["old_text"])
            if count == 0:
                raise ToolError(
                    f"edit {number}: old_text was not found in {edit['path']}. It must match exactly, including "
                    "whitespace. Nothing was changed."
                )
            if count > 1:
                raise ToolError(f"edit {number}: old_text matches {count} places in {edit['path']}. Nothing was changed.")
            texts[target] = text.replace(edit["old_text"], edit["new_text"], 1)
        for target, text in texts.items():
            target.write_text(text, encoding="utf-8")
        return f"applied {len(edits)} edit(s) to {len(texts)} file(s)"

    def _set_json_values(self, path: str, updates: list[dict[str, Any]]) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"file not found: {path}")
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ToolError(f"{path} is not valid JSON: {exc.msg}") from exc
        for number, update in enumerate(updates, 1):
            keys = update["key_path"]
            node: Any = data
            for key in keys[:-1]:
                if not isinstance(node, dict) or key not in node:
                    raise ToolError(f"update {number}: key path {'.'.join(keys)} not found. Nothing was changed.")
                node = node[key]
            if not isinstance(node, dict) or keys[-1] not in node:
                raise ToolError(f"update {number}: key path {'.'.join(keys)} not found. Nothing was changed.")
            node[keys[-1]] = update["value"]
        target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return f"set {len(updates)} value(s) in {path}"

    def _apply_patch(self, patch: str) -> str:
        return "\n".join(apply_unified_diff(patch, self._resolve_for_patch))

    def _run_command(self, command: str) -> str:
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            raise ToolError(f"could not parse the command: {exc}") from exc
        if not parts:
            raise ToolError("empty command")
        program, args = parts[0], parts[1:]
        if program not in ALLOWED_COMMANDS:
            raise ToolError(f"command '{program}' is not allowed; allowed: {', '.join(sorted(ALLOWED_COMMANDS))}")
        if program in ("python", "python3"):
            argv = self._python_argv(args)
        elif program == "pytest":
            self._check_args(args)
            argv = [sys.executable, "-m", "pytest", *args]
        else:
            self._check_args(args)
            argv = [program, *args]
        try:
            proc = run_trusted(argv, self.root, self.command_timeout)
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"command timed out after {self.command_timeout:g}s") from exc
        except FileNotFoundError as exc:
            raise ToolError(f"command not found: {program}") from exc
        return f"exit_code: {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    def _python_argv(self, args: list[str]) -> list[str]:
        if args[:2] == ["-m", "pytest"]:
            self._check_args(args[2:])
            return [sys.executable, "-m", "pytest", *args[2:]]
        if args and not args[0].startswith("-") and args[0].endswith(".py"):
            script = self._resolve(args[0])
            if not script.is_file():
                raise ToolError(f"script not found: {args[0]}")
            self._check_args(args[1:])
            return [sys.executable, str(script), *args[1:]]
        raise ToolError("python may only run a .py script inside the repository, or `-m pytest`")
