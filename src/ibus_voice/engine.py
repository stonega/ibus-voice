from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from ibus_voice.audio import AudioPayload, Recorder
from ibus_voice.config import AudioConfig
from ibus_voice.correction import get_corrector_metadata
from ibus_voice.history import SessionHistory
from ibus_voice.types import CorrectionFailure, ProviderFailure, TranscriptResult


class Committer(Protocol):
    def commit_text(self, text: str) -> None: ...

    def update_preedit(self, text: str) -> None: ...

    def hide_preedit(self) -> None: ...


class SpeechProvider(Protocol):
    def transcribe(self, audio: AudioPayload) -> TranscriptResult: ...


class TextCorrector(Protocol):
    def correct(self, transcript: str) -> str: ...


class StreamingSpeechProvider(Protocol):
    def start_stream(self, audio_config: AudioConfig, on_partial_result: Callable[[str], None]) -> object: ...

    def push_audio_chunk(self, session: object, chunk: bytes) -> None: ...

    def finish_stream(self, session: object, audio: AudioPayload) -> TranscriptResult: ...

    def cancel_stream(self, session: object) -> None: ...


@dataclass(slots=True)
class VoiceEngine:
    recorder: Recorder
    provider: SpeechProvider
    committer: Committer
    corrector: TextCorrector
    history: SessionHistory | None = None
    state: str = "idle"
    last_error: str | None = None
    last_warning: str | None = None
    last_result: TranscriptResult | None = None
    last_raw_text: str | None = None
    last_partial_text: str | None = None
    events: list[str] = field(default_factory=list)
    _stream_session: object | None = field(default=None, init=False, repr=False)

    def handle_press(self) -> None:
        if self.state != "idle":
            self.events.append("ignored_press")
            return
        self.last_error = None
        self.last_warning = None
        self.last_result = None
        self.last_raw_text = None
        self.last_partial_text = None
        self._hide_preedit()
        self._attach_streaming_session()
        self.recorder.start()
        self.state = "recording"
        self.events.append("recording_started")

    def handle_release(self) -> None:
        if self.state != "recording":
            self.events.append("ignored_release")
            return
        audio = self.recorder.stop()
        self._detach_streaming_session()
        self.state = "transcribing"
        self.events.append("recording_stopped")
        try:
            result = self._transcribe(audio)
        except ProviderFailure as exc:
            self.last_error = str(exc)
            self.state = "error"
            self.events.append("transcription_failed")
            self._hide_preedit()
            self._reset_after_error()
            return
        if result.text.strip():
            self.last_raw_text = result.text
            final_text = result.text
            correction_metadata: dict[str, object] = {}
            try:
                final_text = self.corrector.correct(result.text)
                correction_metadata = get_corrector_metadata(self.corrector)
            except CorrectionFailure as exc:
                self.last_warning = str(exc)
                self.events.append("correction_failed_fallback")
            self._hide_preedit()
            self.committer.commit_text(final_text)
            self.last_result = TranscriptResult(
                text=final_text,
                provider=result.provider,
                latency_ms=result.latency_ms,
                metadata={**result.metadata, **correction_metadata, "raw_text": result.text},
            )
            self._save_history(self.last_result, raw_text=result.text)
            self.events.append("text_committed")
        else:
            self._hide_preedit()
        self.state = "idle"
        self.events.append("ready")

    def _attach_streaming_session(self) -> None:
        start_stream = getattr(self.provider, "start_stream", None)
        push_audio_chunk = getattr(self.provider, "push_audio_chunk", None)
        set_chunk_callback = getattr(self.recorder, "set_chunk_callback", None)
        recorder_config = getattr(self.recorder, "config", None)
        if not callable(start_stream) or not callable(push_audio_chunk) or not callable(set_chunk_callback):
            return
        if recorder_config is None:
            return
        session = start_stream(recorder_config, self._handle_partial_result)
        self._stream_session = session
        set_chunk_callback(lambda chunk, active_session=session: push_audio_chunk(active_session, chunk))
        self.events.append("streaming_started")

    def _detach_streaming_session(self) -> None:
        set_chunk_callback = getattr(self.recorder, "set_chunk_callback", None)
        if callable(set_chunk_callback):
            set_chunk_callback(None)

    def _transcribe(self, audio: AudioPayload) -> TranscriptResult:
        if self._stream_session is None:
            return self.provider.transcribe(audio)

        finish_stream = getattr(self.provider, "finish_stream", None)
        cancel_stream = getattr(self.provider, "cancel_stream", None)
        session = self._stream_session
        self._stream_session = None
        try:
            if callable(finish_stream):
                return finish_stream(session, audio)
            return self.provider.transcribe(audio)
        except Exception:
            if callable(cancel_stream):
                cancel_stream(session)
            raise

    def _handle_partial_result(self, text: str) -> None:
        normalized = text.strip()
        self.last_partial_text = normalized or None
        if normalized:
            self.committer.update_preedit(normalized)
            self.events.append("partial_result_updated")
            return
        self._hide_preedit()

    def _hide_preedit(self) -> None:
        self.last_partial_text = None
        self.committer.hide_preedit()

    def _reset_after_error(self) -> None:
        self.state = "idle"
        self.events.append("ready")

    def _save_history(self, result: TranscriptResult, *, raw_text: str) -> None:
        if self.history is None:
            return
        try:
            self.history.save_completed_session(
                result,
                raw_text=raw_text,
                warning=self.last_warning,
            )
        except Exception as exc:
            if self.last_warning is None:
                self.last_warning = f"history: {exc}"
            self.events.append("history_save_failed")
