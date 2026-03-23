from __future__ import annotations

import unittest
import wave
from io import BytesIO

from ibus_voice.audio import MemoryRecorder


class MemoryRecorderTests(unittest.TestCase):
    def test_accumulates_audio(self) -> None:
        recorder = MemoryRecorder()

        recorder.start()
        recorder.push(b"a")
        recorder.push(b"b")

        payload = recorder.stop()

        self.assertEqual(payload.mime_type, "audio/wav")
        with wave.open(BytesIO(payload.data), "rb") as wav_file:
            self.assertEqual(wav_file.readframes(2), b"ab")

    def test_push_requires_recording(self) -> None:
        recorder = MemoryRecorder()

        with self.assertRaises(RuntimeError):
            recorder.push(b"a")
