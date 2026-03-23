from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ibus_voice.cli import main
from ibus_voice.history import SQLiteSessionHistory
from ibus_voice.types import TranscriptResult


class CLITests(unittest.TestCase):
    def test_history_command_prints_completed_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.db"
            history = SQLiteSessionHistory(history_path)
            history.save_completed_session(
                TranscriptResult(text="Hello world.", provider="openai", latency_ms=150),
                raw_text="hello world",
                warning=None,
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["--history", "--history-path", str(history_path)])

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("provider: openai", rendered)
        self.assertIn("final: Hello world.", rendered)
        self.assertIn("raw: hello world", rendered)
        self.assertIn("latency_ms: 150", rendered)

    def test_history_command_prints_empty_message_when_no_records_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.db"
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["--history", "--history-path", str(history_path)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue().strip(), "No history records found.")

    def test_history_command_reports_errors_cleanly(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("ibus_voice.cli.SQLiteSessionHistory", side_effect=RuntimeError("boom")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["--history"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("failed to read history:", stderr.getvalue())
        self.assertIn("boom", stderr.getvalue())

    def test_history_command_uses_configured_history_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            history_path = temp_path / "state" / "history.db"
            history = SQLiteSessionHistory(history_path)
            history.save_completed_session(
                TranscriptResult(text="Configured path.", provider="openai"),
                raw_text="configured path",
                warning=None,
            )
            config_path = temp_path / "config.toml"
            config_path.write_text(
                """
[history]
path = "state/history.db"
""".strip(),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["--history", "--config", str(config_path)])

        self.assertEqual(exit_code, 0)
        self.assertIn("Configured path.", output.getvalue())
