"""Tiny HTTP servers that imitate Ollama and an OpenAI-compatible server, backed by the scripted backend."""
from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

from toolcallbench.backends.scripted import ScriptedBackend


def _make_handler(kind: str, tasks, profile: str, installed: list[str]):
    brain = ScriptedBackend(tasks, profile)

    class Handler(BaseHTTPRequestHandler):
        requests: list[dict] = []

        def log_message(self, *args):  # keep test output quiet
            pass

        def _send(self, payload, status=200):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if kind == "ollama" and self.path == "/api/version":
                self._send({"version": "0.99.0"})
            elif kind == "ollama" and self.path == "/api/tags":
                self._send({"models": [{"name": n} for n in installed]})
            elif kind == "openai" and self.path == "/v1/models":
                self._send({"data": [{"id": "mock"}]})
            else:
                self._send({"error": "not found"}, 404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            Handler.requests.append({"path": self.path, "payload": payload})
            if kind == "ollama" and self.path == "/api/show":
                self._send({"details": {"quantization_level": "Q4_K_M", "parameter_size": "8.2B", "family": "qwen3"},
                            "capabilities": ["completion", "tools"]})
            elif kind == "ollama" and self.path == "/api/chat":
                reply = brain.chat(payload["messages"], payload["tools"])
                message = {"role": "assistant", "content": reply.content}
                if reply.tool_calls:
                    message["tool_calls"] = [{"function": {"name": c.name, "arguments": c.arguments}} for c in reply.tool_calls]
                self._send({"message": message, "eval_count": 20, "eval_duration": 500_000_000, "prompt_eval_count": 100})
            elif kind == "openai" and self.path == "/v1/chat/completions":
                reply = brain.chat(payload["messages"], payload["tools"])
                message = {"role": "assistant", "content": reply.content}
                if reply.tool_calls:
                    message["tool_calls"] = [
                        {"id": f"c{i}", "type": "function",
                         "function": {"name": c.name, "arguments": c.arguments if isinstance(c.arguments, str) else json.dumps(c.arguments)}}
                        for i, c in enumerate(reply.tool_calls)
                    ]
                self._send({"choices": [{"message": message}], "usage": {"completion_tokens": 20, "prompt_tokens": 100}})
            else:
                self._send({"error": "not found"}, 404)

    return Handler


@contextmanager
def mock_server(kind: str, tasks, profile: str = "oracle", installed: list[str] | None = None):
    handler = _make_handler(kind, tasks, profile, installed or ["mock-model:latest"])
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", handler
    finally:
        server.shutdown()
        server.server_close()
