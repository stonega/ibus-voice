from __future__ import annotations

import io
import tarfile
import tempfile
import time
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from ibus_voice import local_asr


class FakeStream:
    def __init__(self) -> None:
        self.accepted: tuple[int, list[float]] | None = None
        self.result = types.SimpleNamespace(text=" transcript ")

    def accept_waveform(self, sample_rate: int, samples: list[float]) -> None:
        self.accepted = (sample_rate, samples)


class FakeRecognizer:
    def __init__(self) -> None:
        self.stream = FakeStream()

    def create_stream(self) -> FakeStream:
        return self.stream

    def decode_stream(self, stream: FakeStream) -> None:
        self.decoded_stream = stream


class FakeOfflineRecognizer:
    last_kwargs: dict | None = None

    @classmethod
    def from_sense_voice(cls, **kwargs):
        cls.last_kwargs = kwargs
        return FakeRecognizer()


class LocalAsrTests(unittest.TestCase):
    def test_ensure_runtime_dependency_reports_interpreter_hint(self) -> None:
        with patch("ibus_voice.local_asr.importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(local_asr.LocalAsrError) as ctx:
                local_asr.ensure_runtime_dependency()

        self.assertIn("sherpa_onnx", str(ctx.exception))
        self.assertIn("interpreter=", str(ctx.exception))
        self.assertIn(" -m pip install sherpa-onnx", str(ctx.exception))

    def test_runtime_status_reports_auto_download_when_model_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("ibus_voice.local_asr.model_root", return_value=Path(temp_dir)):
                with patch("ibus_voice.local_asr.importlib.import_module", return_value=object()):
                    self.assertEqual(local_asr.runtime_status("sensevoice"), "auto-download")

    def test_ensure_model_installed_extracts_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            def fake_download(_spec, destination: Path) -> None:
                with tarfile.open(destination, mode="w:bz2") as archive:
                    for filename, contents in {
                        f"{local_asr.MODEL_DIRECTORY_NAME}/{local_asr.MODEL_CHECK_FILE}": b"model",
                        f"{local_asr.MODEL_DIRECTORY_NAME}/{local_asr.TOKENS_FILE}": b"tokens",
                    }.items():
                        data = io.BytesIO(contents)
                        info = tarfile.TarInfo(filename)
                        info.size = len(contents)
                        archive.addfile(info, data)

            with patch("ibus_voice.local_asr.model_root", return_value=root):
                with patch("ibus_voice.local_asr._download_model_archive", side_effect=fake_download):
                    directory = local_asr.ensure_model_installed("sensevoice")

            self.assertEqual(directory, root / local_asr.MODEL_DIRECTORY_NAME)
            self.assertTrue((directory / local_asr.MODEL_CHECK_FILE).is_file())
            self.assertTrue((directory / local_asr.TOKENS_FILE).is_file())

    def test_transcribe_wav_file_uses_sherpa_python_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            wav_path = temp_path / "speech.wav"
            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\x00\x00\xff\x7f")

            model_dir = temp_path / local_asr.MODEL_DIRECTORY_NAME
            model_dir.mkdir()
            (model_dir / local_asr.MODEL_CHECK_FILE).write_bytes(b"model")
            (model_dir / local_asr.TOKENS_FILE).write_text("tokens", encoding="utf-8")
            fake_module = types.SimpleNamespace(OfflineRecognizer=FakeOfflineRecognizer)

            with patch("ibus_voice.local_asr.ensure_model_installed", return_value=model_dir):
                with patch("ibus_voice.local_asr.importlib.import_module", return_value=fake_module):
                    text = local_asr.transcribe_wav_file(wav_path, "sensevoice")

        self.assertEqual(text, "transcript")
        self.assertEqual(FakeOfflineRecognizer.last_kwargs["model"], str(model_dir / local_asr.MODEL_CHECK_FILE))
        self.assertEqual(FakeOfflineRecognizer.last_kwargs["tokens"], str(model_dir / local_asr.TOKENS_FILE))

    def test_transcribe_wav_file_with_timeout_fails_cleanly(self) -> None:
        with patch("ibus_voice.local_asr.transcribe_wav_file", side_effect=lambda *_args: time.sleep(0.05)):
            with self.assertRaises(local_asr.LocalAsrError) as ctx:
                local_asr.transcribe_wav_file_with_timeout("speech.wav", "sensevoice", 0.01)

        self.assertIn("timed out", str(ctx.exception))
