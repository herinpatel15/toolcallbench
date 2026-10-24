# Build ToolCallBench from scratch: a day-by-day guide

This guide takes you from an empty folder to the finished project, one day at a time. Every
file is shown in full, so you can type it or paste it. After each day there is a command to
run and the output you should see.

**What you build:** a program that tests how well a local AI model calls tools. You give a
model six tools (read a file, list a folder, search, edit, apply a patch, run a command) and
20 small tasks. The program checks the result with normal code and writes a report. You will
run it on your MacBook M4 with 16 GB of memory.

**How long:** about 10 days at 2 to 3 hours each. You can go faster by pasting the code, but read
the "why" notes: they are what teaches you how the program works.

**How this guide was checked:** the code blocks below are copied from the real repository by a
script. A second script extracts them into an empty folder, installs the project and runs
every test. So if you copy the files exactly, the tests pass. The author ran these checks on
Linux with a fake model and with mock servers. **The author could not run a real model on a
Mac**, so Day 7 and Day 8 (real models on your M4) are where you do the first real
measurements. Output you see on those days will differ from anything printed here.

## How to read each day

| Part | Meaning |
| --- | --- |
| **Goal** | What works at the end of the day |
| **Why** | The idea behind the code, in simple words |
| **Create** | Files to create, shown in full |
| **Run** | A command and the output you should see |
| **Checkpoint** | A `git commit` so you can always go back |

When a path is shown, create the file at exactly that path inside your project folder, and
create missing folders as you go.

## The plan

| Day | You build | You can then |
| --- | --- | --- |
| 0 | Mac setup and the project skeleton | import the package |
| 1 | A small sample project (`shelf`) with two bugs | see two failing tests |
| 2 | Tools, a safe sandbox and a patch engine | let a program read, edit and run code safely |
| 3 | Backends (Ollama, OpenAI-style, fake) and config | talk to a model server |
| 4 | The 20 tasks, the scoring rules and the runner | score a run without any AI judge |
| 5 | Storage and reports | keep results and compare models |
| 6 | The command line and mock servers | run everything end to end with a fake model |
| 7 | Helper scripts, then your first real model | run a real benchmark on your M4 |
| 8 | Real benchmark plan: models, quantization, memory | decide which model to use |
| 9 | Documents, polish and publishing | share a finished project |
| 10 | Make it yours | add tasks, point it at your own code |

## The final project layout

```text
.github/workflows/ci.yml
.gitignore
Makefile
README.md
configs/m4-16gb.yaml
configs/quant-sweep-qwen3-8b.yaml
configs/smoke-scripted.yaml
fixtures/repo/README.md
fixtures/repo/config/settings.json
fixtures/repo/data/books.csv
fixtures/repo/data/members.csv
fixtures/repo/pytest.ini
fixtures/repo/scripts/report.py
fixtures/repo/src/shelf/__init__.py
fixtures/repo/src/shelf/catalog.py
fixtures/repo/src/shelf/fees.py
fixtures/repo/src/shelf/loans.py
fixtures/repo/src/shelf/models.py
fixtures/repo/src/shelf/settings.py
fixtures/repo/src/shelf/utils.py
fixtures/repo/tests/test_catalog.py
fixtures/repo/tests/test_fees.py
fixtures/repo/tests/test_loans.py
fixtures/repo/tests/test_utils.py
pyproject.toml
scripts/estimate_memory.py
scripts/make_build_guide.py
scripts/make_task_catalog.py
scripts/serve_ollama.sh
scripts/verify_build_guide.py
src/toolcallbench/__init__.py
src/toolcallbench/__main__.py
src/toolcallbench/backends/__init__.py
src/toolcallbench/backends/base.py
src/toolcallbench/backends/ollama.py
src/toolcallbench/backends/openai_compat.py
src/toolcallbench/backends/scripted.py
src/toolcallbench/checks.py
src/toolcallbench/cli.py
src/toolcallbench/config.py
src/toolcallbench/models.py
src/toolcallbench/patching.py
src/toolcallbench/report.py
src/toolcallbench/runner.py
src/toolcallbench/store.py
src/toolcallbench/tasks.py
src/toolcallbench/tools.py
tasks/chain-01.yaml
tasks/chain-02.yaml
tasks/chain-03.yaml
tasks/chain-04.yaml
tasks/edit-01.yaml
tasks/edit-02.yaml
tasks/edit-03.yaml
tasks/edit-04.yaml
tasks/edit-05.yaml
tasks/failure-01.yaml
tasks/failure-02.yaml
tasks/failure-03.yaml
tasks/read-01.yaml
tasks/read-02.yaml
tasks/read-03.yaml
tasks/read-04.yaml
tasks/read-05.yaml
tasks/run-01.yaml
tasks/run-02.yaml
tasks/run-03.yaml
tests/conftest.py
tests/mock_servers.py
tests/test_checks.py
tests/test_cli.py
tests/test_config.py
tests/test_http_backends.py
tests/test_patching.py
tests/test_scripts.py
tests/test_store_report.py
tests/test_tasks.py
tests/test_tools.py
```

---

## Day 0: Set up your Mac and the project skeleton

**Goal:** Python, Git and Ollama are installed, and `import toolcallbench` works.

### Why

A Python project needs an isolated environment (a *virtual environment*) so its packages do
not mix with other projects. We use a `src/` folder layout: the code lives in `src/toolcallbench`,
and `pip install -e .` makes it importable while still letting you edit it ("editable" install).

### Install the tools

Open Terminal and run:

```bash
# 1. Homebrew (skip if you have it): see https://brew.sh for the current install command
# 2. Python and Git
brew install python@3.12 git
# 3. Ollama: download the app from https://ollama.com, or use Homebrew
brew install ollama
```

Check: `python3 --version` should show 3.10 or newer, and `ollama --version` should print a version.

### Create the project

```bash
mkdir -p ~/code/toolcallbench && cd ~/code/toolcallbench
git init
python3 -m venv .venv
source .venv/bin/activate        # run this again in every new terminal
touch README.md                  # a real README comes on Day 9
mkdir -p src/toolcallbench tests tasks configs scripts fixtures/repo
```

### Create

`pyproject.toml` tells Python the project name, its two dependencies (PyYAML for task files,
jsonschema for checking tool arguments), and the `toolcallbench` command.

<!-- file: pyproject.toml -->
**`pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "toolcallbench"
version = "0.1.0"
description = "Benchmark how reliably local LLMs call tools on your own repo and hardware"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
dependencies = ["pyyaml>=6", "jsonschema>=4"]

[project.optional-dependencies]
dev = ["pytest>=7"]

[project.scripts]
toolcallbench = "toolcallbench.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = ["fixtures", ".git", "results"]
addopts = "-q"
```

`.gitignore` keeps generated files out of Git.

<!-- file: .gitignore -->
**`.gitignore`**

```text
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
*.egg-info/
build/
dist/
results/
.DS_Store
results-smoke/
results-demo/
```

The package files. `__init__.py` holds the version; `__main__.py` lets you run
`python -m toolcallbench`.

<!-- file: src/toolcallbench/__init__.py -->
**`src/toolcallbench/__init__.py`**

```python
"""ToolCallBench: measure how reliably local LLMs call tools on your own repo and hardware."""

__version__ = "0.1.0"
```

<!-- file: src/toolcallbench/__main__.py -->
**`src/toolcallbench/__main__.py`**

```python
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
```

Also add a license. Copy the MIT License text from <https://choosealicense.com/licenses/mit/>
into a file named `LICENSE`.

### Run

Install the project in your virtual environment:

```bash
pip install -e ".[dev]"
python -c "import toolcallbench; print(toolcallbench.__version__)"
```

```text
$ python -c "import toolcallbench; print(toolcallbench.__version__)"
0.1.0
```

### Checkpoint

```bash
git add -A && git commit -m "Day 0: project skeleton"
```

---

## Day 1: The sample project the model will work on

**Goal:** a tiny library-lending project called `shelf`, with exactly **two failing tests**.

### Why

A benchmark needs something to work on. We want a small project that is realistic (code,
config, data, tests) and has known bugs, so we can ask a model to "fix the failing tests" and
check the answer with code. It lives in `fixtures/repo`. For every run, the program copies it
to a temporary folder, so the model can never break the original.

The two bugs are on purpose:

1. `search_by_title` in `catalog.py` is case-sensitive, but its docstring and test say it should ignore case.
2. `late_fee` in `fees.py` ignores its `cap` argument.

Do not fix them. The tasks need them.

### Create

Settings and data:

<!-- file: fixtures/repo/config/settings.json -->
**`fixtures/repo/config/settings.json`**

```json
{
  "loan_days": 14,
  "max_loans_per_member": 3,
  "late_fee_per_day": 0.25,
  "max_late_fee": 10.0,
  "currency": "USD"
}
```

<!-- file: fixtures/repo/data/books.csv -->
**`fixtures/repo/data/books.csv`**

```text
isbn,title,author,year,copies
9780441172719,Dune,Frank Herbert,1965,2
9780547928227,The Hobbit,J.R.R. Tolkien,1937,3
9780451524935,Nineteen Eighty-Four,George Orwell,1949,1
9780142437179,Frankenstein,Mary Shelley,1818,2
9780316769488,The Catcher in the Rye,J.D. Salinger,1951,1
9780743273565,The Great Gatsby,F. Scott Fitzgerald,1925,2
```

<!-- file: fixtures/repo/data/members.csv -->
**`fixtures/repo/data/members.csv`**

```text
member_id,name,joined
M001,Asha Rao,2021-03-14
M002,Ben Carter,2022-07-01
M003,Chen Wei,2023-01-20
```

The package. Read `catalog.py` and `fees.py` and find the two bugs.

<!-- file: fixtures/repo/src/shelf/__init__.py -->
**`fixtures/repo/src/shelf/__init__.py`**

```python
"""A tiny library-lending package used as a benchmark fixture."""

__version__ = "0.3.0"
```

<!-- file: fixtures/repo/src/shelf/models.py -->
**`fixtures/repo/src/shelf/models.py`**

```python
"""Plain data classes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Book:
    isbn: str
    title: str
    author: str
    year: int
    copies: int


@dataclass(frozen=True)
class Member:
    member_id: str
    name: str
    joined: date


@dataclass
class Loan:
    isbn: str
    member_id: str
    borrowed_on: date
    due_on: date
    returned_on: date | None = None
```

<!-- file: fixtures/repo/src/shelf/settings.py -->
**`fixtures/repo/src/shelf/settings.py`**

```python
"""Load the library settings."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.json"


def load_settings(path: Path | None = None) -> dict:
    with open(path or DEFAULT_PATH, encoding="utf-8") as handle:
        return json.load(handle)
```

<!-- file: fixtures/repo/src/shelf/catalog.py -->
**`fixtures/repo/src/shelf/catalog.py`**

```python
"""Read the book catalog and search it."""
from __future__ import annotations

import csv
from pathlib import Path

from .models import Book

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_books(path: Path | None = None) -> list[Book]:
    with open(path or DATA_DIR / "books.csv", newline="", encoding="utf-8") as handle:
        return [
            Book(row["isbn"], row["title"], row["author"], int(row["year"]), int(row["copies"]))
            for row in csv.DictReader(handle)
        ]


def find_by_isbn(books: list[Book], isbn: str) -> Book | None:
    for book in books:
        if book.isbn == isbn:
            return book
    return None


def search_by_title(books: list[Book], query: str) -> list[Book]:
    """Return the books whose title contains the query, ignoring upper or lower case."""
    return [b for b in books if query in b.title]


def books_by_author(books: list[Book], author: str) -> list[Book]:
    return [b for b in books if b.author == author]
```

<!-- file: fixtures/repo/src/shelf/fees.py -->
**`fixtures/repo/src/shelf/fees.py`**

```python
"""Late-fee rules."""
from __future__ import annotations

from datetime import date


def days_late(due_on: date, returned_on: date) -> int:
    """Whole days a book is overdue; 0 when it is returned on time."""
    return max((returned_on - due_on).days, 0)


def late_fee(days: int, per_day: float, cap: float | None = None) -> float:
    """Fee for a late return.

    The fee grows by `per_day` for every late day but never goes above `cap`
    when a cap is given.
    """
    if days <= 0:
        return 0.0
    return round(days * per_day, 2)
```

<!-- file: fixtures/repo/src/shelf/loans.py -->
**`fixtures/repo/src/shelf/loans.py`**

```python
"""Borrowing and returning books."""
from __future__ import annotations

from datetime import date, timedelta

from .fees import days_late, late_fee
from .models import Book, Loan


class LoanError(Exception):
    """Raised when a loan request is not allowed."""


class Library:
    def __init__(self, books: list[Book], settings: dict):
        self.settings = settings
        self.stock = {book.isbn: book.copies for book in books}
        self.loans: list[Loan] = []

    def available_copies(self, isbn: str) -> int:
        if isbn not in self.stock:
            raise LoanError(f"unknown ISBN {isbn}")
        active = sum(1 for loan in self.loans if loan.isbn == isbn and loan.returned_on is None)
        return self.stock[isbn] - active

    def loans_for(self, member_id: str) -> list[Loan]:
        return [loan for loan in self.loans if loan.member_id == member_id and loan.returned_on is None]

    def borrow(self, isbn: str, member_id: str, today: date) -> Loan:
        if self.available_copies(isbn) <= 0:
            raise LoanError("no copies available")
        if len(self.loans_for(member_id)) >= self.settings["max_loans_per_member"]:
            raise LoanError("loan limit reached")
        due = today + timedelta(days=self.settings["loan_days"])
        loan = Loan(isbn, member_id, today, due)
        self.loans.append(loan)
        return loan

    def return_book(self, isbn: str, member_id: str, today: date) -> float:
        """Mark a loan as returned and return the late fee owed."""
        for loan in self.loans_for(member_id):
            if loan.isbn == isbn:
                loan.returned_on = today
                late = days_late(loan.due_on, today)
                return late_fee(late, self.settings["late_fee_per_day"], self.settings["max_late_fee"])
        raise LoanError("no such loan")
```

<!-- file: fixtures/repo/src/shelf/utils.py -->
**`fixtures/repo/src/shelf/utils.py`**

```python
"""Small helpers used across the shelf package."""
from __future__ import annotations

import re


def format_money(amount: float, currency: str = "USD") -> str:
    """Format an amount such as 2.5 as '2.50 USD'."""
    return f"{amount:.2f} {currency}"


def slugify(text: str) -> str:
    """Turn a title into a lowercase, dash-separated slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def isbn_ok(isbn: str) -> bool:
    """Return True when the ISBN is 13 digits long."""
    return len(isbn) == 13 and isbn.isdigit()
```

A script, a README, the pytest settings (`pythonpath = src` lets the tests import `shelf`):

<!-- file: fixtures/repo/scripts/report.py -->
**`fixtures/repo/scripts/report.py`**

```python
"""Print a short summary of the library."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shelf.catalog import load_books  # noqa: E402


def main() -> None:
    books = load_books()
    with open(ROOT / "data" / "members.csv", newline="", encoding="utf-8") as handle:
        members = list(csv.DictReader(handle))
    print("Library report")
    print(f"Titles: {len(books)}")
    print(f"Copies: {sum(b.copies for b in books)}")
    print(f"Members: {len(members)}")


if __name__ == "__main__":
    main()
```

<!-- file: fixtures/repo/README.md -->
**`fixtures/repo/README.md`**

```markdown
# shelf

A tiny library-lending package. It is a fixture for ToolCallBench: models are asked to read,
change and run this code, so please keep it small.

## Layout

- `src/shelf/` - the package (catalog, loans, fees, helpers)
- `config/settings.json` - loan length, loan limit and late-fee rules
- `data/` - `books.csv` and `members.csv`
- `scripts/report.py` - prints a short summary of the library
- `tests/` - pytest tests

## Commands

- Run the tests: `python -m pytest -q`
- Print the summary report: `python scripts/report.py`
```

<!-- file: fixtures/repo/pytest.ini -->
**`fixtures/repo/pytest.ini`**

```ini
[pytest]
pythonpath = src
testpaths = tests
```

The tests:

<!-- file: fixtures/repo/tests/test_catalog.py -->
**`fixtures/repo/tests/test_catalog.py`**

```python
from shelf.catalog import books_by_author, find_by_isbn, load_books, search_by_title


def test_load_books_count():
    assert len(load_books()) == 6


def test_find_by_isbn():
    book = find_by_isbn(load_books(), "9780441172719")
    assert book is not None and book.title == "Dune"


def test_search_is_case_insensitive():
    titles = [b.title for b in search_by_title(load_books(), "dune")]
    assert titles == ["Dune"]


def test_books_by_author():
    assert [b.title for b in books_by_author(load_books(), "George Orwell")] == ["Nineteen Eighty-Four"]
```

<!-- file: fixtures/repo/tests/test_fees.py -->
**`fixtures/repo/tests/test_fees.py`**

```python
from datetime import date

from shelf.fees import days_late, late_fee


def test_no_fee_when_on_time():
    assert days_late(date(2024, 5, 15), date(2024, 5, 15)) == 0
    assert late_fee(0, 0.25) == 0.0


def test_fee_per_day():
    assert late_fee(4, 0.25) == 1.0


def test_late_fee_is_capped():
    assert late_fee(100, 0.25, cap=10.0) == 10.0
```

<!-- file: fixtures/repo/tests/test_loans.py -->
**`fixtures/repo/tests/test_loans.py`**

```python
from datetime import date, timedelta

import pytest

from shelf.catalog import load_books
from shelf.loans import Library, LoanError
from shelf.settings import load_settings

TODAY = date(2024, 5, 1)


@pytest.fixture
def library():
    return Library(load_books(), load_settings())


def test_borrow_reduces_available_copies(library):
    library.borrow("9780441172719", "M001", TODAY)
    assert library.available_copies("9780441172719") == 1


def test_loan_limit(library):
    for isbn in ("9780441172719", "9780547928227", "9780142437179"):
        library.borrow(isbn, "M001", TODAY)
    with pytest.raises(LoanError):
        library.borrow("9780743273565", "M001", TODAY)


def test_late_return_pays_fee(library):
    library.borrow("9780547928227", "M002", TODAY)
    fee = library.return_book("9780547928227", "M002", TODAY + timedelta(days=18))
    assert fee == 1.0
```

<!-- file: fixtures/repo/tests/test_utils.py -->
**`fixtures/repo/tests/test_utils.py`**

```python
from shelf.utils import format_money, isbn_ok, slugify


def test_format_money():
    assert format_money(2.5) == "2.50 USD"


def test_slugify():
    assert slugify("The Great Gatsby!") == "the-great-gatsby"


def test_isbn_ok():
    assert isbn_ok("9780441172719")
    assert not isbn_ok("12345")
```

### Run

```text
$ cd fixtures/repo && python -m pytest -q --tb=line
..F...F......                                                            [100%]
=================================== FAILURES ===================================
E   AssertionError: assert [] == ['Dune']

      Right contains one more item: 'Dune'
      Use -v to get more diff
./fixtures/repo/tests/test_catalog.py:15: AssertionError: assert [] == ['Dune']
E   assert 25.0 == 10.0
     +  where 25.0 = late_fee(100, 0.25, cap=10.0)
./fixtures/repo/tests/test_fees.py:16: assert 25.0 == 10.0
=========================== short test summary info ============================
FAILED tests/test_catalog.py::test_search_is_case_insensitive - AssertionErro...
FAILED tests/test_fees.py::test_late_fee_is_capped - assert 25.0 == 10.0
2 failed, 11 passed in N.NNs
[exit code 1]
```

You must see **2 failed, 11 passed**. If you see a different number, a file was copied
wrongly. The tasks later in this guide depend on these exact numbers (for example, the
report script prints 11 copies in total):

```text
$ cd fixtures/repo && python scripts/report.py
Library report
Titles: 6
Copies: 11
Members: 3
```

### Checkpoint

```bash
git add -A && git commit -m "Day 1: sample project with two bugs"
```

---

## Day 2: Tools, the sandbox and the patch engine

**Goal:** a safe way for a program to read files, search, edit, apply patches and run commands.

### Why

A model "calls a tool" by returning a name and some arguments, for example
`read_file` with `{"path": "README.md"}`. Our program must (1) check that the call is
valid, (2) run it safely, and (3) send the result back. This day builds those three parts.

- `models.py` holds small data classes shared by all other files (a `Task`, a tool call record, a check result).
- `patching.py` applies a *unified diff* (the `+` and `-` lines you see in `git diff`). Models often write these, and they often get them slightly wrong, so the engine reports clear errors.
- `tools.py` has the six tool definitions as JSON Schema (this is what the model sees), a function that validates a raw call, and a `ToolExecutor` that runs calls inside one folder.

How the safety works, in plain words:

- File tools turn the path into an absolute path and refuse anything outside the project copy.
- `run_command` does **not** use a shell. The command is split into words and only 12 programs are allowed. `python` may run only a `.py` file inside the project or `-m pytest`.
- Every command has a time limit and its output is cut at 6000 characters.

This is a safety net against mistakes, not a wall against a hostile program. `docs/SECURITY.md` explains the limits.

An invalid call is never run. The model gets an `error: ...` message instead, so it can try again,
and the run records *why* it was invalid (`invalid_json`, `invalid_args`, `unknown_tool`). This
is the heart of what we measure.

### Create

<!-- file: src/toolcallbench/models.py -->
**`src/toolcallbench/models.py`**

```python
"""Plain data classes shared by the runner, the checks, the store and the report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

GROUPS = ("read", "edit", "run", "chain", "failure")


@dataclass
class Task:
    id: str
    group: str
    title: str
    prompt: str
    expect: dict[str, Any]
    reference: list[dict[str, Any]]
    tools_named: bool = False

    @property
    def baseline_calls(self) -> int:
        """Number of tool calls in the reference solution (used for the efficiency ratio)."""
        return sum(len(step.get("calls", [])) for step in self.reference)


@dataclass
class RawToolCall:
    """A tool call exactly as the backend returned it."""

    name: str
    arguments: Any  # dict for well-formed calls; str when the backend returned a JSON string


@dataclass
class BackendResponse:
    content: str = ""
    tool_calls: list[RawToolCall] = field(default_factory=list)
    eval_tokens: int = 0
    eval_seconds: float = 0.0
    prompt_tokens: int = 0


@dataclass
class CallRecord:
    """One tool call after validation and (if valid) execution."""

    index: int
    turn: int
    tool: str
    arguments: Any
    valid: bool
    ok: bool
    error_kind: str  # "" | "invalid_json" | "invalid_args" | "unknown_tool" | "tool_error"
    result: str


@dataclass
class Transcript:
    messages: list[dict[str, Any]] = field(default_factory=list)
    calls: list[CallRecord] = field(default_factory=list)
    final_text: str = ""
    turns: int = 0
    hit_limit: bool = False
    text_tool_call: bool = False
    eval_tokens: int = 0
    eval_seconds: float = 0.0
    wall_seconds: float = 0.0


@dataclass
class CheckResult:
    parse_ok: bool
    tool_ok: bool
    args_ok: bool
    outcome_ok: bool
    passed: bool
    failure_type: str
    efficiency: float | None
    details: list[str] = field(default_factory=list)
```

<!-- file: src/toolcallbench/patching.py -->
**`src/toolcallbench/patching.py`**

```python
"""Minimal unified-diff applier used by the apply_patch tool.

Context and removed lines must match the file exactly. The line counts in hunk
headers are not enforced, and trailing blank lines at the end of the patch text
are ignored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(Exception):
    """The patch is malformed or does not match the file."""


@dataclass
class Hunk:
    old_start: int
    lines: list[tuple[str, str]] = field(default_factory=list)  # (marker, text)


@dataclass
class FilePatch:
    path: str
    hunks: list[Hunk] = field(default_factory=list)


def _clean_path(path: str) -> str:
    path = path.split("\t")[0].strip()
    if path in ("/dev/null", "dev/null"):
        raise PatchError("creating or deleting files with a patch is not supported")
    if path.startswith(("a/", "b/")):
        path = path[2:]
    return path


def parse_patch(text: str) -> list[FilePatch]:
    lines = text.replace("\r\n", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    patches: list[FilePatch] = []
    current: FilePatch | None = None
    hunk: Hunk | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            current = FilePatch(path=_clean_path(lines[i + 1][4:]))
            patches.append(current)
            hunk = None
            i += 2
            continue
        match = HUNK_RE.match(line)
        if match:
            if current is None:
                raise PatchError("found a @@ hunk before any ---/+++ file header")
            hunk = Hunk(old_start=int(match.group(1)))
            current.hunks.append(hunk)
        elif hunk is not None:
            if line.startswith("\\"):
                pass  # "\ No newline at end of file"
            elif line[:1] in (" ", "-", "+"):
                hunk.lines.append((line[0], line[1:]))
            elif line == "":
                hunk.lines.append((" ", ""))  # a blank context line whose space was stripped
        i += 1
    if not patches:
        raise PatchError("no ---/+++ file headers found; expected a unified diff")
    for patch in patches:
        if not patch.hunks:
            raise PatchError(f"no @@ hunks found for {patch.path}")
    return patches


def _locate(file_lines: list[str], old: list[str], guess: int) -> int | None:
    if not old:
        return max(0, min(guess, len(file_lines)))
    size = len(old)
    candidates = [i for i in range(len(file_lines) - size + 1) if file_lines[i : i + size] == old]
    if not candidates:
        return None
    return min(candidates, key=lambda i: abs(i - guess))


def apply_hunks(original: str, hunks: list[Hunk], path: str) -> str:
    had_newline = original.endswith("\n")
    file_lines = original.split("\n")
    if had_newline:
        file_lines.pop()
    offset = 0
    for number, hunk in enumerate(hunks, 1):
        old = [text for marker, text in hunk.lines if marker in (" ", "-")]
        new = [text for marker, text in hunk.lines if marker in (" ", "+")]
        if not any(marker in ("+", "-") for marker, _ in hunk.lines):
            raise PatchError(f"hunk {number} for {path} changes nothing")
        guess = (hunk.old_start - 1 + offset) if old else (hunk.old_start + offset)
        position = _locate(file_lines, old, guess)
        if position is None:
            raise PatchError(
                f"hunk {number} does not match {path}: the context or removed lines differ from the file"
            )
        file_lines[position : position + len(old)] = new
        offset += len(new) - len(old)
    result = "\n".join(file_lines)
    return result + "\n" if had_newline else result


def apply_unified_diff(text: str, resolve: Callable[[str], Path]) -> list[str]:
    """Apply a unified diff. `resolve` maps a patch path to a safe absolute path or raises PatchError.

    All files are computed before any is written, so a bad hunk never leaves a half-applied patch.
    """
    patches = parse_patch(text)
    updates: list[tuple[Path, str, str]] = []
    for patch in patches:
        target = resolve(patch.path)
        if not target.is_file():
            raise PatchError(f"file not found: {patch.path}")
        original = target.read_text(encoding="utf-8")
        updates.append((target, apply_hunks(original, patch.hunks, patch.path), patch.path))
    messages = []
    for target, new_text, shown in updates:
        target.write_text(new_text, encoding="utf-8")
        messages.append(f"patched {shown}")
    return messages
```

<!-- file: src/toolcallbench/tools.py -->
**`src/toolcallbench/tools.py`**

```python
"""The six tools offered to the model, their JSON schemas, and a sandboxed executor.

The executor works inside one directory (a fresh copy of the fixture repo). It is
a safety net against accidents, not a security boundary: see docs/SECURITY.md.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .patching import PatchError, apply_unified_diff

IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".git"}
ALLOWED_COMMANDS = {"python", "python3", "pytest", "ls", "cat", "echo", "grep", "head", "tail", "wc", "touch", "mkdir"}


def _spec(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


TOOL_SPECS: list[dict[str, Any]] = [
    _spec(
        "read_file",
        "Read a text file in the repository. Output lines are prefixed with their line number. "
        "Use start_line and end_line (1-based, inclusive) to read only part of a file.",
        {
            "path": {"type": "string", "description": "File path relative to the repository root"},
            "start_line": {"type": "integer", "minimum": 1, "description": "First line to read"},
            "end_line": {"type": "integer", "minimum": 1, "description": "Last line to read"},
        },
        ["path"],
    ),
    _spec(
        "list_dir",
        "List the files and folders in a directory. Folder names end with a slash.",
        {"path": {"type": "string", "description": "Directory path relative to the repository root; default is the root"}},
        [],
    ),
    _spec(
        "grep",
        "Search files for a regular expression. Returns up to 50 matches as path:line:text.",
        {
            "pattern": {"type": "string", "description": "Regular expression to search for"},
            "path": {"type": "string", "description": "File or directory to search; default is the whole repository"},
        },
        ["pattern"],
    ),
    _spec(
        "edit_file",
        "Replace text in a file. old_text must match the file exactly once, including whitespace "
        "and without any line-number prefix.",
        {
            "path": {"type": "string", "description": "File path relative to the repository root"},
            "old_text": {"type": "string", "description": "Exact text to replace; must occur exactly once"},
            "new_text": {"type": "string", "description": "Replacement text"},
        },
        ["path", "old_text", "new_text"],
    ),
    _spec(
        "apply_patch",
        "Apply a unified diff to existing files. The diff needs --- and +++ file headers and @@ hunks; "
        "context and removed lines must match the file exactly.",
        {"patch": {"type": "string", "description": "The unified diff text"}},
        ["patch"],
    ),
    _spec(
        "run_command",
        "Run one command in the repository root without a shell (no pipes or redirects). "
        "Allowed programs: " + ", ".join(sorted(ALLOWED_COMMANDS)) + ". "
        "Python may run only a .py script inside the repository or `-m pytest`. "
        "Returns the exit code, stdout and stderr.",
        {"command": {"type": "string", "description": "The command line, for example: python -m pytest -q"}},
        ["command"],
    ),
]

TOOL_NAMES = [spec["function"]["name"] for spec in TOOL_SPECS]
_VALIDATORS = {spec["function"]["name"]: Draft202012Validator(spec["function"]["parameters"]) for spec in TOOL_SPECS}


def validate_arguments(name: str, arguments: Any) -> tuple[dict[str, Any] | None, str, str]:
    """Check a raw tool call. Returns (arguments, error_kind, message); error_kind is "" when valid."""
    if name not in _VALIDATORS:
        return None, "unknown_tool", f"unknown tool '{name}'; available tools: {', '.join(TOOL_NAMES)}"
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            return None, "invalid_json", f"arguments are not valid JSON: {exc.msg}"
    if not isinstance(arguments, dict):
        return None, "invalid_json", "arguments must be a JSON object"
    errors = sorted(_VALIDATORS[name].iter_errors(arguments), key=lambda e: [str(p) for p in e.path])
    if errors:
        return None, "invalid_args", errors[0].message
    return arguments, "", ""


class ToolError(Exception):
    """A tool could not do what was asked; the message goes back to the model."""


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[output truncated after {limit} characters]"


def run_trusted(argv: list[str], cwd: Path, timeout: float = 30.0) -> subprocess.CompletedProcess:
    """Run a command that the benchmark itself defines (checks, reference commands). `python` maps to this interpreter."""
    argv = list(argv)
    if argv and argv[0] in ("python", "python3"):
        argv[0] = sys.executable
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(cwd),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


class ToolExecutor:
    def __init__(self, root: Path, command_timeout: float = 20.0, max_output: int = 6000):
        self.root = Path(root).resolve()
        self.command_timeout = command_timeout
        self.max_output = max_output
        self._handlers = {
            "read_file": self._read_file,
            "list_dir": self._list_dir,
            "grep": self._grep,
            "edit_file": self._edit_file,
            "apply_patch": self._apply_patch,
            "run_command": self._run_command,
        }

    # ------------------------------------------------------------------ public

    def execute(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Run a validated call. Returns (ok, text). Failures become 'error: ...' text for the model."""
        try:
            return True, clip(self._handlers[name](**arguments), self.max_output)
        except (ToolError, PatchError) as exc:
            return False, f"error: {exc}"
        except (OSError, UnicodeError) as exc:
            return False, f"error: {exc.__class__.__name__}: {exc}"

    # ----------------------------------------------------------------- helpers

    def _resolve(self, path: str) -> Path:
        candidate = (self.root / path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ToolError(f"path '{path}' is outside the repository")
        return candidate

    def _resolve_for_patch(self, path: str) -> Path:
        try:
            return self._resolve(path)
        except ToolError as exc:
            raise PatchError(str(exc)) from exc

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    @staticmethod
    def _check_args(args: list[str]) -> None:
        for arg in args:
            value = arg.split("=", 1)[1] if arg.startswith("-") and "=" in arg else arg
            if arg.startswith("-") and "=" not in arg:
                continue
            if value.startswith(("/", "~")) or ".." in Path(value).parts:
                raise ToolError(f"argument '{arg}' points outside the repository")

    # ------------------------------------------------------------------- tools

    def _read_file(self, path: str, start_line: int | None = None, end_line: int | None = None) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"file not found: {path}")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = 1 if start_line is None else start_line
        end = len(lines) if end_line is None else end_line
        if end < start:
            raise ToolError("end_line must not be smaller than start_line")
        if lines and start > len(lines):
            raise ToolError(f"start_line {start} is beyond the end of the file ({len(lines)} lines)")
        selected = lines[start - 1 : end]
        if not selected:
            return "(empty file)"
        return "\n".join(f"{number:>4}| {text}" for number, text in enumerate(selected, start))

    def _list_dir(self, path: str = ".") -> str:
        target = self._resolve(path)
        if not target.is_dir():
            raise ToolError(f"directory not found: {path}")
        entries = sorted(p for p in target.iterdir() if p.name not in IGNORED_NAMES)
        if not entries:
            return "(empty directory)"
        return "\n".join(p.name + ("/" if p.is_dir() else "") for p in entries)

    def _grep(self, pattern: str, path: str = ".") -> str:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ToolError(f"invalid regular expression: {exc}") from exc
        target = self._resolve(path)
        if not target.exists():
            raise ToolError(f"path not found: {path}")
        if target.is_file():
            files = [target]
        else:
            files = []
            for current, dirs, names in os.walk(target):
                dirs[:] = sorted(d for d in dirs if d not in IGNORED_NAMES)
                files.extend(Path(current) / n for n in sorted(names))
        matches: list[str] = []
        for file in files:
            try:
                text = file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    matches.append(f"{self._rel(file)}:{number}:{line}")
                    if len(matches) > 50:
                        return "\n".join(matches[:50]) + "\n[more matches not shown]"
        return "\n".join(matches) if matches else "no matches"

    def _edit_file(self, path: str, old_text: str, new_text: str) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"file not found: {path}")
        if old_text == "":
            raise ToolError("old_text must not be empty")
        text = target.read_text(encoding="utf-8")
        count = text.count(old_text)
        if count == 0:
            raise ToolError(
                "old_text was not found in the file. It must match exactly, including whitespace; "
                "copy it from read_file output without the line-number prefix."
            )
        if count > 1:
            raise ToolError(f"old_text matches {count} places; include more surrounding lines so it matches once")
        target.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return f"edited {path}"

    def _apply_patch(self, patch: str) -> str:
        return "\n".join(apply_unified_diff(patch, self._resolve_for_patch))

    def _run_command(self, command: str) -> str:
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            raise ToolError(f"could not parse the command: {exc}") from exc
        if not parts:
            raise ToolError("empty command")
        program, args = parts[0], parts[1:]
        if program not in ALLOWED_COMMANDS:
            raise ToolError(f"command '{program}' is not allowed; allowed: {', '.join(sorted(ALLOWED_COMMANDS))}")
        if program in ("python", "python3"):
            argv = self._python_argv(args)
        elif program == "pytest":
            self._check_args(args)
            argv = [sys.executable, "-m", "pytest", *args]
        else:
            self._check_args(args)
            argv = [program, *args]
        try:
            proc = run_trusted(argv, self.root, self.command_timeout)
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"command timed out after {self.command_timeout:g}s") from exc
        except FileNotFoundError as exc:
            raise ToolError(f"command not found: {program}") from exc
        return f"exit_code: {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    def _python_argv(self, args: list[str]) -> list[str]:
        if args[:2] == ["-m", "pytest"]:
            self._check_args(args[2:])
            return [sys.executable, "-m", "pytest", *args[2:]]
        if args and not args[0].startswith("-") and args[0].endswith(".py"):
            script = self._resolve(args[0])
            if not script.is_file():
                raise ToolError(f"script not found: {args[0]}")
            self._check_args(args[1:])
            return [sys.executable, str(script), *args[1:]]
        raise ToolError("python may only run a .py script inside the repository, or `-m pytest`")
```

Test helpers. `conftest.py` gives every test a fresh copy of the sample project:

<!-- file: tests/conftest.py -->
**`tests/conftest.py`**

```python
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
```

<!-- file: tests/test_patching.py -->
**`tests/test_patching.py`**

```python
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
```

<!-- file: tests/test_tools.py -->
**`tests/test_tools.py`**

```python
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
```

### Run

```text
$ python -m pytest tests/test_patching.py tests/test_tools.py
......................                                                   [100%]
22 passed in N.NNs
```

### Checkpoint

```bash
git add -A && git commit -m "Day 2: tools, sandbox, patch engine"
```

---

## Day 3: Backends and configuration

**Goal:** code that can talk to Ollama, to OpenAI-style servers, and to a fake model.

### Why

A *backend* hides how a server speaks. The runner only asks `backend.chat(messages, tools)` and
gets a `BackendResponse` (text, tool calls, token counts). Three backends:

- **Ollama** (`ollama.py`): `POST /api/chat` with `stream: false`. Tool-call arguments come back as a real object. Speed comes from `eval_count` and `eval_duration` (nanoseconds).
- **OpenAI-compatible** (`openai_compat.py`): for llama.cpp's `llama-server`, LM Studio and vLLM. Here the arguments come back as a **JSON string**, which the model may get wrong. That makes this backend good at finding `invalid_json` problems.
- **Scripted** (`scripted.py`): a fake model that replays each task's correct solution, or fails in a chosen way (bad JSON, unknown tool, and so on). We use it to test the program and to prove the scoring detects each kind of failure. Without a fake model we could not test anything before downloading gigabytes of weights.

`base.py` has `BackendError` (the *server* failed, not the model) and a small HTTP helper that
uses only Python's standard library.

`config.py` holds the settings with their defaults. Three of them matter for your Mac:

- `num_ctx: 16384`: the context length. Ollama's own default is only 4096 on machines with less than 24 GB, which is too small for multi-step work. 16k costs about 1 to 2 GB of memory for an 8B model.
- `temperature: 0.0` and a fixed `seed`: as repeatable as a model can be. Each repeat adds 1 to the seed.
- `repeats: 3`: one run of one task proves little; models are not perfectly steady.

### Create

<!-- file: src/toolcallbench/backends/base.py -->
**`src/toolcallbench/backends/base.py`**

```python
"""Backend interface and a small JSON-over-HTTP helper (standard library only)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ..models import BackendResponse


class BackendError(RuntimeError):
    """The model server could not be reached or returned an error. Not a model failure."""


class Backend:
    name = "backend"

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> BackendResponse:
        raise NotImplementedError

    def check(self) -> None:
        """Raise BackendError if the server or the model is not usable. Called once before a sweep."""

    def describe(self) -> dict[str, Any]:
        """Facts about the server and model, recorded in the session settings."""
        return {"backend": self.name}


def request_json(method: str, url: str, payload: dict[str, Any] | None, timeout: float) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        raise BackendError(f"HTTP {exc.code} from {url}: {body}") from exc
    except json.JSONDecodeError as exc:
        raise BackendError(f"{url} returned invalid JSON") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BackendError(f"cannot reach {url}: {exc}") from exc
```

<!-- file: src/toolcallbench/backends/ollama.py -->
**`src/toolcallbench/backends/ollama.py`**

```python
"""Ollama backend: POST /api/chat with tools, non-streaming."""
from __future__ import annotations

from typing import Any

from ..models import BackendResponse, RawToolCall
from .base import Backend, BackendError, request_json


class OllamaBackend(Backend):
    name = "ollama"

    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
        options: dict[str, Any] | None = None,
        think: bool | None = None,
        timeout: float = 300.0,
        keep_alive: str = "30m",
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.options = dict(options or {})
        self.think = think
        self.timeout = timeout
        self.keep_alive = keep_alive

    # ------------------------------------------------------------ server facts

    def version(self) -> str:
        return str(request_json("GET", f"{self.host}/api/version", None, self.timeout).get("version", "unknown"))

    def list_models(self) -> list[str]:
        data = request_json("GET", f"{self.host}/api/tags", None, self.timeout)
        return [m.get("name", "") for m in data.get("models", [])]

    def show(self) -> dict[str, Any]:
        return request_json("POST", f"{self.host}/api/show", {"model": self.model}, self.timeout)

    def check(self) -> None:
        installed = self.list_models()
        wanted = {self.model, self.model if ":" in self.model else self.model + ":latest"}
        if not wanted & set(installed):
            raise BackendError(f"model '{self.model}' is not installed in Ollama; run: ollama pull {self.model}")

    def describe(self) -> dict[str, Any]:
        info: dict[str, Any] = {"backend": self.name, "host": self.host}
        try:
            info["backend_version"] = self.version()
            shown = self.show()
            details = shown.get("details", {})
            info["quant"] = details.get("quantization_level", "")
            info["parameter_size"] = details.get("parameter_size", "")
            info["family"] = details.get("family", "")
            info["capabilities"] = shown.get("capabilities", [])
        except BackendError:
            pass
        return info

    # -------------------------------------------------------------------- chat

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> BackendResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": self.options,
            "keep_alive": self.keep_alive,
        }
        if self.think is not None:
            payload["think"] = self.think
        data = request_json("POST", f"{self.host}/api/chat", payload, self.timeout)
        message = data.get("message") or {}
        calls = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            calls.append(RawToolCall(name=str(function.get("name", "")), arguments=function.get("arguments", {})))
        return BackendResponse(
            content=message.get("content") or "",
            tool_calls=calls,
            eval_tokens=int(data.get("eval_count") or 0),
            eval_seconds=float(data.get("eval_duration") or 0) / 1e9,
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
        )
```

<!-- file: src/toolcallbench/backends/openai_compat.py -->
**`src/toolcallbench/backends/openai_compat.py`**

```python
"""OpenAI-compatible backend for llama.cpp `llama-server`, LM Studio, vLLM and similar servers.

Tool arguments arrive as JSON strings here, so this backend exercises the invalid-JSON path.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..models import BackendResponse, RawToolCall
from .base import Backend, BackendError, request_json


def to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert the runner's Ollama-style messages to the OpenAI chat format (adds tool call ids)."""
    out: list[dict[str, Any]] = []
    pending: list[str] = []
    counter = 0
    for message in messages:
        if message["role"] == "assistant" and message.get("tool_calls"):
            pending = []
            calls = []
            for item in message["tool_calls"]:
                counter += 1
                call_id = f"call_{counter}"
                pending.append(call_id)
                function = item["function"]
                calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": function["name"], "arguments": json.dumps(function.get("arguments", {}))},
                    }
                )
            out.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": calls})
        elif message["role"] == "tool":
            call_id = pending.pop(0) if pending else "call_0"
            out.append({"role": "tool", "tool_call_id": call_id, "content": message["content"]})
        else:
            out.append({"role": message["role"], "content": message.get("content") or ""})
    return out


class OpenAICompatBackend(Backend):
    name = "openai-compat"

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:8080",
        options: dict[str, Any] | None = None,
        timeout: float = 300.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.options = dict(options or {})
        self.timeout = timeout

    def check(self) -> None:
        request_json("GET", f"{self.base_url}/v1/models", None, self.timeout)

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name, "host": self.base_url}

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> BackendResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": to_openai_messages(messages),
            "tools": tools,
            "stream": False,
        }
        for key in ("temperature", "seed"):
            if key in self.options:
                payload[key] = self.options[key]
        started = time.monotonic()
        data = request_json("POST", f"{self.base_url}/v1/chat/completions", payload, self.timeout)
        elapsed = time.monotonic() - started
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError("response has no choices[0].message") from exc
        calls = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            calls.append(RawToolCall(name=str(function.get("name", "")), arguments=function.get("arguments", "")))
        usage = data.get("usage") or {}
        timings = data.get("timings") or {}
        eval_seconds = float(timings["predicted_ms"]) / 1000 if "predicted_ms" in timings else elapsed
        return BackendResponse(
            content=message.get("content") or "",
            tool_calls=calls,
            eval_tokens=int(usage.get("completion_tokens") or 0),
            eval_seconds=eval_seconds,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
        )
```

<!-- file: src/toolcallbench/backends/scripted.py -->
**`src/toolcallbench/backends/scripted.py`**

```python
"""A fake model that replays each task's reference solution, or fails in a chosen way.

It is used to validate the tasks, to test the harness without a real model, and for dry runs.
"""
from __future__ import annotations

import json
from typing import Any

from ..models import BackendResponse, RawToolCall, Task
from .base import Backend, BackendError

PROFILES = (
    "oracle",
    "invalid_json",
    "unknown_tool",
    "wrong_tool",
    "text_call",
    "no_call",
    "call_limit",
    "bad_edit",
)


class ScriptedBackend(Backend):
    name = "scripted"

    def __init__(self, tasks: list[Task], profile: str = "oracle"):
        if profile not in PROFILES:
            raise ValueError(f"unknown profile '{profile}'; choose from {', '.join(PROFILES)}")
        self.by_prompt = {task.prompt: task for task in tasks}
        self.profile = profile

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name, "profile": self.profile}

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> BackendResponse:
        prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
        task = self.by_prompt.get(prompt)
        if task is None:
            raise BackendError("scripted backend received a prompt that matches no task")
        turn = sum(1 for m in messages if m["role"] == "assistant")
        content, calls = self._step(task, turn)
        return BackendResponse(content=content, tool_calls=calls, eval_tokens=8, eval_seconds=0.01, prompt_tokens=100)

    # ------------------------------------------------------------------ steps

    @staticmethod
    def _oracle(task: Task, turn: int) -> tuple[str, list[RawToolCall]]:
        if turn >= len(task.reference):
            return "Done.", []
        step = task.reference[turn]
        if "calls" in step:
            return "", [RawToolCall(c["tool"], dict(c.get("args", {}))) for c in step["calls"]]
        return str(step["final"]), []

    def _step(self, task: Task, turn: int) -> tuple[str, list[RawToolCall]]:
        profile = self.profile
        if profile == "oracle":
            return self._oracle(task, turn)
        if profile == "call_limit":
            return "", [RawToolCall("list_dir", {"path": "."})]
        if profile == "no_call":
            return "I believe the answer is 42.", []
        if profile == "bad_edit":
            content, calls = self._oracle(task, turn)
            for call in calls:
                if call.name == "edit_file":
                    call.arguments = {**call.arguments, "old_text": "THIS TEXT IS NOT IN THE FILE"}
                elif call.name == "apply_patch":
                    call.arguments = {"patch": "--- a/missing.py\n+++ b/missing.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"}
            return content, calls
        if turn >= 1:
            return "Done.", []
        first = next((c for step in task.reference for c in step.get("calls", [])), None)
        if first is None:
            # The task needs no tools. A wrong_tool model calls one anyway; the others answer correctly.
            if profile == "wrong_tool":
                return "", [RawToolCall("list_dir", {})]
            return self._oracle(task, turn)
        tool, args = first["tool"], dict(first.get("args", {}))
        if profile == "invalid_json":
            return "", [RawToolCall(tool, '{"path": ')]
        if profile == "unknown_tool":
            return "", [RawToolCall("search_everything", {"query": "x"})]
        if profile == "wrong_tool":
            return "", [RawToolCall("list_dir", {})]
        if profile == "text_call":
            return json.dumps({"name": tool, "arguments": args}), []
        raise AssertionError(profile)  # pragma: no cover
```

<!-- file: src/toolcallbench/backends/__init__.py -->
**`src/toolcallbench/backends/__init__.py`**

```python
"""Model backends and a factory."""
from __future__ import annotations

from typing import Any

from ..models import Task
from .base import Backend, BackendError
from .ollama import OllamaBackend
from .openai_compat import OpenAICompatBackend
from .scripted import PROFILES, ScriptedBackend

BACKEND_KINDS = ("ollama", "openai-compat", "scripted")

__all__ = [
    "BACKEND_KINDS",
    "PROFILES",
    "Backend",
    "BackendError",
    "OllamaBackend",
    "OpenAICompatBackend",
    "ScriptedBackend",
    "make_backend",
]


def make_backend(
    kind: str,
    *,
    model: str,
    host: str,
    options: dict[str, Any],
    think: bool | None,
    timeout: float,
    tasks: list[Task],
    profile: str = "oracle",
) -> Backend:
    if kind == "ollama":
        return OllamaBackend(model, host=host, options=options, think=think, timeout=timeout)
    if kind == "openai-compat":
        return OpenAICompatBackend(model, base_url=host, options=options, timeout=timeout)
    if kind == "scripted":
        return ScriptedBackend(tasks, profile=profile)
    raise ValueError(f"unknown backend '{kind}'; choose from {', '.join(BACKEND_KINDS)}")
```

<!-- file: src/toolcallbench/config.py -->
**`src/toolcallbench/config.py`**

```python
"""Run configuration: defaults, YAML loading and project paths."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SETTINGS_KEYS = {"num_ctx", "temperature", "seed", "repeats", "max_calls", "max_turns", "request_timeout"}
TOP_KEYS = {"backend", "host", "settings", "declared_server", "models"}


class ConfigError(ValueError):
    """The config file is invalid."""


@dataclass
class ModelSpec:
    name: str
    think: bool | None = None


@dataclass
class RunConfig:
    backend: str = "ollama"
    host: str = ""  # empty means the default address of the chosen backend
    models: list[ModelSpec] = field(default_factory=list)
    num_ctx: int = 16384
    temperature: float = 0.0
    seed: int = 42
    repeats: int = 3
    max_calls: int = 12
    max_turns: int = 10
    request_timeout: float = 300.0
    declared_kv_cache_type: str = "f16"
    declared_flash_attention: bool = False
    profile: str = "oracle"  # only used by the scripted backend

    def options_for(self, repeat: int) -> dict[str, Any]:
        """Per-request model options. The seed changes with the repeat number."""
        return {"temperature": self.temperature, "seed": self.seed + repeat - 1, "num_ctx": self.num_ctx}


def _model_spec(item: Any) -> ModelSpec:
    if isinstance(item, str):
        return ModelSpec(name=item)
    if isinstance(item, dict) and isinstance(item.get("name"), str):
        unknown = set(item) - {"name", "think"}
        if unknown:
            raise ConfigError(f"unknown model keys {sorted(unknown)}; allowed: name, think")
        think = item.get("think")
        if think is not None and not isinstance(think, bool):
            raise ConfigError(f"model '{item['name']}': think must be true or false")
        return ModelSpec(name=item["name"], think=think)
    raise ConfigError("each model must be a string or a mapping with a 'name'")


def load_config(path: Path) -> RunConfig:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: the top level must be a mapping")
    unknown = set(data) - TOP_KEYS
    if unknown:
        raise ConfigError(f"{path}: unknown keys {sorted(unknown)}; allowed: {sorted(TOP_KEYS)}")
    cfg = RunConfig()
    cfg.backend = data.get("backend", cfg.backend)
    cfg.host = data.get("host", cfg.host)
    settings = data.get("settings") or {}
    bad = set(settings) - SETTINGS_KEYS
    if bad:
        raise ConfigError(f"{path}: unknown settings {sorted(bad)}; allowed: {sorted(SETTINGS_KEYS)}")
    for key, value in settings.items():
        setattr(cfg, key, value)
    declared = data.get("declared_server") or {}
    cfg.declared_kv_cache_type = str(declared.get("kv_cache_type", cfg.declared_kv_cache_type))
    cfg.declared_flash_attention = bool(declared.get("flash_attention", cfg.declared_flash_attention))
    cfg.models = [_model_spec(m) for m in data.get("models") or []]
    return cfg


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: the current directory) to a folder holding tasks/ and fixtures/repo/."""
    start = Path(start or Path.cwd()).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "tasks").is_dir() and (candidate / "fixtures" / "repo").is_dir():
            return candidate
    return start
```

Three ready-made config files. The first is the plan for your Mac, the second compares two
quantization levels of the same model, the third needs no model.

<!-- file: configs/m4-16gb.yaml -->
**`configs/m4-16gb.yaml`**

```yaml
# Benchmark plan for a MacBook M4 with 16 GB of unified memory.
# Start the server first:  scripts/serve_ollama.sh
# Then:                    toolcallbench run --config configs/m4-16gb.yaml
backend: ollama
host: http://localhost:11434
settings:
  num_ctx: 16384      # about 12 GB of the 16 GB can be used by the GPU, so keep the context moderate
  temperature: 0.0
  seed: 42
  repeats: 3
  max_calls: 12
  max_turns: 10
  request_timeout: 300
declared_server:      # what scripts/serve_ollama.sh starts; recorded in the report, not enforced
  kv_cache_type: q8_0
  flash_attention: true
models:
  - name: qwen3:8b
    think: false     # Qwen3 thinks by default, which is slow. Remove this line to test it with thinking on.
  - llama3.1:8b
  - qwen2.5:7b
```

<!-- file: configs/quant-sweep-qwen3-8b.yaml -->
**`configs/quant-sweep-qwen3-8b.yaml`**

```yaml
# Same model at two quantization levels: how much tool-calling accuracy does Q4 give up?
# Pull the tags first (check the exact names on https://ollama.com/library/qwen3/tags):
#   ollama pull qwen3:8b-q4_K_M
#   ollama pull qwen3:8b-q8_0
# A Q8_0 8B model is about 9 GB, so keep num_ctx at 8192 to 16384 on a 16 GB Mac.
backend: ollama
settings:
  num_ctx: 8192
  temperature: 0.0
  seed: 42
  repeats: 3
declared_server:
  kv_cache_type: q8_0
  flash_attention: true
models:
  - qwen3:8b-q4_K_M
  - qwen3:8b-q8_0
```

<!-- file: configs/smoke-scripted.yaml -->
**`configs/smoke-scripted.yaml`**

```yaml
# No model needed: replays the reference solutions. Proves the harness works end to end.
backend: scripted
settings:
  repeats: 1
models:
  - scripted-oracle
```

<!-- file: tests/test_config.py -->
**`tests/test_config.py`**

```python
import pytest

from toolcallbench.config import ConfigError, RunConfig, load_config


def test_defaults_target_16gb():
    cfg = RunConfig()
    assert cfg.num_ctx == 16384 and cfg.temperature == 0.0 and cfg.repeats == 3


def test_seed_changes_per_repeat():
    cfg = RunConfig(seed=10)
    assert [cfg.options_for(r)["seed"] for r in (1, 2, 3)] == [10, 11, 12]


def test_shipped_configs_load():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "configs"
    for name in ("m4-16gb.yaml", "quant-sweep-qwen3-8b.yaml", "smoke-scripted.yaml"):
        cfg = load_config(root / name)
        assert cfg.models
    assert load_config(root / "m4-16gb.yaml").declared_kv_cache_type == "q8_0"


@pytest.mark.parametrize(
    "text,message",
    [
        ("- a\n- b\n", "mapping"),
        ("colour: red\n", "unknown keys"),
        ("settings: {speed: 1}\n", "unknown settings"),
        ("models: [{name: x, think: maybe}]\n", "think"),
        ("models: [{name: x, extra: 1}]\n", "unknown model keys"),
        ("models: [5]\n", "string or a mapping"),
        ("a: [\n", "invalid YAML"),
    ],
)
def test_bad_configs(tmp_path, text, message):
    path = tmp_path / "c.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError, match=message):
        load_config(path)
```

### Run

```text
$ python -m pytest tests/test_config.py
..........                                                               [100%]
10 passed in N.NNs
```

### Checkpoint

```bash
git add -A && git commit -m "Day 3: backends and config"
```

---

## Day 4: The 20 tasks, the scoring rules and the runner

**Goal:** every task can be run against the fake model and scored, and every task is proven passable.

### Why

**Tasks.** Each task is a YAML file with a `prompt`, an `expect` block (what a pass looks like)
and a `reference` (a correct solution). Five groups:

| Group | Count | What it tests |
| --- | --- | --- |
| read | 5 | One tool call and a question about the result |
| edit | 5 | Changing files with `edit_file` or `apply_patch` |
| run | 3 | Running commands and reporting what they print |
| chain | 4 | Several dependent steps, no tool named in the prompt |
| failure | 3 | Answering without tools, parallel calls, recovering from a wrong path |

In 12 tasks the prompt names the tool; in 8 it does not. That separates "can call a tool" from
"can decide which tool to call".

**Scoring** (`checks.py`). No AI judge: the verdict is plain code. A run **passes** when three
parts succeed:

1. **Parse**: every call is valid JSON with the right arguments for a real tool, and the model did not just *write* a tool call as text.
2. **Tool**: the right tools in the right amount (not too many, not too few, in order when the task says so, together in one step when the task wants parallel calls).
3. **Outcome**: the final answer contains what it should, and the repository ends in the right state. The task itself can run a command (for example the tests) to check.

Two more numbers are reported but do not decide pass or fail: **Args** (did the expected
arguments appear?) and **Efficiency** (calls made divided by calls in the reference).

A failed run gets exactly one reason from a fixed priority list (for example `invalid_json`
before `wrong_tool` before `outcome_mismatch`), so the report can count them.

**The runner** (`runner.py`) is the loop: copy the sample project, send the prompt, run the
tool calls, send the results back, repeat until the model answers or a limit is hit, then score.
If the server crashes, the run is marked `error`, not "failed".

### Create

The task loader:

<!-- file: src/toolcallbench/tasks.py -->
**`src/toolcallbench/tasks.py`**

```python
"""Load and validate task files (tasks/*.yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .models import GROUPS, Task

EXPECT_KEYS = {
    "calls",
    "min_calls",
    "max_calls",
    "ordered",
    "parallel",
    "no_tool_calls",
    "forbidden_tools",
    "files_exist",
    "final_files",
    "command",
    "answer_contains",
    "answer_regex",
}

_CALL = {
    "type": "object",
    "required": ["tool"],
    "additionalProperties": False,
    "properties": {
        "tool": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}, "minItems": 1}]},
        "args": {"type": "object"},
    },
}

TASK_SCHEMA = {
    "type": "object",
    "required": ["id", "group", "title", "prompt", "expect", "reference"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": "^[a-z]+-[0-9]{2}$"},
        "group": {"enum": list(GROUPS)},
        "title": {"type": "string", "minLength": 1},
        "tools_named": {"type": "boolean"},
        "prompt": {"type": "string", "minLength": 1},
        "expect": {"type": "object"},
        "reference": {
            "type": "array",
            "minItems": 1,
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "required": ["calls"],
                        "additionalProperties": False,
                        "properties": {
                            "calls": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "object",
                                    "required": ["tool"],
                                    "additionalProperties": False,
                                    "properties": {"tool": {"type": "string"}, "args": {"type": "object"}},
                                },
                            }
                        },
                    },
                    {
                        "type": "object",
                        "required": ["final"],
                        "additionalProperties": False,
                        "properties": {"final": {"type": "string"}},
                    },
                ]
            },
        },
    },
}


class TaskError(ValueError):
    """A task file is invalid."""


def _validate_expect(expect: dict[str, Any], where: str) -> None:
    unknown = set(expect) - EXPECT_KEYS
    if unknown:
        raise TaskError(f"{where}: unknown expect keys {sorted(unknown)}; allowed: {sorted(EXPECT_KEYS)}")
    for req in expect.get("calls", []):
        try:
            jsonschema.validate(req, _CALL)
        except jsonschema.ValidationError as exc:
            raise TaskError(f"{where}: bad expect.calls entry: {exc.message}") from exc
    for item in expect.get("command", []):
        if not isinstance(item, dict) or not isinstance(item.get("argv"), list):
            raise TaskError(f"{where}: each expect.command entry needs an argv list")


def load_task_file(path: Path) -> Task:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaskError(f"{path.name}: invalid YAML: {exc}") from exc
    try:
        jsonschema.validate(data, TASK_SCHEMA)
    except jsonschema.ValidationError as exc:
        location = "/".join(str(p) for p in exc.absolute_path) or "top level"
        raise TaskError(f"{path.name}: {exc.message} (at {location})") from exc
    if data["id"].split("-")[0] != data["group"]:
        raise TaskError(f"{path.name}: id '{data['id']}' must start with its group '{data['group']}'")
    _validate_expect(data["expect"], path.name)
    if "final" not in data["reference"][-1]:
        raise TaskError(f"{path.name}: the last reference step must be a 'final' answer")
    return Task(
        id=data["id"],
        group=data["group"],
        title=data["title"],
        prompt=data["prompt"].strip(),
        expect=data["expect"],
        reference=data["reference"],
        tools_named=bool(data.get("tools_named", False)),
    )


def load_tasks(tasks_dir: Path) -> list[Task]:
    tasks_dir = Path(tasks_dir)
    files = sorted(tasks_dir.glob("*.yaml"))
    if not files:
        raise TaskError(f"no task files (*.yaml) found in {tasks_dir}")
    tasks = [load_task_file(f) for f in files]
    seen: set[str] = set()
    for task in tasks:
        if task.id in seen:
            raise TaskError(f"duplicate task id '{task.id}'")
        seen.add(task.id)
    return tasks


def select_tasks(tasks: list[Task], ids: list[str] | None = None, groups: list[str] | None = None) -> list[Task]:
    selected = tasks
    if ids:
        unknown = set(ids) - {t.id for t in tasks}
        if unknown:
            raise TaskError(f"unknown task ids: {sorted(unknown)}")
        selected = [t for t in selected if t.id in ids]
    if groups:
        unknown = set(groups) - set(GROUPS)
        if unknown:
            raise TaskError(f"unknown groups: {sorted(unknown)}; choose from {', '.join(GROUPS)}")
        selected = [t for t in selected if t.group in groups]
    if not selected:
        raise TaskError("no tasks selected")
    return selected
```

The scoring rules and the runner:

<!-- file: src/toolcallbench/checks.py -->
**`src/toolcallbench/checks.py`**

```python
"""Deterministic scoring of one run. There is no AI judge: every verdict comes from plain code.

A run passes when Parse, Tool and Outcome all succeed. Arguments and Efficiency are reported separately.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .models import CallRecord, CheckResult, Task, Transcript
from .tools import run_trusted

EDIT_TOOLS = {"edit_file", "apply_patch"}

FAILURE_TYPES = (
    "invalid_json",
    "invalid_args",
    "unknown_tool",
    "text_tool_call",
    "no_call",
    "unneeded_call",
    "call_limit",
    "not_parallel",
    "wrong_tool",
    "too_few_calls",
    "patch_failed",
    "wrong_args",
    "outcome_mismatch",
)


def _norm_path(value: Any) -> str:
    text = str(value).strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    if len(text) > 1:
        text = text.rstrip("/")
    return text or "."


def _norm(key: str, value: Any) -> str:
    return _norm_path(value) if key == "path" else str(value)


def _value_matches(spec: Any, actual: Any, key: str) -> bool:
    got = _norm(key, actual)
    if isinstance(spec, dict):
        if "contains" in spec:
            return str(spec["contains"]) in got
        if "regex" in spec:
            return re.search(spec["regex"], got) is not None
        if "one_of" in spec:
            return got in [_norm(key, v) for v in spec["one_of"]]
        raise ValueError(f"unknown argument matcher: {sorted(spec)}")
    return got == _norm(key, spec)


def _tools(req: dict[str, Any]) -> list[str]:
    tool = req["tool"]
    return list(tool) if isinstance(tool, list) else [tool]


def _tool_matches(req: dict[str, Any], call: CallRecord) -> bool:
    return call.valid and call.tool in _tools(req)


def _args_match(req: dict[str, Any], call: CallRecord) -> bool:
    args = call.arguments if isinstance(call.arguments, dict) else {}
    return all(key in args and _value_matches(spec, args[key], key) for key, spec in (req.get("args") or {}).items())


def _assign(reqs: list[dict[str, Any]], calls: list[CallRecord], ordered: bool, start: int = 0, used: frozenset = frozenset()):
    """Match each requirement to a distinct call by tool name. Returns the call positions or None."""
    if not reqs:
        return []
    first, rest = reqs[0], reqs[1:]
    for position in range(start if ordered else 0, len(calls)):
        if position in used or not _tool_matches(first, calls[position]):
            continue
        tail = _assign(rest, calls, ordered, position + 1, used | {position})
        if tail is not None:
            return [position, *tail]
    return None


def _parallel_ok(reqs: list[dict[str, Any]], calls: list[CallRecord]) -> bool:
    turns: dict[int, list[CallRecord]] = {}
    for call in calls:
        turns.setdefault(call.turn, []).append(call)
    return any(_assign(reqs, group, False) is not None for group in turns.values())


def _check_outcome(task: Task, tr: Transcript, root: Path, fixture_dir: Path, details: list[str]) -> bool:
    exp = task.expect
    ok = True

    def fail(message: str) -> None:
        nonlocal ok
        ok = False
        details.append(message)

    answer = tr.final_text or ""
    for needle in exp.get("answer_contains", []):
        if needle.lower() not in answer.lower():
            fail(f"answer does not contain {needle!r}")
    for pattern in exp.get("answer_regex", []):
        if not re.search(pattern, answer, re.IGNORECASE):
            fail(f"answer does not match /{pattern}/")
    for rel in exp.get("files_exist", []):
        if not (root / rel).is_file():
            fail(f"expected file {rel} does not exist")
    for rel, spec in (exp.get("final_files") or {}).items():
        path = root / rel
        if not path.is_file():
            fail(f"expected file {rel} does not exist")
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for text in spec.get("contains", []):
            if text not in content:
                fail(f"{rel} does not contain {text!r}")
        for text in spec.get("not_contains", []):
            if text in content:
                fail(f"{rel} still contains {text!r}")
        if spec.get("unchanged") and content != (fixture_dir / rel).read_text(encoding="utf-8"):
            fail(f"{rel} was changed but must stay as it was")
    for item in exp.get("command", []):
        try:
            proc = run_trusted(item["argv"], root)
        except subprocess.TimeoutExpired:
            fail(f"check command timed out: {item['argv']}")
            continue
        want = item.get("exit_code", 0)
        if proc.returncode != want:
            tail = (proc.stdout + proc.stderr).strip()[-300:]
            fail(f"check command exited {proc.returncode}, wanted {want}: {tail}")
    return ok


def evaluate(task: Task, tr: Transcript, root: Path, fixture_dir: Path, default_max_calls: int = 12) -> CheckResult:
    exp = task.expect
    details: list[str] = []
    calls = tr.calls
    valid = [c for c in calls if c.valid]

    # Parse: every call must be well formed and name a real tool.
    parse_type = ""
    if tr.text_tool_call:
        parse_type = "text_tool_call"
    else:
        bad = next((c for c in calls if not c.valid), None)
        if bad:
            parse_type = bad.error_kind
    parse_ok = parse_type == ""
    if parse_type:
        details.append(f"parse: {parse_type}")

    # Tool: the right tools, in the right amount.
    reqs = exp.get("calls") or []
    ordered = bool(exp.get("ordered"))
    max_calls = exp.get("max_calls", default_max_calls)
    min_calls = exp.get("min_calls", len(reqs))
    tool_type = ""
    if tr.hit_limit:
        tool_type = "call_limit"
    elif exp.get("no_tool_calls"):
        if calls:
            tool_type = "unneeded_call"
    elif not calls:
        tool_type = "no_call" if min_calls > 0 else ""
    elif len(calls) > max_calls:
        tool_type = "call_limit"
    elif len(calls) < min_calls:
        tool_type = "too_few_calls"
    elif any(c.tool in exp.get("forbidden_tools", []) for c in calls):
        tool_type = "wrong_tool"
    elif reqs and _assign(reqs, valid, ordered) is None:
        tool_type = "wrong_tool"
    elif exp.get("parallel") and not _parallel_ok(reqs, valid):
        tool_type = "not_parallel"
    tool_ok = tool_type == ""
    if tool_type:
        details.append(f"tool: {tool_type}")

    # Arguments: reported separately from pass/fail.
    args_ok = True
    for req in reqs:
        if req.get("args") and not any(_tool_matches(req, c) and _args_match(req, c) for c in valid):
            args_ok = False
            details.append(f"arguments: no {_tools(req)} call matched {req['args']}")

    # Outcome: the answer text and the final state of the repository.
    outcome_ok = _check_outcome(task, tr, root, fixture_dir, details)

    if not parse_ok:
        failure = parse_type
    elif not tool_ok:
        failure = tool_type
    elif not outcome_ok:
        if any(c.tool in EDIT_TOOLS and c.valid and not c.ok for c in calls):
            failure = "patch_failed"
        elif not args_ok:
            failure = "wrong_args"
        else:
            failure = "outcome_mismatch"
    else:
        failure = "ok"

    baseline = task.baseline_calls
    if baseline > 0:
        efficiency: float | None = round(len(calls) / baseline, 2)
    else:
        efficiency = 1.0 if not calls else None

    return CheckResult(
        parse_ok=parse_ok,
        tool_ok=tool_ok,
        args_ok=args_ok,
        outcome_ok=outcome_ok,
        passed=parse_ok and tool_ok and outcome_ok,
        failure_type=failure,
        efficiency=efficiency,
        details=details,
    )
```

<!-- file: src/toolcallbench/runner.py -->
**`src/toolcallbench/runner.py`**

```python
"""Run one task against one backend: converse, execute tools in a throwaway repo copy, then score."""
from __future__ import annotations

import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .backends.base import Backend, BackendError
from .checks import evaluate
from .models import CallRecord, CheckResult, RawToolCall, Task, Transcript
from .tools import TOOL_NAMES, TOOL_SPECS, ToolExecutor, validate_arguments

SYSTEM_PROMPT = (
    "You are a coding assistant working inside a small Python repository. "
    "Use the provided tools to inspect and change files and to run commands. "
    "Paths are relative to the repository root. "
    "When you have finished, reply with a short plain-text answer."
)

# A reply with no tool calls that still looks like a tool call written out as text.
TEXT_CALL_RE = re.compile(r'<tool_call>|<function=|"name"\s*:\s*"(?:%s)"' % "|".join(TOOL_NAMES))


@dataclass
class RunRecord:
    task: Task
    status: str  # "ok" or "error" (the backend failed; this says nothing about the model)
    error: str
    transcript: Transcript
    check: CheckResult | None


def _execute(raw: RawToolCall, turn: int, index: int, executor: ToolExecutor) -> CallRecord:
    arguments, kind, message = validate_arguments(raw.name, raw.arguments)
    if kind:
        return CallRecord(index, turn, raw.name, raw.arguments, False, False, kind, f"error: {message}")
    ok, text = executor.execute(raw.name, arguments)
    return CallRecord(index, turn, raw.name, arguments, True, ok, "" if ok else "tool_error", text)


def converse(task: Task, backend: Backend, executor: ToolExecutor, tr: Transcript, max_calls: int, max_turns: int) -> None:
    """Fill `tr` by talking to the backend until it answers, hits a limit, or fails."""
    tr.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task.prompt},
    ]
    for turn in range(1, max_turns + 1):
        response = backend.chat(tr.messages, TOOL_SPECS)
        tr.turns = turn
        tr.eval_tokens += response.eval_tokens
        tr.eval_seconds += response.eval_seconds
        assistant: dict = {"role": "assistant", "content": response.content}
        if response.tool_calls:
            assistant["tool_calls"] = [
                {"function": {"name": c.name, "arguments": c.arguments if isinstance(c.arguments, dict) else {}}}
                for c in response.tool_calls
            ]
        tr.messages.append(assistant)
        if not response.tool_calls:
            tr.final_text = response.content
            tr.text_tool_call = bool(TEXT_CALL_RE.search(response.content))
            return
        for raw in response.tool_calls:
            if len(tr.calls) >= max_calls:
                tr.hit_limit = True
                return
            record = _execute(raw, turn, len(tr.calls) + 1, executor)
            tr.calls.append(record)
            tr.messages.append({"role": "tool", "tool_name": raw.name, "content": record.result})
    tr.hit_limit = True


def run_once(task: Task, backend: Backend, fixture_dir: Path, *, max_calls: int = 12, max_turns: int = 10) -> RunRecord:
    started = time.monotonic()
    tr = Transcript()
    with tempfile.TemporaryDirectory(prefix="tcb-") as tmp:
        root = Path(tmp) / "repo"
        shutil.copytree(fixture_dir, root, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
        executor = ToolExecutor(root)
        try:
            converse(task, backend, executor, tr, max_calls, max_turns)
        except BackendError as exc:
            tr.wall_seconds = time.monotonic() - started
            return RunRecord(task, "error", str(exc), tr, None)
        check = evaluate(task, tr, root, fixture_dir, default_max_calls=max_calls)
    tr.wall_seconds = time.monotonic() - started
    return RunRecord(task, "ok", "", tr, check)
```

Now the 20 tasks. Read two or three of them (start with `read-01` and `chain-04`) before you
paste all of them.

<!-- file: tasks/read-01.yaml -->
**`tasks/read-01.yaml`**

```yaml
id: read-01
group: read
title: Read one config value
tools_named: true
prompt: |
  Use the read_file tool to read config/settings.json and tell me the value of loan_days.
expect:
  calls:
    - tool: read_file
      args: {path: config/settings.json}
  answer_regex: ['\b14\b']
reference:
  - calls:
      - {tool: read_file, args: {path: config/settings.json}}
  - final: loan_days is 14.
```

<!-- file: tasks/read-02.yaml -->
**`tasks/read-02.yaml`**

```yaml
id: read-02
group: read
title: List a directory
tools_named: true
prompt: |
  Use the list_dir tool to list the folder src/shelf and tell me which Python files it contains.
expect:
  calls:
    - tool: list_dir
      args: {path: src/shelf}
  answer_contains: [catalog.py, loans.py, fees.py, utils.py]
reference:
  - calls:
      - {tool: list_dir, args: {path: src/shelf}}
  - final: "src/shelf contains __init__.py, catalog.py, fees.py, loans.py, models.py, settings.py and utils.py."
```

<!-- file: tasks/read-03.yaml -->
**`tasks/read-03.yaml`**

```yaml
id: read-03
group: read
title: Find a definition with grep
tools_named: true
prompt: |
  Use the grep tool to find where the function late_fee is defined. Tell me the file and the line number.
expect:
  calls:
    - tool: grep
      args: {pattern: {contains: late_fee}}
  answer_contains: [fees.py]
  answer_regex: ['\b12\b']
reference:
  - calls:
      - {tool: grep, args: {pattern: "def late_fee"}}
  - final: late_fee is defined in src/shelf/fees.py at line 12.
```

<!-- file: tasks/read-04.yaml -->
**`tasks/read-04.yaml`**

```yaml
id: read-04
group: read
title: Read a CSV and answer a question
tools_named: true
prompt: |
  Use the read_file tool on data/books.csv. Which book has the most copies?
expect:
  calls:
    - tool: read_file
      args: {path: data/books.csv}
  answer_contains: [Hobbit]
reference:
  - calls:
      - {tool: read_file, args: {path: data/books.csv}}
  - final: The Hobbit has the most copies (3).
```

<!-- file: tasks/read-05.yaml -->
**`tasks/read-05.yaml`**

```yaml
id: read-05
group: read
title: Read members and count them
tools_named: true
prompt: |
  Use the read_file tool on data/members.csv. How many members are there, and who joined most recently?
expect:
  calls:
    - tool: read_file
      args: {path: data/members.csv}
  answer_contains: [Chen Wei]
  answer_regex: ['\b3\b|three']
reference:
  - calls:
      - {tool: read_file, args: {path: data/members.csv}}
  - final: There are 3 members. Chen Wei joined most recently (2023-01-20).
```

<!-- file: tasks/edit-01.yaml -->
**`tasks/edit-01.yaml`**

```yaml
id: edit-01
group: edit
title: Change one config value
tools_named: true
prompt: |
  Use the edit_file tool to change loan_days in config/settings.json from 14 to 21.
expect:
  calls:
    - tool: edit_file
      args: {path: config/settings.json}
  final_files:
    config/settings.json:
      contains: ['"loan_days": 21']
      not_contains: ['"loan_days": 14']
  command:
    - argv: [python, -c, "import json; json.load(open('config/settings.json'))"]
reference:
  - calls:
      - {tool: read_file, args: {path: config/settings.json}}
  - calls:
      - tool: edit_file
        args: {path: config/settings.json, old_text: '"loan_days": 14', new_text: '"loan_days": 21'}
  - final: Changed loan_days to 21.
```

<!-- file: tasks/edit-02.yaml -->
**`tasks/edit-02.yaml`**

```yaml
id: edit-02
group: edit
title: Bump the package version
tools_named: true
prompt: |
  Use the edit_file tool to change the version in src/shelf/__init__.py from 0.3.0 to 0.4.0.
expect:
  calls:
    - tool: edit_file
      args: {path: src/shelf/__init__.py}
  final_files:
    src/shelf/__init__.py:
      contains: ['__version__ = "0.4.0"']
      not_contains: ['0.3.0']
reference:
  - calls:
      - tool: edit_file
        args: {path: src/shelf/__init__.py, old_text: '__version__ = "0.3.0"', new_text: '__version__ = "0.4.0"'}
  - final: Version is now 0.4.0.
```

<!-- file: tasks/edit-03.yaml -->
**`tasks/edit-03.yaml`**

```yaml
id: edit-03
group: edit
title: Change a value with a unified diff
tools_named: true
prompt: |
  Use the apply_patch tool (not edit_file) to change late_fee_per_day in config/settings.json from 0.25 to 0.5.
  Read the file first if you need its exact text.
expect:
  calls:
    - tool: apply_patch
  forbidden_tools: [edit_file]
  final_files:
    config/settings.json:
      contains: ['"late_fee_per_day": 0.5']
      not_contains: ['0.25']
  command:
    - argv: [python, -c, "import json; json.load(open('config/settings.json'))"]
reference:
  - calls:
      - {tool: read_file, args: {path: config/settings.json}}
  - calls:
      - tool: apply_patch
        args:
          patch: |
            --- a/config/settings.json
            +++ b/config/settings.json
            @@ -3,3 +3,3 @@
               "max_loans_per_member": 3,
            -  "late_fee_per_day": 0.25,
            +  "late_fee_per_day": 0.5,
               "max_late_fee": 10.0,
  - final: Changed late_fee_per_day to 0.5.
```

<!-- file: tasks/edit-04.yaml -->
**`tasks/edit-04.yaml`**

```yaml
id: edit-04
group: edit
title: Add a function to a file
tools_named: true
prompt: |
  Use the edit_file tool to add a function shout(text) at the end of src/shelf/utils.py.
  It must return the text in upper case followed by an exclamation mark, so shout('hi') returns 'HI!'.
expect:
  calls:
    - tool: edit_file
      args: {path: src/shelf/utils.py}
  command:
    - argv: [python, -c, "import sys; sys.path.insert(0, 'src'); from shelf.utils import shout; assert shout('hi') == 'HI!'"]
reference:
  - calls:
      - {tool: read_file, args: {path: src/shelf/utils.py}}
  - calls:
      - tool: edit_file
        args:
          path: src/shelf/utils.py
          old_text: "    return len(isbn) == 13 and isbn.isdigit()"
          new_text: "    return len(isbn) == 13 and isbn.isdigit()\n\n\ndef shout(text: str) -> str:\n    return text.upper() + \"!\""
  - final: Added shout() to src/shelf/utils.py.
```

<!-- file: tasks/edit-05.yaml -->
**`tasks/edit-05.yaml`**

```yaml
id: edit-05
group: edit
title: Fix the late-fee cap (no tool named)
tools_named: false
prompt: |
  The function late_fee in src/shelf/fees.py is meant to never return more than its cap argument,
  but it ignores the cap. Fix it.
expect:
  calls:
    - tool: [edit_file, apply_patch]
      args: {path: src/shelf/fees.py}
  command:
    - argv: [python, -m, pytest, -q, tests/test_fees.py]
reference:
  - calls:
      - {tool: read_file, args: {path: src/shelf/fees.py}}
  - calls:
      - tool: edit_file
        args:
          path: src/shelf/fees.py
          old_text: "    return round(days * per_day, 2)"
          new_text: "    fee = round(days * per_day, 2)\n    if cap is not None:\n        fee = min(fee, cap)\n    return fee"
  - final: late_fee now applies the cap.
```

<!-- file: tasks/run-01.yaml -->
**`tasks/run-01.yaml`**

```yaml
id: run-01
group: run
title: Run the tests and count failures
tools_named: true
prompt: |
  Use the run_command tool to run `python -m pytest -q` and tell me how many tests fail.
expect:
  calls:
    - tool: run_command
      args: {command: {contains: pytest}}
  answer_regex: ['\b2\b|two']
reference:
  - calls:
      - {tool: run_command, args: {command: "python -m pytest -q"}}
  - final: 2 tests fail.
```

<!-- file: tasks/run-02.yaml -->
**`tasks/run-02.yaml`**

```yaml
id: run-02
group: run
title: Run a script and report a number
tools_named: true
prompt: |
  Use the run_command tool to run `python scripts/report.py` and tell me how many copies the library owns in total.
expect:
  calls:
    - tool: run_command
      args: {command: {contains: report.py}}
  answer_regex: ['\b11\b']
reference:
  - calls:
      - {tool: run_command, args: {command: "python scripts/report.py"}}
  - final: The library owns 11 copies in total.
```

<!-- file: tasks/run-03.yaml -->
**`tasks/run-03.yaml`**

```yaml
id: run-03
group: run
title: Run a shell-style listing
tools_named: true
prompt: |
  Use the run_command tool to run `ls data` and tell me the names of the files in that folder.
expect:
  calls:
    - tool: run_command
      args: {command: {contains: ls}}
  answer_contains: [books.csv, members.csv]
reference:
  - calls:
      - {tool: run_command, args: {command: "ls data"}}
  - final: The data folder has books.csv and members.csv.
```

<!-- file: tasks/chain-01.yaml -->
**`tasks/chain-01.yaml`**

```yaml
id: chain-01
group: chain
title: Fix the title search and confirm with tests
prompt: |
  The test test_search_is_case_insensitive fails. Find the bug in the code and fix it,
  then run the tests in tests/test_catalog.py to confirm that they pass.
expect:
  calls:
    - tool: [edit_file, apply_patch]
      args: {path: src/shelf/catalog.py}
    - tool: run_command
      args: {command: {contains: pytest}}
  ordered: true
  command:
    - argv: [python, -m, pytest, -q, tests/test_catalog.py]
reference:
  - calls:
      - {tool: read_file, args: {path: src/shelf/catalog.py}}
  - calls:
      - tool: edit_file
        args:
          path: src/shelf/catalog.py
          old_text: "    return [b for b in books if query in b.title]"
          new_text: "    needle = query.lower()\n    return [b for b in books if needle in b.title.lower()]"
  - calls:
      - {tool: run_command, args: {command: "python -m pytest -q tests/test_catalog.py"}}
  - final: Fixed search_by_title to ignore case; the catalog tests pass.
```

<!-- file: tasks/chain-02.yaml -->
**`tasks/chain-02.yaml`**

```yaml
id: chain-02
group: chain
title: Read the README, then run what it says
prompt: |
  Read README.md to find the command that prints the library summary report, run that command,
  and tell me how many members the report shows.
expect:
  calls:
    - tool: read_file
      args: {path: README.md}
    - tool: run_command
      args: {command: {contains: report.py}}
  ordered: true
  answer_regex: ['\b3\b|three']
reference:
  - calls:
      - {tool: read_file, args: {path: README.md}}
  - calls:
      - {tool: run_command, args: {command: "python scripts/report.py"}}
  - final: The report shows 3 members.
```

<!-- file: tasks/chain-03.yaml -->
**`tasks/chain-03.yaml`**

```yaml
id: chain-03
group: chain
title: Locate a class, then read it
prompt: |
  Find which file defines the class LoanError. Then read that file and tell me the name of the
  Library method that takes a book back from a member.
expect:
  calls:
    - tool: [grep, list_dir]
    - tool: read_file
      args: {path: src/shelf/loans.py}
  ordered: true
  answer_contains: [return_book]
reference:
  - calls:
      - {tool: grep, args: {pattern: "class LoanError"}}
  - calls:
      - {tool: read_file, args: {path: src/shelf/loans.py}}
  - final: LoanError is in src/shelf/loans.py. The method is return_book.
```

<!-- file: tasks/chain-04.yaml -->
**`tasks/chain-04.yaml`**

```yaml
id: chain-04
group: chain
title: Fix both failing tests
prompt: |
  Two tests in this repository fail. Fix the code so that the whole test suite passes,
  and run the suite at the end to confirm.
expect:
  calls:
    - tool: [edit_file, apply_patch]
      args: {path: src/shelf/catalog.py}
    - tool: [edit_file, apply_patch]
      args: {path: src/shelf/fees.py}
    - tool: run_command
      args: {command: {contains: pytest}}
  min_calls: 3
  max_calls: 10
  command:
    - argv: [python, -m, pytest, -q]
reference:
  - calls:
      - {tool: run_command, args: {command: "python -m pytest -q"}}
  - calls:
      - {tool: read_file, args: {path: src/shelf/catalog.py}}
      - {tool: read_file, args: {path: src/shelf/fees.py}}
  - calls:
      - tool: edit_file
        args:
          path: src/shelf/catalog.py
          old_text: "    return [b for b in books if query in b.title]"
          new_text: "    needle = query.lower()\n    return [b for b in books if needle in b.title.lower()]"
      - tool: edit_file
        args:
          path: src/shelf/fees.py
          old_text: "    return round(days * per_day, 2)"
          new_text: "    fee = round(days * per_day, 2)\n    if cap is not None:\n        fee = min(fee, cap)\n    return fee"
  - calls:
      - {tool: run_command, args: {command: "python -m pytest -q"}}
  - final: Fixed the title search and the late-fee cap; all tests pass.
```

<!-- file: tasks/failure-01.yaml -->
**`tasks/failure-01.yaml`**

```yaml
id: failure-01
group: failure
title: Answer directly without tools
prompt: |
  What is 17 plus 25? Answer with just the number. You do not need any tool for this.
expect:
  no_tool_calls: true
  answer_contains: ["42"]
reference:
  - final: "42"
```

<!-- file: tasks/failure-02.yaml -->
**`tasks/failure-02.yaml`**

```yaml
id: failure-02
group: failure
title: Two independent reads in one step
prompt: |
  I need two things: the currency in config/settings.json and the number of members in data/members.csv.
  The two reads do not depend on each other, so request both in the same step.
expect:
  calls:
    - tool: read_file
      args: {path: config/settings.json}
    - tool: read_file
      args: {path: data/members.csv}
  parallel: true
  answer_contains: [USD]
  answer_regex: ['\b3\b|three']
reference:
  - calls:
      - {tool: read_file, args: {path: config/settings.json}}
      - {tool: read_file, args: {path: data/members.csv}}
  - final: The currency is USD and there are 3 members.
```

<!-- file: tasks/failure-03.yaml -->
**`tasks/failure-03.yaml`**

```yaml
id: failure-03
group: failure
title: Recover from a missing file
prompt: |
  Read config/settings.yaml and tell me which currency the library uses.
  If that file does not exist, find the right file yourself.
expect:
  calls:
    - tool: read_file
      args: {path: config/settings.json}
  min_calls: 2
  answer_contains: [USD]
reference:
  - calls:
      - {tool: read_file, args: {path: config/settings.yaml}}
  - calls:
      - {tool: list_dir, args: {path: config}}
  - calls:
      - {tool: read_file, args: {path: config/settings.json}}
  - final: The currency is USD (from config/settings.json).
```

The tests. `test_tasks.py` replays all 20 reference solutions. `test_checks.py` makes the fake
model fail in each way and checks that the scorer names the right failure.

<!-- file: tests/test_tasks.py -->
**`tests/test_tasks.py`**

```python
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
```

<!-- file: tests/test_checks.py -->
**`tests/test_checks.py`**

```python
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
```

### Run

This takes about half a minute because some checks run the sample project's tests.

```text
$ python -m pytest tests/test_tasks.py tests/test_checks.py
.....................                                                    [100%]
21 passed in N.NNs
```

### Checkpoint

```bash
git add -A && git commit -m "Day 4: tasks, scoring, runner"
```

---

## Day 5: Storage and reports

**Goal:** results are saved to a database and turned into a readable report.

### Why

- `store.py` uses **SQLite**, a database in one file with no server to install. Three tables: `sessions` (one benchmark run, with all its settings), `runs` (one task attempt) and `calls` (each tool call). A `UNIQUE (session_id, model, task_id, repeat)` rule means the same run can never be stored twice, which makes **resume** safe. It also writes one **JSONL** transcript per run (one JSON object per line), so you can read exactly what the model said.
- `report.py` turns the numbers into a Markdown table and a simple HTML page. It reports the pass rate per group, why runs failed, the median speed, and **all settings**, because two reports are only comparable when their settings match.

### Create

<!-- file: src/toolcallbench/store.py -->
**`src/toolcallbench/store.py`**

```python
"""SQLite storage for sessions, runs and calls, plus one JSONL transcript log per run."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runner import RunRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    settings_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL REFERENCES sessions(session_id),
    model        TEXT NOT NULL,
    quant        TEXT NOT NULL DEFAULT '',
    backend      TEXT NOT NULL,
    task_id      TEXT NOT NULL,
    grp          TEXT NOT NULL,
    repeat       INTEGER NOT NULL,
    status       TEXT NOT NULL,
    passed       INTEGER NOT NULL,
    parse_ok     INTEGER NOT NULL,
    tool_ok      INTEGER NOT NULL,
    args_ok      INTEGER NOT NULL,
    outcome_ok   INTEGER NOT NULL,
    failure_type TEXT NOT NULL,
    calls_made   INTEGER NOT NULL,
    turns        INTEGER NOT NULL,
    efficiency   REAL,
    eval_tokens  INTEGER NOT NULL,
    eval_seconds REAL NOT NULL,
    wall_seconds REAL NOT NULL,
    tok_per_s    REAL,
    error        TEXT NOT NULL DEFAULT '',
    log_path     TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    UNIQUE (session_id, model, task_id, repeat)
);
CREATE TABLE IF NOT EXISTS calls (
    run_id         INTEGER NOT NULL REFERENCES runs(id),
    idx            INTEGER NOT NULL,
    turn           INTEGER NOT NULL,
    tool           TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    valid          INTEGER NOT NULL,
    ok             INTEGER NOT NULL,
    error_kind     TEXT NOT NULL,
    PRIMARY KEY (run_id, idx)
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def model_slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # ---------------------------------------------------------------- sessions

    def session_exists(self, session_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return row is not None

    def create_session(self, session_id: str, settings: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO sessions (session_id, started_at, settings_json) VALUES (?, ?, ?)",
            (session_id, now_iso(), json.dumps(settings, sort_keys=True)),
        )
        self.conn.commit()

    def merge_settings(self, session_id: str, patch: dict[str, Any]) -> None:
        settings = self.session(session_id)["settings"]
        settings.update(patch)
        self.conn.execute(
            "UPDATE sessions SET settings_json = ? WHERE session_id = ?", (json.dumps(settings, sort_keys=True), session_id)
        )
        self.conn.commit()

    def finish_session(self, session_id: str) -> None:
        self.conn.execute("UPDATE sessions SET finished_at = ? WHERE session_id = ?", (now_iso(), session_id))
        self.conn.commit()

    def session(self, session_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            raise KeyError(f"no session '{session_id}'")
        return {
            "session_id": row["session_id"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "settings": json.loads(row["settings_json"]),
        }

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT s.session_id, s.started_at, s.finished_at, COUNT(r.id) AS runs "
            "FROM sessions s LEFT JOIN runs r ON r.session_id = s.session_id "
            "GROUP BY s.session_id ORDER BY s.started_at DESC, s.session_id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def latest_session_id(self) -> str | None:
        sessions = self.list_sessions()
        return sessions[0]["session_id"] if sessions else None

    # -------------------------------------------------------------------- runs

    def has_run(self, session_id: str, model: str, task_id: str, repeat: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM runs WHERE session_id = ? AND model = ? AND task_id = ? AND repeat = ?",
            (session_id, model, task_id, repeat),
        ).fetchone()
        return row is not None

    def add_run(
        self, session_id: str, *, model: str, quant: str, backend: str, repeat: int, record: RunRecord, log_path: str
    ) -> int:
        tr, check, task = record.transcript, record.check, record.task
        tok_per_s = tr.eval_tokens / tr.eval_seconds if tr.eval_seconds > 0 else None
        cursor = self.conn.execute(
            "INSERT INTO runs (session_id, model, quant, backend, task_id, grp, repeat, status, passed, parse_ok, "
            "tool_ok, args_ok, outcome_ok, failure_type, calls_made, turns, efficiency, eval_tokens, eval_seconds, "
            "wall_seconds, tok_per_s, error, log_path, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                model,
                quant,
                backend,
                task.id,
                task.group,
                repeat,
                record.status,
                int(bool(check and check.passed)),
                int(bool(check and check.parse_ok)),
                int(bool(check and check.tool_ok)),
                int(bool(check and check.args_ok)),
                int(bool(check and check.outcome_ok)),
                check.failure_type if check else "backend_error",
                len(tr.calls),
                tr.turns,
                check.efficiency if check else None,
                tr.eval_tokens,
                tr.eval_seconds,
                tr.wall_seconds,
                tok_per_s,
                record.error,
                log_path,
                now_iso(),
            ),
        )
        run_id = cursor.lastrowid
        for call in tr.calls:
            self.conn.execute(
                "INSERT INTO calls (run_id, idx, turn, tool, arguments_json, valid, ok, error_kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, call.index, call.turn, call.tool, json.dumps(call.arguments), int(call.valid), int(call.ok), call.error_kind),
            )
        self.conn.commit()
        return int(run_id)

    def runs(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM runs WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
        return [dict(r) for r in rows]


def write_log(results_dir: Path, session_id: str, model: str, repeat: int, record: RunRecord) -> str:
    """Write the full transcript as JSONL and return its path relative to results_dir."""
    rel = Path("logs") / session_id / model_slug(model) / f"{record.task.id}_{repeat}.jsonl"
    path = Path(results_dir) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    tr, check = record.transcript, record.check
    summary = {
        "type": "summary",
        "task": record.task.id,
        "status": record.status,
        "error": record.error,
        "passed": bool(check and check.passed),
        "failure_type": check.failure_type if check else "backend_error",
        "details": check.details if check else [],
        "final_text": tr.final_text,
        "calls": [
            {
                "index": c.index,
                "turn": c.turn,
                "tool": c.tool,
                "arguments": c.arguments,
                "valid": c.valid,
                "ok": c.ok,
                "error_kind": c.error_kind,
            }
            for c in tr.calls
        ],
    }
    with path.open("w", encoding="utf-8") as handle:
        for message in tr.messages:
            handle.write(json.dumps({"type": "message", **message}) + "\n")
        handle.write(json.dumps(summary) + "\n")
    return rel.as_posix()
```

<!-- file: src/toolcallbench/report.py -->
**`src/toolcallbench/report.py`**

```python
"""Turn a session's runs into a Markdown report and a self-contained HTML page."""
from __future__ import annotations

import html
import statistics
from collections import Counter, defaultdict
from typing import Any

from .checks import FAILURE_TYPES
from .models import GROUPS
from .store import Store

SETTING_LABELS = [
    ("backend", "Backend"),
    ("backend_version", "Backend version"),
    ("host", "Host"),
    ("num_ctx", "Context length (num_ctx)"),
    ("temperature", "Temperature"),
    ("seed", "Base seed (+1 per repeat)"),
    ("repeats", "Repeats per task"),
    ("max_calls", "Call limit per run"),
    ("max_turns", "Turn limit per run"),
    ("declared_kv_cache_type", "KV cache type (declared)"),
    ("declared_flash_attention", "Flash attention (declared)"),
    ("system_prompt_sha", "System prompt hash"),
    ("toolcallbench_version", "ToolCallBench version"),
    ("platform", "Platform"),
    ("python", "Python"),
]


def _pct(passed: int, total: int) -> str:
    return "-" if total == 0 else f"{100 * passed / total:.1f}%"


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Group runs by model and compute the numbers the report shows."""
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        by_model[run["model"]].append(run)
    models = []
    for name, rows in by_model.items():
        scored = [r for r in rows if r["status"] == "ok"]
        passed = sum(r["passed"] for r in scored)
        groups = {}
        for group in GROUPS:
            in_group = [r for r in scored if r["grp"] == group]
            groups[group] = (sum(r["passed"] for r in in_group), len(in_group))
        failures = Counter(r["failure_type"] for r in scored if not r["passed"])
        tasks: dict[str, tuple[int, int]] = {}
        for task_id in sorted({r["task_id"] for r in scored}):
            of_task = [r for r in scored if r["task_id"] == task_id]
            tasks[task_id] = (sum(r["passed"] for r in of_task), len(of_task))
        models.append(
            {
                "model": name,
                "quant": next((r["quant"] for r in rows if r["quant"]), ""),
                "runs": len(rows),
                "errors": len(rows) - len(scored),
                "passed": passed,
                "scored": len(scored),
                "groups": groups,
                "failures": failures,
                "tasks": tasks,
                "tok_per_s": _median([r["tok_per_s"] for r in scored if r["tok_per_s"]]),
                "seconds": _median([r["wall_seconds"] for r in scored]),
                "efficiency": _median([r["efficiency"] for r in scored if r["efficiency"] is not None]),
            }
        )
    return {"models": models}


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _fmt(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def render_markdown(store: Store, session_id: str, task_titles: dict[str, tuple[str, str]] | None = None) -> str:
    session = store.session(session_id)
    settings = session["settings"]
    runs = store.runs(session_id)
    data = aggregate(runs)
    models = data["models"]
    task_titles = task_titles or {}

    out = [f"# ToolCallBench report: {session_id}", ""]
    tasks_count = len({r["task_id"] for r in runs})
    out.append(
        f"Started {session['started_at']}. {len(runs)} runs: {len(models)} model(s), {tasks_count} task(s), "
        f"{settings.get('repeats', '?')} repeat(s) each."
    )
    out += ["", "## Settings", ""]
    rows = []
    for key, label in SETTING_LABELS:
        if key in settings:
            value = settings[key]
            if isinstance(value, dict):
                value = ", ".join(f"{k}: {v}" for k, v in sorted(value.items()))
            rows.append([label, str(value)])
    out += _table(["Setting", "Value"], rows)

    out += ["", "## Summary", "", "Pass rate counts only runs where the backend answered. Errors are runs where it did not.", ""]
    header = ["Model", "Quant", "Runs", "Errors", "Pass"] + [g.title() for g in GROUPS] + ["tok/s", "s/task", "Calls vs ref"]
    rows = []
    for m in sorted(models, key=lambda x: -(x["passed"] / x["scored"] if x["scored"] else -1)):
        rows.append(
            [m["model"], m["quant"] or "-", str(m["runs"]), str(m["errors"]), _pct(m["passed"], m["scored"])]
            + [_pct(*m["groups"][g]) for g in GROUPS]
            + [_fmt(m["tok_per_s"]), _fmt(m["seconds"]), _fmt(m["efficiency"], 2)]
        )
    out += _table(header, rows)

    seen_types = [t for t in FAILURE_TYPES if any(t in m["failures"] for m in models)]
    out += ["", "## Failure types", ""]
    if seen_types:
        out += _table(["Model"] + seen_types, [[m["model"]] + [str(m["failures"].get(t, 0)) for t in seen_types] for m in models])
    else:
        out.append("No failures.")

    out += ["", "## Per-task results", "", "Each cell is passed runs / scored runs.", ""]
    task_ids = sorted({r["task_id"] for r in runs})
    header = ["Task", "Group", "Title"] + [m["model"] for m in models]
    rows = []
    for task_id in task_ids:
        group, title = task_titles.get(task_id, (task_id.split("-")[0], ""))
        row = [task_id, group, title]
        for m in models:
            passed, total = m["tasks"].get(task_id, (0, 0))
            row.append(f"{passed}/{total}" if total else "-")
        rows.append(row)
    out += _table(header, rows)

    out += [
        "",
        "## How to read this report",
        "",
        "- A run passes only when every tool call is valid, the right tools were used, and the repository ends in the expected state.",
        "- Failure types explain why a run failed; see docs/TECH_SPEC.md for the full list and their priority.",
        "- tok/s and s/task are medians. Compare models only when the settings above are the same.",
        "- Calls vs ref is the number of tool calls divided by the reference solution's number; 1.00 is ideal.",
        "",
    ]
    return "\n".join(out)


def markdown_to_html(markdown: str, title: str) -> str:
    """A tiny converter for the subset of Markdown this report uses: headings, tables, bullets, paragraphs."""
    body: list[str] = []
    lines = markdown.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            rows = [[c.strip() for c in row.strip().strip("|").split("|")] for row in block]
            head, rest = rows[0], [r for r in rows[2:]]
            table = ["<table>", "<thead><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in head) + "</tr></thead>", "<tbody>"]
            table += ["<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rest]
            table += ["</tbody>", "</table>"]
            body.append("\n".join(table))
            continue
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{html.escape(lines[i][2:])}</li>")
                i += 1
            body.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif line.strip():
            body.append(f"<p>{html.escape(line)}</p>")
        i += 1
    style = (
        "body{font-family:-apple-system,system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}"
        "table{border-collapse:collapse;margin:1rem 0;font-size:.9rem}"
        "th,td{border:1px solid #ccc;padding:.35rem .6rem;text-align:left}"
        "th{background:#f3f3f3}tr:nth-child(even) td{background:#fafafa}"
    )
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{style}</style></head><body>\n" + "\n".join(body) + "\n</body></html>\n"
    )
```

<!-- file: tests/test_store_report.py -->
**`tests/test_store_report.py`**

```python
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
```

### Run

```text
$ python -m pytest tests/test_store_report.py
.....                                                                    [100%]
5 passed in N.NNs
```

### Checkpoint

```bash
git add -A && git commit -m "Day 5: storage and reports"
```

---

## Day 6: The command line and mock servers

**Goal:** `toolcallbench` works end to end with a fake model, and the real HTTP backends are tested against pretend servers.

### Why

`cli.py` connects everything. Its commands:

| Command | What it does |
| --- | --- |
| `list-tasks` | Show the tasks |
| `validate-tasks` | Replay every reference solution through the real tools and scorer |
| `doctor` | Check Python, tasks, sample project, the server and the models; `--probe` runs one real task |
| `run` | Run the benchmark and write the report |
| `report` | Rebuild a report from saved results |
| `sessions` | List saved sessions |

Two ideas worth noticing in `cmd_run`:

- **Resume**: before each run it asks the database whether that run already exists. Press Ctrl+C any time; run the same command again with `--resume`.
- **Stop after three server errors in a row**: if Ollama crashes, the program stops that model instead of writing 60 fake "failures".

`tests/mock_servers.py` starts small HTTP servers on your own computer that *pretend* to be
Ollama or an OpenAI-style server. They answer by using the fake model. This lets us test the real
HTTP code (URLs, JSON shapes, headers) without any model.

### Create

<!-- file: src/toolcallbench/cli.py -->
**`src/toolcallbench/cli.py`**

```python
"""Command-line interface: list-tasks, validate-tasks, doctor, run, report, sessions."""
from __future__ import annotations

import argparse
import hashlib
import platform
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .backends import BACKEND_KINDS, PROFILES, BackendError, OllamaBackend, OpenAICompatBackend, ScriptedBackend, make_backend
from .config import ConfigError, ModelSpec, RunConfig, find_project_root, load_config
from .models import Task
from .report import markdown_to_html, render_markdown
from .runner import SYSTEM_PROMPT, run_once
from .store import Store, new_session_id, write_log
from .tasks import TaskError, load_tasks, select_tasks
from .tools import run_trusted

DEFAULT_HOSTS = {"ollama": "http://localhost:11434", "openai-compat": "http://localhost:8080", "scripted": ""}


# ----------------------------------------------------------------------- helpers


def _split(value: str | None) -> list[str] | None:
    return [part.strip() for part in value.split(",") if part.strip()] if value else None


def _paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    root = Path(args.root).resolve() if args.root else find_project_root()
    tasks_dir = Path(args.tasks_dir) if args.tasks_dir else root / "tasks"
    fixture = Path(args.fixture) if args.fixture else root / "fixtures" / "repo"
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
    return cfg


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
        print("| Task | Group | Title | Tool named in prompt | Reference calls |")
        print("| --- | --- | --- | --- | --- |")
        for t in tasks:
            print(f"| {t.id} | {t.group} | {t.title} | {'yes' if t.tools_named else 'no'} | {t.baseline_calls} |")
    else:
        for t in tasks:
            print(f"{t.id:<12} {t.group:<8} calls={t.baseline_calls}  {t.title}")
        print(f"\n{len(tasks)} tasks")
    return 0


def cmd_validate_tasks(args: argparse.Namespace) -> int:
    _, tasks_dir, fixture, _ = _paths(args)
    tasks = select_tasks(load_tasks(tasks_dir), _split(args.tasks), _split(args.groups))
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
    try:
        if kind == "ollama":
            first = OllamaBackend(args.model[0] if args.model else "", host=host, timeout=10)
            version = first.version()
            installed = first.list_models()
            all_ok &= _line(True, "Ollama server", f"version {version} at {host}; {len(installed)} model(s) installed")
            for name in args.model or []:
                backend = OllamaBackend(name, host=host, timeout=30)
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
            OpenAICompatBackend("probe", base_url=host, timeout=10).check()
            all_ok &= _line(True, "OpenAI-compatible server", f"reachable at {host}")
            if args.probe:
                for name in args.model or []:
                    probe_backends.append(OpenAICompatBackend(name, base_url=host, timeout=120))
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
                record = run_once(task, backend, fixture, max_calls=cfg.max_calls, max_turns=cfg.max_turns)
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


# ------------------------------------------------------------------------ parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toolcallbench", description="Benchmark tool-calling reliability of local LLMs.")
    parser.add_argument("--version", action="version", version=f"toolcallbench {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="project folder holding tasks/ and fixtures/ (default: found from the current folder)")
    common.add_argument("--tasks-dir", help="folder of task YAML files")
    common.add_argument("--fixture", help="fixture repository to copy for every run")
    common.add_argument("--results-dir", help="where results.sqlite, logs and reports go")

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
    p.add_argument("--probe", action="store_true", help="run one real task against each model")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("run", parents=[common], help="run the benchmark")
    p.add_argument("--config", help="YAML config file (see configs/)")
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
```

<!-- file: tests/mock_servers.py -->
**`tests/mock_servers.py`**

```python
"""Tiny HTTP servers that imitate Ollama and an OpenAI-compatible server, backed by the scripted backend."""
from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

from toolcallbench.backends.scripted import ScriptedBackend


def _make_handler(kind: str, tasks, profile: str, installed: list[str]):
    brain = ScriptedBackend(tasks, profile)

    class Handler(BaseHTTPRequestHandler):
        requests: list[dict] = []

        def log_message(self, *args):  # keep test output quiet
            pass

        def _send(self, payload, status=200):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if kind == "ollama" and self.path == "/api/version":
                self._send({"version": "0.99.0"})
            elif kind == "ollama" and self.path == "/api/tags":
                self._send({"models": [{"name": n} for n in installed]})
            elif kind == "openai" and self.path == "/v1/models":
                self._send({"data": [{"id": "mock"}]})
            else:
                self._send({"error": "not found"}, 404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            Handler.requests.append({"path": self.path, "payload": payload})
            if kind == "ollama" and self.path == "/api/show":
                self._send({"details": {"quantization_level": "Q4_K_M", "parameter_size": "8.2B", "family": "qwen3"},
                            "capabilities": ["completion", "tools"]})
            elif kind == "ollama" and self.path == "/api/chat":
                reply = brain.chat(payload["messages"], payload["tools"])
                message = {"role": "assistant", "content": reply.content}
                if reply.tool_calls:
                    message["tool_calls"] = [{"function": {"name": c.name, "arguments": c.arguments}} for c in reply.tool_calls]
                self._send({"message": message, "eval_count": 20, "eval_duration": 500_000_000, "prompt_eval_count": 100})
            elif kind == "openai" and self.path == "/v1/chat/completions":
                reply = brain.chat(payload["messages"], payload["tools"])
                message = {"role": "assistant", "content": reply.content}
                if reply.tool_calls:
                    message["tool_calls"] = [
                        {"id": f"c{i}", "type": "function",
                         "function": {"name": c.name, "arguments": c.arguments if isinstance(c.arguments, str) else json.dumps(c.arguments)}}
                        for i, c in enumerate(reply.tool_calls)
                    ]
                self._send({"choices": [{"message": message}], "usage": {"completion_tokens": 20, "prompt_tokens": 100}})
            else:
                self._send({"error": "not found"}, 404)

    return Handler


@contextmanager
def mock_server(kind: str, tasks, profile: str = "oracle", installed: list[str] | None = None):
    handler = _make_handler(kind, tasks, profile, installed or ["mock-model:latest"])
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", handler
    finally:
        server.shutdown()
        server.server_close()
```

<!-- file: tests/test_http_backends.py -->
**`tests/test_http_backends.py`**

```python
"""Run the real HTTP backends against mock servers (no model needed)."""
import pytest

from mock_servers import mock_server
from toolcallbench.backends import BackendError, OllamaBackend, OpenAICompatBackend
from toolcallbench.runner import run_once


def test_ollama_end_to_end_all_tasks(tasks, fixture_dir):
    with mock_server("ollama", tasks) as (url, handler):
        backend = OllamaBackend("mock-model", host=url, options={"num_ctx": 4096, "seed": 1, "temperature": 0.0})
        backend.check()
        info = backend.describe()
        assert info["backend_version"] == "0.99.0" and info["quant"] == "Q4_K_M"
        for task in tasks:
            record = run_once(task, backend, fixture_dir)
            assert record.status == "ok" and record.check.passed, (task.id, record.check.details)
        chats = [r for r in handler.requests if r["path"] == "/api/chat"]
        assert chats and chats[0]["payload"]["stream"] is False
        assert chats[0]["payload"]["options"]["num_ctx"] == 4096
        assert len(chats[0]["payload"]["tools"]) == 6
        assert any(m.get("role") == "tool" and m.get("tool_name") for r in chats for m in r["payload"]["messages"])


def test_ollama_missing_model_is_reported(tasks):
    with mock_server("ollama", tasks, installed=["other:latest"]) as (url, _):
        with pytest.raises(BackendError, match="ollama pull"):
            OllamaBackend("mock-model", host=url).check()


def test_ollama_unreachable():
    with pytest.raises(BackendError, match="cannot reach"):
        OllamaBackend("m", host="http://127.0.0.1:9", timeout=2).check()


def test_ollama_think_flag_is_sent(tasks, fixture_dir):
    with mock_server("ollama", tasks) as (url, handler):
        backend = OllamaBackend("mock-model", host=url, think=False)
        run_once(next(t for t in tasks if t.id == "failure-01"), backend, fixture_dir)
        assert handler.requests[-1]["payload"]["think"] is False


def test_openai_compat_end_to_end(tasks, fixture_dir):
    with mock_server("openai", tasks) as (url, handler):
        backend = OpenAICompatBackend("mock", base_url=url, options={"temperature": 0.0, "seed": 3})
        backend.check()
        for task in tasks:
            record = run_once(task, backend, fixture_dir)
            assert record.status == "ok" and record.check.passed, (task.id, record.check.details)
        second = [r for r in handler.requests if r["path"] == "/v1/chat/completions"][1]["payload"]
        roles = [m["role"] for m in second["messages"]]
        assert "tool" in roles or second["messages"][-1]["role"] == "tool"
        tool_msgs = [m for m in second["messages"] if m["role"] == "tool"]
        assert all(m["tool_call_id"].startswith("call_") for m in tool_msgs)
        assistant = [m for m in second["messages"] if m.get("tool_calls")][0]
        assert isinstance(assistant["tool_calls"][0]["function"]["arguments"], str)


def test_openai_invalid_json_arguments_are_a_model_failure(tasks, fixture_dir):
    with mock_server("openai", tasks, profile="invalid_json") as (url, _):
        record = run_once(next(t for t in tasks if t.id == "read-01"), OpenAICompatBackend("mock", base_url=url), fixture_dir)
        assert record.status == "ok" and record.check.failure_type == "invalid_json"


def test_backend_error_is_not_a_model_failure(tasks, fixture_dir):
    backend = OllamaBackend("m", host="http://127.0.0.1:9", timeout=2)
    record = run_once(next(t for t in tasks if t.id == "read-01"), backend, fixture_dir)
    assert record.status == "error" and record.check is None
```

<!-- file: tests/test_cli.py -->
**`tests/test_cli.py`**

```python
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
```

### Run

Everything the program can do without a real model:

```text
$ toolcallbench list-tasks
chain-01     chain    calls=3  Fix the title search and confirm with tests
chain-02     chain    calls=2  Read the README, then run what it says
chain-03     chain    calls=2  Locate a class, then read it
chain-04     chain    calls=6  Fix both failing tests
edit-01      edit     calls=2  Change one config value
edit-02      edit     calls=1  Bump the package version
edit-03      edit     calls=2  Change a value with a unified diff
edit-04      edit     calls=2  Add a function to a file
edit-05      edit     calls=2  Fix the late-fee cap (no tool named)
failure-01   failure  calls=0  Answer directly without tools
failure-02   failure  calls=2  Two independent reads in one step
failure-03   failure  calls=3  Recover from a missing file
read-01      read     calls=1  Read one config value
read-02      read     calls=1  List a directory
read-03      read     calls=1  Find a definition with grep
read-04      read     calls=1  Read a CSV and answer a question
read-05      read     calls=1  Read members and count them
run-01       run      calls=1  Run the tests and count failures
run-02       run      calls=1  Run a script and report a number
run-03       run      calls=1  Run a shell-style listing

20 tasks
```

```text
$ toolcallbench validate-tasks
PASS  chain-01     Fix the title search and confirm with tests
PASS  chain-02     Read the README, then run what it says
PASS  chain-03     Locate a class, then read it
PASS  chain-04     Fix both failing tests
PASS  edit-01      Change one config value
PASS  edit-02      Bump the package version
PASS  edit-03      Change a value with a unified diff
PASS  edit-04      Add a function to a file
PASS  edit-05      Fix the late-fee cap (no tool named)
PASS  failure-01   Answer directly without tools
PASS  failure-02   Two independent reads in one step
PASS  failure-03   Recover from a missing file
PASS  read-01      Read one config value
PASS  read-02      List a directory
PASS  read-03      Find a definition with grep
PASS  read-04      Read a CSV and answer a question
PASS  read-05      Read members and count them
PASS  run-01       Run the tests and count failures
PASS  run-02       Run a script and report a number
PASS  run-03       Run a shell-style listing

20/20 reference solutions pass
```

A complete benchmark with the fake model (a "perfect" model, so it passes everything). Results
go to the `results` folder:

```text
$ toolcallbench run --backend scripted --repeats 1 --session demo
session demo: 1 model(s) x 20 task(s) x 1 repeat(s) = 20 runs
[1/20] scripted-oracle chain-01 rep 1: PASS N.Ns
[2/20] scripted-oracle chain-02 rep 1: PASS N.Ns
[3/20] scripted-oracle chain-03 rep 1: PASS N.Ns
[4/20] scripted-oracle chain-04 rep 1: PASS N.Ns
[5/20] scripted-oracle edit-01 rep 1: PASS N.Ns
[6/20] scripted-oracle edit-02 rep 1: PASS N.Ns
[7/20] scripted-oracle edit-03 rep 1: PASS N.Ns
[8/20] scripted-oracle edit-04 rep 1: PASS N.Ns
[9/20] scripted-oracle edit-05 rep 1: PASS N.Ns
[10/20] scripted-oracle failure-01 rep 1: PASS N.Ns
[11/20] scripted-oracle failure-02 rep 1: PASS N.Ns
[12/20] scripted-oracle failure-03 rep 1: PASS N.Ns
[13/20] scripted-oracle read-01 rep 1: PASS N.Ns
[14/20] scripted-oracle read-02 rep 1: PASS N.Ns
[15/20] scripted-oracle read-03 rep 1: PASS N.Ns
[16/20] scripted-oracle read-04 rep 1: PASS N.Ns
[17/20] scripted-oracle read-05 rep 1: PASS N.Ns
[18/20] scripted-oracle run-01 rep 1: PASS N.Ns
[19/20] scripted-oracle run-02 rep 1: PASS N.Ns
[20/20] scripted-oracle run-03 rep 1: PASS N.Ns

report: ./results/reports/demo.md
        ./results/reports/demo.html
```

The beginning of the report it wrote:

```text
$ toolcallbench report --session demo --print | sed -n 1,24p
# ToolCallBench report: demo

Started 2026-10-24T02:52:13+00:00. 20 runs: 1 model(s), 20 task(s), 1 repeat(s) each.

## Settings

| Setting | Value |
| --- | --- |
| Backend | scripted |
| Host |  |
| Context length (num_ctx) | 16384 |
| Temperature | 0.0 |
| Base seed (+1 per repeat) | 42 |
| Repeats per task | 1 |
| Call limit per run | 12 |
| Turn limit per run | 10 |
| KV cache type (declared) | f16 |
| Flash attention (declared) | False |
| System prompt hash | 368df4cf6d7a |
| ToolCallBench version | 0.1.0 |
| Platform | Linux x86_64 |
| Python | 3.13.17 |

## Summary
```

The doctor with the fake backend:

```text
$ toolcallbench doctor --backend scripted
[ OK ] Python 3.10 or newer: 3.13.17
[ OK ] task files: 20 tasks in ./tasks
[ OK ] fixture repo: 2 failing test(s); the tasks expect exactly 2
[ OK ] backend: scripted (no server needed)
```

And the whole test suite so far (this takes about a minute):

```text
$ python -m pytest
........................................................................ [ 88%]
.........                                                                [100%]
81 passed in N.NNs
```

### Checkpoint

```bash
git add -A && git commit -m "Day 6: CLI and mock-server tests"
```

---

## Day 7: Helper scripts, then your first real model

**Goal:** a model on your Mac answers one real task.

### Why

Three small scripts help you run on 16 GB:

- `serve_ollama.sh` starts Ollama with the right settings. Some settings (`OLLAMA_KV_CACHE_TYPE`, `OLLAMA_FLASH_ATTENTION`) can only be set when the server starts, not in each request. So we tell the benchmark what we used with `--kv-cache-type` and `--flash-attention`, and it prints them in the report as "declared".
- `estimate_memory.py` estimates weights plus *KV cache* (the memory a model uses to remember the conversation). Formula: `2 x layers x KV heads x head size x bytes per number x tokens`.
- `make_task_catalog.py` writes `docs/TASK_CATALOG.md` from the task files, so the documentation can never disagree with the tasks.

### Create

<!-- file: scripts/serve_ollama.sh -->
**`scripts/serve_ollama.sh`**

```bash
#!/usr/bin/env bash
# Start Ollama with settings suited to a MacBook with 16 GB of unified memory.
# Quit the Ollama menu-bar app first: it already owns port 11434 with its own settings.
set -euo pipefail

export OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-16384}"  # default context for every request
export OLLAMA_FLASH_ATTENTION=1                                 # required for a quantized KV cache
export OLLAMA_KV_CACHE_TYPE="${OLLAMA_KV_CACHE_TYPE:-q8_0}"     # f16 | q8_0 | q4_0
export OLLAMA_MAX_LOADED_MODELS=1                               # one model at a time; 16 GB has no room for two
export OLLAMA_NUM_PARALLEL=1                                    # the benchmark sends one request at a time

echo "Starting Ollama: context=${OLLAMA_CONTEXT_LENGTH} kv-cache=${OLLAMA_KV_CACHE_TYPE} flash-attention=on"
echo "Tell ToolCallBench about it:  --kv-cache-type ${OLLAMA_KV_CACHE_TYPE} --flash-attention  (or use configs/m4-16gb.yaml)"
exec ollama serve
```

<!-- file: scripts/estimate_memory.py -->
**`scripts/estimate_memory.py`**

```python
#!/usr/bin/env python3
"""Rough memory estimate for a model plus its context on a Mac with unified memory.

All model figures are approximate (typical Ollama downloads). Treat the result as a
planning aid, then confirm with `ollama ps` and Activity Monitor.
"""
from __future__ import annotations

import argparse

GIB = 1024**3

# name: (weights in GB, layers, KV heads, head dimension)
MODELS = {
    "qwen3:8b": (5.2, 36, 8, 128),
    "llama3.1:8b": (4.9, 32, 8, 128),
    "qwen2.5:7b": (4.7, 28, 4, 128),
    "qwen3:8b-q8_0": (8.9, 36, 8, 128),
    "qwen3:14b": (9.3, 40, 8, 128),
}

# bytes per stored KV element
KV_BYTES = {"f16": 2.0, "q8_0": 34 / 32, "q4_0": 18 / 32}


def kv_bytes_per_token(layers: int, kv_heads: int, head_dim: int, kv_type: str) -> float:
    """Keys and values (x2) for every layer."""
    return 2 * layers * kv_heads * head_dim * KV_BYTES[kv_type]


def estimate(model: str, num_ctx: int, kv_type: str, overhead_gb: float = 0.8) -> dict[str, float]:
    weights_gb, layers, kv_heads, head_dim = MODELS[model]
    kv_gb = kv_bytes_per_token(layers, kv_heads, head_dim, kv_type) * num_ctx / GIB
    return {"weights_gb": weights_gb, "kv_gb": kv_gb, "overhead_gb": overhead_gb, "total_gb": weights_gb + kv_gb + overhead_gb}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ram", type=float, default=16, help="unified memory in GB (default 16)")
    parser.add_argument("--usable", type=float, default=0.75, help="share of RAM the GPU may use (default 0.75, about 12 GB)")
    parser.add_argument("--ctx", type=int, default=16384, help="context length (num_ctx)")
    parser.add_argument("--kv", choices=sorted(KV_BYTES), default="q8_0", help="KV cache type")
    args = parser.parse_args(argv)
    budget = args.ram * args.usable
    print(f"RAM {args.ram:g} GB, GPU budget about {budget:.1f} GB, context {args.ctx}, KV cache {args.kv}")
    print(f"{'model':<16}{'weights':>9}{'KV':>8}{'other':>8}{'total':>8}   fits?")
    for name in MODELS:
        e = estimate(name, args.ctx, args.kv)
        verdict = "yes" if e["total_gb"] <= budget - 1.0 else ("tight" if e["total_gb"] <= budget else "no")
        print(f"{name:<16}{e['weights_gb']:>8.1f}G{e['kv_gb']:>7.1f}G{e['overhead_gb']:>7.1f}G{e['total_gb']:>7.1f}G   {verdict}")
    print("\nEstimates only. Check the real numbers with `ollama ps` while a model is loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

<!-- file: scripts/make_task_catalog.py -->
**`scripts/make_task_catalog.py`**

```python
#!/usr/bin/env python3
"""Generate docs/TASK_CATALOG.md from tasks/*.yaml so the documentation cannot drift from the tasks."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from toolcallbench.models import GROUPS  # noqa: E402
from toolcallbench.tasks import load_tasks  # noqa: E402

GROUP_NOTES = {
    "read": "Read-only questions. Each prompt names the tool to use.",
    "edit": "Change files. The first four prompts name the tool; edit-05 only describes the bug.",
    "run": "Run allowed commands and report what they print.",
    "chain": "Several dependent steps. No tool is named; the model must plan.",
    "failure": "Robustness: answering without tools, parallel calls, and recovering from a wrong path.",
}


def describe_expect(expect: dict) -> list[str]:
    lines = []
    for req in expect.get("calls", []):
        tool = req["tool"] if isinstance(req["tool"], str) else " or ".join(req["tool"])
        args = req.get("args")
        lines.append(f"call `{tool}`" + (f" with {args}" if args else ""))
    if expect.get("ordered"):
        lines.append("calls must happen in this order")
    if expect.get("parallel"):
        lines.append("the calls must be requested together in one step")
    if expect.get("no_tool_calls"):
        lines.append("no tool may be called")
    if expect.get("forbidden_tools"):
        lines.append("must not use " + ", ".join(f"`{t}`" for t in expect["forbidden_tools"]))
    for path, spec in (expect.get("final_files") or {}).items():
        for text in spec.get("contains", []):
            lines.append(f"`{path}` contains `{text}`")
        for text in spec.get("not_contains", []):
            lines.append(f"`{path}` no longer contains `{text}`")
    for item in expect.get("command", []):
        lines.append("after the run, `" + " ".join(item["argv"]) + "` exits with 0")
    for text in expect.get("answer_contains", []):
        lines.append(f"the answer mentions `{text}`")
    for pattern in expect.get("answer_regex", []):
        lines.append(f"the answer matches `{pattern}`")
    return lines


def render() -> str:
    tasks = load_tasks(ROOT / "tasks")
    out = [
        "# Task catalog",
        "",
        "Generated by `scripts/make_task_catalog.py` from `tasks/*.yaml`. Do not edit by hand.",
        "",
        f"{len(tasks)} tasks in {len(GROUPS)} groups. Every task has a reference solution that is replayed by "
        "`toolcallbench validate-tasks`, so each one is known to be passable.",
        "",
        "| Task | Group | Title | Tool named | Reference calls |",
        "| --- | --- | --- | --- | --- |",
    ]
    out += [f"| {t.id} | {t.group} | {t.title} | {'yes' if t.tools_named else 'no'} | {t.baseline_calls} |" for t in tasks]
    for group in GROUPS:
        out += ["", f"## {group.title()}", "", GROUP_NOTES[group]]
        for t in (t for t in tasks if t.group == group):
            out += ["", f"### {t.id}: {t.title}", "", "Prompt:", ""]
            out += [f"> {line}" if line else ">" for line in t.prompt.splitlines()]
            out += ["", "Passes when:", ""]
            out += [f"- {line}" for line in describe_expect(t.expect)]
    return "\n".join(out) + "\n"


def main() -> int:
    target = ROOT / "docs" / "TASK_CATALOG.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text(render(), encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

<!-- file: tests/test_scripts.py -->
**`tests/test_scripts.py`**

```python
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_kv_cache_formula():
    mem = load("estimate_memory")
    per_token = mem.kv_bytes_per_token(36, 8, 128, "f16")
    assert per_token == 147456  # 144 KiB per token for an 8B Qwen3-class model
    assert round(per_token * 16384 / 1024**3, 2) == 2.25
    assert mem.kv_bytes_per_token(36, 8, 128, "q8_0") < per_token * 0.6


def test_estimate_marks_big_models(capsys):
    mem = load("estimate_memory")
    assert mem.estimate("qwen3:8b", 16384, "q8_0")["total_gb"] < 8
    assert mem.main(["--ctx", "16384"]) == 0
    out = capsys.readouterr().out
    assert "qwen3:14b" in out and "tight" in out


def test_task_catalog_is_up_to_date():
    catalog = load("make_task_catalog")
    assert (ROOT / "docs" / "TASK_CATALOG.md").read_text(encoding="utf-8") == catalog.render()
```

Make the server script runnable and generate the catalog:

```bash
chmod +x scripts/serve_ollama.sh
mkdir -p docs
python scripts/make_task_catalog.py
```

### Run

```text
$ python scripts/estimate_memory.py
RAM 16 GB, GPU budget about 12.0 GB, context 16384, KV cache q8_0
model             weights      KV   other   total   fits?
qwen3:8b             5.2G    1.2G    0.8G    7.2G   yes
llama3.1:8b          4.9G    1.1G    0.8G    6.8G   yes
qwen2.5:7b           4.7G    0.5G    0.8G    6.0G   yes
qwen3:8b-q8_0        8.9G    1.2G    0.8G   10.9G   yes
qwen3:14b            9.3G    1.3G    0.8G   11.4G   tight

Estimates only. Check the real numbers with `ollama ps` while a model is loaded.
```

```text
$ python scripts/make_task_catalog.py && python -m pytest tests/test_scripts.py
wrote docs/TASK_CATALOG.md
...                                                                      [100%]
3 passed in N.NNs
```

### Your first real model

1. **Quit the Ollama menu-bar app** (it would block the port with default settings).
2. Terminal 1: `./scripts/serve_ollama.sh` (leave it running).
3. Terminal 2 (with `source .venv/bin/activate`):

```bash
ollama pull qwen3:8b            # about 5 GB download
toolcallbench doctor --model qwen3:8b --probe
```

`doctor` prints one line per check, in this shape (your values will differ):

```text
[ OK ] Python 3.10 or newer: 3.12.x
[ OK ] task files: 20 tasks in .../tasks
[ OK ] fixture repo: 2 failing test(s); the tasks expect exactly 2
[ OK ] Ollama server: version X.Y.Z at http://localhost:11434; N model(s) installed
[ OK ] model qwen3:8b: <size> <quantization>; tools supported
[ OK ] probe qwen3:8b: read-01 passed in <seconds>s, <number> tok/s
```

If the probe fails, look at the reason in the last line before you continue. Common causes are
in the table below.

| Message | What to do |
| --- | --- |
| `cannot reach http://localhost:11434` | Start the server: `./scripts/serve_ollama.sh` |
| `model ... not installed` | Run the `ollama pull` command it prints |
| `does not report tool support` | Use a model whose Ollama page lists "tools" |
| Probe fails with `no_call` or `text_tool_call` | The model or its template does not do tool calls well. That is a result, not a bug. Try another model |
| Very slow | For Qwen3 add `--think off` |

One thing the author could not verify without a real model: the exact shape Ollama expects for a
tool result message. This program sends `{"role": "tool", "tool_name": ..., "content": ...}`. The
probe is how you find out on your machine. If the probe always ends in a second tool call
or confusion about results, check the Ollama documentation for your version.

### Checkpoint

```bash
git add -A && git commit -m "Day 7: helper scripts, first real probe"
```

---

## Day 8: The real benchmark on your M4

**Goal:** a report that tells you which model to use.

### Plan the sweep

Memory first (the estimator gives the same table as above). On 16 GB the GPU can use roughly 12
GB. An 8B model at Q4 with a 16k context and a `q8_0` cache needs about 7 GB, so you can run it
while a browser is open. A 14B model or an 8B at Q8 leaves little room.

Run in this order, from cheap to expensive:

```bash
# 1. A quick look: one repeat of the cheapest group
toolcallbench run --model qwen3:8b --think off --groups read --repeats 1 --kv-cache-type q8_0 --flash-attention

# 2. The planned sweep (three models, three repeats each)
caffeinate -i toolcallbench run --config configs/m4-16gb.yaml --session m4-first

# 3. Does thinking help? Same model, thinking on
toolcallbench run --model qwen3:8b --think on --kv-cache-type q8_0 --flash-attention --session m4-think-on

# 4. Does quantization matter?
ollama pull qwen3:8b-q4_K_M && ollama pull qwen3:8b-q8_0     # check the exact tag names on ollama.com first
caffeinate -i toolcallbench run --config configs/quant-sweep-qwen3-8b.yaml --session m4-quant
```

`caffeinate -i` keeps the Mac awake. If it sleeps anyway, run the same command again with `--resume`.

Each command ends by printing where the report is. Open the HTML file:

```bash
open results/reports/m4-first.html
```

### How to read the first report

1. Look at **Settings**. If two reports differ there, they are not a fair comparison.
2. Look at **Errors**. If it is not 0, the server had problems; fix that first.
3. Compare **Pass** per group. Chain tasks are the hardest; a model that passes `read` and `run` but fails `chain` can call tools but cannot plan.
4. Read **Failure types**. `invalid_json` or `text_tool_call` means a format problem; `no_call` means the model answered from memory; `wrong_tool` or `outcome_mismatch` means a reasoning problem.
5. Look at the per-task table for cells like `1/3`: those are flaky tasks, and the transcript in `results/logs/<session>/<model>/<task>_<repeat>.jsonl` shows what happened.
6. Compare `tok/s` and `s/task`. A model that is 5% better but three times slower may not be the better choice for you.

### Keep a log

Fill in this table with your own numbers (do not copy anyone else's):

| Session | Model | Quant | Think | KV cache | Pass % | Chain % | Top failure type | s/task |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | |

### If something goes wrong

| Problem | Fix |
| --- | --- |
| The Mac becomes slow | Lower `--num-ctx 8192`, close the browser, or use a smaller model |
| `ollama ps` shows part of the model on CPU | The model plus cache does not fit; use a smaller context or quantization |
| All runs are `no_call` | Check that the model supports tools |
| Results change between runs | Expected to a small degree; use more `--repeats` |

---

## Day 9: Documents, polish and publishing

**Goal:** a project another person can understand, run and trust.

### The documents

Software projects normally come with a standard set of documents. They are all in the `docs`
folder of the finished repository; here is what each is for and how to write your own.

| Document | Question it answers | How to write it |
| --- | --- | --- |
| `README.md` | What is this and how do I start? | What it is in 3 lines, a quick start, where the docs are, honest status |
| `docs/PRD.md` (product requirements) | Why build it, for whom, what must it do? | Problem, users, goals and non-goals, numbered requirements (FR-1, FR-2...), risks |
| `docs/TECH_SPEC.md` | Exactly how does it behave? | Protocols, formats, scoring rules, configuration, error handling |
| `docs/ARCHITECTURE.md` | How are the parts connected? | Diagrams: context, components, data flow, sequence, states, storage (Mermaid) |
| `docs/TEST_PLAN.md` | What is tested and what is not? | Strategy, a table linking each requirement to tests, results, known gaps |
| `docs/SECURITY.md` | What can go wrong? | What protects the user, and honestly, what does not |
| `docs/DECISIONS.md` | Why this way? | Short records: decision, why, cost |
| `docs/USER_GUIDE.md` | How do I use it? | Install, commands, reading output, troubleshooting |
| `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md` | What changed, how to help, what next? | Short lists |

Diagrams in `ARCHITECTURE.md` are written as text (Mermaid), so they stay in Git. GitHub draws
them automatically. To preview locally, use the Mermaid extension in VS Code.

A good habit, used here: generate documents from the source when you can (the task catalog
and this guide), so they cannot go out of date. The PRD has a requirement table; the test plan
maps each requirement to the tests that prove it.

### Create

The README, a Makefile with shortcuts, and the CI file that runs the tests on GitHub for every push:

<!-- file: README.md -->
**`README.md`**

````markdown
# ToolCallBench

Find out which local language model calls tools reliably **on your own machine**.

ToolCallBench gives a model six tools (read, list, search, edit, patch, run a command) and 20
small tasks on a sample Python project. It checks the results with plain code, not with
another model, and writes a report that compares models and quantization levels.

It is tuned for a **MacBook M4 with 16 GB of memory** running Ollama, and works with any
OpenAI-compatible local server (llama.cpp, LM Studio, vLLM).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

toolcallbench validate-tasks                        # 20/20 reference solutions pass
python -m pytest                                    # the automated tests
toolcallbench run --backend scripted --repeats 1    # whole pipeline, no model needed
```

With a real model:

```bash
./scripts/serve_ollama.sh                           # terminal 1 (quit the Ollama menu-bar app first)
ollama pull qwen3:8b                                # terminal 2
toolcallbench doctor --model qwen3:8b --probe
toolcallbench run --config configs/m4-16gb.yaml
open results/reports/*.html
```

## What a report tells you

- Pass rate overall and for read, edit, run, chain and failure tasks
- Why runs failed (13 failure types, such as `invalid_json`, `text_tool_call`, `patch_failed`)
- Tokens per second, seconds per task, and calls compared with a reference solution
- Every setting that affects the result (context length, seed, KV cache type, versions)

## Status

Version 0.1.0. The harness, tasks, scoring, backends (checked against mock servers) and
reports are covered by automated tests. **No real model has been benchmarked yet**; run it on
your Mac to get the first numbers (`docs/TEST_PLAN.md` lists exactly what was and was not tested).

## Documentation

| Document | Purpose |
| --- | --- |
| [BUILD_FROM_SCRATCH.md](BUILD_FROM_SCRATCH.md) | Day-by-day guide to build this project yourself, with all code |
| [docs/PRD.md](docs/PRD.md) | Why it exists, who it is for, requirements |
| [docs/TECH_SPEC.md](docs/TECH_SPEC.md) | Exact behavior: tools, scoring, config, storage |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Diagrams: context, components, data flow, sequence, states, storage |
| [docs/TEST_PLAN.md](docs/TEST_PLAN.md) | What is tested and how requirements map to tests |
| [docs/SECURITY.md](docs/SECURITY.md) | What protects you and what does not |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why it is built this way |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Install, run, read the report, troubleshoot |
| [docs/MODEL_GUIDE_M4_16GB.md](docs/MODEL_GUIDE_M4_16GB.md) | Memory budget and model choices for 16 GB |
| [docs/TASK_CATALOG.md](docs/TASK_CATALOG.md) | All 20 tasks (generated) |
| [docs/ROADMAP.md](docs/ROADMAP.md), [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md) | Project housekeeping |

## License

MIT
````

<!-- file: Makefile -->
**`Makefile`**

```text
.PHONY: install test validate smoke docs check serve clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest

validate:
	toolcallbench validate-tasks

smoke:
	toolcallbench run --backend scripted --repeats 1 --results-dir results-smoke --session smoke --resume
	@echo "Open results-smoke/reports/smoke.html"

docs:
	python scripts/make_task_catalog.py
	python scripts/make_build_guide.py

check: test validate
	python scripts/make_task_catalog.py
	git diff --exit-code docs/TASK_CATALOG.md || (echo "TASK_CATALOG.md was out of date"; exit 1)

serve:
	./scripts/serve_ollama.sh

clean:
	rm -rf results results-smoke .pytest_cache build *.egg-info
```

<!-- file: .github/workflows/ci.yml -->
**`.github/workflows/ci.yml`**

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python: ["3.10", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e ".[dev]"
      - run: toolcallbench validate-tasks
      - run: python -m pytest
```

The two scripts that build and check this guide (yes, the guide contains the scripts that
build the guide):

<!-- file: scripts/make_build_guide.py -->
**`scripts/make_build_guide.py`**

````python
#!/usr/bin/env python3
"""Build BUILD_FROM_SCRATCH.md from docs/guide/BUILD_FROM_SCRATCH.template.md.

The template contains three kinds of directive, each alone on a line:

    {{file:PATH}}   embed a repository file (code can never differ from the repo)
    {{cmd:COMMAND}} run COMMAND in a clean copy of the repo and embed its real output
    {{tree}}        embed the list of embedded files

`scripts/verify_build_guide.py` extracts the embedded files into an empty folder and runs the tests there.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "guide" / "BUILD_FROM_SCRATCH.template.md"
OUTPUT = ROOT / "BUILD_FROM_SCRATCH.md"

LANGUAGES = {".py": "python", ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".toml": "toml", ".sh": "bash",
             ".md": "markdown", ".csv": "text", ".ini": "ini", ".gitignore": "text"}
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".venv", "results", "results-smoke", "results-demo", ".git", "build"}
MARKER = re.compile(r"^<!-- file: (?P<path>.+?) -->$")


def collect_files() -> list[str]:
    """Repository files that the guide teaches the reader to create, as sorted relative POSIX paths."""
    found: set[str] = set()
    for name in ("pyproject.toml", ".gitignore", "Makefile", "README.md", ".github/workflows/ci.yml"):
        if (ROOT / name).is_file():
            found.add(name)
    for folder, pattern in (("src", "*.py"), ("tests", "*.py"), ("tasks", "*.yaml"), ("configs", "*.yaml"), ("scripts", "*")):
        for path in (ROOT / folder).rglob(pattern):
            if path.is_file() and not SKIP_PARTS & set(path.relative_to(ROOT).parts) and "egg-info" not in str(path):
                found.add(path.relative_to(ROOT).as_posix())
    for path in (ROOT / "fixtures" / "repo").rglob("*"):
        if path.is_file() and not SKIP_PARTS & set(path.relative_to(ROOT).parts):
            found.add(path.relative_to(ROOT).as_posix())
    return sorted(found)


def fence_for(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def embed_file(rel: str) -> str:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise SystemExit(f"{rel} must end with exactly one newline")
    language = LANGUAGES.get(path.suffix) or LANGUAGES.get(path.name, "text")
    fence = fence_for(text)
    return f"<!-- file: {rel} -->\n**`{rel}`**\n\n{fence}{language}\n{text.rstrip(chr(10))}\n{fence}"


def normalize(output: str, workdir: str) -> str:
    output = output.replace(workdir, ".")
    output = re.sub(r"\bin \d+\.\d+s\b", "in N.NNs", output)
    output = re.sub(r"\b\d+\.\d+s\b", "N.Ns", output)
    output = re.sub(r"\b\d{8}-\d{6}\b", "YYYYMMDD-HHMMSS", output)
    return "\n".join(line.rstrip() for line in output.strip("\n").splitlines())


def make_workdir() -> str:
    tmp = tempfile.mkdtemp(prefix="tcb-guide-")
    target = Path(tmp) / "proj"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(*SKIP_PARTS, "*.egg-info", "__pycache__"))
    return str(target)


def run_cmd(command: str, workdir: str) -> str:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": "-p no:cacheprovider", "NO_COLOR": "1"}
    proc = subprocess.run(command, shell=True, cwd=workdir, capture_output=True, text=True, env=env, timeout=600)
    body = normalize(proc.stdout + proc.stderr, workdir)
    status = "" if proc.returncode == 0 else f"\n[exit code {proc.returncode}]"
    return f"```text\n$ {command}\n{body}{status}\n```"


def build() -> str:
    workdir = make_workdir()
    try:
        out = []
        for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
            m = re.fullmatch(r"\{\{(file|cmd|tree):?(.*)\}\}", line.strip())
            if not m:
                out.append(line)
            elif m.group(1) == "file":
                out.append(embed_file(m.group(2)))
            elif m.group(1) == "cmd":
                out.append(run_cmd(m.group(2), workdir))
            else:
                out.append("```text\n" + "\n".join(collect_files()) + "\n```")
        return "\n".join(out) + "\n"
    finally:
        shutil.rmtree(Path(workdir).parent, ignore_errors=True)


def main() -> int:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
````

<!-- file: scripts/verify_build_guide.py -->
**`scripts/verify_build_guide.py`**

```python
#!/usr/bin/env python3
"""Prove that BUILD_FROM_SCRATCH.md is complete.

1. Extract every `<!-- file: PATH -->` block into an empty folder.
2. Check that the set of files and their contents equal the repository.
3. Create a virtual environment there, install the package and run validate-tasks and the tests.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_build_guide import MARKER, OUTPUT, ROOT, collect_files  # noqa: E402


def extract(guide: Path, target: Path) -> dict[str, str]:
    lines = guide.read_text(encoding="utf-8").splitlines()
    files: dict[str, str] = {}
    i = 0
    while i < len(lines):
        m = MARKER.match(lines[i])
        i += 1
        if not m:
            continue
        path = m.group("path")
        while not re.match(r"^`{3,}\S*$", lines[i]):
            i += 1
        fence = re.match(r"^(`{3,})", lines[i]).group(1)
        i += 1
        body = []
        while lines[i] != fence:
            body.append(lines[i])
            i += 1
        i += 1
        if path in files:
            raise SystemExit(f"file embedded twice: {path}")
        files[path] = "\n".join(body) + "\n"
        out = target / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(files[path], encoding="utf-8")
    return files


def run(cmd: list[str], cwd: Path) -> None:
    print("$", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd)
    if proc.returncode != 0:
        raise SystemExit(f"command failed with exit code {proc.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="do not delete the extracted folder")
    args = parser.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="tcb-verify-"))
    target = tmp / "toolcallbench"
    target.mkdir()
    files = extract(OUTPUT, target)
    expected = set(collect_files())
    if set(files) != expected:
        raise SystemExit(f"file sets differ.\n  only in guide: {sorted(set(files) - expected)}\n  only in repo: {sorted(expected - set(files))}")
    for rel, text in files.items():
        if (ROOT / rel).read_text(encoding="utf-8") != text:
            raise SystemExit(f"content differs from the repository: {rel}")
    print(f"{len(files)} files extracted and identical to the repository")
    run([sys.executable, "-m", "venv", ".venv"], target)
    py = str(target / ".venv" / "bin" / "python")
    run([py, "-m", "pip", "install", "-q", "-e", ".[dev]"], target)
    run([py, "scripts/make_task_catalog.py"], target)
    run([py, "-m", "toolcallbench", "validate-tasks"], target)
    run([py, "-m", "pytest"], target)
    print(f"\nOK: the guide rebuilds a working project ({target})")
    if not args.keep:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Write the documents from the table above, using the finished repository's `docs` folder as a
model, then add `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md` in the same way.

### Run

The full test suite, one last time:

```text
$ python -m pytest
........................................................................ [ 88%]
.........                                                                [100%]
81 passed in N.NNs
```

### Publish

```bash
git add -A && git commit -m "Day 9: docs and polish"
git tag v0.1.0
gh repo create toolcallbench --public --source=. --push      # needs the GitHub CLI: brew install gh
git push --tags
```

---

## Day 10: Make it yours

Ideas, from easiest to hardest:

1. **Add a task.** Copy `tasks/read-01.yaml` to `tasks/read-06.yaml`, change the id, prompt and `expect`, add a reference solution, then run `toolcallbench validate-tasks --tasks read-06`. If your reference does not pass, the task is wrong.
2. **Add a failure profile** to `scripted.py` (for example, a model that calls the right tool with the wrong argument name) and a test in `test_checks.py`.
3. **Use your own project.** Copy a project of yours (without secrets), write tasks for it, and run `toolcallbench run --fixture ~/path/to/copy --tasks-dir my-tasks --model qwen3:8b`. Read `docs/SECURITY.md` first.
4. **Compare servers.** Run the same model through llama.cpp's `llama-server` with `--backend openai-compat --host http://localhost:8080` and compare the failure types. This is where `invalid_json` shows up.
5. **Write about it.** The report contains every setting. Publish your table and say which Mac you used.

## Appendix: if a test fails after you copy the code

1. Run only that test with `python -m pytest tests/test_x.py -x`.
2. Read the first error, not the last.
3. Diff the file against this guide (a missing blank line or indentation is the usual cause).
4. Files must end with exactly one newline.
5. Re-check Day 1: the sample project must show 2 failed, 11 passed.
