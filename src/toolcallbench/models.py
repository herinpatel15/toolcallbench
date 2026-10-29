"""Plain data classes shared by the runner, the checks, the store and the report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

GROUPS = ("read", "edit", "run", "chain", "failure")


@dataclass
class Task:
    id: str
    group: str
    title: str
    prompt: str
    expect: dict[str, Any]
    reference: list[dict[str, Any]]
    tools_named: bool = False

    @property
    def baseline_calls(self) -> int:
        """Number of tool calls in the reference solution (used for the efficiency ratio)."""
        return sum(len(step.get("calls", [])) for step in self.reference)


@dataclass
class RawToolCall:
    """A tool call exactly as the backend returned it."""

    name: str
    arguments: Any  # dict for well-formed calls; str when the backend returned a JSON string


@dataclass
class BackendResponse:
    content: str = ""
    tool_calls: list[RawToolCall] = field(default_factory=list)
    eval_tokens: int = 0
    eval_seconds: float = 0.0
    prompt_tokens: int = 0
    prompt_seconds: float = 0.0  # time spent reading the prompt (0 when the server does not report it)
    load_seconds: float = 0.0  # time spent loading the model into memory (Ollama only)


@dataclass
class CallRecord:
    """One tool call after validation and (if valid) execution."""

    index: int
    turn: int
    tool: str
    arguments: Any
    valid: bool
    ok: bool
    error_kind: str  # "" | "invalid_json" | "invalid_args" | "unknown_tool" | "tool_error"
    result: str


@dataclass
class Transcript:
    messages: list[dict[str, Any]] = field(default_factory=list)
    calls: list[CallRecord] = field(default_factory=list)
    final_text: str = ""
    turns: int = 0
    hit_limit: bool = False
    text_tool_call: bool = False
    eval_tokens: int = 0
    eval_seconds: float = 0.0
    prompt_tokens: int = 0
    prompt_seconds: float = 0.0
    load_seconds: float = 0.0
    wall_seconds: float = 0.0
    final_diff: str = ""  # unified diff of the repository the model left behind, against the starting fixture


@dataclass
class CheckResult:
    parse_ok: bool
    tool_ok: bool
    args_ok: bool
    outcome_ok: bool
    passed: bool
    failure_type: str
    efficiency: float | None
    details: list[str] = field(default_factory=list)
