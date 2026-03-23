from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ibus_voice.cleanup import OpenAICompatibleCleaner, build_cleaner
from ibus_voice.config import CleanupConfig
from ibus_voice.types import CleanupFailure


class FakeTransport:
    def __init__(self, response: dict | None = None, failure: Exception | None = None) -> None:
        self.response = response or {}
        self.failure = failure
        self.last_request: dict | None = None

    def post_json(self, url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
        self.last_request = {
            "url": url,
            "headers": headers,
            "payload": payload,
            "timeout": timeout,
        }
        if self.failure is not None:
            raise self.failure
        return self.response


class CleanupTests(unittest.TestCase):
    def test_build_cleaner_returns_passthrough_when_disabled(self) -> None:
        cleaner = build_cleaner(None)

        self.assertEqual(cleaner.clean(" raw transcript "), " raw transcript ")

    def test_openai_cleaner_builds_chat_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            system_prompt = base / "system.txt"
            user_prompt = base / "user.txt"
            system_prompt.write_text("Fix text.", encoding="utf-8")
            user_prompt.write_text("Transcript: {transcript}", encoding="utf-8")
            transport = FakeTransport(
                {"choices": [{"message": {"content": " Cleaned transcript. "}}]}
            )
            cleaner = OpenAICompatibleCleaner(
                config=CleanupConfig(
                    enabled=True,
                    base_url="https://api.openai.com/v1",
                    api_key="secret",
                    model="gpt-4o-mini",
                    timeout_seconds=5.0,
                    system_prompt_path=system_prompt,
                    user_prompt_path=user_prompt,
                ),
                transport=transport,
            )

            result = cleaner.clean("hello world")

        self.assertEqual(result, "Cleaned transcript.")
        self.assertEqual(transport.last_request["url"], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(
            transport.last_request["payload"]["messages"][1]["content"],
            "Transcript: hello world",
        )

    def test_openai_cleaner_rejects_empty_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            system_prompt = base / "system.txt"
            user_prompt = base / "user.txt"
            system_prompt.write_text("Fix text.", encoding="utf-8")
            user_prompt.write_text("Transcript: {transcript}", encoding="utf-8")
            cleaner = OpenAICompatibleCleaner(
                config=CleanupConfig(
                    enabled=True,
                    base_url="https://api.openai.com/v1",
                    api_key="secret",
                    model="gpt-4o-mini",
                    system_prompt_path=system_prompt,
                    user_prompt_path=user_prompt,
                ),
                transport=FakeTransport({"choices": [{"message": {"content": ""}}]}),
            )

            with self.assertRaises(CleanupFailure):
                cleaner.clean("hello world")

    def test_openai_cleaner_wraps_transport_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            system_prompt = base / "system.txt"
            user_prompt = base / "user.txt"
            system_prompt.write_text("Fix text.", encoding="utf-8")
            user_prompt.write_text("Transcript: {transcript}", encoding="utf-8")
            cleaner = OpenAICompatibleCleaner(
                config=CleanupConfig(
                    enabled=True,
                    base_url="https://api.openai.com/v1",
                    api_key="secret",
                    model="gpt-4o-mini",
                    system_prompt_path=system_prompt,
                    user_prompt_path=user_prompt,
                ),
                transport=FakeTransport(failure=RuntimeError("timeout")),
            )

            with self.assertRaises(CleanupFailure):
                cleaner.clean("hello world")
