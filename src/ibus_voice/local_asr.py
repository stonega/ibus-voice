from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path
import array
import importlib
import os
import shutil
import site
import sys
import tarfile
import tempfile
import urllib.request
import wave


MODEL_NAME = "sensevoice"
MODEL_DIRECTORY_NAME = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"
)
MODEL_CHECK_FILE = "model.int8.onnx"
TOKENS_FILE = "tokens.txt"
DEFAULT_MODEL_ROOT = Path.home() / ".local" / "share" / "ibus-voice" / "models"


class LocalAsrError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    directory_name: str
    url: str
    check_file: str
    tokens_file: str


SENSEVOICE_MODEL = ModelSpec(
    name=MODEL_NAME,
    directory_name=MODEL_DIRECTORY_NAME,
    url=MODEL_URL,
    check_file=MODEL_CHECK_FILE,
    tokens_file=TOKENS_FILE,
)


def ensure_supported_model(model_name: str) -> None:
    if model_name != MODEL_NAME:
        raise LocalAsrError(
            f'unsupported local model "{model_name}"; only "{MODEL_NAME}" is available'
        )


def model_root() -> Path:
    override = os.environ.get("IBUS_VOICE_MODEL_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_MODEL_ROOT


def model_directory(model_name: str) -> Path:
    ensure_supported_model(model_name)
    return model_root() / SENSEVOICE_MODEL.directory_name


def is_model_installed(model_name: str) -> bool:
    directory = model_directory(model_name)
    return (directory / SENSEVOICE_MODEL.check_file).is_file() and (directory / SENSEVOICE_MODEL.tokens_file).is_file()


def ensure_runtime_dependency() -> None:
    try:
        importlib.import_module("sherpa_onnx")
    except ImportError as exc:
        user_site = site.getusersitepackages()
        install_command = f"{sys.executable} -m pip install sherpa-onnx"
        raise LocalAsrError(
            "local ASR runtime is unavailable because this interpreter could not import "
            f"'sherpa_onnx': interpreter={sys.executable} user_site={user_site}. "
            f"Install it into this Python with: {install_command}"
        ) from exc


def runtime_status(model_name: str) -> str:
    ensure_supported_model(model_name)
    ensure_runtime_dependency()
    return "installed" if is_model_installed(model_name) else "auto-download"


def _download_model_archive(spec: ModelSpec, destination: Path) -> None:
    request = urllib.request.Request(spec.url, headers={"User-Agent": "ibus-voice"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    resolved_destination = destination.resolve()
    for member in archive.getmembers():
        member_path = (resolved_destination / member.name).resolve()
        if os.path.commonpath([str(resolved_destination), str(member_path)]) != str(resolved_destination):
            raise LocalAsrError(f"refusing to extract unexpected archive path: {member.name}")
    archive.extractall(resolved_destination)


def ensure_model_installed(model_name: str) -> Path:
    ensure_supported_model(model_name)
    directory = model_directory(model_name)
    if is_model_installed(model_name):
        return directory

    root = model_root()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ibus-voice-model-", dir=root) as tmpdir:
        archive_path = Path(tmpdir) / f"{SENSEVOICE_MODEL.directory_name}.tar.bz2"
        try:
            _download_model_archive(SENSEVOICE_MODEL, archive_path)
            with tarfile.open(archive_path, mode="r:bz2") as archive:
                _safe_extract(archive, root)
        except Exception as exc:
            raise LocalAsrError(f"failed to install local ASR model: {exc}") from exc

    if not is_model_installed(model_name):
        raise LocalAsrError("local ASR model installation completed but required files were missing")
    return directory


def _read_wave_mono_float32(path: Path) -> tuple[int, list[float]]:
    try:
        with wave.open(str(path), "rb") as handle:
            sample_rate = handle.getframerate()
            sample_width = handle.getsampwidth()
            channel_count = handle.getnchannels()
            frame_count = handle.getnframes()
            pcm = handle.readframes(frame_count)
    except wave.Error as exc:
        raise LocalAsrError(f"unsupported WAV input: {exc}") from exc

    if sample_width != 2:
        raise LocalAsrError(f"unsupported WAV sample width: {sample_width * 8}-bit")
    if channel_count < 1:
        raise LocalAsrError("WAV input did not contain any channels")

    samples = array.array("h")
    samples.frombytes(pcm)
    channel_stride = channel_count
    mono_samples = [samples[index] / 32768.0 for index in range(0, len(samples), channel_stride)]
    return sample_rate, mono_samples


def transcribe_wav_file(path: str | os.PathLike[str], model_name: str) -> str:
    ensure_runtime_dependency()
    model_dir = ensure_model_installed(model_name)
    sherpa_onnx = importlib.import_module("sherpa_onnx")

    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(model_dir / SENSEVOICE_MODEL.check_file),
        tokens=str(model_dir / SENSEVOICE_MODEL.tokens_file),
        use_itn=True,
        num_threads=2,
        debug=False,
    )
    sample_rate, samples = _read_wave_mono_float32(Path(path))
    stream = recognizer.create_stream()
    stream.accept_waveform(sample_rate, samples)
    recognizer.decode_stream(stream)

    result = stream.result
    if hasattr(result, "text"):
        return str(result.text).strip()
    if isinstance(result, dict):
        return str(result.get("text", "")).strip()
    return str(result).strip()


def transcribe_wav_file_with_timeout(
    path: str | os.PathLike[str],
    model_name: str,
    timeout_seconds: float,
) -> str:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(transcribe_wav_file, path, model_name)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise LocalAsrError(f"transcription timed out after {timeout_seconds}s") from exc
