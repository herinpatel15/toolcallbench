"""OpenAI-compatible backend for llama.cpp `llama-server`, LM Studio, vLLM and similar servers.

Tool arguments arrive as JSON strings here, so this backend exercises the invalid-JSON path.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..models import BackendResponse, RawToolCall
from .base import Backend, BackendError, request_json


def to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert the runner's Ollama-style messages to the OpenAI chat format (adds tool call ids)."""
    out: list[dict[str, Any]] = []
    pending: list[str] = []
    counter = 0
    for message in messages:
        if message["role"] == "assistant" and message.get("tool_calls"):
            pending = []
            calls = []
            for item in message["tool_calls"]:
                counter += 1
                call_id = f"call_{counter}"
                pending.append(call_id)
                function = item["function"]
                calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": function["name"], "arguments": json.dumps(function.get("arguments", {}))},
                    }
                )
            out.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": calls})
        elif message["role"] == "tool":
            call_id = pending.pop(0) if pending else "call_0"
            out.append({"role": "tool", "tool_call_id": call_id, "content": message["content"]})
        else:
            out.append({"role": message["role"], "content": message.get("content") or ""})
    return out


class OpenAICompatBackend(Backend):
    name = "openai-compat"

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:8080",
        options: dict[str, Any] | None = None,
        timeout: float = 300.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.options = dict(options or {})
        self.timeout = timeout

    def check(self) -> None:
        request_json("GET", f"{self.base_url}/v1/models", None, self.timeout)

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name, "host": self.base_url}

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> BackendResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": to_openai_messages(messages),
            "tools": tools,
            "stream": False,
        }
        for key in ("temperature", "seed"):
            if key in self.options:
                payload[key] = self.options[key]
        started = time.monotonic()
        data = request_json("POST", f"{self.base_url}/v1/chat/completions", payload, self.timeout)
        elapsed = time.monotonic() - started
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError("response has no choices[0].message") from exc
        calls = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            calls.append(RawToolCall(name=str(function.get("name", "")), arguments=function.get("arguments", "")))
        usage = data.get("usage") or {}
        timings = data.get("timings") or {}
        eval_seconds = float(timings["predicted_ms"]) / 1000 if "predicted_ms" in timings else elapsed
        return BackendResponse(
            content=message.get("content") or "",
            tool_calls=calls,
            eval_tokens=int(usage.get("completion_tokens") or 0),
            eval_seconds=eval_seconds,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
        )
