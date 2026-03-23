from __future__ import annotations

import unittest
from pathlib import Path

from ibus_voice.config import parse_config


class ParseConfigTests(unittest.TestCase):
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
        self.assertIsNone(config.cleanup)

    def test_missing_provider_fields_fail(self) -> None:
        with self.assertRaises(ValueError):
            parse_config({"provider": {"name": "openai"}})

    def test_parse_cleanup_config_with_relative_paths(self) -> None:
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
                    "api_key": "cleanup-secret",
                    "model": "gpt-4o-mini",
                    "system_prompt_path": "prompts/system.txt",
                    "user_prompt_path": "prompts/user.txt",
                },
            },
            base_dir=Path("/tmp/ibus-voice-config"),
        )

        self.assertTrue(config.cleanup.enabled)
        self.assertEqual(config.cleanup.base_url, "https://api.openai.com/v1")
        self.assertEqual(
            config.cleanup.system_prompt_path,
            Path("/tmp/ibus-voice-config/prompts/system.txt").resolve(),
        )
        self.assertEqual(
            config.cleanup.user_prompt_path,
            Path("/tmp/ibus-voice-config/prompts/user.txt").resolve(),
        )

    def test_enabled_cleanup_requires_provider_fields(self) -> None:
        with self.assertRaises(ValueError):
            parse_config(
                {
                    "provider": {
                        "name": "openai",
                        "api_key": "secret",
                        "model": "gpt-4o-transcribe",
                    },
                    "cleanup": {"enabled": True, "base_url": "https://api.openai.com/v1"},
                }
            )
