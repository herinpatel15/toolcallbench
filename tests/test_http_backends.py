"""Run the real HTTP backends against mock servers (no model needed)."""
import pytest

from mock_servers import mock_server
from toolcallbench.backends import BackendError, OllamaBackend, OpenAICompatBackend
from toolcallbench.runner import run_once


def test_ollama_end_to_end_all_tasks(tasks, fixture_dir):
    with mock_server("ollama", tasks) as (url, handler):
        backend = OllamaBackend("mock-model", host=url, options={"num_ctx": 4096, "seed": 1, "temperature": 0.0})
        backend.check()
        info = backend.describe()
        assert info["backend_version"] == "0.99.0" and info["quant"] == "Q4_K_M"
        for task in tasks:
            record = run_once(task, backend, fixture_dir)
            assert record.status == "ok" and record.check.passed, (task.id, record.check.details)
        chats = [r for r in handler.requests if r["path"] == "/api/chat"]
        assert chats and chats[0]["payload"]["stream"] is False
        assert chats[0]["payload"]["options"]["num_ctx"] == 4096
        assert len(chats[0]["payload"]["tools"]) == 6
        assert any(m.get("role") == "tool" and m.get("tool_name") for r in chats for m in r["payload"]["messages"])


def test_ollama_missing_model_is_reported(tasks):
    with mock_server("ollama", tasks, installed=["other:latest"]) as (url, _):
        with pytest.raises(BackendError, match="ollama pull"):
            OllamaBackend("mock-model", host=url).check()


def test_ollama_unreachable():
    with pytest.raises(BackendError, match="cannot reach"):
        OllamaBackend("m", host="http://127.0.0.1:9", timeout=2).check()


def test_ollama_think_flag_is_sent(tasks, fixture_dir):
    with mock_server("ollama", tasks) as (url, handler):
        backend = OllamaBackend("mock-model", host=url, think=False)
        run_once(next(t for t in tasks if t.id == "failure-01"), backend, fixture_dir)
        assert handler.requests[-1]["payload"]["think"] is False


def test_openai_compat_end_to_end(tasks, fixture_dir):
    with mock_server("openai", tasks) as (url, handler):
        backend = OpenAICompatBackend("mock", base_url=url, options={"temperature": 0.0, "seed": 3})
        backend.check()
        for task in tasks:
            record = run_once(task, backend, fixture_dir)
            assert record.status == "ok" and record.check.passed, (task.id, record.check.details)
        second = [r for r in handler.requests if r["path"] == "/v1/chat/completions"][1]["payload"]
        roles = [m["role"] for m in second["messages"]]
        assert "tool" in roles or second["messages"][-1]["role"] == "tool"
        tool_msgs = [m for m in second["messages"] if m["role"] == "tool"]
        assert all(m["tool_call_id"].startswith("call_") for m in tool_msgs)
        assistant = [m for m in second["messages"] if m.get("tool_calls")][0]
        assert isinstance(assistant["tool_calls"][0]["function"]["arguments"], str)


def test_openai_invalid_json_arguments_are_a_model_failure(tasks, fixture_dir):
    with mock_server("openai", tasks, profile="invalid_json") as (url, _):
        record = run_once(next(t for t in tasks if t.id == "read-01"), OpenAICompatBackend("mock", base_url=url), fixture_dir)
        assert record.status == "ok" and record.check.failure_type == "invalid_json"


def test_backend_error_is_not_a_model_failure(tasks, fixture_dir):
    backend = OllamaBackend("m", host="http://127.0.0.1:9", timeout=2)
    record = run_once(next(t for t in tasks if t.id == "read-01"), backend, fixture_dir)
    assert record.status == "error" and record.check is None
