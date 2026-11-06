"""Run configuration: defaults, YAML loading and project paths."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SETTINGS_KEYS = {
    "num_ctx",
    "temperature",
    "seed",
    "repeats",
    "max_calls",
    "max_turns",
    "request_timeout",
    "max_calls_per_turn",
    "tools_offered",
}
TOP_KEYS = {"backend", "host", "api_key_env", "settings", "declared_server", "models"}
DEFAULT_API_KEY_ENV = "TOOLCALLBENCH_API_KEY"


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
    max_calls_per_turn: int = 0  # 0 = run every call the model makes in one reply
    tools_offered: str = "all"  # "all" or "task" (only the tools the reference solution uses)
    api_key_env: str = ""  # name of the environment variable that holds the API key (never the key itself)
    api_key: str = field(default="", repr=False)  # read from that variable at run time; never saved
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
    cfg.api_key_env = data.get("api_key_env", cfg.api_key_env)
    if not isinstance(cfg.api_key_env, str) or (cfg.api_key_env and not cfg.api_key_env.replace("_", "").isalnum()):
        raise ConfigError(f"{path}: api_key_env must be the NAME of an environment variable, not the key itself")
    settings = data.get("settings") or {}
    bad = set(settings) - SETTINGS_KEYS
    if bad:
        raise ConfigError(f"{path}: unknown settings {sorted(bad)}; allowed: {sorted(SETTINGS_KEYS)}")
    for key, value in settings.items():
        setattr(cfg, key, value)
    if cfg.tools_offered not in ("all", "task"):
        raise ConfigError(f"{path}: tools_offered must be 'all' or 'task'")
    if not isinstance(cfg.max_calls_per_turn, int) or cfg.max_calls_per_turn < 0:
        raise ConfigError(f"{path}: max_calls_per_turn must be 0 or a positive whole number")
    declared = data.get("declared_server") or {}
    cfg.declared_kv_cache_type = str(declared.get("kv_cache_type", cfg.declared_kv_cache_type))
    cfg.declared_flash_attention = bool(declared.get("flash_attention", cfg.declared_flash_attention))
    cfg.models = [_model_spec(m) for m in data.get("models") or []]
    return cfg


def data_dir() -> Path:
    """The tasks, fixture repository and example configs that ship inside the installed package."""
    return Path(__file__).resolve().parent / "data"


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: the current directory) to a folder holding tasks/ and fixtures/repo/.

    Returns `start` itself when there is none; the caller then falls back to the built-in data.
    """
    start = Path(start or Path.cwd()).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "tasks").is_dir() and (candidate / "fixtures" / "repo").is_dir():
            return candidate
    return start
