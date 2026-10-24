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

    root = Path(__file__).resolve().parents[1] / "src" / "toolcallbench" / "data" / "configs"
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
