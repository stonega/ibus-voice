from __future__ import annotations

import unittest

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

    def test_missing_provider_fields_fail(self) -> None:
        with self.assertRaises(ValueError):
            parse_config({"provider": {"name": "openai"}})
