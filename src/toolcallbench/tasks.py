"""Load and validate task files (tasks/*.yaml)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .models import GROUPS, Task
from .tools import EXTRA_TOOL_NAMES

EXPECT_KEYS = {
    "calls",
    "min_calls",
    "max_calls",
    "ordered",
    "after_last_edit",
    "parallel",
    "no_tool_calls",
    "forbidden_tools",
    "files_exist",
    "final_files",
    "command",
    "answer_contains",
    "answer_regex",
}

_CALL = {
    "type": "object",
    "required": ["tool"],
    "additionalProperties": False,
    "properties": {
        "tool": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}, "minItems": 1}]},
        "args": {"type": "object"},
    },
}

TASK_SCHEMA = {
    "type": "object",
    "required": ["id", "group", "title", "prompt", "expect", "reference"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": "^[a-z]+-[0-9]{2}$"},
        "group": {"enum": list(GROUPS)},
        "title": {"type": "string", "minLength": 1},
        "tools_named": {"type": "boolean"},
        "optional": {"type": "boolean"},
        "version": {"type": "integer", "minimum": 1},
        "extra_tools": {"type": "array", "items": {"enum": list(EXTRA_TOOL_NAMES)}, "uniqueItems": True},
        "prompt": {"type": "string", "minLength": 1},
        "expect": {"type": "object"},
        "reference": {
            "type": "array",
            "minItems": 1,
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "required": ["calls"],
                        "additionalProperties": False,
                        "properties": {
                            "calls": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "object",
                                    "required": ["tool"],
                                    "additionalProperties": False,
                                    "properties": {"tool": {"type": "string"}, "args": {"type": "object"}},
                                },
                            }
                        },
                    },
                    {
                        "type": "object",
                        "required": ["final"],
                        "additionalProperties": False,
                        "properties": {"final": {"type": "string"}},
                    },
                ]
            },
        },
    },
}


class TaskError(ValueError):
    """A task file is invalid."""


def _validate_expect(expect: dict[str, Any], where: str) -> None:
    unknown = set(expect) - EXPECT_KEYS
    if unknown:
        raise TaskError(f"{where}: unknown expect keys {sorted(unknown)}; allowed: {sorted(EXPECT_KEYS)}")
    for req in expect.get("calls", []):
        try:
            jsonschema.validate(req, _CALL)
        except jsonschema.ValidationError as exc:
            raise TaskError(f"{where}: bad expect.calls entry: {exc.message}") from exc
    for req in expect.get("after_last_edit", []):
        try:
            jsonschema.validate(req, _CALL)
        except jsonschema.ValidationError as exc:
            raise TaskError(f"{where}: bad expect.after_last_edit entry: {exc.message}") from exc
    for item in expect.get("command", []):
        if not isinstance(item, dict) or not isinstance(item.get("argv"), list):
            raise TaskError(f"{where}: each expect.command entry needs an argv list")


def load_task_file(path: Path) -> Task:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaskError(f"{path.name}: invalid YAML: {exc}") from exc
    try:
        jsonschema.validate(data, TASK_SCHEMA)
    except jsonschema.ValidationError as exc:
        location = "/".join(str(p) for p in exc.absolute_path) or "top level"
        raise TaskError(f"{path.name}: {exc.message} (at {location})") from exc
    if data["id"].split("-")[0] != data["group"]:
        raise TaskError(f"{path.name}: id '{data['id']}' must start with its group '{data['group']}'")
    _validate_expect(data["expect"], path.name)
    if "final" not in data["reference"][-1]:
        raise TaskError(f"{path.name}: the last reference step must be a 'final' answer")
    return Task(
        id=data["id"],
        group=data["group"],
        title=data["title"],
        prompt=data["prompt"].strip(),
        expect=data["expect"],
        reference=data["reference"],
        tools_named=bool(data.get("tools_named", False)),
        optional=bool(data.get("optional", False)),
        extra_tools=list(data.get("extra_tools", [])),
        version=int(data.get("version", 1)),
    )


def load_tasks(tasks_dir: Path) -> list[Task]:
    tasks_dir = Path(tasks_dir)
    files = sorted(tasks_dir.glob("*.yaml"))
    if not files:
        raise TaskError(f"no task files (*.yaml) found in {tasks_dir}")
    tasks = [load_task_file(f) for f in files]
    seen: set[str] = set()
    for task in tasks:
        if task.id in seen:
            raise TaskError(f"duplicate task id '{task.id}'")
        seen.add(task.id)
    return tasks


def select_tasks(
    tasks: list[Task],
    ids: list[str] | None = None,
    groups: list[str] | None = None,
    include_optional: bool = False,
) -> list[Task]:
    """Pick tasks. Optional tasks are left out of a default run; naming them (ids or groups) brings them in."""
    selected = tasks
    if ids:
        unknown = set(ids) - {t.id for t in tasks}
        if unknown:
            raise TaskError(f"unknown task ids: {sorted(unknown)}")
        selected = [t for t in selected if t.id in ids]
    if groups:
        unknown = set(groups) - set(GROUPS)
        if unknown:
            raise TaskError(f"unknown groups: {sorted(unknown)}; choose from {', '.join(GROUPS)}")
        selected = [t for t in selected if t.group in groups]
    if not ids and not groups and not include_optional:
        selected = [t for t in selected if not t.optional]
    if not selected:
        raise TaskError("no tasks selected")
    return selected


def tasks_fingerprint(tasks: list[Task]) -> str:
    """A short hash of everything that decides how a task is run and scored. Used to warn when two sessions differ."""
    payload = [
        {
            "id": t.id,
            "version": t.version,
            "prompt": t.prompt,
            "expect": t.expect,
            "extra_tools": t.extra_tools,
        }
        for t in sorted(tasks, key=lambda t: t.id)
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
