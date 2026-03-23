from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ibus_voice.config import CleanupConfig
from ibus_voice.providers.http import HttpTransport, UrllibTransport
from ibus_voice.types import CleanupFailure


OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"


class TextCleaner(Protocol):
    def clean(self, transcript: str) -> str: ...


@dataclass(slots=True)
class PassThroughCleaner:
    def clean(self, transcript: str) -> str:
        return transcript


@dataclass(slots=True)
class OpenAICompatibleCleaner:
    config: CleanupConfig
    transport: HttpTransport
    name: str = "cleanup"

    @classmethod
    def from_config(cls, config: CleanupConfig) -> "OpenAICompatibleCleaner":
        return cls(config=config, transport=UrllibTransport())

    def clean(self, transcript: str) -> str:
        if not transcript.strip():
            return transcript
        system_prompt = _read_prompt_file(self.config.system_prompt_path)
        user_prompt = _render_user_prompt(self.config.user_prompt_path, transcript)
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
            raise CleanupFailure(self.name, str(exc), retryable=True) from exc
        text = _extract_message_text(response).strip()
        if not text:
            raise CleanupFailure(self.name, "cleanup returned empty text")
        return text


def build_cleaner(config: CleanupConfig | None) -> TextCleaner:
    if config is None or not config.enabled:
        return PassThroughCleaner()
    return OpenAICompatibleCleaner.from_config(config)


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


def _render_user_prompt(path: Path | None, transcript: str) -> str:
    template = _read_prompt_file(path)
    try:
        return template.format(transcript=transcript)
    except KeyError as exc:
        raise CleanupFailure("cleanup", f"unsupported prompt placeholder: {exc.args[0]}") from exc


def _read_prompt_file(path: Path | None) -> str:
    if path is None:
        raise CleanupFailure("cleanup", "prompt path is not configured")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CleanupFailure("cleanup", f"failed to read prompt file: {path}") from exc
