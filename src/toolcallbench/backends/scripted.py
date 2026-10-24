"""A fake model that replays each task's reference solution, or fails in a chosen way.

It is used to validate the tasks, to test the harness without a real model, and for dry runs.
"""
from __future__ import annotations

import json
from typing import Any

from ..models import BackendResponse, RawToolCall, Task
from .base import Backend, BackendError

PROFILES = (
    "oracle",
    "invalid_json",
    "unknown_tool",
    "wrong_tool",
    "text_call",
    "no_call",
    "call_limit",
    "bad_edit",
)


class ScriptedBackend(Backend):
    name = "scripted"

    def __init__(self, tasks: list[Task], profile: str = "oracle"):
        if profile not in PROFILES:
            raise ValueError(f"unknown profile '{profile}'; choose from {', '.join(PROFILES)}")
        self.by_prompt = {task.prompt: task for task in tasks}
        self.profile = profile

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name, "profile": self.profile}

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> BackendResponse:
        prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
        task = self.by_prompt.get(prompt)
        if task is None:
            raise BackendError("scripted backend received a prompt that matches no task")
        turn = sum(1 for m in messages if m["role"] == "assistant")
        content, calls = self._step(task, turn)
        return BackendResponse(content=content, tool_calls=calls, eval_tokens=8, eval_seconds=0.01, prompt_tokens=100)

    # ------------------------------------------------------------------ steps

    @staticmethod
    def _oracle(task: Task, turn: int) -> tuple[str, list[RawToolCall]]:
        if turn >= len(task.reference):
            return "Done.", []
        step = task.reference[turn]
        if "calls" in step:
            return "", [RawToolCall(c["tool"], dict(c.get("args", {}))) for c in step["calls"]]
        return str(step["final"]), []

    def _step(self, task: Task, turn: int) -> tuple[str, list[RawToolCall]]:
        profile = self.profile
        if profile == "oracle":
            return self._oracle(task, turn)
        if profile == "call_limit":
            return "", [RawToolCall("list_dir", {"path": "."})]
        if profile == "no_call":
            return "I believe the answer is 42.", []
        if profile == "bad_edit":
            content, calls = self._oracle(task, turn)
            for call in calls:
                if call.name == "edit_file":
                    call.arguments = {**call.arguments, "old_text": "THIS TEXT IS NOT IN THE FILE"}
                elif call.name == "apply_patch":
                    call.arguments = {"patch": "--- a/missing.py\n+++ b/missing.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"}
            return content, calls
        if turn >= 1:
            return "Done.", []
        first = next((c for step in task.reference for c in step.get("calls", [])), None)
        if first is None:
            # The task needs no tools. A wrong_tool model calls one anyway; the others answer correctly.
            if profile == "wrong_tool":
                return "", [RawToolCall("list_dir", {})]
            return self._oracle(task, turn)
        tool, args = first["tool"], dict(first.get("args", {}))
        if profile == "invalid_json":
            return "", [RawToolCall(tool, '{"path": ')]
        if profile == "unknown_tool":
            return "", [RawToolCall("search_everything", {"query": "x"})]
        if profile == "wrong_tool":
            return "", [RawToolCall("list_dir", {})]
        if profile == "text_call":
            return json.dumps({"name": tool, "arguments": args}), []
        raise AssertionError(profile)  # pragma: no cover
