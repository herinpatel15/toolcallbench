"""Export a session's runs as JSON or CSV so results can be shared or analysed elsewhere."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from .store import Store

RUN_COLUMNS = [
    "session_id",
    "model",
    "quant",
    "backend",
    "task_id",
    "grp",
    "repeat",
    "status",
    "passed",
    "failure_type",
    "calls_made",
    "turns",
    "efficiency",
    "eval_tokens",
    "eval_seconds",
    "prompt_tokens",
    "prompt_seconds",
    "load_seconds",
    "wall_seconds",
    "tok_per_s",
    "error",
    "created_at",
]

FORMATS = ("json", "csv")


def export_session(store: Store, session_id: str, fmt: str) -> str:
    if fmt not in FORMATS:
        raise ValueError(f"unknown format '{fmt}'; choose from {', '.join(FORMATS)}")
    session = store.session(session_id)
    rows: list[dict[str, Any]] = [{key: run.get(key) for key in RUN_COLUMNS} for run in store.runs(session_id)]
    if fmt == "json":
        payload = {
            "session_id": session_id,
            "started_at": session["started_at"],
            "finished_at": session["finished_at"],
            "settings": session["settings"],
            "runs": rows,
        }
        return json.dumps(payload, indent=2) + "\n"
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=RUN_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
