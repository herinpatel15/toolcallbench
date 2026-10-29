"""Ollama backend: POST /api/chat with tools, non-streaming."""
from __future__ import annotations

from typing import Any

from ..models import BackendResponse, RawToolCall
from .base import Backend, BackendError, request_json


class OllamaBackend(Backend):
    name = "ollama"

    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
        options: dict[str, Any] | None = None,
        think: bool | None = None,
        timeout: float = 300.0,
        keep_alive: str = "30m",
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.options = dict(options or {})
        self.think = think
        self.timeout = timeout
        self.keep_alive = keep_alive

    # ------------------------------------------------------------ server facts

    def version(self) -> str:
        return str(request_json("GET", f"{self.host}/api/version", None, self.timeout).get("version", "unknown"))

    def list_models(self) -> list[str]:
        data = request_json("GET", f"{self.host}/api/tags", None, self.timeout)
        return [m.get("name", "") for m in data.get("models", [])]

    def show(self) -> dict[str, Any]:
        return request_json("POST", f"{self.host}/api/show", {"model": self.model}, self.timeout)

    def check(self) -> None:
        installed = self.list_models()
        wanted = {self.model, self.model if ":" in self.model else self.model + ":latest"}
        if not wanted & set(installed):
            raise BackendError(f"model '{self.model}' is not installed in Ollama; run: ollama pull {self.model}")

    def describe(self) -> dict[str, Any]:
        info: dict[str, Any] = {"backend": self.name, "host": self.host}
        try:
            info["backend_version"] = self.version()
            shown = self.show()
            details = shown.get("details", {})
            info["quant"] = details.get("quantization_level", "")
            info["parameter_size"] = details.get("parameter_size", "")
            info["family"] = details.get("family", "")
            info["capabilities"] = shown.get("capabilities", [])
        except BackendError:
            pass
        return info

    # -------------------------------------------------------------------- chat

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> BackendResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": self.options,
            "keep_alive": self.keep_alive,
        }
        if self.think is not None:
            payload["think"] = self.think
        data = request_json("POST", f"{self.host}/api/chat", payload, self.timeout)
        message = data.get("message") or {}
        calls = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            calls.append(RawToolCall(name=str(function.get("name", "")), arguments=function.get("arguments", {})))
        return BackendResponse(
            content=message.get("content") or "",
            tool_calls=calls,
            eval_tokens=int(data.get("eval_count") or 0),
            eval_seconds=float(data.get("eval_duration") or 0) / 1e9,
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            prompt_seconds=float(data.get("prompt_eval_duration") or 0) / 1e9,
            load_seconds=float(data.get("load_duration") or 0) / 1e9,
        )
