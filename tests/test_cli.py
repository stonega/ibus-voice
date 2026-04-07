from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ibus_voice.cli import main
from ibus_voice.config import AppConfig, AudioConfig, CorrectionConfig, HistoryConfig, HotkeyConfig, ProviderConfig
from ibus_voice.history import SQLiteSessionHistory
from ibus_voice.metadata import ISSUES, REPOSITORY, VERSION
from ibus_voice.types import ProviderFailure, TranscriptResult


class CLITests(unittest.TestCase):
    def test_version_command_prints_version_creator_and_github_links(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--version"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            output.getvalue(),
            f"version: {VERSION}\ncreated by: Stone\nrepository: {REPOSITORY}\nissues: {ISSUES}\n",
        )

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

    def test_check_command_reports_listenhub_binary_path(self) -> None:
        config = AppConfig(
            provider=ProviderConfig(name="listenhub", model="sensevoice"),
            audio=AudioConfig(),
            hotkey=HotkeyConfig(),
            history=HistoryConfig(path=Path("/tmp/history.db")),
            correction=None,
        )
        output = io.StringIO()
        with patch("ibus_voice.cli.load_config", return_value=config), \
             patch("ibus_voice.cli.build_provider", return_value=object()), \
             patch("ibus_voice.cli.ensure_local_provider_ready", return_value="auto-download"):
            with redirect_stdout(output):
                exit_code = main(["--check"])

        self.assertEqual(exit_code, 0)
        self.assertIn("provider=listenhub", output.getvalue())
        self.assertIn("local_asr=auto-download", output.getvalue())

    def test_check_command_reports_local_fallback_status_for_openai_transcriptions(self) -> None:
        config = AppConfig(
            provider=ProviderConfig(
                name="openai_transcriptions",
                model="whisper-1",
                endpoint="http://127.0.0.1:8000/v1/audio/transcriptions",
            ),
            audio=AudioConfig(),
            hotkey=HotkeyConfig(),
            history=HistoryConfig(path=Path("/tmp/history.db")),
            correction=None,
        )
        output = io.StringIO()
        with patch("ibus_voice.cli.load_config", return_value=config), \
             patch("ibus_voice.cli.build_provider", return_value=object()), \
             patch("ibus_voice.cli.ensure_local_provider_ready", return_value="ready"):
            with redirect_stdout(output):
                exit_code = main(["--check"])

        self.assertEqual(exit_code, 0)
        self.assertIn("provider=openai_transcriptions", output.getvalue())
        self.assertIn("local_asr=ready", output.getvalue())

    def test_check_command_fails_cleanly_when_listenhub_binary_is_missing(self) -> None:
        config = AppConfig(
            provider=ProviderConfig(name="listenhub", model="sensevoice"),
            audio=AudioConfig(),
            hotkey=HotkeyConfig(),
            history=HistoryConfig(path=Path("/tmp/history.db")),
            correction=None,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("ibus_voice.cli.load_config", return_value=config), \
             patch("ibus_voice.cli.build_provider", return_value=object()), \
             patch("ibus_voice.cli.ensure_local_provider_ready", side_effect=ProviderFailure("listenhub", "missing runtime")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["--check"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("config check failed:", stderr.getvalue())
        self.assertIn("missing runtime", stderr.getvalue())

    def test_check_command_fails_when_openai_transcriptions_fallback_runtime_is_missing(self) -> None:
        config = AppConfig(
            provider=ProviderConfig(
                name="openai_transcriptions",
                model="whisper-1",
                endpoint="http://127.0.0.1:8000/v1/audio/transcriptions",
            ),
            audio=AudioConfig(),
            hotkey=HotkeyConfig(),
            history=HistoryConfig(path=Path("/tmp/history.db")),
            correction=None,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("ibus_voice.cli.load_config", return_value=config), \
             patch("ibus_voice.cli.build_provider", return_value=object()), \
             patch("ibus_voice.cli.ensure_local_provider_ready", side_effect=ProviderFailure("listenhub", "missing runtime")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["--check"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("config check failed:", stderr.getvalue())
        self.assertIn("missing runtime", stderr.getvalue())

    def test_add_word_appends_to_configured_dictionary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dictionary_path = Path(temp_dir) / "dictionary.txt"
            dictionary_path.write_text("IBus\n", encoding="utf-8")
            config = AppConfig(
                provider=ProviderConfig(name="listenhub", model="sensevoice", dictionary_path=dictionary_path),
                audio=AudioConfig(),
                hotkey=HotkeyConfig(),
                history=HistoryConfig(path=Path(temp_dir) / "history.db"),
                correction=None,
            )
            output = io.StringIO()
            with patch("ibus_voice.cli.load_config", return_value=config):
                with redirect_stdout(output):
                    exit_code = main(["--add-word", "ibus-voice"])
            dictionary_text = dictionary_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(dictionary_text, "IBus\nibus-voice\n")
        self.assertIn(str(dictionary_path), output.getvalue())
        self.assertIn("added:", output.getvalue())

    def test_add_word_reports_when_word_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dictionary_path = Path(temp_dir) / "dictionary.txt"
            dictionary_path.write_text("IBus\nibus-voice\n", encoding="utf-8")
            config = AppConfig(
                provider=ProviderConfig(name="listenhub", model="sensevoice", dictionary_path=dictionary_path),
                audio=AudioConfig(),
                hotkey=HotkeyConfig(),
                history=HistoryConfig(path=Path(temp_dir) / "history.db"),
                correction=None,
            )
            output = io.StringIO()
            with patch("ibus_voice.cli.load_config", return_value=config):
                with redirect_stdout(output):
                    exit_code = main(["--add-word", "ibus-voice"])
            dictionary_text = dictionary_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(dictionary_text, "IBus\nibus-voice\n")
        self.assertIn("already present:", output.getvalue())

    def test_add_word_updates_distinct_provider_and_correction_dictionaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            provider_dictionary_path = Path(temp_dir) / "provider.txt"
            correction_dictionary_path = Path(temp_dir) / "correction.txt"
            config = AppConfig(
                provider=ProviderConfig(name="listenhub", model="sensevoice", dictionary_path=provider_dictionary_path),
                audio=AudioConfig(),
                hotkey=HotkeyConfig(),
                history=HistoryConfig(path=Path(temp_dir) / "history.db"),
                correction=CorrectionConfig(
                    enabled=True,
                    base_url="https://api.openai.com/v1",
                    api_key="x",
                    model="gpt-4o-mini",
                    dictionary_path=correction_dictionary_path,
                ),
            )
            output = io.StringIO()
            with patch("ibus_voice.cli.load_config", return_value=config):
                with redirect_stdout(output):
                    exit_code = main(["--add-word", "IBus"])
            provider_dictionary_text = provider_dictionary_path.read_text(encoding="utf-8")
            correction_dictionary_text = correction_dictionary_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_dictionary_text, "IBus\n")
        self.assertEqual(correction_dictionary_text, "IBus\n")
        self.assertEqual(output.getvalue().count("added:"), 2)

    def test_add_word_fails_for_blank_word(self) -> None:
        config = AppConfig(
            provider=ProviderConfig(name="listenhub", model="sensevoice", dictionary_path=Path("/tmp/dictionary.txt")),
            audio=AudioConfig(),
            hotkey=HotkeyConfig(),
            history=HistoryConfig(path=Path("/tmp/history.db")),
            correction=None,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("ibus_voice.cli.load_config", return_value=config):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["--add-word", "   "])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("failed to add dictionary word:", stderr.getvalue())
