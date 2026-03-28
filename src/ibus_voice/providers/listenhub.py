from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic
from typing import Protocol

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.types import ProviderFailure, TranscriptResult


DEFAULT_BINARY = "coli"
DEFAULT_MODEL = "sensevoice"
BUNDLED_BINARY_RELATIVE_PATH = Path("bin") / DEFAULT_BINARY


def bundled_coli_binary_path() -> str | None:
    bundled_path = Path(__file__).resolve().parents[3] / BUNDLED_BINARY_RELATIVE_PATH
    if bundled_path.is_file() and os.access(bundled_path, os.X_OK):
        return str(bundled_path)
    return None


def find_coli_binary() -> str | None:
    bundled_path = bundled_coli_binary_path()
    if bundled_path is not None:
        return bundled_path
    return shutil.which(DEFAULT_BINARY)


def ensure_coli_available() -> str:
    binary_path = find_coli_binary()
    if binary_path is None:
        raise ProviderFailure(
            "listenhub",
            "coli is not bundled and not on PATH; install @marswave/coli first",
        )
    return binary_path


class CommandRunner(Protocol):
    def run(self, command: list[str], timeout: float) -> tuple[int, str, str]: ...


@dataclass(slots=True)
class SubprocessRunner:
    def run(self, command: list[str], timeout: float) -> tuple[int, str, str]:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return completed.returncode, completed.stdout, completed.stderr


@dataclass(slots=True)
class ListenHubProvider:
    config: ProviderConfig
    runner: CommandRunner
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
            runner=SubprocessRunner(),
        )

    def transcribe(self, audio: AudioPayload) -> TranscriptResult:
        if not audio.data:
            raise ProviderFailure(self.name, "audio payload is empty")
        started = monotonic()
        binary_path = ensure_coli_available()
        with TemporaryDirectory(prefix="ibus-voice-listenhub-") as tmpdir:
            audio_path = Path(tmpdir) / audio.filename
            audio_path.write_bytes(audio.data)
            command = [binary_path, "asr", "--model", self.config.model, str(audio_path)]
            try:
                returncode, stdout, stderr = self.runner.run(command, timeout=self.config.timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                raise ProviderFailure(self.name, f"transcription timed out after {self.config.timeout_seconds}s", retryable=True) from exc
            except FileNotFoundError as exc:
                raise ProviderFailure(
                    self.name,
                    "coli could not be executed; ensure the bundled CLI is present or install @marswave/coli",
                    retryable=True,
                ) from exc
            except Exception as exc:  # pragma: no cover - exercised via mocked failures
                raise ProviderFailure(self.name, str(exc), retryable=True) from exc

        if returncode != 0:
            detail = stderr.strip() or stdout.strip() or f"coli exited with status {returncode}"
            raise ProviderFailure(self.name, detail, retryable=True)

        text = stdout.strip()
        if not text:
            raise ProviderFailure(self.name, "provider returned an empty transcript")
        return TranscriptResult(
            text=text,
            provider=self.name,
            latency_ms=int((monotonic() - started) * 1000),
            metadata={"model": self.config.model, "command": "coli asr"},
        )
