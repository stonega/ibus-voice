from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from json import JSONDecodeError
from typing import Protocol

from ibus_voice.config import DEFAULT_CONFIG_DIR
from ibus_voice.types import TranscriptResult


DEFAULT_HISTORY_PATH = DEFAULT_CONFIG_DIR / "history.db"


@dataclass(slots=True)
class HistorySession:
    created_at: str
    provider: str
    final_text: str
    raw_text: str
    latency_ms: int | None
    warning: str | None
    metadata_json: str


class SessionHistory(Protocol):
    def save_completed_session(
        self,
        result: TranscriptResult,
        *,
        raw_text: str,
        warning: str | None,
    ) -> None: ...


@dataclass(slots=True)
class SQLiteSessionHistory:
    path: Path = DEFAULT_HISTORY_PATH

    def __post_init__(self) -> None:
        self.path = Path(self.path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save_completed_session(
        self,
        result: TranscriptResult,
        *,
        raw_text: str,
        warning: str | None,
    ) -> None:
        metadata_json = json.dumps(result.metadata, ensure_ascii=True, sort_keys=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    provider,
                    final_text,
                    raw_text,
                    latency_ms,
                    warning,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    result.provider,
                    result.text,
                    raw_text,
                    result.latency_ms,
                    warning,
                    metadata_json,
                ),
            )
            connection.commit()

    def list_completed_sessions(self, *, limit: int = 20) -> list[HistorySession]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """
                SELECT created_at, provider, final_text, raw_text, latency_ms, warning, metadata_json
                FROM sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            HistorySession(
                created_at=row[0],
                provider=row[1],
                final_text=row[2],
                raw_text=row[3],
                latency_ms=row[4],
                warning=row[5],
                metadata_json=row[6],
            )
            for row in rows
        ]

    def _initialize(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    provider TEXT NOT NULL,
                    final_text TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    latency_ms INTEGER,
                    warning TEXT,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.commit()


def render_recent_history(path: Path | None, *, limit: int = 10) -> str:
    if path is None:
        return ""
    history_path = Path(path).expanduser()
    if not history_path.exists():
        return ""
    with sqlite3.connect(history_path) as connection:
        rows = connection.execute(
            """
            SELECT created_at, provider, final_text
            FROM sessions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    if not rows:
        return ""
    lines = []
    for created_at, provider, final_text in reversed(rows):
        lines.append(f"[{created_at}] {provider}: {final_text}")
    return "\n".join(lines)


def format_completed_sessions(sessions: list[HistorySession]) -> str:
    if not sessions:
        return "No history records found."
    blocks = []
    for session in sessions:
        lines = [
            f"time: {session.created_at}",
            f"provider: {session.provider}",
            f"final: {session.final_text}",
            f"raw: {session.raw_text}",
        ]
        if session.latency_ms is not None:
            lines.append(f"latency_ms: {session.latency_ms}")
        if session.warning:
            lines.append(f"warning: {session.warning}")
        usage = _extract_correction_usage(session.metadata_json)
        if usage:
            lines.append(
                "correction_usage: "
                f"prompt={usage.get('prompt_tokens', '?')} "
                f"completion={usage.get('completion_tokens', '?')} "
                f"total={usage.get('total_tokens', '?')}"
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _extract_correction_usage(metadata_json: str) -> dict[str, int]:
    try:
        metadata = json.loads(metadata_json)
    except JSONDecodeError:
        return {}
    if not isinstance(metadata, dict):
        return {}
    usage = metadata.get("correction_usage")
    if not isinstance(usage, dict):
        usage = metadata.get("cleanup_usage")
    if not isinstance(usage, dict):
        return {}
    normalized = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            normalized[key] = value
    return normalized
