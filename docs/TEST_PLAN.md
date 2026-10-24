# Test plan

## 1. Strategy

The risk in this project is not the HTTP plumbing; it is **a scorer that gives a wrong
verdict**, because then every report is wrong. So the tests concentrate on three things:

1. Every task can be passed, and cannot be passed by doing nothing (reference solutions, `no_call` profile).
2. Every failure type is detected when it is imitated (scripted profiles and hand-built transcripts).
3. The tools cannot leave their sandbox, and bad input produces clear errors.

The real HTTP backends are tested against mock servers that follow the Ollama and
OpenAI-compatible request and response shapes.

| Level | Where | Needs a model? |
| --- | --- | --- |
| Unit | `test_patching`, `test_tools`, `test_config`, `test_scripts` | no |
| Component | `test_tasks`, `test_checks`, `test_store_report` | no (scripted backend) |
| Integration | `test_http_backends`, `test_cli` | no (mock servers) |
| System | `toolcallbench validate-tasks`; scripted `run` | no |
| Acceptance | `doctor --probe`, then a real `run` | **yes: the owner's Mac** |

## 2. How to run

```bash
python -m pytest                       # all automated tests
toolcallbench validate-tasks           # system-level check of the 20 tasks
python scripts/verify_build_guide.py   # rebuild from BUILD_FROM_SCRATCH.md and test the result
```

## 3. Requirement traceability

| Requirement | Verified by |
| --- | --- |
| FR-1 20 tasks in 5 groups | `test_tasks::test_twenty_tasks_across_five_groups`, `test_twelve_name_their_tools` |
| FR-2 backends | `test_http_backends` (Ollama, OpenAI-compatible), scripted backend used everywhere |
| FR-3 six tools, validation | `test_tools::test_six_tools_with_object_schemas`, `test_validate_arguments` |
| FR-4 sandbox | `test_tools::test_read_file_errors`, `test_run_command_allowlist_and_confinement`, `test_output_is_truncated`, `test_patching` |
| FR-5 scoring, 13 failure types | `test_checks` (profiles and hand-built transcripts), `test_failure_types_are_all_documented` |
| FR-6 repeats, settings recorded | `test_config::test_seed_changes_per_repeat`, `test_cli::test_run_against_mock_ollama` (settings JSON) |
| FR-7 SQLite and JSONL | `test_store_report::test_store_roundtrip_and_resume_keys`, `test_jsonl_log_has_messages_and_summary` |
| FR-8 resume | `test_cli::test_scripted_run_report_and_resume`, `test_resume_after_partial` |
| FR-9 reports | `test_store_report::test_aggregate_and_report`, `test_html_escapes_content` |
| FR-10 reference solutions | `test_tasks::test_every_reference_solution_passes`, `test_cli::test_validate_tasks` |
| FR-11 doctor | `test_cli::test_doctor_scripted`, `test_doctor_with_mock_ollama_and_probe`, `test_doctor_server_down` |
| FR-12 configs | `test_config::test_shipped_configs_load` |
| FR-13 backend errors are not model failures | `test_http_backends::test_backend_error_is_not_a_model_failure`, `test_cli::test_three_backend_errors_in_a_row_stop_a_model`, `test_unreachable_server_stops_before_running` |
| FR-14 memory estimate | `test_scripts::test_kv_cache_formula`, `test_estimate_marks_big_models` |
| NFR-6 clear errors | `test_config::test_bad_configs`, `test_tasks::test_task_validation`, `test_cli::test_run_requires_models` |
| Docs do not drift | `test_scripts::test_task_catalog_is_up_to_date`; `verify_build_guide.py` |

## 4. Failure-detection matrix

| Imitated behavior | Scripted profile or transcript | Expected failure type |
| --- | --- | --- |
| Broken JSON arguments | `invalid_json` | `invalid_json` |
| Invented tool | `unknown_tool` | `unknown_tool` |
| Tool call written as text | `text_call` | `text_tool_call` |
| Answers without using tools | `no_call` | `no_call` |
| Never stops calling | `call_limit` | `call_limit` |
| Wrong tool | `wrong_tool` | `wrong_tool` |
| Calls a tool when none is needed | `wrong_tool` on `failure-01` | `unneeded_call` |
| Edit that does not apply | `bad_edit` | `patch_failed` |
| Parallel calls sent one per turn | hand-built transcript | `not_parallel` |
| Stops early | hand-built transcript | `too_few_calls` |
| Wrong answer, right call | hand-built transcript | `outcome_mismatch` |
| Wrong path | hand-built transcript | `wrong_args` |
| `invalid_args` | covered at validation level in `test_tools::test_validate_arguments` | `invalid_args` |

## 5. Results of the last run

Recorded when version 0.1.0 was assembled, on Linux (Python 3.13) in a cloud sandbox.

| Check | Result |
| --- | --- |
| `python -m pytest` | 81 passed |
| `toolcallbench validate-tasks` | 20/20 reference solutions pass |
| Scripted end-to-end `run` with resume | passes (`test_cli`) |
| Mermaid diagrams in `ARCHITECTURE.md` | all 7 render |
| `scripts/verify_build_guide.py` | passes: guide extracted to an empty folder, identical to the repo, 20/20 tasks, 81 tests pass |
| Line coverage of `src/toolcallbench` | 92% (section 6) |

| Test file | Tests |
| --- | --- |
| `test_checks.py` | 14 |
| `test_cli.py` | 13 |
| `test_config.py` | 10 |
| `test_http_backends.py` | 7 |
| `test_patching.py` | 5 |
| `test_scripts.py` | 3 |
| `test_store_report.py` | 5 |
| `test_tasks.py` | 7 |
| `test_tools.py` | 17 |

## 6. Coverage

Line coverage measured with `coverage` over `src/toolcallbench`: **92%** (1409 statements, 108 missed). Lowest: `__main__.py` (0%, a two-line entry point), `base.py` 85%, `tools.py` 86%. The uncovered lines are mostly rare error branches (timeouts, unreadable files).

## 7. What has **not** been tested

Be clear about these before trusting a number from a report.

1. **No real model has been run.** Everything model-related uses the scripted backend or mock servers. Whether a particular model can pass a task is exactly what the benchmark is for.
2. **Real Ollama behavior** is assumed from its documented API. The one detail not confirmed from documentation is the shape of tool-result messages (`role: tool` with `tool_name`). `doctor --probe` is the first real check.
3. **macOS**. The development run was on Linux. The code uses only portable Python and standard tools (`ls`, `cat`, `grep`, `head`, `tail`, `wc`), but BSD versions of these tools differ slightly from GNU ones; only the simple forms are used by the tasks.
4. **Performance on 16 GB**: memory figures are estimates (see `MODEL_GUIDE_M4_16GB.md`).
5. **llama.cpp, LM Studio and vLLM**: only the shape of the OpenAI-compatible protocol is tested, against a mock.
6. **Hostile models**: the sandbox is a safety net (`SECURITY.md`).

## 8. Exit criteria for the acceptance test on the Mac

- `toolcallbench doctor --model <model> --probe` ends with no `FAIL` line.
- A `run` of one model finishes with 0 errors in the Errors column.
- `ollama ps` while running shows the whole model on the GPU (no CPU split).
- The report's Settings table matches what you started the server with.
