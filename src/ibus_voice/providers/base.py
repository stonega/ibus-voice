from __future__ import annotations

from typing import Protocol

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.types import TranscriptResult


class SpeechProvider(Protocol):
    name: str

    def transcribe(self, audio: AudioPayload) -> TranscriptResult: ...

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "SpeechProvider": ...
