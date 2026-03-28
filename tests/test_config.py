from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ibus_voice.config import DEFAULT_COMPANION_FILES, DEFAULT_CONFIG_TEXT, load_config, load_history_path, parse_config


class ParseConfigTests(unittest.TestCase):
    def test_provider_defaults_to_listenhub(self) -> None:
        config = parse_config({}, base_dir=Path("/tmp/ibus-voice-config"))

        self.assertEqual(config.provider.name, "listenhub")
        self.assertEqual(config.provider.api_key, "")
        self.assertEqual(config.provider.model, "sensevoice")
        self.assertEqual(
            config.provider.dictionary_path,
            Path("/tmp/ibus-voice-config/dictionary.txt").resolve(),
        )

    def test_parse_valid_config(self) -> None:
        config = parse_config(
            {
                "provider": {
                    "name": "openai",
                    "api_key": "secret",
                    "model": "gpt-4o-transcribe",
                },
                "audio": {"sample_rate": 8000},
                "hotkey": {"key": "space", "modifiers": ["Control", "Shift"]},
            }
        )

        self.assertEqual(config.provider.name, "openai")
        self.assertEqual(config.audio.sample_rate, 8000)
        self.assertEqual(config.hotkey.modifiers, ("Control", "Shift"))
        self.assertEqual(config.history.path, Path.home() / ".config" / "ibus-voice" / "history.db")
        self.assertIsNone(config.correction)

    def test_missing_provider_fields_fail(self) -> None:
        with self.assertRaises(ValueError):
            parse_config({"provider": {"name": "openai"}})

    def test_parse_listenhub_provider_without_api_key(self) -> None:
        config = parse_config(
            {
                "provider": {
                    "name": "listenhub",
                },
            },
            base_dir=Path("/tmp/ibus-voice-config"),
        )

        self.assertEqual(config.provider.name, "listenhub")
        self.assertEqual(config.provider.api_key, "")
        self.assertEqual(config.provider.model, "sensevoice")
        self.assertEqual(
            config.provider.dictionary_path,
            Path("/tmp/ibus-voice-config/dictionary.txt").resolve(),
        )

    def test_parse_correction_config_with_relative_paths(self) -> None:
        config = parse_config(
            {
                "provider": {
                    "name": "openai",
                    "api_key": "secret",
                    "model": "gpt-4o-transcribe",
                },
                "correction": {
                    "enabled": True,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "correction-secret",
                    "model": "gpt-4o-mini",
                    "system_prompt_path": "prompts/system.txt",
                    "user_prompt_path": "prompts/user.txt",
                },
                "history": {
                    "path": "state/history.db",
                },
            },
            base_dir=Path("/tmp/ibus-voice-config"),
        )

        self.assertTrue(config.correction.enabled)
        self.assertEqual(config.correction.base_url, "https://api.openai.com/v1")
        self.assertEqual(
            config.provider.dictionary_path,
            Path("/tmp/ibus-voice-config/dictionary.txt").resolve(),
        )
        self.assertEqual(
            config.correction.dictionary_path,
            Path("/tmp/ibus-voice-config/dictionary.txt").resolve(),
        )
        self.assertEqual(
            config.history.path,
            Path("/tmp/ibus-voice-config/state/history.db").resolve(),
        )
        self.assertEqual(
            config.correction.history_path,
            Path("/tmp/ibus-voice-config/state/history.db").resolve(),
        )
        self.assertEqual(
            config.correction.system_prompt_path,
            Path("/tmp/ibus-voice-config/prompts/system.txt").resolve(),
        )
        self.assertEqual(
            config.correction.user_prompt_path,
            Path("/tmp/ibus-voice-config/prompts/user.txt").resolve(),
        )

    def test_enabled_correction_requires_provider_fields(self) -> None:
        with self.assertRaises(ValueError):
            parse_config(
                {
                    "provider": {
                        "name": "openai",
                        "api_key": "secret",
                        "model": "gpt-4o-transcribe",
                    },
                    "correction": {"enabled": True, "base_url": "https://api.openai.com/v1"},
                }
            )

    def test_correction_history_path_defaults_to_top_level_history_path(self) -> None:
        config = parse_config(
            {
                "provider": {
                    "name": "openai",
                    "api_key": "secret",
                    "model": "gpt-4o-transcribe",
                },
                "history": {
                    "path": "custom-history.db",
                },
                "correction": {
                    "enabled": True,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "correction-secret",
                    "model": "gpt-4o-mini",
                },
            },
            base_dir=Path("/tmp/ibus-voice-config"),
        )

        self.assertEqual(
            config.correction.history_path,
            Path("/tmp/ibus-voice-config/custom-history.db").resolve(),
        )

    def test_legacy_cleanup_section_is_supported(self) -> None:
        config = parse_config(
            {
                "provider": {
                    "name": "openai",
                    "api_key": "secret",
                    "model": "gpt-4o-transcribe",
                },
                "cleanup": {
                    "enabled": True,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "legacy-secret",
                    "model": "gpt-4o-mini",
                },
            }
        )

        self.assertTrue(config.correction.enabled)

    def test_cleanup_and_correction_sections_conflict(self) -> None:
        with self.assertRaises(ValueError):
            parse_config(
                {
                    "provider": {
                        "name": "openai",
                        "api_key": "secret",
                        "model": "gpt-4o-transcribe",
                    },
                    "cleanup": {"enabled": False},
                    "correction": {"enabled": False},
                }
            )

    def test_load_config_creates_default_config_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config" / "ibus-voice" / "config.toml"
            with patch("ibus_voice.config.DEFAULT_CONFIG_PATH", config_path):
                config = load_config()

            self.assertTrue(config_path.exists())
            self.assertEqual(config_path.read_text(encoding="utf-8"), DEFAULT_CONFIG_TEXT)
            self.assertEqual(config.provider.name, "listenhub")
            self.assertEqual(config.provider.model, "sensevoice")
            self.assertEqual(
                config.history.path,
                (config_path.parent / "history.db").resolve(),
            )
            for filename, contents in DEFAULT_COMPANION_FILES.items():
                self.assertEqual((config_path.parent / filename).read_text(encoding="utf-8"), contents)

    def test_load_history_path_creates_default_config_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config" / "ibus-voice" / "config.toml"
            with patch("ibus_voice.config.DEFAULT_CONFIG_PATH", config_path):
                history_path = load_history_path()

            self.assertTrue(config_path.exists())
            self.assertEqual(history_path, (config_path.parent / "history.db").resolve())
            for filename, contents in DEFAULT_COMPANION_FILES.items():
                self.assertEqual((config_path.parent / filename).read_text(encoding="utf-8"), contents)

    def test_load_config_does_not_create_missing_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "missing.toml"

            with self.assertRaises(FileNotFoundError):
                load_config(config_path)

            self.assertFalse(config_path.exists())
