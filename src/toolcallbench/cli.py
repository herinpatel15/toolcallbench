"""Command-line interface: list-tasks, validate-tasks, doctor, run, report, sessions."""
from __future__ import annotations

import argparse
import hashlib
import platform
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .backends import BACKEND_KINDS, PROFILES, BackendError, OllamaBackend, OpenAICompatBackend, ScriptedBackend, make_backend
from .config import ConfigError, ModelSpec, RunConfig, find_project_root, load_config
from .models import Task
from .report import markdown_to_html, render_markdown
from .runner import SYSTEM_PROMPT, run_once
from .store import Store, new_session_id, write_log
from .tasks import TaskError, load_tasks, select_tasks
from .tools import run_trusted

DEFAULT_HOSTS = {"ollama": "http://localhost:11434", "openai-compat": "http://localhost:8080", "scripted": ""}


# ----------------------------------------------------------------------- helpers


def _split(value: str | None) -> list[str] | None:
    return [part.strip() for part in value.split(",") if part.strip()] if value else None


def _paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    root = Path(args.root).resolve() if args.root else find_project_root()
    tasks_dir = Path(args.tasks_dir) if args.tasks_dir else root / "tasks"
    fixture = Path(args.fixture) if args.fixture else root / "fixtures" / "repo"
    results = Path(args.results_dir) if args.results_dir else root / "results"
    return root, tasks_dir, fixture, results


def _titles(tasks: list[Task]) -> dict[str, tuple[str, str]]:
    return {t.id: (t.group, t.title) for t in tasks}


def build_config(args: argparse.Namespace) -> RunConfig:
    cfg = load_config(Path(args.config)) if args.config else RunConfig()
    if args.backend:
        cfg.backend = args.backend
    if args.host:
        cfg.host = args.host
    for name in ("num_ctx", "temperature", "seed", "repeats", "max_calls", "max_turns"):
        value = getattr(args, name)
        if value is not None:
            setattr(cfg, name, value)
    if args.kv_cache_type:
        cfg.declared_kv_cache_type = args.kv_cache_type
    if args.flash_attention:
        cfg.declared_flash_attention = True
    if args.profile:
        cfg.profile = args.profile
    if args.model:
        cfg.models = [ModelSpec(name=m) for m in args.model]
    if args.think != "default":
        for spec in cfg.models:
            spec.think = args.think == "on"
    cfg.host = cfg.host or DEFAULT_HOSTS.get(cfg.backend, "")
    if cfg.backend == "scripted" and not cfg.models:
        cfg.models = [ModelSpec(name=f"scripted-{cfg.profile}")]
    if not cfg.models:
        raise ConfigError("no models given: use --model NAME (repeatable) or --config FILE")
    if cfg.repeats < 1 or cfg.max_calls < 1 or cfg.max_turns < 1:
        raise ConfigError("repeats, max_calls and max_turns must be at least 1")
    return cfg


def _session_settings(cfg: RunConfig, tasks: list[Task]) -> dict[str, Any]:
    return {
        "backend": cfg.backend,
        "host": cfg.host,
        "num_ctx": cfg.num_ctx,
        "temperature": cfg.temperature,
        "seed": cfg.seed,
        "repeats": cfg.repeats,
        "max_calls": cfg.max_calls,
        "max_turns": cfg.max_turns,
        "declared_kv_cache_type": cfg.declared_kv_cache_type,
        "declared_flash_attention": cfg.declared_flash_attention,
        "think": {m.name: m.think for m in cfg.models},
        "system_prompt_sha": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:12],
        "toolcallbench_version": __version__,
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.machine()}",
        "tasks": [t.id for t in tasks],
    }


def write_reports(store: Store, session_id: str, results_dir: Path, tasks: list[Task]) -> tuple[Path, Path]:
    markdown = render_markdown(store, session_id, _titles(tasks))
    out_dir = results_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{session_id}.md"
    html_path = out_dir / f"{session_id}.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(markdown_to_html(markdown, f"ToolCallBench {session_id}"), encoding="utf-8")
    return md_path, html_path


# ---------------------------------------------------------------------- commands


def cmd_list_tasks(args: argparse.Namespace) -> int:
    _, tasks_dir, _, _ = _paths(args)
    tasks = load_tasks(tasks_dir)
    if args.markdown:
        print("| Task | Group | Title | Tool named in prompt | Reference calls |")
        print("| --- | --- | --- | --- | --- |")
        for t in tasks:
            print(f"| {t.id} | {t.group} | {t.title} | {'yes' if t.tools_named else 'no'} | {t.baseline_calls} |")
    else:
        for t in tasks:
            print(f"{t.id:<12} {t.group:<8} calls={t.baseline_calls}  {t.title}")
        print(f"\n{len(tasks)} tasks")
    return 0


def cmd_validate_tasks(args: argparse.Namespace) -> int:
    _, tasks_dir, fixture, _ = _paths(args)
    tasks = select_tasks(load_tasks(tasks_dir), _split(args.tasks), _split(args.groups))
    backend = ScriptedBackend(tasks, "oracle")
    failed = 0
    for task in tasks:
        record = run_once(task, backend, fixture)
        ok = record.status == "ok" and record.check is not None and record.check.passed
        print(f"{'PASS' if ok else 'FAIL'}  {task.id:<12} {task.title}")
        if not ok:
            failed += 1
            for line in (record.check.details if record.check else [record.error]):
                print(f"      {line}")
    print(f"\n{len(tasks) - failed}/{len(tasks)} reference solutions pass")
    return 1 if failed else 0


def _line(ok: bool, label: str, detail: str = "") -> bool:
    print(f"[{' OK ' if ok else 'FAIL'}] {label}" + (f": {detail}" if detail else ""))
    return ok


def cmd_doctor(args: argparse.Namespace) -> int:
    _, tasks_dir, fixture, _ = _paths(args)
    all_ok = True
    all_ok &= _line(sys.version_info >= (3, 10), "Python 3.10 or newer", platform.python_version())
    tasks: list[Task] = []
    try:
        tasks = load_tasks(tasks_dir)
        all_ok &= _line(True, "task files", f"{len(tasks)} tasks in {tasks_dir}")
    except TaskError as exc:
        all_ok &= _line(False, "task files", str(exc))
    if fixture.is_dir():
        with tempfile.TemporaryDirectory(prefix="tcb-doctor-") as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(fixture, copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
            proc = run_trusted(["python", "-m", "pytest", "-q"], copy)
            match = re.search(r"(\d+) failed", proc.stdout)
            failing = int(match.group(1)) if match else 0
            if "No module named pytest" in proc.stderr + proc.stdout:
                all_ok &= _line(False, "pytest in this Python", "not installed; run: pip install pytest")
            else:
                all_ok &= _line(failing == 2, "fixture repo", f"{failing} failing test(s); the tasks expect exactly 2")
    else:
        all_ok &= _line(False, "fixture repo", f"not found at {fixture}")

    kind = args.backend or "ollama"
    host = args.host or DEFAULT_HOSTS[kind]
    if kind == "scripted":
        _line(True, "backend", "scripted (no server needed)")
        return 0 if all_ok else 1
    probe_backends = []
    cfg = load_config(Path(args.config)) if args.config else RunConfig()
    think_by_model = {spec.name: spec.think for spec in cfg.models}
    try:
        if kind == "ollama":
            first = OllamaBackend(args.model[0] if args.model else "", host=host, timeout=10)
            version = first.version()
            installed = first.list_models()
            all_ok &= _line(True, "Ollama server", f"version {version} at {host}; {len(installed)} model(s) installed")
            for name in args.model or []:
                backend = OllamaBackend(
                    name, host=host, options=cfg.options_for(1), think=think_by_model.get(name), timeout=cfg.request_timeout
                )
                if not ({name, name if ":" in name else name + ":latest"} & set(installed)):
                    all_ok &= _line(False, f"model {name}", f"not installed; run: ollama pull {name}")
                    continue
                info = backend.describe()
                caps = info.get("capabilities") or []
                if caps and "tools" not in caps:
                    all_ok &= _line(False, f"model {name}", f"does not report tool support (capabilities: {caps})")
                    continue
                note = "tools supported" if caps else "capabilities not reported by this Ollama version"
                _line(True, f"model {name}", f"{info.get('parameter_size', '?')} {info.get('quant', '?')}; {note}")
                probe_backends.append(backend)
        else:
            OpenAICompatBackend("probe", base_url=host, timeout=10).check()
            all_ok &= _line(True, "OpenAI-compatible server", f"reachable at {host}")
            if args.probe:
                for name in args.model or []:
                    probe_backends.append(OpenAICompatBackend(name, base_url=host, timeout=120))
    except BackendError as exc:
        all_ok &= _line(False, "model server", f"{exc}" + ("; start it with: ollama serve" if kind == "ollama" else ""))
    if args.probe and probe_backends and tasks:
        task = next(t for t in tasks if t.id == "read-01")
        for backend in probe_backends:
            record = run_once(task, backend, fixture)
            if record.status == "error":
                all_ok &= _line(False, f"probe {backend.model}", record.error)
            else:
                check = record.check
                tps = record.transcript.eval_tokens / record.transcript.eval_seconds if record.transcript.eval_seconds else 0
                all_ok &= _line(
                    check.passed,
                    f"probe {backend.model}",
                    f"read-01 {'passed' if check.passed else 'failed: ' + check.failure_type} "
                    f"in {record.transcript.wall_seconds:.1f}s, {tps:.1f} tok/s",
                )
    return 0 if all_ok else 1


def cmd_run(args: argparse.Namespace) -> int:
    _, tasks_dir, fixture, results_dir = _paths(args)
    cfg = build_config(args)
    tasks = select_tasks(load_tasks(tasks_dir), _split(args.tasks), _split(args.groups))
    store = Store(results_dir / "results.sqlite")
    session_id = args.session or new_session_id()
    if store.session_exists(session_id):
        if not args.resume:
            print(f"session '{session_id}' already exists; add --resume to continue it", file=sys.stderr)
            return 2
    else:
        store.create_session(session_id, _session_settings(cfg, tasks))
    total = len(cfg.models) * len(tasks) * cfg.repeats
    print(f"session {session_id}: {len(cfg.models)} model(s) x {len(tasks)} task(s) x {cfg.repeats} repeat(s) = {total} runs")
    done = 0
    for spec in cfg.models:
        backend = make_backend(
            cfg.backend,
            model=spec.name,
            host=cfg.host,
            options=cfg.options_for(1),
            think=spec.think,
            timeout=cfg.request_timeout,
            tasks=tasks,
            profile=cfg.profile,
        )
        try:
            backend.check()
        except BackendError as exc:
            print(f"error: {exc}", file=sys.stderr)
            store.close()
            return 1
        info = backend.describe()
        quant = str(info.get("quant", ""))
        if info.get("backend_version"):
            store.merge_settings(session_id, {"backend_version": info["backend_version"]})
        consecutive_errors = 0
        aborted = False
        for task in tasks:
            if aborted:
                break
            for repeat in range(1, cfg.repeats + 1):
                done += 1
                if store.has_run(session_id, spec.name, task.id, repeat):
                    continue
                if hasattr(backend, "options"):
                    backend.options = cfg.options_for(repeat)
                record = run_once(task, backend, fixture, max_calls=cfg.max_calls, max_turns=cfg.max_turns)
                log_path = write_log(results_dir, session_id, spec.name, repeat, record)
                store.add_run(session_id, model=spec.name, quant=quant, backend=cfg.backend, repeat=repeat, record=record, log_path=log_path)
                if record.status == "error":
                    verdict = f"ERROR ({record.error[:60]})"
                    consecutive_errors += 1
                else:
                    verdict = "PASS" if record.check.passed else f"FAIL ({record.check.failure_type})"
                    consecutive_errors = 0
                print(f"[{done}/{total}] {spec.name} {task.id} rep {repeat}: {verdict} {record.transcript.wall_seconds:.1f}s", flush=True)
                if consecutive_errors >= 3:
                    print(f"stopping {spec.name}: 3 backend errors in a row", file=sys.stderr)
                    aborted = True
                    break
    store.finish_session(session_id)
    md_path, html_path = write_reports(store, session_id, results_dir, tasks)
    print(f"\nreport: {md_path}\n        {html_path}")
    store.close()
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    _, tasks_dir, _, results_dir = _paths(args)
    db = results_dir / "results.sqlite"
    if not db.exists():
        print(f"no results database at {db}; run a benchmark first", file=sys.stderr)
        return 1
    store = Store(db)
    session_id = store.latest_session_id() if args.session in (None, "latest") else args.session
    if session_id is None or not store.session_exists(session_id):
        print(f"no such session: {args.session}", file=sys.stderr)
        return 1
    try:
        tasks = load_tasks(tasks_dir)
    except TaskError:
        tasks = []
    md_path, html_path = write_reports(store, session_id, results_dir, tasks)
    if args.print:
        print(md_path.read_text(encoding="utf-8"))
    print(f"report: {md_path}\n        {html_path}")
    store.close()
    return 0


def cmd_sessions(args: argparse.Namespace) -> int:
    _, _, _, results_dir = _paths(args)
    db = results_dir / "results.sqlite"
    if not db.exists():
        print("no sessions yet")
        return 0
    store = Store(db)
    for s in store.list_sessions():
        state = "finished" if s["finished_at"] else "unfinished"
        print(f"{s['session_id']}  {s['runs']:>5} runs  {state}")
    store.close()
    return 0


# ------------------------------------------------------------------------ parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toolcallbench", description="Benchmark tool-calling reliability of local LLMs.")
    parser.add_argument("--version", action="version", version=f"toolcallbench {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="project folder holding tasks/ and fixtures/ (default: found from the current folder)")
    common.add_argument("--tasks-dir", help="folder of task YAML files")
    common.add_argument("--fixture", help="fixture repository to copy for every run")
    common.add_argument("--results-dir", help="where results.sqlite, logs and reports go")

    p = sub.add_parser("list-tasks", parents=[common], help="list the benchmark tasks")
    p.add_argument("--markdown", action="store_true", help="print a Markdown table")
    p.set_defaults(func=cmd_list_tasks)

    p = sub.add_parser("validate-tasks", parents=[common], help="run every task's reference solution through the checker")
    p.add_argument("--tasks", help="comma-separated task ids")
    p.add_argument("--groups", help="comma-separated groups")
    p.set_defaults(func=cmd_validate_tasks)

    p = sub.add_parser("doctor", parents=[common], help="check the setup and optionally probe a model")
    p.add_argument("--backend", choices=BACKEND_KINDS)
    p.add_argument("--host")
    p.add_argument("--model", action="append", help="model to check (repeatable)")
    p.add_argument("--config", help="YAML config file; the probe then uses its settings (num_ctx, temperature, think, timeout)")
    p.add_argument("--probe", action="store_true", help="run one real task against each model")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("run", parents=[common], help="run the benchmark")
    p.add_argument("--config", help="YAML config file (see configs/)")
    p.add_argument("--backend", choices=BACKEND_KINDS)
    p.add_argument("--host", help="server address")
    p.add_argument("--model", action="append", help="model name (repeatable); replaces models from --config")
    p.add_argument("--think", choices=["default", "on", "off"], default="default", help="Ollama thinking mode for thinking-capable models")
    p.add_argument("--num-ctx", type=int, dest="num_ctx")
    p.add_argument("--temperature", type=float)
    p.add_argument("--seed", type=int)
    p.add_argument("--repeats", type=int)
    p.add_argument("--max-calls", type=int, dest="max_calls")
    p.add_argument("--max-turns", type=int, dest="max_turns")
    p.add_argument("--kv-cache-type", dest="kv_cache_type", help="KV cache type your server was started with (recorded only)")
    p.add_argument("--flash-attention", action="store_true", help="record that the server runs with flash attention")
    p.add_argument("--profile", choices=PROFILES, help="behaviour of the scripted backend")
    p.add_argument("--tasks", help="comma-separated task ids")
    p.add_argument("--groups", help="comma-separated groups")
    p.add_argument("--session", help="session id; with --resume continues an earlier session")
    p.add_argument("--resume", action="store_true", help="skip runs already stored in the session")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report", parents=[common], help="build the Markdown and HTML report for a session")
    p.add_argument("--session", help="session id or 'latest' (default)")
    p.add_argument("--print", action="store_true", help="also print the Markdown report")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("sessions", parents=[common], help="list stored sessions")
    p.set_defaults(func=cmd_sessions)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (TaskError, ConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\ninterrupted; continue later with --resume", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
