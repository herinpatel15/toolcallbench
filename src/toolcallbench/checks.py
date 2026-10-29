"""Deterministic scoring of one run. There is no AI judge: every verdict comes from plain code.

A run passes when Parse, Tool and Outcome all succeed. Arguments and Efficiency are reported separately.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .models import CallRecord, CheckResult, Task, Transcript
from .tools import run_trusted

EDIT_TOOLS = {"edit_file", "apply_patch"}

FAILURE_TYPES = (
    "invalid_json",
    "invalid_args",
    "unknown_tool",
    "text_tool_call",
    "no_call",
    "unneeded_call",
    "call_limit",
    "not_parallel",
    "wrong_tool",
    "too_few_calls",
    "patch_failed",
    "wrong_args",
    "outcome_mismatch",
)


def _norm_path(value: Any) -> str:
    text = str(value).strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    if len(text) > 1:
        text = text.rstrip("/")
    return text or "."


def _norm(key: str, value: Any) -> str:
    return _norm_path(value) if key == "path" else str(value)


def _value_matches(spec: Any, actual: Any, key: str) -> bool:
    got = _norm(key, actual)
    if isinstance(spec, dict):
        if "contains" in spec:
            return str(spec["contains"]) in got
        if "regex" in spec:
            return re.search(spec["regex"], got) is not None
        if "one_of" in spec:
            return got in [_norm(key, v) for v in spec["one_of"]]
        raise ValueError(f"unknown argument matcher: {sorted(spec)}")
    return got == _norm(key, spec)


def _tools(req: dict[str, Any]) -> list[str]:
    tool = req["tool"]
    return list(tool) if isinstance(tool, list) else [tool]


def _tool_matches(req: dict[str, Any], call: CallRecord) -> bool:
    return call.valid and call.tool in _tools(req)


def _args_match(req: dict[str, Any], call: CallRecord) -> bool:
    args = call.arguments if isinstance(call.arguments, dict) else {}
    return all(key in args and _value_matches(spec, args[key], key) for key, spec in (req.get("args") or {}).items())


def _assign(reqs: list[dict[str, Any]], calls: list[CallRecord], ordered: bool, start: int = 0, used: frozenset = frozenset()):
    """Match each requirement to a distinct call by tool name. Returns the call positions or None."""
    if not reqs:
        return []
    first, rest = reqs[0], reqs[1:]
    for position in range(start if ordered else 0, len(calls)):
        if position in used or not _tool_matches(first, calls[position]):
            continue
        tail = _assign(rest, calls, ordered, position + 1, used | {position})
        if tail is not None:
            return [position, *tail]
    return None


def _parallel_ok(reqs: list[dict[str, Any]], calls: list[CallRecord]) -> bool:
    turns: dict[int, list[CallRecord]] = {}
    for call in calls:
        turns.setdefault(call.turn, []).append(call)
    return any(_assign(reqs, group, False) is not None for group in turns.values())


def _check_outcome(task: Task, tr: Transcript, root: Path, fixture_dir: Path, details: list[str]) -> bool:
    exp = task.expect
    ok = True

    def fail(message: str) -> None:
        nonlocal ok
        ok = False
        details.append(message)

    answer = tr.final_text or ""
    for needle in exp.get("answer_contains", []):
        if needle.lower() not in answer.lower():
            fail(f"answer does not contain {needle!r}")
    for pattern in exp.get("answer_regex", []):
        if not re.search(pattern, answer, re.IGNORECASE):
            fail(f"answer does not match /{pattern}/")
    for rel in exp.get("files_exist", []):
        if not (root / rel).is_file():
            fail(f"expected file {rel} does not exist")
    for rel, spec in (exp.get("final_files") or {}).items():
        path = root / rel
        if not path.is_file():
            fail(f"expected file {rel} does not exist")
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for text in spec.get("contains", []):
            if text not in content:
                fail(f"{rel} does not contain {text!r}")
        for text in spec.get("not_contains", []):
            if text in content:
                fail(f"{rel} still contains {text!r}")
        if spec.get("unchanged") and content != (fixture_dir / rel).read_text(encoding="utf-8"):
            fail(f"{rel} was changed but must stay as it was")
    for item in exp.get("command", []):
        try:
            proc = run_trusted(item["argv"], root)
        except subprocess.TimeoutExpired:
            fail(f"check command timed out: {item['argv']}")
            continue
        want = item.get("exit_code", 0)
        if proc.returncode != want:
            tail = (proc.stdout + proc.stderr).strip()[-300:]
            fail(f"check command exited {proc.returncode}, wanted {want}: {tail}")
    return ok


def evaluate(task: Task, tr: Transcript, root: Path, fixture_dir: Path, default_max_calls: int = 12) -> CheckResult:
    exp = task.expect
    details: list[str] = []
    calls = tr.calls
    valid = [c for c in calls if c.valid]

    # Parse: every call must be well formed and name a real tool.
    parse_type = ""
    if tr.text_tool_call:
        parse_type = "text_tool_call"
    else:
        bad = next((c for c in calls if not c.valid), None)
        if bad:
            parse_type = bad.error_kind
    parse_ok = parse_type == ""
    if parse_type:
        details.append(f"parse: {parse_type}")

    # Tool: the right tools, in the right amount.
    reqs = exp.get("calls") or []
    ordered = bool(exp.get("ordered"))
    max_calls = exp.get("max_calls", default_max_calls)
    min_calls = exp.get("min_calls", len(reqs))
    tool_type = ""
    if tr.hit_limit:
        tool_type = "call_limit"
    elif exp.get("no_tool_calls"):
        if calls:
            tool_type = "unneeded_call"
    elif not calls:
        tool_type = "no_call" if min_calls > 0 else ""
    elif len(calls) > max_calls:
        tool_type = "call_limit"
    elif len(calls) < min_calls:
        tool_type = "too_few_calls"
    elif any(c.tool in exp.get("forbidden_tools", []) for c in calls):
        tool_type = "wrong_tool"
    elif reqs and _assign(reqs, valid, ordered) is None:
        tool_type = "wrong_tool"
    elif exp.get("parallel") and not _parallel_ok(reqs, valid):
        tool_type = "not_parallel"
    tool_ok = tool_type == ""
    if tool_type:
        details.append(f"tool: {tool_type}")

    # Arguments: reported separately from pass/fail.
    args_ok = True
    for req in reqs:
        if req.get("args") and not any(_tool_matches(req, c) and _args_match(req, c) for c in valid):
            args_ok = False
            details.append(f"arguments: no {_tools(req)} call matched {req['args']}")

    # Outcome: the answer text and the final state of the repository.
    outcome_ok = _check_outcome(task, tr, root, fixture_dir, details)
    if tool_type == "call_limit":
        # Say what was hit and whether the work was actually done, so a "too strict" budget is easy to spot.
        details.append(
            f"limit: {len(calls)} calls in {tr.turns} turns (this task allows {max_calls} calls); "
            f"final repo state was {'correct' if outcome_ok else 'wrong'}"
        )

    if not parse_ok:
        failure = parse_type
    elif not tool_ok:
        failure = tool_type
    elif not outcome_ok:
        if any(c.tool in EDIT_TOOLS and c.valid and not c.ok for c in calls):
            failure = "patch_failed"
        elif not args_ok:
            failure = "wrong_args"
        else:
            failure = "outcome_mismatch"
    else:
        failure = "ok"

    baseline = task.baseline_calls
    if baseline > 0:
        efficiency: float | None = round(len(calls) / baseline, 2)
    else:
        efficiency = 1.0 if not calls else None

    return CheckResult(
        parse_ok=parse_ok,
        tool_ok=tool_ok,
        args_ok=args_ok,
        outcome_ok=outcome_ok,
        passed=parse_ok and tool_ok and outcome_ok,
        failure_type=failure,
        efficiency=efficiency,
        details=details,
    )
