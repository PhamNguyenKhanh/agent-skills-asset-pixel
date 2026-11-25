"""User configuration loader for provider keys and routing order (never logs secrets)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROVIDER_ENV_MAP: dict[str, tuple[str, ...]] = {
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "xai": ("XAI_API_KEY",),
    "fal": ("FAL_KEY",),
}


def user_config_paths() -> list[Path]:
    """Candidate user-level config paths (outside project directory)."""
    paths: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        paths.append(Path(appdata) / "pixel-forge" / "config.json")
        paths.append(Path(appdata) / "agent-sprite-forge" / "config.json")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    home = Path.home()
    cfg_root = Path(xdg) if xdg else (home / ".config")
    paths.append(cfg_root / "pixel-forge" / "config.json")
    paths.append(cfg_root / "agent-sprite-forge" / "config.json")
    return paths


def load_user_config() -> dict[str, Any]:
    """Load first existing user config file, or return empty dict."""
    for path in user_config_paths():
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def get_api_key(provider: str) -> str | None:
    """Resolve API key for a single provider (environment takes precedence over user config)."""
    env_names = PROVIDER_ENV_MAP.get(provider, ())
    for env_name in env_names:
        val = os.environ.get(env_name, "").strip()
        if val:
            return val
    cfg = load_user_config()
    for env_name in env_names:
        val = str(cfg.get(env_name, "")).strip()
        if val:
            return val
    return None


def known_secrets() -> list[str]:
    """Return list of configured secret values strictly for redaction."""
    found: list[str] = []
    for provider in PROVIDER_ENV_MAP:
        key = get_api_key(provider)
        if key and len(key) >= 8:
            found.append(key)
    return found


def preferred_order(kind: str) -> list[str]:
    """Return user's preferred provider order for `image` or `video` from config."""
    cfg = load_user_config()
    providers_cfg = cfg.get("providers")
    if isinstance(providers_cfg, dict):
        order_cfg = providers_cfg.get("order")
        if isinstance(order_cfg, dict):
            items = order_cfg.get(kind)
            if isinstance(items, list):
                return [str(x).strip().lower() for x in items if str(x).strip()]
    return []


def configured_model(provider: str, kind: str) -> str | None:
    cfg = load_user_config()
    models = cfg.get("models")
    if isinstance(models, dict):
        entry = models.get(provider)
        if isinstance(entry, str) and entry.strip():
            return entry.strip()
        if isinstance(entry, dict):
            val = entry.get(kind)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def provider_key_status() -> dict[str, bool]:
    """Report yes/no key availability without ever revealing secret values."""
    return {provider: bool(get_api_key(provider)) for provider in PROVIDER_ENV_MAP}
