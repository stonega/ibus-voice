from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from time import monotonic

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.providers.http import HttpTransport, UrllibTransport
from ibus_voice.types import ProviderFailure, TranscriptResult


DEFAULT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@dataclass(slots=True)
class GeminiProvider:
    config: ProviderConfig
    transport: HttpTransport
    name: str = "gemini"

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "GeminiProvider":
        return cls(config=config, transport=UrllibTransport())

    def transcribe(self, audio: AudioPayload) -> TranscriptResult:
        if not audio.data:
            raise ProviderFailure(self.name, "audio payload is empty")
        started = monotonic()
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Transcribe this audio and return plain text only."},
                        {
                            "inlineData": {
                                "mimeType": audio.mime_type,
                                "data": b64encode(audio.data).decode("ascii"),
                            }
                        },
                    ]
                }
            ]
        }
        headers = {"x-goog-api-key": self.config.api_key}
        url = self.config.endpoint or DEFAULT_ENDPOINT.format(model=self.config.model)
        try:
            response = self.transport.post_json(url, headers, payload, self.config.timeout_seconds)
        except Exception as exc:  # pragma: no cover - exercised via mocked failures
            raise ProviderFailure(self.name, str(exc), retryable=True) from exc
        text = _extract_text(response).strip()
        if not text:
            raise ProviderFailure(self.name, "provider returned an empty transcript")
        return TranscriptResult(
            text=text,
            provider=self.name,
            latency_ms=int((monotonic() - started) * 1000),
            metadata={"model": self.config.model},
        )


def _extract_text(response: dict) -> str:
    candidates = response.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if text:
                return str(text)
    return ""
