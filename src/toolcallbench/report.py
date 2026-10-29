"""Turn a session's runs into a Markdown report and a self-contained HTML page."""
from __future__ import annotations

import html
import statistics
from collections import Counter, defaultdict
from typing import Any

from .checks import FAILURE_TYPES
from .models import GROUPS
from .store import Store

SETTING_LABELS = [
    ("backend", "Backend"),
    ("backend_version", "Backend version"),
    ("host", "Host"),
    ("num_ctx", "Context length (num_ctx)"),
    ("temperature", "Temperature"),
    ("seed", "Base seed (+1 per repeat)"),
    ("repeats", "Repeats per task"),
    ("max_calls", "Call limit per run"),
    ("max_turns", "Turn limit per run"),
    ("declared_kv_cache_type", "KV cache type (declared)"),
    ("declared_flash_attention", "Flash attention (declared)"),
    ("system_prompt_sha", "System prompt hash"),
    ("toolcallbench_version", "ToolCallBench version"),
    ("platform", "Platform"),
    ("python", "Python"),
]


def _pct(passed: int, total: int) -> str:
    return "-" if total == 0 else f"{100 * passed / total:.1f}%"


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Group runs by model and compute the numbers the report shows."""
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        by_model[run["model"]].append(run)
    models = []
    for name, rows in by_model.items():
        scored = [r for r in rows if r["status"] == "ok"]
        passed = sum(r["passed"] for r in scored)
        groups = {}
        for group in GROUPS:
            in_group = [r for r in scored if r["grp"] == group]
            groups[group] = (sum(r["passed"] for r in in_group), len(in_group))
        failures = Counter(r["failure_type"] for r in scored if not r["passed"])
        tasks: dict[str, tuple[int, int]] = {}
        for task_id in sorted({r["task_id"] for r in scored}):
            of_task = [r for r in scored if r["task_id"] == task_id]
            tasks[task_id] = (sum(r["passed"] for r in of_task), len(of_task))
        models.append(
            {
                "model": name,
                "quant": next((r["quant"] for r in rows if r["quant"]), ""),
                "runs": len(rows),
                "errors": len(rows) - len(scored),
                "passed": passed,
                "scored": len(scored),
                "groups": groups,
                "failures": failures,
                "tasks": tasks,
                "tok_per_s": _median([r["tok_per_s"] for r in scored if r["tok_per_s"]]),
                "seconds": _median([r["wall_seconds"] for r in scored]),
                "efficiency": _median([r["efficiency"] for r in scored if r["efficiency"] is not None]),
                "out_tokens": _median([r["eval_tokens"] for r in scored]),
                "prompt_tokens": _median([r["prompt_tokens"] for r in scored]),
                "gen_seconds": _median([r["eval_seconds"] for r in scored]),
                "prompt_seconds": _median([r["prompt_seconds"] for r in scored]),
                "load_seconds": _median([r["load_seconds"] for r in scored]),
            }
        )
    return {"models": models}


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _fmt(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def render_markdown(store: Store, session_id: str, task_titles: dict[str, tuple[str, str]] | None = None) -> str:
    session = store.session(session_id)
    settings = session["settings"]
    runs = store.runs(session_id)
    data = aggregate(runs)
    models = data["models"]
    task_titles = task_titles or {}

    out = [f"# ToolCallBench report: {session_id}", ""]
    tasks_count = len({r["task_id"] for r in runs})
    out.append(
        f"Started {session['started_at']}. {len(runs)} runs: {len(models)} model(s), {tasks_count} task(s), "
        f"{settings.get('repeats', '?')} repeat(s) each."
    )
    out += ["", "## Settings", ""]
    rows = []
    for key, label in SETTING_LABELS:
        if key in settings:
            value = settings[key]
            if isinstance(value, dict):
                value = ", ".join(f"{k}: {v}" for k, v in sorted(value.items()))
            rows.append([label, str(value)])
    out += _table(["Setting", "Value"], rows)

    out += ["", "## Summary", "", "Pass rate counts only runs where the backend answered. Errors are runs where it did not.", ""]
    header = ["Model", "Quant", "Runs", "Errors", "Pass"] + [g.title() for g in GROUPS] + ["tok/s", "s/task", "Calls vs ref"]
    rows = []
    for m in sorted(models, key=lambda x: -(x["passed"] / x["scored"] if x["scored"] else -1)):
        rows.append(
            [m["model"], m["quant"] or "-", str(m["runs"]), str(m["errors"]), _pct(m["passed"], m["scored"])]
            + [_pct(*m["groups"][g]) for g in GROUPS]
            + [_fmt(m["tok_per_s"]), _fmt(m["seconds"]), _fmt(m["efficiency"], 2)]
        )
    out += _table(header, rows)

    out += ["", "## Where the time went", "", "Medians per task. A dash means the server did not report that number.", ""]
    rows = []
    for m in models:
        rows.append(
            [m["model"], _fmt(m["seconds"]), _fmt(m["gen_seconds"]), _fmt(m["prompt_seconds"] or None), _fmt(m["load_seconds"] or None)]
            + [_fmt(m["out_tokens"], 0), _fmt(m["prompt_tokens"] or None, 0)]
        )
    out += _table(["Model", "s/task", "Generating s", "Reading prompt s", "Loading s", "Output tokens", "Prompt tokens"], rows)

    seen_types = [t for t in FAILURE_TYPES if any(t in m["failures"] for m in models)]
    out += ["", "## Failure types", ""]
    if seen_types:
        out += _table(["Model"] + seen_types, [[m["model"]] + [str(m["failures"].get(t, 0)) for t in seen_types] for m in models])
    else:
        out.append("No failures.")

    out += ["", "## Per-task results", "", "Each cell is passed runs / scored runs.", ""]
    task_ids = sorted({r["task_id"] for r in runs})
    header = ["Task", "Group", "Title"] + [m["model"] for m in models]
    rows = []
    for task_id in task_ids:
        group, title = task_titles.get(task_id, (task_id.split("-")[0], ""))
        row = [task_id, group, title]
        for m in models:
            passed, total = m["tasks"].get(task_id, (0, 0))
            row.append(f"{passed}/{total}" if total else "-")
        rows.append(row)
    out += _table(header, rows)

    out += [
        "",
        "## How to read this report",
        "",
        "- A run passes only when every tool call is valid, the right tools were used, and the repository ends in the expected state.",
        "- Failure types explain why a run failed; see docs/TECH_SPEC.md for the full list and their priority.",
        "- tok/s and s/task are medians. Compare models only when the settings above are the same.",
        "- Calls vs ref is the number of tool calls divided by the reference solution's number; 1.00 is ideal.",
        "",
    ]
    return "\n".join(out)


def markdown_to_html(markdown: str, title: str) -> str:
    """A tiny converter for the subset of Markdown this report uses: headings, tables, bullets, paragraphs."""
    body: list[str] = []
    lines = markdown.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            rows = [[c.strip() for c in row.strip().strip("|").split("|")] for row in block]
            head, rest = rows[0], [r for r in rows[2:]]
            table = ["<table>", "<thead><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in head) + "</tr></thead>", "<tbody>"]
            table += ["<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rest]
            table += ["</tbody>", "</table>"]
            body.append("\n".join(table))
            continue
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{html.escape(lines[i][2:])}</li>")
                i += 1
            body.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif line.strip():
            body.append(f"<p>{html.escape(line)}</p>")
        i += 1
    style = (
        "body{font-family:-apple-system,system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}"
        "table{border-collapse:collapse;margin:1rem 0;font-size:.9rem}"
        "th,td{border:1px solid #ccc;padding:.35rem .6rem;text-align:left}"
        "th{background:#f3f3f3}tr:nth-child(even) td{background:#fafafa}"
    )
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{style}</style></head><body>\n" + "\n".join(body) + "\n</body></html>\n"
    )
