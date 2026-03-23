from __future__ import annotations

import unittest

from ibus_voice.audio import AudioPayload, MemoryRecorder
from ibus_voice.engine import VoiceEngine
from ibus_voice.types import CorrectionFailure, ProviderFailure, TranscriptResult


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


class StubCorrector:
    def __init__(
        self,
        text: str | None = None,
        failure: Exception | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.text = text
        self.failure = failure
        self.metadata = metadata or {}

    def correct(self, transcript: str) -> str:
        if self.failure is not None:
            raise self.failure
        if self.text is None:
            return transcript
        return self.text

    def get_metadata(self) -> dict[str, object]:
        return dict(self.metadata)


class StubHistory:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.saved: list[dict[str, object]] = []

    def save_completed_session(
        self,
        result: TranscriptResult,
        *,
        raw_text: str,
        warning: str | None,
    ) -> None:
        if self.failure is not None:
            raise self.failure
        self.saved.append(
            {
                "result": result,
                "raw_text": raw_text,
                "warning": warning,
            }
        )


class VoiceEngineTests(unittest.TestCase):
    def test_press_release_commits_result(self) -> None:
        recorder = MemoryRecorder()
        provider = StubProvider(TranscriptResult(text="hello world", provider="stub"))
        committer = StubCommitter()
        engine = VoiceEngine(recorder=recorder, provider=provider, committer=committer, corrector=StubCorrector())

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
            corrector=StubCorrector(),
        )

        engine.handle_release()

        self.assertEqual(engine.state, "idle")
        self.assertIn("ignored_release", engine.events)

    def test_transcription_failure_resets_to_idle(self) -> None:
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(failure=ProviderFailure("stub", "boom")),
            committer=StubCommitter(),
            corrector=StubCorrector(),
        )

        engine.handle_press()
        engine.recorder.push(b"voice")  # type: ignore[attr-defined]
        engine.handle_release()

        self.assertEqual(engine.state, "idle")
        self.assertEqual(engine.last_error, "stub: boom")
        self.assertIn("transcription_failed", engine.events)

    def test_correction_result_is_committed_when_available(self) -> None:
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(TranscriptResult(text="hello world", provider="stub")),
            committer=StubCommitter(),
            corrector=StubCorrector(
                text="Hello world.",
                metadata={"correction_usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}},
            ),
        )

        engine.handle_press()
        engine.recorder.push(b"voice")  # type: ignore[attr-defined]
        engine.handle_release()

        self.assertEqual(engine.committer.values, ["Hello world."])  # type: ignore[attr-defined]
        self.assertEqual(engine.last_raw_text, "hello world")
        self.assertEqual(engine.last_result.text, "Hello world.")
        self.assertEqual(engine.last_result.metadata["raw_text"], "hello world")
        self.assertEqual(
            engine.last_result.metadata["correction_usage"],
            {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
        )

    def test_correction_failure_falls_back_to_raw_text(self) -> None:
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(TranscriptResult(text="hello world", provider="stub")),
            committer=StubCommitter(),
            corrector=StubCorrector(failure=CorrectionFailure("correction", "timeout")),
        )

        engine.handle_press()
        engine.recorder.push(b"voice")  # type: ignore[attr-defined]
        engine.handle_release()

        self.assertEqual(engine.committer.values, ["hello world"])  # type: ignore[attr-defined]
        self.assertEqual(engine.last_warning, "correction: timeout")
        self.assertIn("correction_failed_fallback", engine.events)

    def test_completed_session_is_saved_to_history(self) -> None:
        history = StubHistory()
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(TranscriptResult(text="hello world", provider="stub", latency_ms=42)),
            committer=StubCommitter(),
            corrector=StubCorrector(text="Hello world."),
            history=history,
        )

        engine.handle_press()
        engine.recorder.push(b"voice")  # type: ignore[attr-defined]
        engine.handle_release()

        self.assertEqual(len(history.saved), 1)
        saved = history.saved[0]
        self.assertEqual(saved["raw_text"], "hello world")
        self.assertEqual(saved["warning"], None)
        self.assertEqual(saved["result"].text, "Hello world.")  # type: ignore[union-attr]

    def test_history_failure_does_not_break_commit(self) -> None:
        engine = VoiceEngine(
            recorder=MemoryRecorder(),
            provider=StubProvider(TranscriptResult(text="hello world", provider="stub")),
            committer=StubCommitter(),
            corrector=StubCorrector(),
            history=StubHistory(failure=RuntimeError("database is locked")),
        )

        engine.handle_press()
        engine.recorder.push(b"voice")  # type: ignore[attr-defined]
        engine.handle_release()

        self.assertEqual(engine.committer.values, ["hello world"])  # type: ignore[attr-defined]
        self.assertEqual(engine.last_warning, "history: database is locked")
        self.assertIn("history_save_failed", engine.events)
