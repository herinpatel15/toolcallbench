import pytest

from toolcallbench.patching import PatchError, apply_unified_diff


def resolver(tmp_path):
    return lambda p: tmp_path / p


def test_apply_simple_hunk(tmp_path):
    (tmp_path / "a.txt").write_text("one\ntwo\nthree\n")
    patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1,3 +1,3 @@\n one\n-two\n+TWO\n three\n"
    apply_unified_diff(patch, resolver(tmp_path))
    assert (tmp_path / "a.txt").read_text() == "one\nTWO\nthree\n"


def test_wrong_line_numbers_are_tolerated(tmp_path):
    (tmp_path / "a.txt").write_text("one\ntwo\nthree\n")
    patch = "--- a/a.txt\n+++ b/a.txt\n@@ -9,3 +9,3 @@\n one\n-two\n+TWO\n three\n"
    apply_unified_diff(patch, resolver(tmp_path))
    assert "TWO" in (tmp_path / "a.txt").read_text()


def test_context_mismatch_fails_and_leaves_file(tmp_path):
    (tmp_path / "a.txt").write_text("one\ntwo\nthree\n")
    patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1,3 +1,3 @@\n one\n-NOPE\n+TWO\n three\n"
    with pytest.raises(PatchError):
        apply_unified_diff(patch, resolver(tmp_path))
    assert (tmp_path / "a.txt").read_text() == "one\ntwo\nthree\n"


def test_missing_file_and_garbage(tmp_path):
    with pytest.raises(PatchError):
        apply_unified_diff("--- a/x.txt\n+++ b/x.txt\n@@ -1,1 +1,1 @@\n-a\n+b\n", resolver(tmp_path))
    with pytest.raises(PatchError):
        apply_unified_diff("this is not a diff", resolver(tmp_path))


def test_new_file_not_supported(tmp_path):
    with pytest.raises(PatchError):
        apply_unified_diff("--- /dev/null\n+++ b/new.txt\n@@ -0,0 +1,1 @@\n+hi\n", resolver(tmp_path))
