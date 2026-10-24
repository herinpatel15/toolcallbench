import pytest

from toolcallbench.tools import TOOL_SPECS, ToolExecutor, validate_arguments


def test_six_tools_with_object_schemas():
    names = [s["function"]["name"] for s in TOOL_SPECS]
    assert names == ["read_file", "list_dir", "grep", "edit_file", "apply_patch", "run_command"]


@pytest.mark.parametrize(
    "name,args,kind",
    [
        ("read_file", {"path": "a"}, ""),
        ("read_file", '{"path": "a"}', ""),
        ("read_file", '{"path": ', "invalid_json"),
        ("read_file", "[1, 2]", "invalid_json"),
        ("read_file", {}, "invalid_args"),
        ("read_file", {"path": 5}, "invalid_args"),
        ("read_file", {"path": "a", "extra": 1}, "invalid_args"),
        ("nope", {}, "unknown_tool"),
    ],
)
def test_validate_arguments(name, args, kind):
    assert validate_arguments(name, args)[1] == kind


def test_read_file_with_line_numbers_and_range(repo):
    ex = ToolExecutor(repo)
    ok, text = ex.execute("read_file", {"path": "config/settings.json", "start_line": 2, "end_line": 2})
    assert ok and text.strip().startswith("2|") and "loan_days" in text


def test_read_file_errors(repo):
    ex = ToolExecutor(repo)
    assert ex.execute("read_file", {"path": "missing.txt"})[0] is False
    assert ex.execute("read_file", {"path": "../outside"})[0] is False
    assert ex.execute("read_file", {"path": "/etc/passwd"})[0] is False


def test_list_dir_marks_folders(repo):
    ok, text = ExecutorHelper(repo).run("list_dir", {"path": "."})
    assert ok and "src/" in text and "README.md" in text.splitlines()


class ExecutorHelper:
    def __init__(self, root):
        self.ex = ToolExecutor(root)

    def run(self, name, args):
        return self.ex.execute(name, args)


def test_grep_finds_and_reports_none(repo):
    ex = ToolExecutor(repo)
    assert "fees.py:12:" in ex.execute("grep", {"pattern": "def late_fee"})[1]
    assert ex.execute("grep", {"pattern": "zzzzqqq"}) == (True, "no matches")
    assert ex.execute("grep", {"pattern": "("})[0] is False


def test_edit_file_rules(repo):
    ex = ToolExecutor(repo)
    assert ex.execute("edit_file", {"path": "src/shelf/__init__.py", "old_text": "0.3.0", "new_text": "0.9.0"})[0]
    assert "0.9.0" in (repo / "src/shelf/__init__.py").read_text()
    assert ex.execute("edit_file", {"path": "src/shelf/__init__.py", "old_text": "nope", "new_text": "x"})[0] is False
    assert ex.execute("edit_file", {"path": "src/shelf/models.py", "old_text": "date", "new_text": "x"})[0] is False  # many matches
    assert ex.execute("edit_file", {"path": "src/shelf/models.py", "old_text": "", "new_text": "x"})[0] is False


def test_apply_patch_tool(repo):
    ex = ToolExecutor(repo)
    patch = "--- a/src/shelf/__init__.py\n+++ b/src/shelf/__init__.py\n@@ -2,2 +2,2 @@\n \n-__version__ = \"0.3.0\"\n+__version__ = \"1.0.0\"\n"
    ok, text = ex.execute("apply_patch", {"patch": patch})
    assert ok, text
    assert '"1.0.0"' in (repo / "src/shelf/__init__.py").read_text()


def test_run_command_allowlist_and_confinement(repo):
    ex = ToolExecutor(repo)
    ok, text = ex.execute("run_command", {"command": "python scripts/report.py"})
    assert ok and "Copies: 11" in text
    assert ex.execute("run_command", {"command": "rm -rf ."})[0] is False
    assert ex.execute("run_command", {"command": "curl http://example.com"})[0] is False
    assert ex.execute("run_command", {"command": "cat /etc/passwd"})[0] is False
    assert ex.execute("run_command", {"command": "cat ../x"})[0] is False
    assert ex.execute("run_command", {"command": "python -c 'print(1)'"})[0] is False
    assert ex.execute("run_command", {"command": "ls | wc"})[0] is True  # pipe is just extra arguments to ls, no shell
    assert (repo / "src").is_dir()


def test_output_is_truncated(repo):
    (repo / "big.txt").write_text("x" * 20000)
    ok, text = ToolExecutor(repo, max_output=100).execute("read_file", {"path": "big.txt"})
    assert ok and "truncated" in text and len(text) < 200
