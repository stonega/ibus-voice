from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TranscriptResult:
    text: str
    provider: str
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderFailure(Exception):
    provider: str
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.provider}: {self.message}"


@dataclass(slots=True)
class CleanupFailure(Exception):
    cleaner: str
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.cleaner}: {self.message}"


@dataclass(slots=True)
class CorrectionFailure(Exception):
    corrector: str
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.corrector}: {self.message}"
