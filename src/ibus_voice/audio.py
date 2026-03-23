from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Protocol
import wave

from .config import AudioConfig


@dataclass(slots=True)
class AudioPayload:
    data: bytes
    mime_type: str
    filename: str


class Recorder(Protocol):
    def start(self) -> None: ...

    def stop(self) -> AudioPayload: ...


@dataclass(slots=True)
class MemoryRecorder:
    config: AudioConfig = field(default_factory=AudioConfig)
    chunks: list[bytes] = field(default_factory=list)
    recording: bool = False

    def start(self) -> None:
        self.recording = True
        self.chunks.clear()

    def push(self, chunk: bytes) -> None:
        if not self.recording:
            raise RuntimeError("recorder is not active")
        self.chunks.append(chunk)

    def stop(self) -> AudioPayload:
        if not self.recording:
            return AudioPayload(data=b"", mime_type="audio/wav", filename="speech.wav")
        self.recording = False
        raw_audio = b"".join(self.chunks)
        return AudioPayload(
            data=pcm_to_wav_bytes(raw_audio, self.config),
            mime_type="audio/wav",
            filename="speech.wav",
        )


class PyAudioRecorder:
    def __init__(self, config: AudioConfig) -> None:
        self._config = config
        self._audio = None
        self._stream = None
        self._frames: list[bytes] = []

    def start(self) -> None:
        import pyaudio

        self._frames = []
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            format=self._audio.get_format_from_width(self._config.sample_width),
            channels=self._config.channels,
            rate=self._config.sample_rate,
            input=True,
            input_device_index=self._config.input_device_index,
            frames_per_buffer=self._config.chunk_size,
            stream_callback=self._on_audio_chunk,
        )
        self._stream.start_stream()

    def stop(self) -> AudioPayload:
        if self._stream is None:
            return AudioPayload(data=b"", mime_type="audio/wav", filename="speech.wav")
        self._stream.stop_stream()
        self._stream.close()
        self._stream = None
        if self._audio is not None:
            self._audio.terminate()
            self._audio = None
        raw_audio = b"".join(self._frames)
        return AudioPayload(
            data=pcm_to_wav_bytes(raw_audio, self._config),
            mime_type="audio/wav",
            filename="speech.wav",
        )

    def _on_audio_chunk(self, in_data, frame_count, time_info, status_flags):
        del frame_count, time_info, status_flags
        self._frames.append(in_data)
        import pyaudio

        return (None, pyaudio.paContinue)


def pcm_to_wav_bytes(audio_bytes: bytes, config: AudioConfig) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(config.channels)
        wav_file.setsampwidth(config.sample_width)
        wav_file.setframerate(config.sample_rate)
        wav_file.writeframes(audio_bytes)
    return buffer.getvalue()
