from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
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
        text = str(response.get("text", "")).strip()
        if not text:
            raise ProviderFailure(self.name, "provider returned an empty transcript")
        return TranscriptResult(
            text=text,
            provider=self.name,
            latency_ms=int((monotonic() - started) * 1000),
            metadata={"model": self.config.model},
        )
