from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.providers.base import validate_transcript_text
from ibus_voice.providers.http import HttpTransport, UrllibTransport
from ibus_voice.types import ProviderFailure, TranscriptResult


DEFAULT_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"


@dataclass(slots=True)
class OpenAIProvider:
    config: ProviderConfig
    transport: HttpTransport
    name: str = "openai"

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "OpenAIProvider":
        return cls(config=config, transport=UrllibTransport())

    def transcribe(self, audio: AudioPayload) -> TranscriptResult:
        if not audio.data:
            raise ProviderFailure(self.name, "audio payload is empty")
        started = monotonic()
        fields = {
            "model": self.config.model,
            "response_format": "json",
        }
        prompt = _build_transcription_prompt(self.config.dictionary_path)
        if prompt:
            fields["prompt"] = prompt
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        url = self.config.endpoint or DEFAULT_ENDPOINT
        try:
            response = self.transport.post_multipart(
                url,
                headers,
                fields,
                {"file": (audio.filename, audio.mime_type, audio.data)},
                self.config.timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover - exercised via mocked failures
            raise ProviderFailure(self.name, str(exc), retryable=True) from exc
        text = validate_transcript_text(self.name, str(response.get("text", "")))
        return TranscriptResult(
            text=text,
            provider=self.name,
            latency_ms=int((monotonic() - started) * 1000),
            metadata={"model": self.config.model},
        )


def _build_transcription_prompt(dictionary_path) -> str:
    prompt = (
        "Transcribe this audio and return plain text only.\n"
        "Keep the words in the language or languages actually spoken.\n"
        "Do not translate, summarize, or answer.\n"
        "Preserve mixed-language phrasing, code-switching, names, and technical terms."
    )
    if dictionary_path is None:
        return prompt
    try:
        dictionary = dictionary_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return prompt
    if not dictionary:
        return prompt
    return f"{prompt}\nPrefer these canonical terms when transcribing:\n{dictionary}"
