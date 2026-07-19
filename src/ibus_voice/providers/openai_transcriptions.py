from __future__ import annotations

from dataclasses import dataclass
from socket import timeout as SocketTimeout
from time import monotonic
from urllib.error import URLError

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.local_asr import MODEL_NAME as DEFAULT_FALLBACK_MODEL
from ibus_voice.providers.base import validate_transcript_text
from ibus_voice.providers.http import HttpTransport, UrllibTransport
from ibus_voice.providers.listenhub import ListenHubProvider
from ibus_voice.providers.openai import _build_transcription_prompt
from ibus_voice.types import ProviderFailure, TranscriptResult


@dataclass(slots=True)
class OpenAITranscriptionsProvider:
    config: ProviderConfig
    transport: HttpTransport
    fallback_provider: ListenHubProvider
    name: str = "openai_transcriptions"

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "OpenAITranscriptionsProvider":
        return cls(
            config=config,
            transport=UrllibTransport(),
            fallback_provider=ListenHubProvider.from_config(
                ProviderConfig(
                    name="listenhub",
                    model=DEFAULT_FALLBACK_MODEL,
                    timeout_seconds=config.timeout_seconds,
                    dictionary_path=config.dictionary_path,
                )
            ),
        )

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
        headers: dict[str, str] = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        try:
            response = self.transport.post_multipart(
                self.config.endpoint or "",
                headers,
                fields,
                {"file": (audio.filename, audio.mime_type, audio.data)},
                self.config.timeout_seconds,
            )
        except Exception as exc:  # pragma: no branch - timeout/failure split is unit tested
            if _is_timeout_error(exc):
                return self._transcribe_with_fallback(audio, started)
            raise ProviderFailure(self.name, str(exc), retryable=True) from exc

        text = validate_transcript_text(self.name, str(response.get("text", "")))
        return TranscriptResult(
            text=text,
            provider=self.name,
            latency_ms=int((monotonic() - started) * 1000),
            metadata={
                "model": self.config.model,
                "endpoint": self.config.endpoint or "",
                "fallback_used": False,
            },
        )

    def _transcribe_with_fallback(self, audio: AudioPayload, started: float) -> TranscriptResult:
        fallback_result = self.fallback_provider.transcribe(audio)
        return TranscriptResult(
            text=fallback_result.text,
            provider=self.name,
            latency_ms=int((monotonic() - started) * 1000),
            metadata={
                **fallback_result.metadata,
                "model": self.config.model,
                "endpoint": self.config.endpoint or "",
                "fallback_used": True,
                "fallback_provider": fallback_result.provider,
            },
        )


def _is_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, SocketTimeout)):
        return True
    if isinstance(exc, URLError):
        reason = exc.reason
        return isinstance(reason, (TimeoutError, SocketTimeout))
    return "timed out" in str(exc).lower()
