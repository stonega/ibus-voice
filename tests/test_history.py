from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ibus_voice.history import SQLiteSessionHistory
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
                warning="cleanup: timeout",
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
        self.assertEqual(row[4], "cleanup: timeout")
        self.assertEqual(
            json.loads(row[5]),
            {"language": "en", "raw_text": "hello world"},
        )
