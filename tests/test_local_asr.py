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
        self.streams: list[FakeStream] = []

    def create_stream(self) -> FakeStream:
        stream = FakeStream()
        self.streams.append(stream)
        return stream

    def decode_stream(self, stream: FakeStream) -> None:
        self.decoded_stream = stream


class FakeOfflineRecognizer:
    build_count = 0
    last_kwargs: dict | None = None
    last_recognizer: FakeRecognizer | None = None

    @classmethod
    def from_qwen3_asr(cls, **kwargs):
        cls.build_count += 1
        cls.last_kwargs = kwargs
        cls.last_recognizer = FakeRecognizer()
        return cls.last_recognizer


def create_fake_model(root: Path) -> Path:
    model_dir = root / local_asr.MODEL_DIRECTORY_NAME
    for relative_path in local_asr.MODEL_REQUIRED_FILES:
        path = model_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"model-data")
    return model_dir


class LocalAsrTests(unittest.TestCase):
    def setUp(self) -> None:
        local_asr._reset_recognizer_cache()
        FakeOfflineRecognizer.build_count = 0
        FakeOfflineRecognizer.last_kwargs = None
        FakeOfflineRecognizer.last_recognizer = None

    def tearDown(self) -> None:
        local_asr._reset_recognizer_cache()

    def test_ensure_runtime_dependency_reports_interpreter_hint(self) -> None:
        with patch("ibus_voice.local_asr.importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(local_asr.LocalAsrError) as ctx:
                local_asr.ensure_runtime_dependency()

        self.assertIn("sherpa_onnx", str(ctx.exception))
        self.assertIn("interpreter=", str(ctx.exception))
        self.assertIn(" -m pip install --upgrade", str(ctx.exception))
        self.assertIn("sherpa-onnx>=1.12.36", str(ctx.exception))

    def test_ensure_runtime_dependency_rejects_runtime_without_qwen_support(self) -> None:
        incompatible_runtime = types.SimpleNamespace(__version__="1.12.0", OfflineRecognizer=object())
        with patch("ibus_voice.local_asr.importlib.import_module", return_value=incompatible_runtime):
            with self.assertRaises(local_asr.LocalAsrError) as ctx:
                local_asr.ensure_runtime_dependency()

        self.assertIn("does not support Qwen3-ASR", str(ctx.exception))
        self.assertIn("version=1.12.0", str(ctx.exception))

    def test_ensure_runtime_dependency_rejects_old_runtime_with_qwen_api(self) -> None:
        old_runtime = types.SimpleNamespace(
            __version__="1.12.34",
            OfflineRecognizer=FakeOfflineRecognizer,
        )
        with patch("ibus_voice.local_asr.importlib.import_module", return_value=old_runtime):
            with self.assertRaises(local_asr.LocalAsrError) as ctx:
                local_asr.ensure_runtime_dependency()

        self.assertIn("version=1.12.34", str(ctx.exception))

    def test_ensure_runtime_dependency_bootstraps_from_bundled_wheelhouse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_site = Path(temp_dir) / "runtime" / "cp314"
            wheelhouse = Path(temp_dir) / "wheelhouse"
            wheelhouse.mkdir()
            imported = {"count": 0}
            real_import_module = local_asr.importlib.import_module

            def fake_import(name: str):
                if name != "sherpa_onnx":
                    return real_import_module(name)
                imported["count"] += 1
                if imported["count"] == 1:
                    raise ImportError("missing")
                return types.SimpleNamespace(OfflineRecognizer=FakeOfflineRecognizer)

            with patch("ibus_voice.local_asr.importlib.import_module", side_effect=fake_import):
                with patch("ibus_voice.local_asr.bundled_wheelhouse", return_value=wheelhouse):
                    with patch("ibus_voice.local_asr.runtime_site_packages", return_value=runtime_site):
                        with patch("ibus_voice.local_asr._install_runtime_from_wheelhouse") as install_runtime:
                            local_asr.ensure_runtime_dependency()

        install_runtime.assert_called_once_with(wheelhouse, runtime_site)

    def test_ensure_runtime_dependency_upgrades_stale_private_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_site = Path(temp_dir) / "runtime" / "cp314"
            runtime_site.mkdir(parents=True)
            wheelhouse = Path(temp_dir) / "wheelhouse"
            wheelhouse.mkdir()
            fake_module = types.SimpleNamespace(
                __version__="1.13.4",
                OfflineRecognizer=FakeOfflineRecognizer,
            )
            imports = [ImportError("incompatible vendor runtime"), fake_module]

            with patch("ibus_voice.local_asr.bundled_wheelhouse", return_value=wheelhouse):
                with patch("ibus_voice.local_asr.runtime_site_packages", return_value=runtime_site):
                    with patch(
                        "ibus_voice.local_asr._runtime_site_dependency_version",
                        return_value="1.12.0",
                    ):
                        with patch("ibus_voice.local_asr._install_runtime_from_wheelhouse") as install_runtime:
                            with patch("ibus_voice.local_asr.importlib.import_module", side_effect=imports):
                                local_asr.ensure_runtime_dependency()

        install_runtime.assert_called_once_with(wheelhouse, runtime_site)

    def test_bundled_runtime_install_upgrades_target_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wheelhouse = Path(temp_dir) / "wheelhouse"
            wheelhouse.mkdir()
            destination = Path(temp_dir) / "runtime"
            completed = types.SimpleNamespace(returncode=0)

            with patch("ibus_voice.local_asr.subprocess.run", return_value=completed) as run:
                local_asr._install_runtime_from_wheelhouse(wheelhouse, destination)

        command = run.call_args.args[0]
        self.assertIn("--no-index", command)
        self.assertIn("--upgrade", command)
        self.assertIn(f"--find-links={wheelhouse}", command)

    def test_legacy_sensevoice_name_maps_to_qwen(self) -> None:
        self.assertEqual(local_asr.normalize_model_name("sensevoice"), local_asr.MODEL_NAME)
        self.assertEqual(local_asr.normalize_model_name("Qwen3-ASR-0.6B"), local_asr.MODEL_NAME)

    def test_unsupported_model_fails_cleanly(self) -> None:
        with self.assertRaises(local_asr.LocalAsrError) as ctx:
            local_asr.normalize_model_name("whisper-tiny.en")

        self.assertIn(local_asr.MODEL_NAME, str(ctx.exception))

    def test_runtime_status_reports_auto_download_when_model_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("ibus_voice.local_asr.model_root", return_value=Path(temp_dir)):
                fake_module = types.SimpleNamespace(OfflineRecognizer=FakeOfflineRecognizer)
                with patch("ibus_voice.local_asr.importlib.import_module", return_value=fake_module):
                    self.assertEqual(local_asr.runtime_status(local_asr.MODEL_NAME), "auto-download")

    def test_download_model_archive_rejects_checksum_mismatch(self) -> None:
        spec = local_asr.ModelSpec(
            name="test",
            directory_name="test",
            url="https://example.invalid/model.tar.bz2",
            sha256="0" * 64,
            required_files=("model.onnx",),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "model.tar.bz2"
            with patch("ibus_voice.local_asr.urllib.request.urlopen", return_value=io.BytesIO(b"invalid")):
                with self.assertRaises(local_asr.LocalAsrError) as ctx:
                    local_asr._download_model_archive(spec, destination)

            self.assertFalse(destination.exists())

        self.assertIn("checksum validation", str(ctx.exception))

    def test_ensure_model_installed_extracts_complete_qwen_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            def fake_download(_spec, destination: Path) -> None:
                with tarfile.open(destination, mode="w:bz2") as archive:
                    for relative_path in local_asr.MODEL_REQUIRED_FILES:
                        filename = f"{local_asr.MODEL_DIRECTORY_NAME}/{relative_path}"
                        contents = relative_path.encode("utf-8")
                        info = tarfile.TarInfo(filename)
                        info.size = len(contents)
                        archive.addfile(info, io.BytesIO(contents))

            with patch("ibus_voice.local_asr.model_root", return_value=root):
                with patch("ibus_voice.local_asr._download_model_archive", side_effect=fake_download):
                    directory = local_asr.ensure_model_installed(local_asr.MODEL_NAME)

            self.assertEqual(directory, root / local_asr.MODEL_DIRECTORY_NAME)
            for relative_path in local_asr.MODEL_REQUIRED_FILES:
                self.assertTrue((directory / relative_path).is_file())

    def test_model_installation_rejects_empty_required_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_dir = create_fake_model(root)
            (model_dir / local_asr.DECODER_FILE).write_bytes(b"")

            with patch("ibus_voice.local_asr.model_root", return_value=root):
                self.assertFalse(local_asr.is_model_installed(local_asr.MODEL_NAME))

    def test_transcribe_wav_file_configures_and_reuses_qwen_recognizer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_dir = create_fake_model(root)
            wav_path = root / "speech.wav"
            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\x00\x00\xff\x7f")

            fake_module = types.SimpleNamespace(OfflineRecognizer=FakeOfflineRecognizer)
            with patch("ibus_voice.local_asr.model_root", return_value=root):
                with patch("ibus_voice.local_asr.importlib.import_module", return_value=fake_module):
                    first_text = local_asr.transcribe_wav_file(wav_path, local_asr.MODEL_NAME)
                    second_text = local_asr.transcribe_wav_file(wav_path, "sensevoice")

        self.assertEqual(first_text, "transcript")
        self.assertEqual(second_text, "transcript")
        self.assertEqual(FakeOfflineRecognizer.build_count, 1)
        self.assertEqual(
            FakeOfflineRecognizer.last_kwargs["conv_frontend"],
            str(model_dir / local_asr.CONV_FRONTEND_FILE),
        )
        self.assertEqual(
            FakeOfflineRecognizer.last_kwargs["encoder"],
            str(model_dir / local_asr.ENCODER_FILE),
        )
        self.assertEqual(
            FakeOfflineRecognizer.last_kwargs["decoder"],
            str(model_dir / local_asr.DECODER_FILE),
        )
        self.assertEqual(
            FakeOfflineRecognizer.last_kwargs["tokenizer"],
            str(model_dir / local_asr.TOKENIZER_DIRECTORY),
        )
        self.assertEqual(FakeOfflineRecognizer.last_kwargs["max_new_tokens"], 512)

    def test_initialize_local_asr_preloads_cached_recognizer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fake_model(root)
            fake_module = types.SimpleNamespace(OfflineRecognizer=FakeOfflineRecognizer)

            with patch("ibus_voice.local_asr.model_root", return_value=root):
                with patch("ibus_voice.local_asr.importlib.import_module", return_value=fake_module):
                    local_asr.initialize_local_asr(local_asr.MODEL_NAME)
                    local_asr.initialize_local_asr(local_asr.MODEL_NAME)

        self.assertEqual(FakeOfflineRecognizer.build_count, 1)

    def test_transcribe_wav_file_with_timeout_fails_cleanly(self) -> None:
        started = time.monotonic()
        with patch("ibus_voice.local_asr.transcribe_wav_file", side_effect=lambda *_args: time.sleep(0.05)):
            with self.assertRaises(local_asr.LocalAsrError) as ctx:
                local_asr.transcribe_wav_file_with_timeout("speech.wav", local_asr.MODEL_NAME, 0.01)

        self.assertLess(time.monotonic() - started, 0.04)
        self.assertIn("timed out", str(ctx.exception))

    def test_pcm16le_to_mono_float32_uses_configured_channel_stride(self) -> None:
        samples = b"\x00\x40\x00\x20\x00\x20\x00\x10"

        mono = local_asr.pcm16le_to_mono_float32(samples, channels=2)

        self.assertEqual(mono, [0.5, 0.25])

    def test_transcribe_pcm16le_bytes_passes_audio_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fake_model(root)
            fake_module = types.SimpleNamespace(OfflineRecognizer=FakeOfflineRecognizer)

            with patch("ibus_voice.local_asr.model_root", return_value=root):
                with patch("ibus_voice.local_asr.importlib.import_module", return_value=fake_module):
                    text = local_asr.transcribe_pcm16le_bytes(
                        b"\x00\x40\x00\x20\x00\x20\x00\x10",
                        16000,
                        local_asr.MODEL_NAME,
                        channels=2,
                    )

        self.assertEqual(text, "transcript")
        accepted = FakeOfflineRecognizer.last_recognizer.streams[0].accepted
        self.assertEqual(accepted, (16000, [0.5, 0.25]))
