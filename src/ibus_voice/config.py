from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "ibus-voice" / "config.toml"


@dataclass(slots=True)
class ProviderConfig:
    name: str
    api_key: str
    model: str
    endpoint: str | None = None
    timeout_seconds: float = 30.0


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
class AppConfig:
    provider: ProviderConfig
    audio: AudioConfig
    hotkey: HotkeyConfig


def load_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return parse_config(raw)


def parse_config(raw: dict) -> AppConfig:
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
    return AppConfig(provider=provider, audio=audio, hotkey=hotkey)


def _optional_str(value: object) -> str | None:
    return None if value in (None, "") else str(value)


def _optional_int(value: object) -> int | None:
    return None if value in (None, "") else int(value)
