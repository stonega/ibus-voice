from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ibus_voice.config import CorrectionConfig
from ibus_voice.history import render_recent_history
from ibus_voice.providers.http import HttpTransport, UrllibTransport
from ibus_voice.types import CorrectionFailure


OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"


class TextCorrector(Protocol):
    def correct(self, transcript: str) -> str: ...


@dataclass(slots=True)
class PassThroughCorrector:
    def correct(self, transcript: str) -> str:
        return transcript

    def get_metadata(self) -> dict[str, object]:
        return {}


@dataclass(slots=True)
class OpenAICompatibleCorrector:
    config: CorrectionConfig
    transport: HttpTransport
    name: str = "correction"
    last_metadata: dict[str, object] | None = None

    @classmethod
    def from_config(cls, config: CorrectionConfig) -> "OpenAICompatibleCorrector":
        return cls(config=config, transport=UrllibTransport())

    def correct(self, transcript: str) -> str:
        self.last_metadata = None
        if not transcript.strip():
            return transcript
        system_prompt = _read_prompt_file(self.config.system_prompt_path)
        user_prompt = _render_user_prompt(self.config, transcript)
        payload = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        url = _build_chat_completions_url(self.config.base_url)
        try:
            response = self.transport.post_json(url, headers, payload, self.config.timeout_seconds)
        except Exception as exc:  # pragma: no cover - exercised via mocked failures
            raise CorrectionFailure(self.name, str(exc), retryable=True) from exc
        text = _extract_message_text(response).strip()
        if not text:
            raise CorrectionFailure(self.name, "correction returned empty text")
        self.last_metadata = _extract_correction_metadata(response)
        return text

    def get_metadata(self) -> dict[str, object]:
        return dict(self.last_metadata or {})


def build_corrector(config: CorrectionConfig | None) -> TextCorrector:
    if config is None or not config.enabled:
        return PassThroughCorrector()
    return OpenAICompatibleCorrector.from_config(config)


def get_corrector_metadata(corrector: TextCorrector) -> dict[str, object]:
    getter = getattr(corrector, "get_metadata", None)
    if not callable(getter):
        return {}
    metadata = getter()
    if not isinstance(metadata, dict):
        return {}
    return metadata


def _build_chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{OPENAI_CHAT_COMPLETIONS_PATH}"


def _extract_message_text(response: dict) -> str:
    for candidate in response.get("choices", []):
        message = candidate.get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content:
            return content
        if isinstance(content, list):
            parts = [str(part.get("text", "")) for part in content if isinstance(part, dict)]
            joined = "".join(parts).strip()
            if joined:
                return joined
    return ""


def _extract_correction_metadata(response: dict) -> dict[str, object]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return {}
    normalized_usage = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            normalized_usage[key] = value
    if not normalized_usage:
        return {}
    return {"correction_usage": normalized_usage}


def _render_user_prompt(config: CorrectionConfig, transcript: str) -> str:
    template = _read_prompt_file(config.user_prompt_path)
    dictionary = _read_optional_text_file(config.dictionary_path)
    history = render_recent_history(config.history_path)
    try:
        return template.format(
            transcript=transcript,
            dictionary=dictionary,
            history=history,
        )
    except KeyError as exc:
        raise CorrectionFailure("correction", f"unsupported prompt placeholder: {exc.args[0]}") from exc


def _read_prompt_file(path: Path | None) -> str:
    if path is None:
        raise CorrectionFailure("correction", "prompt path is not configured")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CorrectionFailure("correction", f"failed to read prompt file: {path}") from exc


def _read_optional_text_file(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise CorrectionFailure("correction", f"failed to read prompt file: {path}") from exc
