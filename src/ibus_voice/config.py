from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "ibus-voice" / "config.toml"
DEFAULT_CONFIG_DIR = DEFAULT_CONFIG_PATH.parent


@dataclass(slots=True)
class ProviderConfig:
    name: str
    api_key: str
    model: str
    endpoint: str | None = None
    timeout_seconds: float = 30.0
    dictionary_path: Path | None = None


@dataclass(slots=True)
class AudioConfig:
    sample_rate: int = 16_000
    channels: int = 1
    chunk_size: int = 1024
    sample_width: int = 2
    input_device_index: int | None = None


@dataclass(slots=True)
class HotkeyConfig:
    key: str = "space"
    modifiers: tuple[str, ...] = ("Control",)


@dataclass(slots=True)
class CleanupConfig:
    enabled: bool = False
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 8.0
    dictionary_path: Path | None = None
    history_path: Path | None = None
    system_prompt_path: Path | None = None
    user_prompt_path: Path | None = None


@dataclass(slots=True)
class AppConfig:
    provider: ProviderConfig
    audio: AudioConfig
    hotkey: HotkeyConfig
    cleanup: CleanupConfig | None = None


def load_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return parse_config(raw, base_dir=config_path.expanduser().resolve().parent)


def parse_config(raw: dict, *, base_dir: Path | None = None) -> AppConfig:
    provider_section = raw.get("provider", {})
    name = provider_section.get("name")
    api_key = provider_section.get("api_key")
    model = provider_section.get("model")
    if not name or not api_key or not model:
        raise ValueError("provider.name, provider.api_key, and provider.model are required")

    audio_section = raw.get("audio", {})
    hotkey_section = raw.get("hotkey", {})

    provider = ProviderConfig(
        name=str(name),
        api_key=str(api_key),
        model=str(model),
        endpoint=_optional_str(provider_section.get("endpoint")),
        timeout_seconds=float(provider_section.get("timeout_seconds", 30.0)),
        dictionary_path=_resolve_optional_path(provider_section.get("dictionary_path", "dictionary.txt"), base_dir or DEFAULT_CONFIG_DIR),
    )
    audio = AudioConfig(
        sample_rate=int(audio_section.get("sample_rate", 16_000)),
        channels=int(audio_section.get("channels", 1)),
        chunk_size=int(audio_section.get("chunk_size", 1024)),
        sample_width=int(audio_section.get("sample_width", 2)),
        input_device_index=_optional_int(audio_section.get("input_device_index")),
    )
    modifiers = hotkey_section.get("modifiers", ["Control"])
    if isinstance(modifiers, str):
        modifiers = [modifiers]
    hotkey = HotkeyConfig(
        key=str(hotkey_section.get("key", "space")),
        modifiers=tuple(str(item) for item in modifiers),
    )
    cleanup = _parse_cleanup_config(raw.get("cleanup"), base_dir=base_dir or DEFAULT_CONFIG_DIR)
    return AppConfig(provider=provider, audio=audio, hotkey=hotkey, cleanup=cleanup)


def _parse_cleanup_config(raw: object, *, base_dir: Path) -> CleanupConfig | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("cleanup section must be a table")

    enabled = bool(raw.get("enabled", False))
    if not enabled:
        return CleanupConfig(enabled=False)

    base_url = _required_str(raw.get("base_url"), "cleanup.base_url")
    api_key = _required_str(raw.get("api_key"), "cleanup.api_key")
    model = _required_str(raw.get("model"), "cleanup.model")
    return CleanupConfig(
        enabled=True,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=float(raw.get("timeout_seconds", 8.0)),
        dictionary_path=_resolve_optional_path(raw.get("dictionary_path", "dictionary.txt"), base_dir),
        history_path=_resolve_optional_path(raw.get("history_path", "history.db"), base_dir),
        system_prompt_path=_resolve_optional_path(raw.get("system_prompt_path", "system_prompt.txt"), base_dir),
        user_prompt_path=_resolve_optional_path(raw.get("user_prompt_path", "user_prompt.txt"), base_dir),
    )


def _optional_str(value: object) -> str | None:
    return None if value in (None, "") else str(value)


def _optional_int(value: object) -> int | None:
    return None if value in (None, "") else int(value)


def _required_str(value: object, field_name: str) -> str:
    if value in (None, ""):
        raise ValueError(f"{field_name} is required when cleanup is enabled")
    return str(value)


def _resolve_optional_path(value: object, base_dir: Path) -> Path | None:
    text = _optional_str(value)
    if text is None:
        return None
    path = Path(text).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()
