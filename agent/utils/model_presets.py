import json
import os

from .agent_config import AgentConfig
from .dotenv import load_dotenv_once


def _default_model_kwargs() -> dict:
    return AgentConfig.model_fields["model_kwargs"].default_factory()


def _default_special_tokens() -> dict:
    return AgentConfig.model_fields["special_tokens"].default_factory()


DEFAULT_PRESET: dict = {
    "api_type": None,
    "api_key_env": None,
    "api_base_env": None,
    "model_name": None,
    "stream": AgentConfig.model_fields["stream"].default,
    "special_tokens": _default_special_tokens(),
    "model_kwargs": _default_model_kwargs(),
}


def _merge_preset_defaults(raw: dict) -> dict:
    merged = dict(DEFAULT_PRESET)
    merged.update(raw)
    if "special_tokens" not in raw or not isinstance(raw.get("special_tokens"), dict):
        merged["special_tokens"] = _default_special_tokens()
    if "model_kwargs" not in raw or not isinstance(raw.get("model_kwargs"), dict):
        merged["model_kwargs"] = _default_model_kwargs()
    if "stream" not in raw:
        merged["stream"] = DEFAULT_PRESET["stream"]
    return merged


def _validate_preset(pid: str, preset: dict):
    required = ("api_type", "api_key_env", "api_base_env", "model_name", "stream", "special_tokens", "model_kwargs")
    missing = [k for k in required if k not in preset or preset[k] is None or preset[k] == ""]
    if missing:
        raise ValueError(f"preset {pid} missing fields: {', '.join(missing)}")
    if preset["api_type"] not in ("openai", "anthropic"):
        raise ValueError(f"preset {pid} unsupported api_type: {preset['api_type']}")
    if not isinstance(preset["special_tokens"], dict):
        raise ValueError(f"preset {pid} special_tokens must be dict")
    if not isinstance(preset["model_kwargs"], dict):
        raise ValueError(f"preset {pid} model_kwargs must be dict")


def _load_model_presets() -> dict:
    load_dotenv_once()
    p = os.getenv("EVOAGENT_MODEL_PRESETS_PATH", "").strip()
    if not p:
        p = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "model_presets.json"))
    if not os.path.isabs(p):
        p = os.path.abspath(p)
    with open(p, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError("model_presets.json must be an object")
    out = {}
    for pid, raw in data.items():
        if not isinstance(raw, dict):
            raise ValueError(f"preset {pid} must be an object")
        merged = _merge_preset_defaults(raw)
        _validate_preset(str(pid), merged)
        out[str(pid)] = merged
    return out


MODEL_PRESETS: dict = _load_model_presets()

DEFAULT_MODEL: str = os.getenv("EVOAGENT_DEFAULT_MODEL", "").strip()
