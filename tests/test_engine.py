from __future__ import annotations

import unittest

from ibus_voice.audio import AudioPayload, MemoryRecorder
from ibus_voice.engine import VoiceEngine
from ibus_voice.types import CleanupFailure, ProviderFailure, TranscriptResult


class StubCommitter:
    def __init__(self) -> None:
        self.values: list[str] = []

    def commit_text(self, text: str) -> None:
        self.values.append(text)


class StubProvider:
    def __init__(self, result: TranscriptResult | None = None, failure: Exception | None = None) -> None:
        self.result = result
        self.failure = failure

    def transcribe(self, audio: AudioPayload) -> TranscriptResult:
        if self.failure is not None:
            raise self.failure
        assert self.result is not None
        if not audio.data:
            raise ProviderFailure("stub", "missing audio")
        return self.result


class StubCleaner:
    def __init__(self, text: str | None = None, failure: Exception | None = None) -> None:
        self.text = text
        self.failure = failure

    def clean(self, transcript: str) -> str:
        if self.failure is not None:
            raise self.failure
        if self.text is None:
            return transcript
        return self.text


class VoiceEngineTests(unittest.TestCase):
    def test_press_release_commits_result(self) -> None:
        recorder = MemoryRecorder()
        provider = StubProvider(TranscriptResult(text="hello world", provider="stub"))
        committer = StubCommitter()
        engine = VoiceEngine(recorder=recorder, provider=provider, committer=committer, cleaner=StubCleaner())

        engine.handle_press()
        recorder.push(b"voice")
        engine.handle_release()

        self.assertEqual(engine.state, "idle")
        self.assertEqual(committer.values, ["hello world"])
        self.assertEqual(engine.last_result.text, "hello world")

    def test_release_without_recording_is_ignored(self) -> None:
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(TranscriptResult(text="ignored", provider="stub")),
            committer=StubCommitter(),
            cleaner=StubCleaner(),
        )

        engine.handle_release()

        self.assertEqual(engine.state, "idle")
        self.assertIn("ignored_release", engine.events)

    def test_transcription_failure_resets_to_idle(self) -> None:
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(failure=ProviderFailure("stub", "boom")),
            committer=StubCommitter(),
            cleaner=StubCleaner(),
        )

        engine.handle_press()
        engine.recorder.push(b"voice")  # type: ignore[attr-defined]
        engine.handle_release()

        self.assertEqual(engine.state, "idle")
        self.assertEqual(engine.last_error, "stub: boom")
        self.assertIn("transcription_failed", engine.events)

    def test_cleanup_result_is_committed_when_available(self) -> None:
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(TranscriptResult(text="hello world", provider="stub")),
            committer=StubCommitter(),
            cleaner=StubCleaner(text="Hello world."),
        )

        engine.handle_press()
        engine.recorder.push(b"voice")  # type: ignore[attr-defined]
        engine.handle_release()

        self.assertEqual(engine.committer.values, ["Hello world."])  # type: ignore[attr-defined]
        self.assertEqual(engine.last_raw_text, "hello world")
        self.assertEqual(engine.last_result.text, "Hello world.")
        self.assertEqual(engine.last_result.metadata["raw_text"], "hello world")

    def test_cleanup_failure_falls_back_to_raw_text(self) -> None:
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(TranscriptResult(text="hello world", provider="stub")),
            committer=StubCommitter(),
            cleaner=StubCleaner(failure=CleanupFailure("cleanup", "timeout")),
        )

        engine.handle_press()
        engine.recorder.push(b"voice")  # type: ignore[attr-defined]
        engine.handle_release()

        self.assertEqual(engine.committer.values, ["hello world"])  # type: ignore[attr-defined]
        self.assertEqual(engine.last_warning, "cleanup: timeout")
        self.assertIn("cleanup_failed_fallback", engine.events)
