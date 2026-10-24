"""Run one task against one backend: converse, execute tools in a throwaway repo copy, then score."""
from __future__ import annotations

import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .backends.base import Backend, BackendError
from .checks import evaluate
from .models import CallRecord, CheckResult, RawToolCall, Task, Transcript
from .tools import TOOL_NAMES, TOOL_SPECS, ToolExecutor, validate_arguments

SYSTEM_PROMPT = (
    "You are a coding assistant working inside a small Python repository. "
    "Use the provided tools to inspect and change files and to run commands. "
    "Paths are relative to the repository root. "
    "When you have finished, reply with a short plain-text answer."
)

# A reply with no tool calls that still looks like a tool call written out as text.
TEXT_CALL_RE = re.compile(r'<tool_call>|<function=|"name"\s*:\s*"(?:%s)"' % "|".join(TOOL_NAMES))


@dataclass
class RunRecord:
    task: Task
    status: str  # "ok" or "error" (the backend failed; this says nothing about the model)
    error: str
    transcript: Transcript
    check: CheckResult | None


def _execute(raw: RawToolCall, turn: int, index: int, executor: ToolExecutor) -> CallRecord:
    arguments, kind, message = validate_arguments(raw.name, raw.arguments)
    if kind:
        return CallRecord(index, turn, raw.name, raw.arguments, False, False, kind, f"error: {message}")
    ok, text = executor.execute(raw.name, arguments)
    return CallRecord(index, turn, raw.name, arguments, True, ok, "" if ok else "tool_error", text)


def converse(task: Task, backend: Backend, executor: ToolExecutor, tr: Transcript, max_calls: int, max_turns: int) -> None:
    """Fill `tr` by talking to the backend until it answers, hits a limit, or fails."""
    tr.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task.prompt},
    ]
    for turn in range(1, max_turns + 1):
        response = backend.chat(tr.messages, TOOL_SPECS)
        tr.turns = turn
        tr.eval_tokens += response.eval_tokens
        tr.eval_seconds += response.eval_seconds
        assistant: dict = {"role": "assistant", "content": response.content}
        if response.tool_calls:
            assistant["tool_calls"] = [
                {"function": {"name": c.name, "arguments": c.arguments if isinstance(c.arguments, dict) else {}}}
                for c in response.tool_calls
            ]
        tr.messages.append(assistant)
        if not response.tool_calls:
            tr.final_text = response.content
            tr.text_tool_call = bool(TEXT_CALL_RE.search(response.content))
            return
        for raw in response.tool_calls:
            if len(tr.calls) >= max_calls:
                tr.hit_limit = True
                return
            record = _execute(raw, turn, len(tr.calls) + 1, executor)
            tr.calls.append(record)
            tr.messages.append({"role": "tool", "tool_name": raw.name, "content": record.result})
    tr.hit_limit = True


def run_once(task: Task, backend: Backend, fixture_dir: Path, *, max_calls: int = 12, max_turns: int = 10) -> RunRecord:
    started = time.monotonic()
    tr = Transcript()
    with tempfile.TemporaryDirectory(prefix="tcb-") as tmp:
        root = Path(tmp) / "repo"
        shutil.copytree(fixture_dir, root, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
        executor = ToolExecutor(root)
        try:
            converse(task, backend, executor, tr, max_calls, max_turns)
        except BackendError as exc:
            tr.wall_seconds = time.monotonic() - started
            return RunRecord(task, "error", str(exc), tr, None)
        check = evaluate(task, tr, root, fixture_dir, default_max_calls=max_calls)
    tr.wall_seconds = time.monotonic() - started
    return RunRecord(task, "ok", "", tr, check)
