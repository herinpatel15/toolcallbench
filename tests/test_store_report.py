from toolcallbench.backends.scripted import ScriptedBackend
from toolcallbench.report import aggregate, markdown_to_html, render_markdown
from toolcallbench.runner import run_once
from toolcallbench.store import Store, model_slug, write_log


def fill(tmp_path, tasks, fixture_dir):
    store = Store(tmp_path / "r.sqlite")
    store.create_session("s1", {"repeats": 1, "backend": "scripted"})
    for model, profile in (("good", "oracle"), ("bad", "no_call")):
        backend = ScriptedBackend(tasks, profile)
        for task in tasks:
            record = run_once(task, backend, fixture_dir)
            log = write_log(tmp_path, "s1", model, 1, record)
            store.add_run("s1", model=model, quant="Q4_K_M", backend="scripted", repeat=1, record=record, log_path=log)
    return store


def test_store_roundtrip_and_resume_keys(tmp_path, tasks, fixture_dir):
    store = fill(tmp_path, tasks, fixture_dir)
    assert store.has_run("s1", "good", "read-01", 1) and not store.has_run("s1", "good", "read-01", 2)
    assert len(store.runs("s1")) == 40
    assert store.latest_session_id() == "s1"
    assert store.list_sessions()[0]["runs"] == 40


def test_jsonl_log_has_messages_and_summary(tmp_path, tasks, fixture_dir):
    fill(tmp_path, tasks, fixture_dir)
    lines = (tmp_path / "logs" / "s1" / "good" / "read-01_1.jsonl").read_text().splitlines()
    assert '"type": "summary"' in lines[-1] and '"role": "system"' in lines[0]


def test_aggregate_and_report(tmp_path, tasks, fixture_dir):
    store = fill(tmp_path, tasks, fixture_dir)
    models = {m["model"]: m for m in aggregate(store.runs("s1"))["models"]}
    assert models["good"]["passed"] == 20 and models["bad"]["passed"] == 1  # failure-01 needs no tools
    md = render_markdown(store, "s1", {t.id: (t.group, t.title) for t in tasks})
    assert "## Summary" in md and "no_call" in md and "100.0%" in md and "5.0%" in md
    html = markdown_to_html(md, "T")
    assert "<table>" in html and "<script" not in html


def test_html_escapes_content():
    assert "&lt;script&gt;" in markdown_to_html("# <script>alert(1)</script>", "x")


def test_model_slug():
    assert model_slug("qwen3:8b-q4_K_M/x") == "qwen3_8b-q4_K_M_x"
