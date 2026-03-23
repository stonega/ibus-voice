from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Protocol

from ibus_voice.config import DEFAULT_CONFIG_DIR
from ibus_voice.types import TranscriptResult


DEFAULT_HISTORY_PATH = DEFAULT_CONFIG_DIR / "history.db"


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
