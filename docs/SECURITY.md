# Security notes

ToolCallBench executes text produced by a language model. This document says what protects
you, and what does not.

## What the tool does to limit damage

| Protection | How |
| --- | --- |
| Throwaway workspace | Every run works in a fresh copy of the fixture repository in a temp folder; deleted afterwards |
| Path confinement | File tools resolve paths and reject anything outside the copy (`..`, absolute paths, symlinks that leave it) |
| No shell | Commands are split with `shlex` and run directly; `|`, `>`, `;`, `&&` and `$()` have no special meaning |
| Allow-list | Only 12 programs; `python` only runs a `.py` file in the copy or `-m pytest` |
| Argument filter | Arguments starting with `/` or `~`, or containing `..`, are rejected |
| Time and size limits | 20 s per command, 6000 characters of output, 12 tool calls per run |
| Minimal environment | Commands get only `PATH`, `HOME` (set to the copy), and a few locale variables |

## What it does **not** protect against

This is a safety net against accidents, **not a security boundary**.

- `edit_file` can change an existing `.py` file (for example `scripts/report.py`), and `run_command` can then run it. That script runs with your user's permissions and can touch your real files or use the network.
- `pytest` imports and runs test files, which the model may have edited.
- Copying the fixture follows symlinks, so a symlink in a fixture that points at private files would copy those files into the workspace, where the model can read them. Keep secrets out of any fixture.

If you point `--fixture` at **your own repository**, the same limits apply. Do these first:

1. Use a copy of the project without secrets (`.env`, keys, tokens).
2. Run the benchmark as a normal user, never with `sudo`.
3. For untrusted models, run inside a VM or container with no network.

## Data handling

- Nothing is sent anywhere except to the model server you configure.
- Transcripts in `results/logs/` contain full prompts and file contents from the fixture; do not publish them if your fixture is private.
- `results/` is in `.gitignore`.

## Dependencies

`pyyaml` and `jsonschema` only. HTTP uses the standard library.

## Reporting a problem

Open an issue with the command you ran and the report's Settings table. For a security issue,
do not paste secrets into the issue.
