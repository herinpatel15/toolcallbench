"""Command-line interface: init, list-tasks, validate-tasks, doctor, run, report, sessions, compare, export."""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .backends import BACKEND_KINDS, PROFILES, BackendError, OllamaBackend, OpenAICompatBackend, ScriptedBackend, make_backend
from .compare import render_compare
from .config import DEFAULT_API_KEY_ENV, ConfigError, ModelSpec, RunConfig, data_dir, find_project_root, load_config
from .export import FORMATS, export_session
from .models import Task
from .report import markdown_to_html, render_markdown
from .runner import SYSTEM_PROMPT, run_once
from .store import Store, new_session_id, write_log
from .tasks import TaskError, load_tasks, select_tasks, tasks_fingerprint
from .tools import TOOLS_OFFERED_MODES, run_trusted

DEFAULT_HOSTS = {"ollama": "http://localhost:11434", "openai-compat": "http://localhost:8080", "scripted": ""}


# ----------------------------------------------------------------------- helpers


def _split(value: str | None) -> list[str] | None:
    return [part.strip() for part in value.split(",") if part.strip()] if value else None


def _paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    root = Path(args.root).resolve() if args.root else find_project_root()
    local_tasks, local_fixture = root / "tasks", root / "fixtures" / "repo"
    custom = local_tasks.is_dir() and local_fixture.is_dir()  # a folder with its own tasks wins over the built-in ones
    tasks_dir = Path(args.tasks_dir) if args.tasks_dir else local_tasks if custom else data_dir() / "tasks"
    fixture = Path(args.fixture) if args.fixture else local_fixture if custom else data_dir() / "fixtures" / "repo"
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
    if args.tools_offered:
        cfg.tools_offered = args.tools_offered
    if args.max_calls_per_turn is not None:
        cfg.max_calls_per_turn = args.max_calls_per_turn
    if args.api_key_env:
        cfg.api_key_env = args.api_key_env
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
    if cfg.max_calls_per_turn < 0:
        raise ConfigError("max_calls_per_turn must be 0 or more")
    cfg.api_key_env, cfg.api_key = resolve_api_key(cfg.backend, cfg.api_key_env)
    return cfg


def resolve_api_key(backend: str, env_name: str) -> tuple[str, str]:
    """Read the API key from an environment variable. The key itself is never accepted on the command line or in YAML."""
    if backend != "openai-compat":
        if env_name:
            raise ConfigError("an API key is only used with --backend openai-compat")
        return "", ""
    name = env_name or DEFAULT_API_KEY_ENV
    key = os.environ.get(name, "")
    if env_name and not key:
        raise ConfigError(f"environment variable {env_name} is not set (it should hold your API key)")
    return (name if key else ""), key


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
        "tools_offered": cfg.tools_offered,
        "max_calls_per_turn": cfg.max_calls_per_turn,
        "api_key_env": cfg.api_key_env or "none",
        "tasks_sha": tasks_fingerprint(tasks),
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
        print("| Task | Group | Title | Tool named in prompt | Reference calls | In default run |")
        print("| --- | --- | --- | --- | --- | --- |")
        for t in tasks:
            print(f"| {t.id} | {t.group} | {t.title} | {'yes' if t.tools_named else 'no'} | {t.baseline_calls} | {'no (optional)' if t.optional else 'yes'} |")
    else:
        for t in tasks:
            mark = "  [optional]" if t.optional else ""
            print(f"{t.id:<12} {t.group:<8} calls={t.baseline_calls}  {t.title}{mark}")
        core = sum(1 for t in tasks if not t.optional)
        print(f"\n{len(tasks)} tasks ({core} in a default run, {len(tasks) - core} optional: select them with --groups or --tasks)")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Copy the example configs (and optionally the tasks and fixture repo) into a working folder."""
    target = Path(args.dir).resolve()
    copies = [(data_dir() / "configs", target / "configs")]
    if args.with_tasks:
        copies += [(data_dir() / "tasks", target / "tasks"), (data_dir() / "fixtures" / "repo", target / "fixtures" / "repo")]
    existing = [dest for _, dest in copies if dest.exists()]
    if existing:
        for dest in existing:
            print(f"error: {dest} already exists; remove it or pick another folder", file=sys.stderr)
        return 1
    for src, dest in copies:
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
        print(f"created {dest.relative_to(target)}/")
    print("\nNext:")
    print("  1. Edit configs/my-models.yaml and list the models you have pulled in Ollama")
    print("  2. toolcallbench doctor --probe --config configs/my-models.yaml")
    print("  3. toolcallbench run --config configs/my-models.yaml")
    return 0


def cmd_validate_tasks(args: argparse.Namespace) -> int:
    _, tasks_dir, fixture, _ = _paths(args)
    tasks = select_tasks(load_tasks(tasks_dir), _split(args.tasks), _split(args.groups), include_optional=True)
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
            key_name, key = resolve_api_key("openai-compat", args.api_key_env or cfg.api_key_env)
            OpenAICompatBackend("probe", base_url=host, timeout=10, api_key=key).check()
            all_ok &= _line(True, "OpenAI-compatible server", f"reachable at {host}" + (f" (API key from {key_name})" if key else ""))
            if args.probe:
                for name in args.model or []:
                    probe_backends.append(OpenAICompatBackend(name, base_url=host, timeout=120, api_key=key))
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
            api_key=cfg.api_key,
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
                record = run_once(
                    task,
                    backend,
                    fixture,
                    max_calls=cfg.max_calls,
                    max_turns=cfg.max_turns,
                    tools_offered=cfg.tools_offered,
                    max_calls_per_turn=cfg.max_calls_per_turn,
                )
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


def _open_store(args: argparse.Namespace) -> tuple[Store | None, Path]:
    _, _, _, results_dir = _paths(args)
    db = results_dir / "results.sqlite"
    if not db.exists():
        print(f"no results database at {db}; run a benchmark first", file=sys.stderr)
        return None, results_dir
    return Store(db), results_dir


def _resolve_session(store: Store, name: str | None, offset: int = 0) -> str | None:
    """'latest' is the newest session, 'previous' the one before it; anything else is a session id."""
    sessions = [s["session_id"] for s in store.list_sessions()]
    if name in (None, "latest"):
        return sessions[offset] if len(sessions) > offset else None
    if name == "previous":
        return sessions[1] if len(sessions) > 1 else None
    return name if store.session_exists(name) else None


def cmd_compare(args: argparse.Namespace) -> int:
    store, results_dir = _open_store(args)
    if store is None:
        return 1
    id_b = _resolve_session(store, args.second or "latest")
    id_a = _resolve_session(store, args.first or "previous")
    if id_a is None or id_b is None:
        print("need two sessions to compare; see: toolcallbench sessions", file=sys.stderr)
        store.close()
        return 1
    if id_a == id_b:
        print("both names point at the same session", file=sys.stderr)
        store.close()
        return 1
    markdown = render_compare(store, id_a, id_b)
    out_dir = results_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"compare-{id_a}-vs-{id_b}.md"
    path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"saved: {path}")
    store.close()
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store, results_dir = _open_store(args)
    if store is None:
        return 1
    session_id = _resolve_session(store, args.session)
    if session_id is None:
        print(f"no such session: {args.session}", file=sys.stderr)
        store.close()
        return 1
    text = export_session(store, session_id, args.format)
    if args.output == "-":
        sys.stdout.write(text)
    else:
        path = Path(args.output) if args.output else results_dir / "exports" / f"{session_id}.{args.format}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"exported {session_id} to {path}")
    store.close()
    return 0


# ------------------------------------------------------------------------ parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toolcallbench", description="Benchmark tool-calling reliability of local LLMs.")
    parser.add_argument("--version", action="version", version=f"toolcallbench {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="working folder; results go to <root>/results (default: the current folder). A tasks/ and fixtures/repo/ inside it replace the built-in tasks")
    common.add_argument("--tasks-dir", help="folder of task YAML files")
    common.add_argument("--fixture", help="fixture repository to copy for every run")
    common.add_argument("--results-dir", help="where results.sqlite, logs and reports go")

    p = sub.add_parser("init", help="create a working folder with example configs")
    p.add_argument("dir", nargs="?", default=".", help="folder to create files in (default: the current folder)")
    p.add_argument("--with-tasks", action="store_true", help="also copy the 20 tasks and the fixture repo so you can edit them")
    p.set_defaults(func=cmd_init)

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
    p.add_argument("--api-key-env", dest="api_key_env", help="NAME of the environment variable holding an API key (openai-compat backend only)")
    p.add_argument("--probe", action="store_true", help="run one real task against each model")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("run", parents=[common], help="run the benchmark")
    p.add_argument("--config", help="YAML config file (create examples with: toolcallbench init)")
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
    p.add_argument("--tools-offered", choices=TOOLS_OFFERED_MODES, dest="tools_offered", help="all (default): every tool; task: only the tools the task's reference solution uses (an ablation)")
    p.add_argument("--max-calls-per-turn", type=int, dest="max_calls_per_turn", help="run only this many calls from each model reply (default 0: run all of them)")
    p.add_argument("--api-key-env", dest="api_key_env", help="NAME of the environment variable holding an API key (openai-compat backend only). The key itself is never taken as an argument")
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

    p = sub.add_parser("compare", parents=[common], help="compare two sessions: pass rates, changed tasks, failure families")
    p.add_argument("first", nargs="?", help="session id, or 'previous' (default)")
    p.add_argument("second", nargs="?", help="session id, or 'latest' (default)")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("export", parents=[common], help="write a session's runs as JSON or CSV")
    p.add_argument("--session", help="session id or 'latest' (default)")
    p.add_argument("--format", choices=FORMATS, default="json")
    p.add_argument("--output", help="file to write; '-' prints to the terminal (default: results/exports/<session>.<format>)")
    p.set_defaults(func=cmd_export)
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
