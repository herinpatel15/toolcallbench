"""Tests for v1.1.0: confidence ranges, compare, export, nested tools, tool options, API key."""
import csv
import io
import json
import sqlite3

import pytest

from mock_servers import mock_server
from toolcallbench.backends import OpenAICompatBackend
from toolcallbench.backends.scripted import ScriptedBackend
from toolcallbench.checks import evaluate
from toolcallbench.cli import main as cli_main
from toolcallbench.compare import render_compare, settings_differences
from toolcallbench.config import ConfigError, load_config
from toolcallbench.export import export_session
from toolcallbench.models import CallRecord, Transcript
from toolcallbench.report import render_markdown
from toolcallbench.runner import run_once
from toolcallbench.stats import format_range, ranges_overlap, wilson_interval
from toolcallbench.store import Store, write_log
from toolcallbench.tasks import select_tasks, tasks_fingerprint
from toolcallbench.tools import ToolExecutor, tool_specs_for, validate_arguments


def cli(*argv):
    return cli_main(list(argv))


def fill(store, sid, tasks, fixture_dir, model, profile, settings=None, repeats=1, tmp=None):
    store.create_session(sid, settings or {"repeats": repeats, "backend": "scripted"})
    backend = ScriptedBackend(tasks, profile)
    for task in tasks:
        for repeat in range(1, repeats + 1):
            record = run_once(task, backend, fixture_dir)
            log = write_log(tmp, sid, model, repeat, record)
            store.add_run(sid, model=model, quant="", backend="scripted", repeat=repeat, record=record, log_path=log)


# ------------------------------------------------------------------ confidence range


def test_wilson_interval_known_values():
    low, high = wilson_interval(19, 20)
    assert 0.74 < low < 0.78 and 0.97 < high < 1.0
    assert wilson_interval(0, 0) == (0.0, 1.0)
    low, high = wilson_interval(0, 20)
    assert low == 0.0 and 0.1 < high < 0.2


def test_more_runs_give_a_narrower_range():
    narrow = wilson_interval(150, 200)
    wide = wilson_interval(15, 20)
    assert narrow[1] - narrow[0] < wide[1] - wide[0]


def test_overlap_and_format():
    assert ranges_overlap((0.5, 0.8), (0.7, 0.9)) and not ranges_overlap((0.1, 0.3), (0.6, 0.9))
    assert format_range(15, 20).endswith("%") and format_range(0, 0) == "-"


def test_report_shows_range_and_notes_overlaps(tmp_path, tasks, fixture_dir):
    store = Store(tmp_path / "r.sqlite")
    fill(store, "s1", tasks, fixture_dir, "good", "oracle", tmp=tmp_path)
    # a second model in the same session whose score is close to the first
    backend = ScriptedBackend(tasks, "bad_edit")
    for task in tasks:
        record = run_once(task, backend, fixture_dir)
        store.add_run("s1", model="close", quant="", backend="scripted", repeat=1, record=record, log_path=write_log(tmp_path, "s1", "close", 1, record))
    md = render_markdown(store, "s1", {t.id: (t.group, t.title) for t in tasks})
    assert "95% range" in md and "Only 1 repeat" in md  # repeats below 3 are flagged


def test_overlapping_ranges_are_called_out():
    from toolcallbench.report import _noise_notes

    a = {"model": "a", "scored": 20, "passed": 17, "range": wilson_interval(17, 20)}
    b = {"model": "b", "scored": 20, "passed": 15, "range": wilson_interval(15, 20)}
    c = {"model": "c", "scored": 20, "passed": 2, "range": wilson_interval(2, 20)}
    notes = "\n".join(_noise_notes([a, b, c], 5))
    assert "a and b: no clear difference" in notes
    assert "c: no clear" not in notes and "and c" not in notes
    assert "Only" not in notes


def test_consistency_table_appears_only_with_repeats(tmp_path, tasks, fixture_dir):
    store = Store(tmp_path / "r.sqlite")
    fill(store, "one", tasks, fixture_dir, "m", "oracle", tmp=tmp_path)
    assert "Run-to-run consistency" not in render_markdown(store, "one")
    fill(store, "two", tasks, fixture_dir, "m", "oracle", repeats=2, tmp=tmp_path, settings={"repeats": 2})
    assert "Run-to-run consistency" in render_markdown(store, "two")


def test_report_hides_groups_that_were_not_run(tmp_path, tasks, fixture_dir):
    store = Store(tmp_path / "r.sqlite")
    fill(store, "s1", tasks, fixture_dir, "m", "oracle", tmp=tmp_path)
    header = next(line for line in render_markdown(store, "s1").splitlines() if line.startswith("| Model | Quant"))
    assert "Nested" not in header and "Chain" in header


# ------------------------------------------------------------------ compare / export


def test_compare_flags_differences_and_verdicts(tmp_path, tasks, fixture_dir):
    store = Store(tmp_path / "r.sqlite")
    fill(store, "a", tasks, fixture_dir, "m", "no_call", settings={"repeats": 1, "num_ctx": 4096, "tasks_sha": "aaa"}, tmp=tmp_path)
    fill(store, "b", tasks, fixture_dir, "m", "oracle", settings={"repeats": 1, "num_ctx": 8192, "tasks_sha": "bbb"}, tmp=tmp_path)
    md = render_compare(store, "a", "b")
    assert "better in B" in md and "Context length" in md and "task sets differ" in md
    assert "improved" in md and "Failure family" in md


def test_compare_identical_settings_and_same_model_noise(tmp_path, tasks, fixture_dir):
    store = Store(tmp_path / "r.sqlite")
    fill(store, "a", tasks, fixture_dir, "m", "oracle", tmp=tmp_path)
    fill(store, "b", tasks, fixture_dir, "m", "oracle", tmp=tmp_path)
    md = render_compare(store, "a", "b")
    assert "identical" in md and "no clear difference" in md and "No task changed" in md


def test_settings_differences_ignores_equal_values():
    assert settings_differences({"num_ctx": 1}, {"num_ctx": 1}) == []
    assert settings_differences({"num_ctx": 1}, {"num_ctx": 2}) == [("Context length", 1, 2)]


def test_export_json_and_csv(tmp_path, tasks, fixture_dir):
    store = Store(tmp_path / "r.sqlite")
    fill(store, "s1", tasks, fixture_dir, "m", "oracle", tmp=tmp_path)
    data = json.loads(export_session(store, "s1", "json"))
    assert data["session_id"] == "s1" and len(data["runs"]) == 20 and data["runs"][0]["model"] == "m"
    rows = list(csv.DictReader(io.StringIO(export_session(store, "s1", "csv"))))
    assert len(rows) == 20 and {"task_id", "passed", "failure_type", "prompt_tokens"} <= set(rows[0])
    with pytest.raises(ValueError):
        export_session(store, "s1", "xml")


def test_cli_compare_and_export(tmp_path, capsys):
    res = str(tmp_path / "res")
    assert cli("run", "--backend", "scripted", "--repeats", "1", "--tasks", "read-01,read-02", "--results-dir", res, "--session", "one") == 0
    assert cli("run", "--backend", "scripted", "--profile", "no_call", "--repeats", "1", "--tasks", "read-01,read-02", "--results-dir", res, "--session", "two") == 0
    capsys.readouterr()
    assert cli("compare", "--results-dir", res) == 0  # previous vs latest
    out = capsys.readouterr().out
    assert "one (A) vs two (B)" in out and (tmp_path / "res" / "reports" / "compare-one-vs-two.md").exists()
    assert cli("compare", "one", "one", "--results-dir", res) == 1
    assert cli("export", "--format", "csv", "--results-dir", res) == 0
    assert (tmp_path / "res" / "exports" / "two.csv").exists()
    assert cli("export", "--session", "one", "--output", "-", "--results-dir", res) == 0
    assert '"session_id": "one"' in capsys.readouterr().out
    assert cli("export", "--session", "nope", "--results-dir", res) == 1


def test_compare_needs_two_sessions(tmp_path, capsys):
    res = str(tmp_path / "res")
    cli("run", "--backend", "scripted", "--repeats", "1", "--tasks", "read-01", "--results-dir", res)
    assert cli("compare", "--results-dir", res) == 1
    assert "need two sessions" in capsys.readouterr().err


# ------------------------------------------------------------------ task sets


def test_optional_tasks_need_to_be_named(all_tasks):
    default = select_tasks(all_tasks)
    assert len(default) == 20 and not any(t.optional for t in default)
    assert [t.id for t in select_tasks(all_tasks, groups=["nested"])] == ["nested-01", "nested-02", "nested-03", "nested-04"]
    assert [t.id for t in select_tasks(all_tasks, ids=["nested-02"])] == ["nested-02"]
    assert len(select_tasks(all_tasks, include_optional=True)) == 24


def test_task_fingerprint_changes_when_a_task_changes(all_tasks):
    before = tasks_fingerprint(all_tasks)
    assert before == tasks_fingerprint(list(reversed(all_tasks)))  # order does not matter
    chain4 = next(t for t in all_tasks if t.id == "chain-04")
    chain4.expect["max_calls"] = 99
    try:
        assert tasks_fingerprint(all_tasks) != before
    finally:
        chain4.expect.pop("max_calls", None)
        chain4.expect["max_calls"] = 10


def test_chain_04_is_version_2(all_tasks):
    assert next(t for t in all_tasks if t.id == "chain-04").version == 2


# ------------------------------------------------------------------ nested tools


def test_apply_edits_is_all_or_nothing(repo):
    executor = ToolExecutor(repo)
    before = (repo / "src/shelf/fees.py").read_text()
    ok, text = executor.execute(
        "apply_edits",
        {
            "edits": [
                {"path": "src/shelf/fees.py", "old_text": "return 0.0", "new_text": "return 1.0"},
                {"path": "src/shelf/catalog.py", "old_text": "THIS IS NOT THERE", "new_text": "x"},
            ]
        },
    )
    assert not ok and "edit 2" in text and "Nothing was changed" in text
    assert (repo / "src/shelf/fees.py").read_text() == before


def test_apply_edits_chains_edits_in_the_same_file(repo):
    executor = ToolExecutor(repo)
    ok, text = executor.execute(
        "apply_edits",
        {
            "edits": [
                {"path": "src/shelf/fees.py", "old_text": "return 0.0", "new_text": "return 1.0"},
                {"path": "src/shelf/fees.py", "old_text": "return 1.0", "new_text": "return 2.0"},
            ]
        },
    )
    assert ok and "return 2.0" in (repo / "src/shelf/fees.py").read_text()


def test_set_json_values_sets_and_refuses_unknown_keys(repo):
    executor = ToolExecutor(repo)
    ok, _ = executor.execute("set_json_values", {"path": "config/settings.json", "updates": [{"key_path": ["loan_days"], "value": 30}]})
    assert ok and json.loads((repo / "config/settings.json").read_text())["loan_days"] == 30
    before = (repo / "config/settings.json").read_text()
    ok, text = executor.execute("set_json_values", {"path": "config/settings.json", "updates": [{"key_path": ["no", "such"], "value": 1}]})
    assert not ok and "not found" in text and (repo / "config/settings.json").read_text() == before


@pytest.mark.parametrize(
    "arguments,kind",
    [
        ({"edits": "not a list"}, "invalid_args"),
        ({"edits": []}, "invalid_args"),
        ({"edits": [{"path": "a.py", "old_text": "x"}]}, "invalid_args"),  # new_text missing
        ({"edits": [{"path": "a.py", "old_text": "x", "new_text": "y", "extra": 1}]}, "invalid_args"),
        ('{"edits": [', "invalid_json"),
    ],
)
def test_nested_arguments_are_validated(arguments, kind):
    assert validate_arguments("apply_edits", arguments, ["apply_edits"])[1] == kind


def test_a_tool_that_was_not_offered_is_unknown(all_tasks):
    good = {"edits": [{"path": "a.py", "old_text": "x", "new_text": "y"}]}
    assert validate_arguments("apply_edits", good)[1] == "unknown_tool"  # default: core tools only
    assert validate_arguments("apply_edits", good, ["apply_edits"])[1] == ""


def test_nested_tasks_pass_with_the_oracle_and_fail_with_bad_edits(all_tasks, fixture_dir):
    nested = [t for t in all_tasks if t.group == "nested"]
    for profile, should_pass in (("oracle", True), ("bad_edit", False), ("no_call", False)):
        backend = ScriptedBackend(nested, profile)
        for task in nested:
            record = run_once(task, backend, fixture_dir)
            assert record.check.passed is should_pass, (profile, task.id, record.check.details)


def test_nested_tools_are_only_offered_to_tasks_that_ask(all_tasks):
    names = lambda task, mode="all": [s["function"]["name"] for s in tool_specs_for(task, mode)]  # noqa: E731
    by_id = {t.id: t for t in all_tasks}
    assert len(names(by_id["read-01"])) == 6 and "apply_edits" not in names(by_id["chain-04"])
    assert names(by_id["nested-01"])[-1] == "apply_edits" and len(names(by_id["nested-03"])) == 8


# ------------------------------------------------------------------ tool options


def test_tools_offered_task_mode_gives_only_the_needed_tools(all_tasks):
    by_id = {t.id: t for t in all_tasks}
    names = [s["function"]["name"] for s in tool_specs_for(by_id["read-01"], "task")]
    assert names == ["read_file"]
    assert len(tool_specs_for(by_id["failure-01"], "task")) == 6  # no tool needed: keep the core tools so a wrong call shows
    with pytest.raises(ValueError):
        tool_specs_for(by_id["read-01"], "some")


def test_tools_offered_task_mode_makes_other_tools_unknown(tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "read-01")
    record = run_once(task, ScriptedBackend(tasks, "wrong_tool"), fixture_dir, tools_offered="task")
    assert record.check.failure_type == "unknown_tool"  # list_dir was not offered
    record = run_once(task, ScriptedBackend(tasks, "oracle"), fixture_dir, tools_offered="task")
    assert record.check.passed


def test_one_call_per_turn_skips_the_rest(tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "failure-02")  # asks for two independent reads in one step
    full = run_once(task, ScriptedBackend(tasks, "oracle"), fixture_dir)
    assert full.check.passed
    limited = run_once(task, ScriptedBackend(tasks, "oracle"), fixture_dir, max_calls_per_turn=1)
    assert not limited.check.passed and len(limited.transcript.calls) < len(full.transcript.calls)
    assert any("skipped: only 1 call(s) per turn" in str(m.get("content")) for m in limited.transcript.messages)


# ------------------------------------------------------------------ tests after the last edit


def _transcript(calls, final="Done."):
    tr = Transcript(final_text=final)
    tr.calls = [CallRecord(i, 1, tool, args, True, True, "", "") for i, (tool, args) in enumerate(calls, 1)]
    return tr


def test_chain_04_needs_a_test_run_after_the_last_edit(all_tasks, fixture_dir, repo):
    task = next(t for t in all_tasks if t.id == "chain-04")
    edit = lambda p: ("edit_file", {"path": p, "old_text": "a", "new_text": "b"})  # noqa: E731
    run = ("run_command", {"command": "python -m pytest -q"})
    # a test run before the edits only: calls are right, but nothing confirms the fix
    tr = _transcript([run, edit("src/shelf/catalog.py"), edit("src/shelf/fees.py")])
    assert evaluate(task, tr, repo, fixture_dir).failure_type == "no_confirm_run"
    # a test run after the last edit satisfies the check (the repo is unfixed here, so only the tool check is asserted)
    tr = _transcript([edit("src/shelf/catalog.py"), edit("src/shelf/fees.py"), run])
    assert evaluate(task, tr, repo, fixture_dir).tool_ok
    # a test run between the edits is not enough
    tr = _transcript([edit("src/shelf/catalog.py"), run, edit("src/shelf/fees.py")])
    assert evaluate(task, tr, repo, fixture_dir).failure_type == "no_confirm_run"


def test_failed_edits_do_not_count_as_the_last_edit(all_tasks, fixture_dir, repo):
    task = next(t for t in all_tasks if t.id == "chain-04")
    tr = Transcript(final_text="Done.")
    tr.calls = [
        CallRecord(1, 1, "edit_file", {"path": "src/shelf/catalog.py", "old_text": "a", "new_text": "b"}, True, True, "", ""),
        CallRecord(2, 1, "edit_file", {"path": "src/shelf/fees.py", "old_text": "a", "new_text": "b"}, True, True, "", ""),
        CallRecord(3, 2, "run_command", {"command": "pytest"}, True, True, "", ""),
        CallRecord(4, 3, "edit_file", {"path": "src/shelf/fees.py", "old_text": "zz", "new_text": "b"}, True, False, "tool_error", "error"),
    ]
    assert evaluate(task, tr, repo, fixture_dir).tool_ok


# ------------------------------------------------------------------ API key


def test_api_key_is_sent_as_a_bearer_token(tasks, fixture_dir):
    with mock_server("openai", tasks) as (url, handler):
        backend = OpenAICompatBackend("mock", base_url=url, api_key="sk-test-123")
        backend.check()
        run_once(next(t for t in tasks if t.id == "failure-01"), backend, fixture_dir)
        assert all(r["auth"] == "Bearer sk-test-123" for r in handler.requests)
        assert backend.describe()["api_key"] == "set" and "sk-test-123" not in json.dumps(backend.describe())


def test_no_key_means_no_authorization_header(tasks):
    with mock_server("openai", tasks) as (url, handler):
        OpenAICompatBackend("mock", base_url=url).check()
        assert handler.requests[-1]["auth"] == ""


def test_run_reads_the_key_from_the_named_variable_and_never_saves_it(tmp_path, tasks, monkeypatch):
    monkeypatch.setenv("MY_BENCH_KEY", "sk-secret-value")
    res = str(tmp_path / "res")
    with mock_server("openai", tasks) as (url, handler):
        code = cli("run", "--backend", "openai-compat", "--host", url, "--model", "mock", "--repeats", "1", "--tasks", "failure-01",
                   "--api-key-env", "MY_BENCH_KEY", "--results-dir", res, "--session", "k")
        assert code == 0 and all(r["auth"] == "Bearer sk-secret-value" for r in handler.requests)
    stored = json.dumps(Store(tmp_path / "res" / "results.sqlite").session("k")["settings"])
    assert "sk-secret-value" not in stored and "MY_BENCH_KEY" in stored
    for path in (tmp_path / "res").rglob("*"):
        if path.is_file():
            assert b"sk-secret-value" not in path.read_bytes(), path


def test_missing_key_variable_is_an_error(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("NOT_SET_ANYWHERE", raising=False)
    code = cli("run", "--backend", "openai-compat", "--model", "m", "--api-key-env", "NOT_SET_ANYWHERE", "--results-dir", str(tmp_path))
    assert code == 2 and "NOT_SET_ANYWHERE is not set" in capsys.readouterr().err


def test_key_with_other_backends_is_an_error(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("SOME_KEY", "x")
    assert cli("run", "--backend", "scripted", "--api-key-env", "SOME_KEY", "--results-dir", str(tmp_path)) == 2
    assert "only used with --backend openai-compat" in capsys.readouterr().err


def test_a_pasted_key_in_the_config_is_refused(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text("backend: openai-compat\napi_key_env: sk-abc123-this-is-a-key\nmodels: [m]\n")
    with pytest.raises(ConfigError, match="NAME of an environment variable"):
        load_config(path)


# ------------------------------------------------------------------ config keys


def test_new_settings_load_and_validate(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text("settings:\n  tools_offered: task\n  max_calls_per_turn: 1\nmodels: [m]\n")
    cfg = load_config(path)
    assert cfg.tools_offered == "task" and cfg.max_calls_per_turn == 1
    path.write_text("settings:\n  tools_offered: some\nmodels: [m]\n")
    with pytest.raises(ConfigError, match="tools_offered"):
        load_config(path)
    path.write_text("settings:\n  max_calls_per_turn: -1\nmodels: [m]\n")
    with pytest.raises(ConfigError, match="max_calls_per_turn"):
        load_config(path)


def test_session_records_the_new_settings(tmp_path):
    res = str(tmp_path / "res")
    assert cli("run", "--backend", "scripted", "--repeats", "1", "--tasks", "read-01", "--tools-offered", "task", "--max-calls-per-turn", "2",
               "--results-dir", res, "--session", "s") == 0
    settings = Store(tmp_path / "res" / "results.sqlite").session("s")["settings"]
    assert settings["tools_offered"] == "task" and settings["max_calls_per_turn"] == 2 and len(settings["tasks_sha"]) == 12


def test_cli_runs_the_nested_group(tmp_path):
    res = str(tmp_path / "res")
    assert cli("run", "--backend", "scripted", "--repeats", "1", "--groups", "nested", "--results-dir", res, "--session", "n") == 0
    db = sqlite3.connect(tmp_path / "res" / "results.sqlite")
    assert db.execute("select count(*), sum(passed) from runs").fetchone() == (4, 4)
