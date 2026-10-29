import sqlite3

from toolcallbench.backends.ollama import OllamaBackend
from toolcallbench.backends.scripted import ScriptedBackend
from toolcallbench.report import render_markdown
from toolcallbench.runner import run_once
from toolcallbench.store import Store, write_log


def _store_with_runs(tmp_path, tasks, fixture_dir, profile="oracle", ids=("read-01", "chain-04")):
    store = Store(tmp_path / "r.sqlite")
    store.create_session("s1", {"repeats": 1, "backend": "scripted"})
    backend = ScriptedBackend(tasks, profile)
    for task in [t for t in tasks if t.id in ids]:
        record = run_once(task, backend, fixture_dir)
        log = write_log(tmp_path, "s1", "m", 1, record)
        store.add_run("s1", model="m", quant="", backend="scripted", repeat=1, record=record, log_path=log)
    return store


def test_prompt_tokens_are_stored_per_run(tmp_path, tasks, fixture_dir):
    store = _store_with_runs(tmp_path, tasks, fixture_dir)
    rows = store.runs("s1")
    assert all(r["prompt_tokens"] > 0 for r in rows)  # the scripted backend reports 100 per turn
    assert {"prompt_seconds", "load_seconds"} <= set(rows[0])


def test_report_has_a_time_breakdown(tmp_path, tasks, fixture_dir):
    store = _store_with_runs(tmp_path, tasks, fixture_dir)
    md = render_markdown(store, "s1", {t.id: (t.group, t.title) for t in tasks})
    assert "## Where the time went" in md and "Reading prompt s" in md


def test_old_database_gets_the_new_columns(tmp_path):
    path = tmp_path / "old.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE sessions (session_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, settings_json TEXT NOT NULL);"
        "CREATE TABLE runs (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, model TEXT, eval_tokens INTEGER, eval_seconds REAL, wall_seconds REAL);"
    )
    conn.commit()
    conn.close()
    store = Store(path)
    cols = {row["name"] for row in store.conn.execute("PRAGMA table_info(runs)")}
    assert {"prompt_tokens", "prompt_seconds", "load_seconds"} <= cols


def test_ollama_prompt_and_load_timing_are_read(tasks):
    reply = {
        "message": {"role": "assistant", "content": "ok"},
        "eval_count": 20, "eval_duration": 500_000_000,
        "prompt_eval_count": 300, "prompt_eval_duration": 2_000_000_000, "load_duration": 1_500_000_000,
    }
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            body = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        backend = OllamaBackend("m", host=f"http://127.0.0.1:{server.server_port}", options={}, timeout=5)
        response = backend.chat([{"role": "user", "content": "hi"}], [])
    finally:
        server.shutdown()
    assert response.prompt_tokens == 300
    assert response.prompt_seconds == 2.0 and response.load_seconds == 1.5


def test_call_limit_details_say_whether_the_repo_was_fixed(tmp_path, tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "chain-04")
    backend = ScriptedBackend(tasks, "oracle")
    record = run_once(task, backend, fixture_dir, max_calls=12)
    assert record.check.passed  # sanity: the reference solution fits the budget
    # Squeeze the task's own budget so the oracle exceeds it.
    task.expect["max_calls"] = 2
    record = run_once(task, ScriptedBackend(tasks, "oracle"), fixture_dir, max_calls=12)
    assert record.check.failure_type == "call_limit"
    assert any(d.startswith("limit:") and "final repo state was correct" in d for d in record.check.details)


def test_log_keeps_the_final_repo_diff(tmp_path, tasks, fixture_dir):
    import json

    task = next(t for t in tasks if t.id == "edit-01")
    record = run_once(task, ScriptedBackend(tasks, "oracle"), fixture_dir)
    assert "+++ b/" in record.transcript.final_diff  # the oracle edits one file
    log = write_log(tmp_path, "s1", "m", 1, record)
    summary = json.loads((tmp_path / log).read_text().splitlines()[-1])
    assert summary["final_diff"] == record.transcript.final_diff


def test_read_only_run_has_an_empty_diff(tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "read-01")
    record = run_once(task, ScriptedBackend(tasks, "oracle"), fixture_dir)
    assert record.transcript.final_diff == ""
