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
