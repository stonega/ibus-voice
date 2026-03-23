from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.providers.factory import build_provider
from ibus_voice.providers.gemini import GeminiProvider
from ibus_voice.providers.openai import OpenAIProvider
from ibus_voice.types import ProviderFailure


class FakeTransport:
    def __init__(self, response: dict | None = None, failure: Exception | None = None) -> None:
        self.response = response or {}
        self.failure = failure
        self.last_request: dict | None = None

    def post_json(self, url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
        self.last_request = {
            "kind": "json",
            "url": url,
            "headers": headers,
            "payload": payload,
            "timeout": timeout,
        }
        if self.failure is not None:
            raise self.failure
        return self.response

    def post_multipart(
        self,
        url: str,
        headers: dict[str, str],
        fields: dict[str, str],
        files: dict[str, tuple[str, str, bytes]],
        timeout: float,
    ) -> dict:
        self.last_request = {
            "kind": "multipart",
            "url": url,
            "headers": headers,
            "fields": fields,
            "files": files,
            "timeout": timeout,
        }
        if self.failure is not None:
            raise self.failure
        return self.response


class ProviderTests(unittest.TestCase):
    def test_openai_normalizes_text(self) -> None:
        provider = OpenAIProvider(
            config=ProviderConfig(name="openai", api_key="x", model="m"),
            transport=FakeTransport({"text": " hello "}),
        )

        result = provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertEqual(result.text, "hello")
        self.assertEqual(result.provider, "openai")
        self.assertEqual(provider.transport.last_request["kind"], "multipart")
        self.assertEqual(provider.transport.last_request["fields"]["model"], "m")

    def test_openai_uses_dictionary_as_transcription_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dictionary = Path(tmpdir) / "dictionary.txt"
            dictionary.write_text("IBus\nOpenAI", encoding="utf-8")
            provider = OpenAIProvider(
                config=ProviderConfig(name="openai", api_key="x", model="m", dictionary_path=dictionary),
                transport=FakeTransport({"text": " hello "}),
            )

            provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertIn("Prefer these canonical terms", provider.transport.last_request["fields"]["prompt"])
        self.assertIn("IBus\nOpenAI", provider.transport.last_request["fields"]["prompt"])

    def test_gemini_extracts_candidate_text(self) -> None:
        provider = GeminiProvider(
            config=ProviderConfig(name="gemini", api_key="x", model="m"),
            transport=FakeTransport(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": " transcript "}]}},
                    ]
                }
            ),
        )

        result = provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertEqual(result.text, "transcript")
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(provider.transport.last_request["kind"], "json")

    def test_gemini_uses_dictionary_in_transcription_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dictionary = Path(tmpdir) / "dictionary.txt"
            dictionary.write_text("IBus\nOpenAI", encoding="utf-8")
            provider = GeminiProvider(
                config=ProviderConfig(name="gemini", api_key="x", model="m", dictionary_path=dictionary),
                transport=FakeTransport(
                    {
                        "candidates": [
                            {"content": {"parts": [{"text": " transcript "}]}},
                        ]
                    }
                ),
            )

            provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        prompt = provider.transport.last_request["payload"]["contents"][0]["parts"][0]["text"]
        self.assertIn("Prefer these canonical terms", prompt)
        self.assertIn("IBus\nOpenAI", prompt)

    def test_provider_factory_rejects_unknown_provider(self) -> None:
        with self.assertRaises(ProviderFailure):
            build_provider(ProviderConfig(name="unknown", api_key="x", model="m"))
