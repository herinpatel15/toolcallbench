"""Compare two sessions: what changed between two runs of the benchmark."""
from __future__ import annotations

from typing import Any

from .report import FAILURE_FAMILIES, _fmt, _pct, _table, aggregate
from .stats import format_range, ranges_overlap
from .store import Store

# Settings that change how a model behaves or how runs are scored. A difference here may explain a difference in results.
COMPARED_SETTINGS = [
    ("backend", "Backend"),
    ("backend_version", "Backend version"),
    ("host", "Host"),
    ("num_ctx", "Context length"),
    ("temperature", "Temperature"),
    ("seed", "Base seed"),
    ("repeats", "Repeats"),
    ("max_calls", "Call limit"),
    ("max_turns", "Turn limit"),
    ("tools_offered", "Tools offered"),
    ("max_calls_per_turn", "Calls run per reply"),
    ("declared_kv_cache_type", "KV cache type"),
    ("declared_flash_attention", "Flash attention"),
    ("think", "Thinking mode"),
    ("system_prompt_sha", "System prompt hash"),
    ("tasks_sha", "Task set hash"),
    ("toolcallbench_version", "ToolCallBench version"),
]


def _same(a: Any, b: Any) -> bool:
    return a == b


def settings_differences(a: dict[str, Any], b: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    rows = []
    for key, label in COMPARED_SETTINGS:
        left, right = a.get(key, "-"), b.get(key, "-")
        if not _same(left, right):
            rows.append((label, left, right))
    return rows


def _verdict(first: dict[str, Any], second: dict[str, Any]) -> str:
    if not first["scored"] or not second["scored"]:
        return "-"
    if ranges_overlap(first["range"], second["range"]):
        return "no clear difference"
    return "better in B" if first["range"][1] < second["range"][0] else "worse in B"


def _family_counts(model: dict[str, Any]) -> dict[str, int]:
    return {family: sum(model["failures"].get(t, 0) for t in types) for family, types in FAILURE_FAMILIES.items()}


def render_compare(store: Store, id_a: str, id_b: str) -> str:
    runs_a, runs_b = store.runs(id_a), store.runs(id_b)
    set_a, set_b = store.session(id_a)["settings"], store.session(id_b)["settings"]
    models_a = {m["model"]: m for m in aggregate(runs_a)["models"]}
    models_b = {m["model"]: m for m in aggregate(runs_b)["models"]}
    both = [name for name in models_a if name in models_b]

    out = [f"# ToolCallBench comparison: {id_a} (A) vs {id_b} (B)", ""]

    out += ["## Are the two runs comparable?", ""]
    differences = settings_differences(set_a, set_b)
    if differences:
        out += ["These settings differ, so a change in results may come from them and not from the model:", ""]
        out += _table(["Setting", "A", "B"], [[label, str(x), str(y)] for label, x, y in differences])
    else:
        out.append("The settings, task set and versions are identical.")
    if set_a.get("tasks_sha") and set_b.get("tasks_sha") and set_a["tasks_sha"] != set_b["tasks_sha"]:
        out += ["", "**The task sets differ.** Compare only the tasks both runs share, and treat overall pass rates with care."]

    out += ["", "## Pass rate by model", ""]
    if both:
        rows = []
        for name in both:
            a, b = models_a[name], models_b[name]
            change = "-"
            if a["scored"] and b["scored"]:
                change = f"{100 * (b['passed'] / b['scored'] - a['passed'] / a['scored']):+.1f} pts"
            rows.append(
                [
                    name,
                    f"{_pct(a['passed'], a['scored'])} ({format_range(a['passed'], a['scored'])})",
                    f"{_pct(b['passed'], b['scored'])} ({format_range(b['passed'], b['scored'])})",
                    change,
                    _verdict(a, b),
                    f"{_fmt(a['seconds'])} / {_fmt(b['seconds'])}",
                ]
            )
        out += _table(["Model", "Pass A (95% range)", "Pass B (95% range)", "Change", "Verdict", "s/task A / B"], rows)
        out += ["", "'No clear difference' means the 95% ranges overlap: the change could be noise."]
    else:
        out.append("The two sessions have no model in common.")
    only_a = [n for n in models_a if n not in models_b]
    only_b = [n for n in models_b if n not in models_a]
    if only_a:
        out += ["", f"Only in A: {', '.join(only_a)}"]
    if only_b:
        out += ["", f"Only in B: {', '.join(only_b)}"]

    out += ["", "## Tasks that changed", ""]
    rows = []
    for name in both:
        for task_id in sorted(set(models_a[name]["tasks"]) & set(models_b[name]["tasks"])):
            pa, ta = models_a[name]["tasks"][task_id]
            pb, tb = models_b[name]["tasks"][task_id]
            if ta and tb and pa / ta != pb / tb:
                arrow = "improved" if pb / tb > pa / ta else "got worse"
                rows.append([name, task_id, f"{pa}/{ta}", f"{pb}/{tb}", arrow])
    out += _table(["Model", "Task", "A", "B", "Change"], rows) if rows else ["No task changed."]

    out += ["", "## Why runs failed: change by family", ""]
    rows = []
    for name in both:
        fa, fb = _family_counts(models_a[name]), _family_counts(models_b[name])
        for family in FAILURE_FAMILIES:
            if fa[family] != fb[family]:
                rows.append([name, family, str(fa[family]), str(fb[family])])
    out += _table(["Model", "Failure family", "A", "B"], rows) if rows else ["No change in failure families."]
    out.append("")
    return "\n".join(out)
