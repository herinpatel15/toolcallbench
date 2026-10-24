import pytest
import yaml

from toolcallbench.models import GROUPS
from toolcallbench.runner import run_once
from toolcallbench.backends.scripted import ScriptedBackend
from toolcallbench.tasks import TaskError, load_task_file, load_tasks, select_tasks


def test_twenty_tasks_across_five_groups(tasks):
    assert len(tasks) == 20
    assert {t.group for t in tasks} == set(GROUPS)
    assert len({t.id for t in tasks}) == 20


def test_twelve_name_their_tools(tasks):
    assert sum(t.tools_named for t in tasks) == 12


def test_every_reference_solution_passes(tasks, fixture_dir):
    backend = ScriptedBackend(tasks, "oracle")
    for task in tasks:
        record = run_once(task, backend, fixture_dir)
        assert record.status == "ok" and record.check.passed, (task.id, record.check.details)
        assert record.check.efficiency == 1.0


def test_do_nothing_never_passes_a_task_that_needs_work(tasks, fixture_dir):
    backend = ScriptedBackend(tasks, "no_call")
    for task in tasks:
        if task.id == "failure-01":
            continue
        assert not run_once(task, backend, fixture_dir).check.passed, task.id


def test_select_tasks(tasks):
    assert [t.id for t in select_tasks(tasks, ["read-01"])] == ["read-01"]
    assert all(t.group == "edit" for t in select_tasks(tasks, groups=["edit"]))
    with pytest.raises(TaskError):
        select_tasks(tasks, ["nope-99"])
    with pytest.raises(TaskError):
        select_tasks(tasks, groups=["nope"])


def _write(tmp_path, data):
    path = tmp_path / "t.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def good():
    return {"id": "read-99", "group": "read", "title": "t", "prompt": "p", "expect": {}, "reference": [{"final": "x"}]}


def test_task_validation(tmp_path):
    assert load_task_file(_write(tmp_path, good())).id == "read-99"
    bad = good(); bad["group"] = "edit"
    with pytest.raises(TaskError, match="must start with its group"):
        load_task_file(_write(tmp_path, bad))
    bad = good(); bad["expect"] = {"colour": 1}
    with pytest.raises(TaskError, match="unknown expect keys"):
        load_task_file(_write(tmp_path, bad))
    bad = good(); bad["reference"] = [{"calls": [{"tool": "list_dir"}]}]
    with pytest.raises(TaskError, match="final"):
        load_task_file(_write(tmp_path, bad))
    bad = good(); del bad["prompt"]
    with pytest.raises(TaskError):
        load_task_file(_write(tmp_path, bad))


def test_empty_folder_and_duplicates(tmp_path):
    with pytest.raises(TaskError, match="no task files"):
        load_tasks(tmp_path)
    (tmp_path / "a.yaml").write_text(yaml.safe_dump(good()))
    (tmp_path / "b.yaml").write_text(yaml.safe_dump(good()))
    with pytest.raises(TaskError, match="duplicate"):
        load_tasks(tmp_path)
