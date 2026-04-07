from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from ibus_voice.audio import AudioPayload
from ibus_voice.config import AudioConfig, ProviderConfig
from ibus_voice.local_asr import LocalAsrError
from ibus_voice.providers.factory import build_provider
from ibus_voice.providers.gemini import GeminiProvider
from ibus_voice.providers.listenhub import ListenHubProvider, ensure_local_provider_ready
from ibus_voice.providers.openai import OpenAIProvider
from ibus_voice.providers.openai_transcriptions import OpenAITranscriptionsProvider
from ibus_voice.types import ProviderFailure, TranscriptResult


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


class StubFallbackProvider:
    def __init__(self, result: TranscriptResult) -> None:
        self.result = result
        self.calls = 0

    def transcribe(self, audio: AudioPayload) -> TranscriptResult:
        del audio
        self.calls += 1
        return self.result


class ProviderTests(unittest.TestCase):
    def test_ensure_local_provider_ready_returns_runtime_status(self) -> None:
        with patch("ibus_voice.providers.listenhub.runtime_status", return_value="auto-download"):
            self.assertEqual(ensure_local_provider_ready("sensevoice"), "auto-download")

    def test_ensure_local_provider_ready_wraps_runtime_errors(self) -> None:
        with patch("ibus_voice.providers.listenhub.runtime_status", side_effect=LocalAsrError("boom")):
            with self.assertRaises(ProviderFailure) as ctx:
                ensure_local_provider_ready("sensevoice")

        self.assertIn("boom", str(ctx.exception))

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

    def test_openai_transcriptions_uses_configured_endpoint(self) -> None:
        provider = OpenAITranscriptionsProvider(
            config=ProviderConfig(
                name="openai_transcriptions",
                model="whisper-1",
                endpoint="http://127.0.0.1:8000/v1/audio/transcriptions",
            ),
            transport=FakeTransport({"text": " hello "}),
            fallback_provider=ListenHubProvider.from_config(ProviderConfig(name="listenhub", model="sensevoice")),
        )

        result = provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertEqual(result.text, "hello")
        self.assertEqual(result.provider, "openai_transcriptions")
        self.assertEqual(
            provider.transport.last_request["url"],
            "http://127.0.0.1:8000/v1/audio/transcriptions",
        )
        self.assertFalse(result.metadata["fallback_used"])

    def test_openai_transcriptions_falls_back_to_local_on_timeout(self) -> None:
        fallback_provider = StubFallbackProvider(
            TranscriptResult(
                text="local transcript",
                provider="listenhub",
                metadata={"engine": "local-sensevoice"},
            )
        )
        provider = OpenAITranscriptionsProvider(
            config=ProviderConfig(
                name="openai_transcriptions",
                model="whisper-1",
                endpoint="http://127.0.0.1:8000/v1/audio/transcriptions",
            ),
            transport=FakeTransport(failure=TimeoutError("timed out")),
            fallback_provider=fallback_provider,
        )

        result = provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertEqual(fallback_provider.calls, 1)
        self.assertEqual(result.text, "local transcript")
        self.assertEqual(result.provider, "openai_transcriptions")
        self.assertTrue(result.metadata["fallback_used"])
        self.assertEqual(result.metadata["fallback_provider"], "listenhub")
        self.assertEqual(result.metadata["engine"], "local-sensevoice")

    def test_openai_transcriptions_does_not_fall_back_on_http_error(self) -> None:
        fallback_provider = StubFallbackProvider(
            TranscriptResult(text="local transcript", provider="listenhub")
        )
        provider = OpenAITranscriptionsProvider(
            config=ProviderConfig(
                name="openai_transcriptions",
                model="whisper-1",
                endpoint="http://127.0.0.1:8000/v1/audio/transcriptions",
            ),
            transport=FakeTransport(failure=RuntimeError("HTTP 500: boom")),
            fallback_provider=fallback_provider,
        )

        with self.assertRaises(ProviderFailure) as ctx:
            provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertEqual(fallback_provider.calls, 0)
        self.assertIn("HTTP 500", str(ctx.exception))

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

    def test_listenhub_uses_local_asr(self) -> None:
        provider = ListenHubProvider(config=ProviderConfig(name="listenhub", model="sensevoice"))

        with patch("ibus_voice.providers.listenhub.transcribe_wav_file_with_timeout", return_value=" transcript "):
            result = provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertEqual(result.text, "transcript")
        self.assertEqual(result.provider, "listenhub")
        self.assertEqual(result.metadata["engine"], "local-sensevoice")
        self.assertEqual(result.metadata["model"], "sensevoice")

    def test_listenhub_readiness_status_reports_runtime_state(self) -> None:
        provider = ListenHubProvider(config=ProviderConfig(name="listenhub", model="sensevoice"))

        with patch("ibus_voice.providers.listenhub.ensure_local_provider_ready", return_value="auto-download"):
            self.assertEqual(provider.readiness_status(), "auto-download")

    def test_listenhub_wraps_local_runtime_failure(self) -> None:
        provider = ListenHubProvider(config=ProviderConfig(name="listenhub", model="sensevoice"))

        with patch(
            "ibus_voice.providers.listenhub.transcribe_wav_file_with_timeout",
            side_effect=RuntimeError("install failed"),
        ):
            with self.assertRaises(ProviderFailure) as ctx:
                provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertIn("install failed", str(ctx.exception))

    def test_listenhub_returns_empty_transcript_failure(self) -> None:
        provider = ListenHubProvider(config=ProviderConfig(name="listenhub", model="sensevoice"))

        with patch("ibus_voice.providers.listenhub.transcribe_wav_file_with_timeout", return_value=""):
            with self.assertRaises(ProviderFailure) as ctx:
                provider.transcribe(AudioPayload(data=b"audio", mime_type="audio/wav", filename="speech.wav"))

        self.assertIn("empty transcript", str(ctx.exception))

    def test_listenhub_finish_stream_reuses_pcm_buffer_for_final_decode(self) -> None:
        provider = ListenHubProvider(config=ProviderConfig(name="listenhub", model="sensevoice"))
        audio_config = AudioConfig(sample_rate=16000, channels=2, sample_width=2)
        partials: list[str] = []
        session = provider.start_stream(audio_config, partials.append)
        session.pcm_bytes.extend(b"\x00\x40\x00\x20\x00\x20\x00\x10")

        with patch("ibus_voice.providers.listenhub.transcribe_wav_file_with_timeout") as wav_decode:
            with patch("ibus_voice.providers.listenhub.transcribe_pcm16le_bytes", return_value=" final transcript ") as pcm_decode:
                result = provider.finish_stream(
                    session,
                    AudioPayload(data=b"unused", mime_type="audio/wav", filename="speech.wav"),
                )

        wav_decode.assert_not_called()
        pcm_decode.assert_called_once_with(
            b"\x00\x40\x00\x20\x00\x20\x00\x10",
            16000,
            "sensevoice",
            channels=2,
            sample_width=2,
        )
        self.assertEqual(result.text, "final transcript")

    def test_provider_factory_builds_listenhub(self) -> None:
        provider = build_provider(ProviderConfig(name="listenhub", model="sensevoice"))

        self.assertIsInstance(provider, ListenHubProvider)

    def test_provider_factory_builds_openai_transcriptions(self) -> None:
        provider = build_provider(
            ProviderConfig(
                name="openai_transcriptions",
                model="whisper-1",
                endpoint="http://127.0.0.1:8000/v1/audio/transcriptions",
            )
        )

        self.assertIsInstance(provider, OpenAITranscriptionsProvider)

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
