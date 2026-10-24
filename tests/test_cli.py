import sqlite3

import pytest

from mock_servers import mock_server
from toolcallbench.cli import main

ROOT_ARGS = []


def cli(*args):
    return main(list(args))


def test_list_tasks(capsys):
    assert cli("list-tasks") == 0
    out = capsys.readouterr().out
    assert "read-01" in out and "20 tasks" in out
    assert cli("list-tasks", "--markdown") == 0
    assert "| Task |" in capsys.readouterr().out


def test_validate_tasks(capsys):
    assert cli("validate-tasks") == 0
    assert "20/20 reference solutions pass" in capsys.readouterr().out


def test_scripted_run_report_and_resume(tmp_path, capsys):
    res = str(tmp_path / "results")
    assert cli("run", "--backend", "scripted", "--repeats", "2", "--results-dir", res, "--session", "t1") == 0
    out = capsys.readouterr().out
    assert "= 40 runs" in out
    assert (tmp_path / "results" / "reports" / "t1.md").is_file()
    assert (tmp_path / "results" / "reports" / "t1.html").is_file()
    # the same session id without --resume is refused
    assert cli("run", "--backend", "scripted", "--results-dir", res, "--session", "t1") == 2
    # resume runs nothing new
    assert cli("run", "--backend", "scripted", "--repeats", "2", "--results-dir", res, "--session", "t1", "--resume") == 0
    db = sqlite3.connect(tmp_path / "results" / "results.sqlite")
    assert db.execute("select count(*) from runs").fetchone()[0] == 40
    assert cli("sessions", "--results-dir", res) == 0
    assert "t1" in capsys.readouterr().out
    assert cli("report", "--results-dir", res, "--print") == 0
    assert "# ToolCallBench report: t1" in capsys.readouterr().out


def test_resume_after_partial(tmp_path):
    res = str(tmp_path / "results")
    assert cli("run", "--backend", "scripted", "--tasks", "read-01,read-02", "--results-dir", res, "--session", "p") == 0
    assert cli("run", "--backend", "scripted", "--results-dir", res, "--session", "p", "--resume") == 0
    db = sqlite3.connect(tmp_path / "results" / "results.sqlite")
    assert db.execute("select count(*) from runs").fetchone()[0] == 60  # 20 tasks x 3 default repeats, no duplicates
    assert db.execute("select count(distinct task_id) from runs").fetchone()[0] == 20


def test_run_requires_models(tmp_path, capsys):
    assert cli("run", "--backend", "ollama", "--results-dir", str(tmp_path)) == 2
    assert "no models given" in capsys.readouterr().err


def test_unknown_task_is_reported(tmp_path, capsys):
    assert cli("run", "--backend", "scripted", "--tasks", "zzz-01", "--results-dir", str(tmp_path)) == 2


def test_run_against_mock_ollama(tmp_path, tasks):
    with mock_server("ollama", tasks) as (url, _):
        res = str(tmp_path / "res")
        code = cli("run", "--backend", "ollama", "--host", url, "--model", "mock-model", "--repeats", "1",
                   "--groups", "read", "--results-dir", res, "--session", "m1", "--num-ctx", "8192", "--kv-cache-type", "q8_0")
        assert code == 0
    db = sqlite3.connect(tmp_path / "res" / "results.sqlite")
    rows = db.execute("select passed, quant from runs").fetchall()
    assert len(rows) == 5 and all(r == (1, "Q4_K_M") for r in rows)
    settings = db.execute("select settings_json from sessions").fetchone()[0]
    assert '"backend_version": "0.99.0"' in settings and '"declared_kv_cache_type": "q8_0"' in settings


def test_unreachable_server_stops_before_running(tmp_path, capsys):
    code = cli("run", "--backend", "openai-compat", "--host", "http://127.0.0.1:9", "--model", "x", "--results-dir", str(tmp_path))
    assert code == 1  # server check fails before any run
    assert "cannot reach" in capsys.readouterr().err


def test_doctor_scripted(capsys):
    assert cli("doctor", "--backend", "scripted") == 0
    out = capsys.readouterr().out
    assert "[ OK ] fixture repo: 2 failing test(s)" in out


def test_doctor_with_mock_ollama_and_probe(tasks, capsys):
    with mock_server("ollama", tasks) as (url, _):
        assert cli("doctor", "--host", url, "--model", "mock-model", "--probe") == 0
        out = capsys.readouterr().out
        assert "Ollama server" in out and "probe mock-model" in out and "tok/s" in out
        assert cli("doctor", "--host", url, "--model", "missing-model") == 1
        assert "ollama pull missing-model" in capsys.readouterr().out


def test_doctor_server_down(capsys):
    assert cli("doctor", "--host", "http://127.0.0.1:9") == 1
    assert "ollama serve" in capsys.readouterr().out


def test_report_without_results(tmp_path, capsys):
    assert cli("report", "--results-dir", str(tmp_path / "none")) == 1


def test_three_backend_errors_in_a_row_stop_a_model(tmp_path, monkeypatch, capsys):
    from toolcallbench import cli as cli_module
    from toolcallbench.backends import Backend, BackendError

    class Flaky(Backend):
        name = "flaky"

        def chat(self, messages, tools):
            raise BackendError("server crashed")

    monkeypatch.setattr(cli_module, "make_backend", lambda *a, **k: Flaky())
    res = tmp_path / "res"
    assert cli("run", "--backend", "scripted", "--results-dir", str(res), "--session", "f") == 0
    assert "3 backend errors in a row" in capsys.readouterr().err
    db = sqlite3.connect(res / "results.sqlite")
    assert db.execute("select count(*), min(status), max(status) from runs").fetchone() == (3, "error", "error")
    assert db.execute("select count(*) from runs where passed = 1").fetchone()[0] == 0


def test_init_creates_configs_and_refuses_overwrite(tmp_path, capsys):
    assert cli("init", str(tmp_path)) == 0
    assert (tmp_path / "configs" / "my-models.yaml").is_file()
    assert not (tmp_path / "tasks").exists()
    assert cli("init", str(tmp_path)) == 1
    assert "already exists" in capsys.readouterr().err


def test_init_with_tasks_gives_a_folder_that_runs(tmp_path, capsys, monkeypatch):
    assert cli("init", str(tmp_path), "--with-tasks") == 0
    assert (tmp_path / "fixtures" / "repo" / "pytest.ini").is_file()
    monkeypatch.chdir(tmp_path)
    assert cli("validate-tasks") == 0
    assert "20/20 reference solutions pass" in capsys.readouterr().out
