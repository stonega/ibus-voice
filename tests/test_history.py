from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ibus_voice.history import SQLiteSessionHistory, format_completed_sessions
from ibus_voice.types import TranscriptResult


class SQLiteSessionHistoryTests(unittest.TestCase):
    def test_save_completed_session_persists_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.db"
            history = SQLiteSessionHistory(history_path)

            history.save_completed_session(
                TranscriptResult(
                    text="Hello world.",
                    provider="openai",
                    latency_ms=1200,
                    metadata={"raw_text": "hello world", "language": "en"},
                ),
                raw_text="hello world",
                warning="correction: timeout",
            )

            with sqlite3.connect(history_path) as connection:
                row = connection.execute(
                    """
                    SELECT provider, final_text, raw_text, latency_ms, warning, metadata_json
                    FROM sessions
                    """
                ).fetchone()

        assert row is not None
        self.assertEqual(row[0], "openai")
        self.assertEqual(row[1], "Hello world.")
        self.assertEqual(row[2], "hello world")
        self.assertEqual(row[3], 1200)
        self.assertEqual(row[4], "correction: timeout")
        self.assertEqual(
            json.loads(row[5]),
            {"language": "en", "raw_text": "hello world"},
        )

    def test_list_completed_sessions_returns_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.db"
            history = SQLiteSessionHistory(history_path)

            history.save_completed_session(
                TranscriptResult(text="first", provider="openai"),
                raw_text="first",
                warning=None,
            )
            history.save_completed_session(
                TranscriptResult(text="second", provider="gemini"),
                raw_text="second",
                warning="correction: timeout",
            )

            sessions = history.list_completed_sessions(limit=10)

        self.assertEqual([session.final_text for session in sessions], ["second", "first"])
        self.assertEqual(sessions[0].warning, "correction: timeout")

    def test_format_completed_sessions_renders_human_readable_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.db"
            history = SQLiteSessionHistory(history_path)
            history.save_completed_session(
                TranscriptResult(text="Hello world.", provider="openai", latency_ms=1200),
                raw_text="hello world",
                warning="correction: timeout",
            )

            rendered = format_completed_sessions(history.list_completed_sessions(limit=10))

        self.assertIn("provider: openai", rendered)
        self.assertIn("final: Hello world.", rendered)
        self.assertIn("raw: hello world", rendered)
        self.assertIn("latency_ms: 1200", rendered)
        self.assertIn("warning: correction: timeout", rendered)

    def test_format_completed_sessions_renders_correction_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.db"
            history = SQLiteSessionHistory(history_path)
            history.save_completed_session(
                TranscriptResult(
                    text="Hello world.",
                    provider="openai",
                    metadata={"correction_usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}},
                ),
                raw_text="hello world",
                warning=None,
            )

            rendered = format_completed_sessions(history.list_completed_sessions(limit=10))

        self.assertIn("correction_usage: prompt=10 completion=4 total=14", rendered)
