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
    model: str
    api_key: str = ""
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
class CorrectionConfig:
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
class HistoryConfig:
    path: Path = DEFAULT_CONFIG_DIR / "history.db"


@dataclass(slots=True)
class AppConfig:
    provider: ProviderConfig
    audio: AudioConfig
    hotkey: HotkeyConfig
    history: HistoryConfig
    correction: CorrectionConfig | None = None

    @property
    def cleanup(self) -> CorrectionConfig | None:
        return self.correction


def load_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return parse_config(raw, base_dir=config_path.expanduser().resolve().parent)


def load_history_path(path: str | os.PathLike[str] | None = None) -> Path:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return _parse_history_config(raw.get("history"), base_dir=config_path.expanduser().resolve().parent).path


def parse_config(raw: dict, *, base_dir: Path | None = None) -> AppConfig:
    provider_section = raw.get("provider", {})
    audio_section = raw.get("audio", {})
    hotkey_section = raw.get("hotkey", {})
    config_base_dir = base_dir or DEFAULT_CONFIG_DIR

    provider = _parse_provider_config(provider_section, base_dir=config_base_dir)
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
    history = _parse_history_config(raw.get("history"), base_dir=config_base_dir)
    hotkey = HotkeyConfig(
        key=str(hotkey_section.get("key", "space")),
        modifiers=tuple(str(item) for item in modifiers),
    )
    correction = _parse_correction_config(
        raw.get("correction"),
        legacy_raw=raw.get("cleanup"),
        base_dir=config_base_dir,
        default_history_path=history.path,
    )
    return AppConfig(provider=provider, audio=audio, hotkey=hotkey, history=history, correction=correction)


def _parse_provider_config(raw: object, *, base_dir: Path) -> ProviderConfig:
    if not isinstance(raw, dict):
        raise ValueError("provider section must be a table")
    name = str(raw.get("name", "listenhub"))
    normalized_name = name.lower()
    model = _optional_str(raw.get("model"))
    api_key = _optional_str(raw.get("api_key")) or ""

    if normalized_name in {"openai", "gemini"}:
        if not api_key or not model:
            raise ValueError("provider.api_key and provider.model are required for remote providers")
    elif normalized_name == "listenhub":
        model = model or "sensevoice"
    elif not model:
        raise ValueError("provider.model is required")

    return ProviderConfig(
        name=name,
        model=model or "",
        api_key=api_key,
        endpoint=_optional_str(raw.get("endpoint")),
        timeout_seconds=float(raw.get("timeout_seconds", 30.0)),
        dictionary_path=_resolve_optional_path(raw.get("dictionary_path", "dictionary.txt"), base_dir),
    )

def _parse_history_config(raw: object, *, base_dir: Path) -> HistoryConfig:
    if raw is None:
        return HistoryConfig(path=(base_dir / "history.db").resolve())
    if not isinstance(raw, dict):
        raise ValueError("history section must be a table")
    return HistoryConfig(
        path=_resolve_optional_path(raw.get("path", "history.db"), base_dir) or (base_dir / "history.db").resolve()
    )


def _parse_correction_config(
    raw: object,
    *,
    legacy_raw: object,
    base_dir: Path,
    default_history_path: Path,
) -> CorrectionConfig | None:
    if raw is not None and legacy_raw is not None:
        raise ValueError("use only one of correction or cleanup sections")
    source = raw if raw is not None else legacy_raw
    section_name = "correction" if raw is not None else "cleanup"
    if source is None:
        return None
    if not isinstance(source, dict):
        raise ValueError(f"{section_name} section must be a table")

    enabled = bool(source.get("enabled", False))
    if not enabled:
        return CorrectionConfig(enabled=False)

    base_url = _required_str(source.get("base_url"), f"{section_name}.base_url")
    api_key = _required_str(source.get("api_key"), f"{section_name}.api_key")
    model = _required_str(source.get("model"), f"{section_name}.model")
    return CorrectionConfig(
        enabled=True,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=float(source.get("timeout_seconds", 8.0)),
        dictionary_path=_resolve_optional_path(source.get("dictionary_path", "dictionary.txt"), base_dir),
        history_path=_resolve_optional_path(source.get("history_path"), base_dir) or default_history_path,
        system_prompt_path=_resolve_optional_path(source.get("system_prompt_path", "system_prompt.txt"), base_dir),
        user_prompt_path=_resolve_optional_path(source.get("user_prompt_path", "user_prompt.txt"), base_dir),
    )


CleanupConfig = CorrectionConfig


def _optional_str(value: object) -> str | None:
    return None if value in (None, "") else str(value)


def _optional_int(value: object) -> int | None:
    return None if value in (None, "") else int(value)


def _required_str(value: object, field_name: str) -> str:
    if value in (None, ""):
        raise ValueError(f"{field_name} is required when correction is enabled")
    return str(value)


def _required_value(value: object, field_name: str) -> str:
    if value in (None, ""):
        raise ValueError(f"{field_name} is required")
    return str(value)


def _resolve_optional_path(value: object, base_dir: Path) -> Path | None:
    text = _optional_str(value)
    if text is None:
        return None
    path = Path(text).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()
