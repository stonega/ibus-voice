from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.local_asr import (
    LocalAsrError,
    MODEL_NAME as DEFAULT_MODEL,
    runtime_status,
    transcribe_wav_file_with_timeout,
)
from ibus_voice.types import ProviderFailure, TranscriptResult


def ensure_local_provider_ready(model_name: str) -> str:
    try:
        return runtime_status(model_name)
    except LocalAsrError as exc:
        raise ProviderFailure("listenhub", str(exc)) from exc


@dataclass(slots=True)
class ListenHubProvider:
    config: ProviderConfig
    name: str = "listenhub"

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "ListenHubProvider":
        model = config.model or DEFAULT_MODEL
        return cls(
            config=ProviderConfig(
                name=config.name,
                api_key=config.api_key,
                model=model,
                endpoint=config.endpoint,
                timeout_seconds=config.timeout_seconds,
                dictionary_path=config.dictionary_path,
            ),
        )

    def readiness_status(self) -> str | None:
        return ensure_local_provider_ready(self.config.model)

    def transcribe(self, audio: AudioPayload) -> TranscriptResult:
        if not audio.data:
            raise ProviderFailure(self.name, "audio payload is empty")

        started = monotonic()
        try:
            with TemporaryDirectory(prefix="ibus-voice-listenhub-") as tmpdir:
                audio_path = Path(tmpdir) / audio.filename
                audio_path.write_bytes(audio.data)
                text = transcribe_wav_file_with_timeout(
                    audio_path,
                    self.config.model,
                    self.config.timeout_seconds,
                )
        except LocalAsrError as exc:
            raise ProviderFailure(self.name, str(exc), retryable=True) from exc
        except Exception as exc:  # pragma: no cover - unexpected runtime failures
            raise ProviderFailure(self.name, str(exc), retryable=True) from exc

        text = text.strip()
        if not text:
            raise ProviderFailure(self.name, "provider returned an empty transcript")

        return TranscriptResult(
            text=text,
            provider=self.name,
            latency_ms=int((monotonic() - started) * 1000),
            metadata={"model": self.config.model, "engine": "local-sensevoice"},
        )
