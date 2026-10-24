"""Each failure profile must be detected as exactly the failure it imitates."""
import pytest

from toolcallbench.backends.scripted import ScriptedBackend
from toolcallbench.checks import FAILURE_TYPES
from toolcallbench.runner import run_once


def run(tasks, fixture_dir, task_id, profile, **kw):
    task = next(t for t in tasks if t.id == task_id)
    return run_once(task, ScriptedBackend(tasks, profile), fixture_dir, **kw)


@pytest.mark.parametrize(
    "profile,expected",
    [
        ("invalid_json", "invalid_json"),
        ("unknown_tool", "unknown_tool"),
        ("text_call", "text_tool_call"),
        ("no_call", "no_call"),
        ("call_limit", "call_limit"),
        ("wrong_tool", "wrong_tool"),
    ],
)
def test_profile_is_classified(tasks, fixture_dir, profile, expected):
    record = run(tasks, fixture_dir, "read-01", profile)
    assert not record.check.passed
    assert record.check.failure_type == expected


def test_bad_edit_is_patch_failed(tasks, fixture_dir):
    record = run(tasks, fixture_dir, "edit-01", "bad_edit")
    assert record.check.failure_type == "patch_failed"


def test_unneeded_call(tasks, fixture_dir):
    record = run(tasks, fixture_dir, "failure-01", "wrong_tool")
    assert record.check.failure_type == "unneeded_call"


def test_not_parallel_when_calls_are_in_separate_turns(tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "failure-02")
    from toolcallbench.models import CallRecord, Transcript
    from toolcallbench.checks import evaluate

    tr = Transcript(final_text="USD and 3 members")
    tr.calls = [
        CallRecord(1, 1, "read_file", {"path": "config/settings.json"}, True, True, "", ""),
        CallRecord(2, 2, "read_file", {"path": "data/members.csv"}, True, True, "", ""),
    ]
    check = evaluate(task, tr, fixture_dir, fixture_dir)
    assert check.failure_type == "not_parallel" and not check.passed


def test_too_few_calls(tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "chain-02")
    from toolcallbench.models import CallRecord, Transcript
    from toolcallbench.checks import evaluate

    tr = Transcript(final_text="3 members")
    tr.calls = [CallRecord(1, 1, "read_file", {"path": "README.md"}, True, True, "", "")]
    assert evaluate(task, tr, fixture_dir, fixture_dir).failure_type == "too_few_calls"


def test_wrong_answer_is_outcome_mismatch(tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "read-01")
    from toolcallbench.models import CallRecord, Transcript
    from toolcallbench.checks import evaluate

    tr = Transcript(final_text="It is 30.")
    tr.calls = [CallRecord(1, 1, "read_file", {"path": "config/settings.json"}, True, True, "", "")]
    check = evaluate(task, tr, fixture_dir, fixture_dir)
    assert check.failure_type == "outcome_mismatch" and check.args_ok


def test_wrong_path_is_wrong_args(tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "read-01")
    from toolcallbench.models import CallRecord, Transcript
    from toolcallbench.checks import evaluate

    tr = Transcript(final_text="loan_days is 30")
    tr.calls = [CallRecord(1, 1, "read_file", {"path": "config/other.json"}, True, False, "tool_error", "")]
    check = evaluate(task, tr, fixture_dir, fixture_dir)
    assert check.failure_type == "wrong_args" and not check.args_ok


def test_path_variants_are_accepted(tasks, fixture_dir):
    task = next(t for t in tasks if t.id == "read-01")
    from toolcallbench.models import CallRecord, Transcript
    from toolcallbench.checks import evaluate

    for path in ("./config/settings.json", "config//settings.json".replace("//", "/"), "config\\settings.json"):
        tr = Transcript(final_text="14")
        tr.calls = [CallRecord(1, 1, "read_file", {"path": path}, True, True, "", "")]
        assert evaluate(task, tr, fixture_dir, fixture_dir).passed, path


def test_failure_types_are_all_documented():
    assert len(FAILURE_TYPES) == len(set(FAILURE_TYPES)) == 13
