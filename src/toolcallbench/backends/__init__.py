"""Model backends and a factory."""
from __future__ import annotations

from typing import Any

from ..models import Task
from .base import Backend, BackendError
from .ollama import OllamaBackend
from .openai_compat import OpenAICompatBackend
from .scripted import PROFILES, ScriptedBackend

BACKEND_KINDS = ("ollama", "openai-compat", "scripted")

__all__ = [
    "BACKEND_KINDS",
    "PROFILES",
    "Backend",
    "BackendError",
    "OllamaBackend",
    "OpenAICompatBackend",
    "ScriptedBackend",
    "make_backend",
]


def make_backend(
    kind: str,
    *,
    model: str,
    host: str,
    options: dict[str, Any],
    think: bool | None,
    timeout: float,
    tasks: list[Task],
    profile: str = "oracle",
) -> Backend:
    if kind == "ollama":
        return OllamaBackend(model, host=host, options=options, think=think, timeout=timeout)
    if kind == "openai-compat":
        return OpenAICompatBackend(model, base_url=host, options=options, timeout=timeout)
    if kind == "scripted":
        return ScriptedBackend(tasks, profile=profile)
    raise ValueError(f"unknown backend '{kind}'; choose from {', '.join(BACKEND_KINDS)}")
