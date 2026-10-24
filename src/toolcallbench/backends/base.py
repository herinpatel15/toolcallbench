"""Backend interface and a small JSON-over-HTTP helper (standard library only)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ..models import BackendResponse


class BackendError(RuntimeError):
    """The model server could not be reached or returned an error. Not a model failure."""


class Backend:
    name = "backend"

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> BackendResponse:
        raise NotImplementedError

    def check(self) -> None:
        """Raise BackendError if the server or the model is not usable. Called once before a sweep."""

    def describe(self) -> dict[str, Any]:
        """Facts about the server and model, recorded in the session settings."""
        return {"backend": self.name}


def request_json(method: str, url: str, payload: dict[str, Any] | None, timeout: float) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        raise BackendError(f"HTTP {exc.code} from {url}: {body}") from exc
    except json.JSONDecodeError as exc:
        raise BackendError(f"{url} returned invalid JSON") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BackendError(f"cannot reach {url}: {exc}") from exc
