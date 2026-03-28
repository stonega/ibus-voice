from __future__ import annotations

from typing import Protocol

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.types import ProviderFailure, TranscriptResult


class SpeechProvider(Protocol):
    name: str

    def transcribe(self, audio: AudioPayload) -> TranscriptResult: ...

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "SpeechProvider": ...


_PROMPT_ECHO_MARKERS = (
    "transcribe this audio and return plain text only",
    "return plain text only",
    "let's transcribe this audio",
)

_REFUSAL_MARKERS = (
    "unable to process audio",
    "unable to transcribe",
    "cannot process audio",
    "cannot transcribe",
    "can't process audio",
    "can't transcribe",
)


def validate_transcript_text(provider_name: str, text: str) -> str:
    normalized = text.strip()
    if not normalized:
        raise ProviderFailure(provider_name, "provider returned an empty transcript")

    collapsed = " ".join(normalized.lower().split())
    if any(marker in collapsed for marker in _PROMPT_ECHO_MARKERS):
        raise ProviderFailure(
            provider_name,
            f"provider returned non-transcript content [non_transcript_response]: {normalized[:160]}",
        )
    if any(marker in collapsed for marker in _REFUSAL_MARKERS):
        raise ProviderFailure(
            provider_name,
            f"provider could not process the audio [audio_not_processed]: {normalized[:160]}",
            retryable=True,
        )
    return normalized
