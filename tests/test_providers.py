from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from ibus_voice.audio import AudioPayload
from ibus_voice.config import ProviderConfig
from ibus_voice.providers.factory import build_provider
from ibus_voice.providers.gemini import GeminiProvider
from ibus_voice.providers.listenhub import ListenHubProvider
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


class FakeRunner:
    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        failure: Exception | None = None,
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.failure = failure
        self.last_command: list[str] | None = None
        self.last_timeout: float | None = None

    def run(self, command: list[str], timeout: float) -> tuple[int, str, str]:
        self.last_command = command
        self.last_timeout = timeout
        if self.failure is not None:
            raise self.failure
        return self.returncode, self.stdout, self.stderr


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
        self.assertIn("language or languages actually spoken", provider.transport.last_request["fields"]["prompt"])
        self.assertIn("Do not translate", provider.transport.last_request["fields"]["prompt"])

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

    def test_openai_rejects_prompt_echo_response(self) -> None:
        provider = OpenAIProvider(
            config=ProviderConfig(name="openai", api_key="x", model="m"),
            transport=FakeTransport(
                {
                    "text": (
                        "Transcribe this audio and return plain text only.\n"
                        "Let's transcribe this audio and return plain text only.\n"
                        "I am unable to process audio."
                    )
                }
            ),
        )

        with self.assertRaises(ProviderFailure) as ctx:
            provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertIn("non_transcript_response", str(ctx.exception))

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
        self.assertIn("language or languages actually spoken", prompt)
        self.assertIn("Preserve mixed-language phrasing", prompt)

    def test_gemini_rejects_audio_processing_refusal(self) -> None:
        provider = GeminiProvider(
            config=ProviderConfig(name="gemini", api_key="x", model="m"),
            transport=FakeTransport(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "I am unable to process audio. Therefore, I cannot transcribe the audio for you."}]}}
                    ]
                }
            ),
        )

        with self.assertRaises(ProviderFailure) as ctx:
            provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertIn("audio_not_processed", str(ctx.exception))

    def test_listenhub_uses_coli_cli(self) -> None:
        runner = FakeRunner(stdout=" transcript ")
        provider = ListenHubProvider(
            config=ProviderConfig(name="listenhub", model="sensevoice"),
            runner=runner,
        )

        with patch("ibus_voice.providers.listenhub.ensure_coli_available", return_value="/usr/bin/coli"):
            result = provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertEqual(result.text, "transcript")
        self.assertEqual(result.provider, "listenhub")
        self.assertEqual(runner.last_command[:4], ["/usr/bin/coli", "asr", "--model", "sensevoice"])
        self.assertEqual(runner.last_command[-1][-10:], "speech.wav")
        self.assertEqual(runner.last_timeout, 30.0)

    def test_listenhub_wraps_missing_coli_binary(self) -> None:
        provider = ListenHubProvider(
            config=ProviderConfig(name="listenhub", model="sensevoice"),
            runner=FakeRunner(failure=FileNotFoundError("coli")),
        )

        with self.assertRaises(ProviderFailure) as ctx:
            provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertIn("install @marswave/coli", str(ctx.exception))

    def test_listenhub_returns_stderr_on_failure(self) -> None:
        provider = ListenHubProvider(
            config=ProviderConfig(name="listenhub", model="sensevoice"),
            runner=FakeRunner(returncode=2, stderr="bad audio"),
        )

        with patch("ibus_voice.providers.listenhub.ensure_coli_available", return_value="/usr/bin/coli"):
            with self.assertRaises(ProviderFailure) as ctx:
                provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertIn("bad audio", str(ctx.exception))

    def test_provider_factory_builds_listenhub(self) -> None:
        provider = build_provider(ProviderConfig(name="listenhub", model="sensevoice"))

        self.assertIsInstance(provider, ListenHubProvider)

    def test_provider_factory_rejects_unknown_provider(self) -> None:
        with self.assertRaises(ProviderFailure):
            build_provider(ProviderConfig(name="unknown", api_key="x", model="m"))


class HttpTransportTests(unittest.TestCase):
    def test_http_error_uses_json_message_and_code(self) -> None:
        error_body = b'{"error":{"code":"unsupported_audio_format","message":"Only wav is supported"}}'
        response = patch("urllib.request.urlopen", side_effect=HTTPError(
            url="https://example.invalid",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=None,
        ))

        with response as mock_urlopen:
            mock_urlopen.side_effect.fp = None

            class ResponseError(HTTPError):
                def read(self_nonlocal) -> bytes:
                    return error_body

            mock_urlopen.side_effect = ResponseError(
                url="https://example.invalid",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=None,
            )

            provider = OpenAIProvider(
                config=ProviderConfig(name="openai", api_key="x", model="m"),
                transport=OpenAIProvider.from_config(ProviderConfig(name="openai", api_key="x", model="m")).transport,
            )

            with self.assertRaises(ProviderFailure) as ctx:
                provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertIn("HTTP 400: unsupported_audio_format: Only wav is supported", str(ctx.exception))
