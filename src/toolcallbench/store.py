"""SQLite storage for sessions, runs and calls, plus one JSONL transcript log per run."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runner import RunRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    settings_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL REFERENCES sessions(session_id),
    model        TEXT NOT NULL,
    quant        TEXT NOT NULL DEFAULT '',
    backend      TEXT NOT NULL,
    task_id      TEXT NOT NULL,
    grp          TEXT NOT NULL,
    repeat       INTEGER NOT NULL,
    status       TEXT NOT NULL,
    passed       INTEGER NOT NULL,
    parse_ok     INTEGER NOT NULL,
    tool_ok      INTEGER NOT NULL,
    args_ok      INTEGER NOT NULL,
    outcome_ok   INTEGER NOT NULL,
    failure_type TEXT NOT NULL,
    calls_made   INTEGER NOT NULL,
    turns        INTEGER NOT NULL,
    efficiency   REAL,
    eval_tokens  INTEGER NOT NULL,
    eval_seconds REAL NOT NULL,
    prompt_tokens  INTEGER NOT NULL DEFAULT 0,
    prompt_seconds REAL NOT NULL DEFAULT 0,
    load_seconds   REAL NOT NULL DEFAULT 0,
    wall_seconds REAL NOT NULL,
    tok_per_s    REAL,
    error        TEXT NOT NULL DEFAULT '',
    log_path     TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    UNIQUE (session_id, model, task_id, repeat)
);
CREATE TABLE IF NOT EXISTS calls (
    run_id         INTEGER NOT NULL REFERENCES runs(id),
    idx            INTEGER NOT NULL,
    turn           INTEGER NOT NULL,
    tool           TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    valid          INTEGER NOT NULL,
    ok             INTEGER NOT NULL,
    error_kind     TEXT NOT NULL,
    PRIMARY KEY (run_id, idx)
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def model_slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._add_missing_columns()

    def _add_missing_columns(self) -> None:
        """Databases made by older versions lack the prompt/load timing columns; add them in place."""
        have = {row["name"] for row in self.conn.execute("PRAGMA table_info(runs)")}
        for name, ddl in (
            ("prompt_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("prompt_seconds", "REAL NOT NULL DEFAULT 0"),
            ("load_seconds", "REAL NOT NULL DEFAULT 0"),
        ):
            if name not in have:
                self.conn.execute(f"ALTER TABLE runs ADD COLUMN {name} {ddl}")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ---------------------------------------------------------------- sessions

    def session_exists(self, session_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return row is not None

    def create_session(self, session_id: str, settings: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO sessions (session_id, started_at, settings_json) VALUES (?, ?, ?)",
            (session_id, now_iso(), json.dumps(settings, sort_keys=True)),
        )
        self.conn.commit()

    def merge_settings(self, session_id: str, patch: dict[str, Any]) -> None:
        settings = self.session(session_id)["settings"]
        settings.update(patch)
        self.conn.execute(
            "UPDATE sessions SET settings_json = ? WHERE session_id = ?", (json.dumps(settings, sort_keys=True), session_id)
        )
        self.conn.commit()

    def finish_session(self, session_id: str) -> None:
        self.conn.execute("UPDATE sessions SET finished_at = ? WHERE session_id = ?", (now_iso(), session_id))
        self.conn.commit()

    def session(self, session_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            raise KeyError(f"no session '{session_id}'")
        return {
            "session_id": row["session_id"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "settings": json.loads(row["settings_json"]),
        }

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT s.session_id, s.started_at, s.finished_at, COUNT(r.id) AS runs "
            "FROM sessions s LEFT JOIN runs r ON r.session_id = s.session_id "
            "GROUP BY s.session_id ORDER BY s.started_at DESC, s.session_id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def latest_session_id(self) -> str | None:
        sessions = self.list_sessions()
        return sessions[0]["session_id"] if sessions else None

    # -------------------------------------------------------------------- runs

    def has_run(self, session_id: str, model: str, task_id: str, repeat: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM runs WHERE session_id = ? AND model = ? AND task_id = ? AND repeat = ?",
            (session_id, model, task_id, repeat),
        ).fetchone()
        return row is not None

    def add_run(
        self, session_id: str, *, model: str, quant: str, backend: str, repeat: int, record: RunRecord, log_path: str
    ) -> int:
        tr, check, task = record.transcript, record.check, record.task
        tok_per_s = tr.eval_tokens / tr.eval_seconds if tr.eval_seconds > 0 else None
        cursor = self.conn.execute(
            "INSERT INTO runs (session_id, model, quant, backend, task_id, grp, repeat, status, passed, parse_ok, "
            "tool_ok, args_ok, outcome_ok, failure_type, calls_made, turns, efficiency, eval_tokens, eval_seconds, "
            "prompt_tokens, prompt_seconds, load_seconds, wall_seconds, tok_per_s, error, log_path, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                model,
                quant,
                backend,
                task.id,
                task.group,
                repeat,
                record.status,
                int(bool(check and check.passed)),
                int(bool(check and check.parse_ok)),
                int(bool(check and check.tool_ok)),
                int(bool(check and check.args_ok)),
                int(bool(check and check.outcome_ok)),
                check.failure_type if check else "backend_error",
                len(tr.calls),
                tr.turns,
                check.efficiency if check else None,
                tr.eval_tokens,
                tr.eval_seconds,
                tr.prompt_tokens,
                tr.prompt_seconds,
                tr.load_seconds,
                tr.wall_seconds,
                tok_per_s,
                record.error,
                log_path,
                now_iso(),
            ),
        )
        run_id = cursor.lastrowid
        for call in tr.calls:
            self.conn.execute(
                "INSERT INTO calls (run_id, idx, turn, tool, arguments_json, valid, ok, error_kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, call.index, call.turn, call.tool, json.dumps(call.arguments), int(call.valid), int(call.ok), call.error_kind),
            )
        self.conn.commit()
        return int(run_id)

    def runs(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM runs WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
        return [dict(r) for r in rows]


def write_log(results_dir: Path, session_id: str, model: str, repeat: int, record: RunRecord) -> str:
    """Write the full transcript as JSONL and return its path relative to results_dir."""
    rel = Path("logs") / session_id / model_slug(model) / f"{record.task.id}_{repeat}.jsonl"
    path = Path(results_dir) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    tr, check = record.transcript, record.check
    summary = {
        "type": "summary",
        "task": record.task.id,
        "status": record.status,
        "error": record.error,
        "passed": bool(check and check.passed),
        "failure_type": check.failure_type if check else "backend_error",
        "details": check.details if check else [],
        "final_text": tr.final_text,
        "final_diff": tr.final_diff,
        "calls": [
            {
                "index": c.index,
                "turn": c.turn,
                "tool": c.tool,
                "arguments": c.arguments,
                "valid": c.valid,
                "ok": c.ok,
                "error_kind": c.error_kind,
            }
            for c in tr.calls
        ],
    }
    with path.open("w", encoding="utf-8") as handle:
        for message in tr.messages:
            handle.write(json.dumps({"type": "message", **message}) + "\n")
        handle.write(json.dumps(summary) + "\n")
    return rel.as_posix()
