import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "repo"
TASKS_DIR = ROOT / "tasks"


@pytest.fixture(scope="session")
def tasks():
    from toolcallbench.tasks import load_tasks

    return load_tasks(TASKS_DIR)


@pytest.fixture
def fixture_dir():
    return FIXTURE


@pytest.fixture
def repo(tmp_path):
    """A fresh writable copy of the fixture repository."""
    target = tmp_path / "repo"
    shutil.copytree(FIXTURE, target, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return target
