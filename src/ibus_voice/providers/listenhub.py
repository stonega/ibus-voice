from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from time import monotonic
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from ibus_voice.audio import AudioPayload
from ibus_voice.config import AudioConfig
from ibus_voice.config import ProviderConfig
from ibus_voice.local_asr import (
    initialize_local_asr,
    LocalAsrError,
    MODEL_NAME as DEFAULT_MODEL,
    normalize_model_name,
    runtime_status,
    transcribe_pcm16le_bytes,
    transcribe_wav_file_with_timeout,
)
from ibus_voice.types import ProviderFailure, TranscriptResult


STREAMING_PARTIAL_INTERVAL_SECONDS = 0.35
STREAMING_PARTIAL_MIN_PCM_BYTES = 4096


@dataclass(slots=True)
class _StreamingSession:
    audio_config: AudioConfig
    on_partial_result: Callable[[str], None]
    pcm_bytes: bytearray
    lock: Lock
    executor: ThreadPoolExecutor
    started_at: float
    last_submitted_at: float = 0.0
    future: Future[str] | None = None
    closed: bool = False


def _decode_partial(model_name: str, audio_config: AudioConfig, audio_bytes: bytes) -> str:
    return transcribe_pcm16le_bytes(
        audio_bytes,
        audio_config.sample_rate,
        model_name,
        channels=audio_config.channels,
        sample_width=audio_config.sample_width,
    )


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
        model = normalize_model_name(config.model or DEFAULT_MODEL)
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

    def initialize(self) -> None:
        try:
            initialize_local_asr(self.config.model)
        except LocalAsrError as exc:
            raise ProviderFailure(self.name, str(exc), retryable=True) from exc

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
            metadata={"model": self.config.model, "engine": "local-qwen3-asr"},
        )

    def start_stream(self, audio_config: AudioConfig, on_partial_result) -> _StreamingSession:
        return _StreamingSession(
            audio_config=audio_config,
            on_partial_result=on_partial_result,
            pcm_bytes=bytearray(),
            lock=Lock(),
            executor=ThreadPoolExecutor(max_workers=1, thread_name_prefix="ibus-voice-listenhub"),
            started_at=monotonic(),
        )

    def push_audio_chunk(self, session: _StreamingSession, chunk: bytes) -> None:
        with session.lock:
            if session.closed:
                return
            session.pcm_bytes.extend(chunk)
            if len(session.pcm_bytes) < STREAMING_PARTIAL_MIN_PCM_BYTES:
                return
            if session.future is not None and not session.future.done():
                return
            now = monotonic()
            if now - session.last_submitted_at < STREAMING_PARTIAL_INTERVAL_SECONDS:
                return
            snapshot = bytes(session.pcm_bytes)
            session.last_submitted_at = now
            session.future = session.executor.submit(_decode_partial, self.config.model, session.audio_config, snapshot)
        session.future.add_done_callback(lambda future: self._publish_partial_result(session, future))

    def finish_stream(self, session: _StreamingSession, audio: AudioPayload) -> TranscriptResult:
        del audio
        text = ""
        with session.lock:
            session.closed = True
            future = session.future
            pcm_bytes = bytes(session.pcm_bytes)
        if future is not None:
            try:
                text = future.result(timeout=min(self.config.timeout_seconds, 2.0))
            except Exception:
                text = ""
            else:
                text = text.strip()
                if text:
                    session.on_partial_result(text)
        try:
            if not text:
                text = _decode_partial(self.config.model, session.audio_config, pcm_bytes).strip()
        except LocalAsrError as exc:
            raise ProviderFailure(self.name, str(exc), retryable=True) from exc
        except Exception as exc:  # pragma: no cover - unexpected runtime failures
            raise ProviderFailure(self.name, str(exc), retryable=True) from exc
        finally:
            session.executor.shutdown(wait=False, cancel_futures=False)

        if not text:
            raise ProviderFailure(self.name, "provider returned an empty transcript")
        return TranscriptResult(
            text=text,
            provider=self.name,
            latency_ms=int((monotonic() - session.started_at) * 1000),
            metadata={"model": self.config.model, "engine": "local-qwen3-asr"},
        )

    def cancel_stream(self, session: _StreamingSession) -> None:
        with session.lock:
            session.closed = True
            future = session.future
        if future is not None:
            future.cancel()
        session.executor.shutdown(wait=False, cancel_futures=True)

    def _publish_partial_result(self, session: _StreamingSession, future: Future[str]) -> None:
        try:
            text = future.result().strip()
        except Exception:
            return
        if not text:
            return
        with session.lock:
            if session.closed:
                return
        session.on_partial_result(text)
