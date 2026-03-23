from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ibus_voice.audio import AudioPayload, Recorder
from ibus_voice.types import CleanupFailure, ProviderFailure, TranscriptResult


class Committer(Protocol):
    def commit_text(self, text: str) -> None: ...


class SpeechProvider(Protocol):
    def transcribe(self, audio: AudioPayload) -> TranscriptResult: ...


class TextCleaner(Protocol):
    def clean(self, transcript: str) -> str: ...


@dataclass(slots=True)
class VoiceEngine:
    recorder: Recorder
    provider: SpeechProvider
    committer: Committer
    cleaner: TextCleaner
    state: str = "idle"
    last_error: str | None = None
    last_warning: str | None = None
    last_result: TranscriptResult | None = None
    last_raw_text: str | None = None
    events: list[str] = field(default_factory=list)

    def handle_press(self) -> None:
        if self.state != "idle":
            self.events.append("ignored_press")
            return
        self.last_error = None
        self.last_warning = None
        self.last_result = None
        self.last_raw_text = None
        self.recorder.start()
        self.state = "recording"
        self.events.append("recording_started")

    def handle_release(self) -> None:
        if self.state != "recording":
            self.events.append("ignored_release")
            return
        audio = self.recorder.stop()
        self.state = "transcribing"
        self.events.append("recording_stopped")
        try:
            result = self.provider.transcribe(audio)
        except ProviderFailure as exc:
            self.last_error = str(exc)
            self.state = "error"
            self.events.append("transcription_failed")
            self._reset_after_error()
            return
        if result.text.strip():
            self.last_raw_text = result.text
            final_text = result.text
            try:
                final_text = self.cleaner.clean(result.text)
            except CleanupFailure as exc:
                self.last_warning = str(exc)
                self.events.append("cleanup_failed_fallback")
            self.committer.commit_text(final_text)
            self.last_result = TranscriptResult(
                text=final_text,
                provider=result.provider,
                latency_ms=result.latency_ms,
                metadata={**result.metadata, "raw_text": result.text},
            )
            self.events.append("text_committed")
        self.state = "idle"
        self.events.append("ready")

    def _reset_after_error(self) -> None:
        self.state = "idle"
        self.events.append("ready")
