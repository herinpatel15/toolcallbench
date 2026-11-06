import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "toolcallbench" / "data"
FIXTURE = DATA / "fixtures" / "repo"
TASKS_DIR = DATA / "tasks"


@pytest.fixture(scope="session")
def all_tasks():
    """Every task, including the optional ones."""
    from toolcallbench.tasks import load_tasks

    return load_tasks(TASKS_DIR)


@pytest.fixture(scope="session")
def tasks(all_tasks):
    """The core tasks that a default run uses."""
    return [t for t in all_tasks if not t.optional]


@pytest.fixture
def fixture_dir():
    return FIXTURE


@pytest.fixture
def repo(tmp_path):
    """A fresh writable copy of the fixture repository."""
    target = tmp_path / "repo"
    shutil.copytree(FIXTURE, target, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return target
