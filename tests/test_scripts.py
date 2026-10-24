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
