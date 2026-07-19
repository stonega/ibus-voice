from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from threading import RLock
import array
import hashlib
import importlib
import os
import site
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import wave


MODEL_NAME = "qwen3-asr-0.6b"
LEGACY_MODEL_NAMES = frozenset({"sensevoice"})
MODEL_DIRECTORY_NAME = "sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25"
MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25.tar.bz2"
)
MODEL_SHA256 = "393f8a14e2f5fb96746aaab342997a40641001fbd5bf9592a080a8329178ee96"
CONV_FRONTEND_FILE = "conv_frontend.onnx"
ENCODER_FILE = "encoder.int8.onnx"
DECODER_FILE = "decoder.int8.onnx"
TOKENIZER_DIRECTORY = "tokenizer"
TOKENIZER_FILES = ("merges.txt", "tokenizer_config.json", "vocab.json")
MODEL_REQUIRED_FILES = (
    CONV_FRONTEND_FILE,
    ENCODER_FILE,
    DECODER_FILE,
    *(f"{TOKENIZER_DIRECTORY}/{filename}" for filename in TOKENIZER_FILES),
)
DEFAULT_MODEL_ROOT = Path.home() / ".local" / "share" / "ibus-voice" / "models"
DEFAULT_RUNTIME_ROOT = Path.home() / ".local" / "share" / "ibus-voice" / "runtime"
WHEELHOUSE_DIR_NAME = "wheelhouse"
MINIMUM_SHERPA_ONNX_VERSION = "1.12.36"
QWEN3_ASR_MAX_TOKENS = 512
QWEN3_ASR_NUM_THREADS = 2


class LocalAsrError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    directory_name: str
    url: str
    sha256: str
    required_files: tuple[str, ...]


QWEN3_ASR_MODEL = ModelSpec(
    name=MODEL_NAME,
    directory_name=MODEL_DIRECTORY_NAME,
    url=MODEL_URL,
    sha256=MODEL_SHA256,
    required_files=MODEL_REQUIRED_FILES,
)

_RECOGNIZER_LOCK = RLock()
_cached_recognizer: object | None = None
_cached_recognizer_key: tuple[str, Path] | None = None


def normalize_model_name(model_name: str) -> str:
    normalized = model_name.strip().casefold()
    if normalized in LEGACY_MODEL_NAMES:
        return MODEL_NAME
    if normalized == MODEL_NAME:
        return MODEL_NAME
    raise LocalAsrError(
        f'unsupported local model "{model_name}"; only "{MODEL_NAME}" is available'
    )


def ensure_supported_model(model_name: str) -> None:
    normalize_model_name(model_name)


def model_root() -> Path:
    override = os.environ.get("IBUS_VOICE_MODEL_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_MODEL_ROOT


def model_directory(model_name: str) -> Path:
    normalize_model_name(model_name)
    return model_root() / QWEN3_ASR_MODEL.directory_name


def is_model_installed(model_name: str) -> bool:
    directory = model_directory(model_name)
    return all(
        (directory / relative_path).is_file()
        and (directory / relative_path).stat().st_size > 0
        for relative_path in QWEN3_ASR_MODEL.required_files
    )


def ensure_runtime_dependency() -> None:
    try:
        sherpa_onnx = importlib.import_module("sherpa_onnx")
        _validate_runtime_dependency(sherpa_onnx)
        return
    except ImportError:
        pass

    runtime_site = runtime_site_packages()
    wheelhouse = bundled_wheelhouse()
    if runtime_site.is_dir():
        runtime_version = _runtime_site_dependency_version(runtime_site)
        parsed_runtime_version = _parse_version(runtime_version or "")
        parsed_minimum_version = _parse_version(MINIMUM_SHERPA_ONNX_VERSION)
        if (
            wheelhouse is not None
            and parsed_runtime_version is not None
            and parsed_minimum_version is not None
            and parsed_runtime_version < parsed_minimum_version
        ):
            try:
                _install_runtime_from_wheelhouse(wheelhouse, runtime_site)
            except Exception as exc:
                raise LocalAsrError(
                    f"failed to upgrade local ASR runtime from bundled wheelhouse: {exc}"
                ) from exc
        _activate_runtime_site_packages(runtime_site)
        try:
            sherpa_onnx = importlib.import_module("sherpa_onnx")
            _validate_runtime_dependency(sherpa_onnx)
            return
        except ImportError:
            pass

    if wheelhouse is not None:
        try:
            _install_runtime_from_wheelhouse(wheelhouse, runtime_site)
            _activate_runtime_site_packages(runtime_site)
            sherpa_onnx = importlib.import_module("sherpa_onnx")
            _validate_runtime_dependency(sherpa_onnx)
            return
        except Exception as exc:
            raise LocalAsrError(f"failed to install local ASR runtime from bundled wheelhouse: {exc}") from exc

    user_site = site.getusersitepackages()
    install_command = (
        f"{sys.executable} -m pip install --upgrade "
        f"'sherpa-onnx>={MINIMUM_SHERPA_ONNX_VERSION}'"
    )
    raise LocalAsrError(
        "local ASR runtime is unavailable because this interpreter could not import "
        f"'sherpa_onnx': interpreter={sys.executable} user_site={user_site}. "
        f"Install it into this Python with: {install_command}"
    )


def _validate_runtime_dependency(sherpa_onnx: object) -> None:
    offline_recognizer = getattr(sherpa_onnx, "OfflineRecognizer", None)
    has_qwen_api = callable(getattr(offline_recognizer, "from_qwen3_asr", None))
    installed_version = str(getattr(sherpa_onnx, "__version__", "unknown"))
    parsed_version = _parse_version(installed_version)
    minimum_version = _parse_version(MINIMUM_SHERPA_ONNX_VERSION)
    has_supported_version = (
        parsed_version is None
        or minimum_version is None
        or parsed_version >= minimum_version
    )
    if has_qwen_api and has_supported_version:
        return

    install_command = (
        f"{sys.executable} -m pip install --upgrade "
        f"'sherpa-onnx>={MINIMUM_SHERPA_ONNX_VERSION}'"
    )
    raise LocalAsrError(
        "local ASR runtime does not support Qwen3-ASR: "
        f"installed sherpa-onnx version={installed_version}. "
        f"Upgrade it with: {install_command}"
    )


def _parse_version(version: str) -> tuple[int, int, int] | None:
    parts = version.split(".", maxsplit=3)
    if len(parts) < 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def runtime_root() -> Path:
    override = os.environ.get("IBUS_VOICE_RUNTIME_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_RUNTIME_ROOT


def runtime_site_packages() -> Path:
    python_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    return runtime_root() / python_tag


def _runtime_site_dependency_version(path: Path) -> str | None:
    for distribution in importlib_metadata.distributions(path=[str(path)]):
        package_name = str(distribution.metadata.get("Name", "")).casefold().replace("_", "-")
        if package_name == "sherpa-onnx":
            return distribution.version
    return None


def _activate_runtime_site_packages(path: Path) -> None:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def bundled_wheelhouse() -> Path | None:
    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        candidate = parent / WHEELHOUSE_DIR_NAME
        if candidate.is_dir():
            return candidate
    return None


def _install_runtime_from_wheelhouse(wheelhouse: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-index",
                "--upgrade",
                f"--find-links={wheelhouse}",
                "--target",
                str(destination),
                "sherpa-onnx",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise LocalAsrError(f"missing pip for interpreter {sys.executable}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise LocalAsrError(stderr) from exc

    if result.returncode != 0:
        raise LocalAsrError("pip installation did not complete successfully")


def runtime_status(model_name: str) -> str:
    ensure_supported_model(model_name)
    ensure_runtime_dependency()
    return "installed" if is_model_installed(model_name) else "auto-download"


def _download_model_archive(spec: ModelSpec, destination: Path) -> None:
    request = urllib.request.Request(spec.url, headers={"User-Agent": "ibus-voice"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as handle:
        digest = hashlib.sha256()
        while chunk := response.read(1024 * 1024):
            handle.write(chunk)
            digest.update(chunk)

    actual_sha256 = digest.hexdigest()
    if actual_sha256 != spec.sha256:
        destination.unlink(missing_ok=True)
        raise LocalAsrError(
            "downloaded local ASR model failed checksum validation: "
            f"expected {spec.sha256}, got {actual_sha256}"
        )


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    resolved_destination = destination.resolve()
    for member in archive.getmembers():
        member_path = (resolved_destination / member.name).resolve()
        if os.path.commonpath([str(resolved_destination), str(member_path)]) != str(resolved_destination):
            raise LocalAsrError(f"refusing to extract unexpected archive path: {member.name}")
    archive.extractall(resolved_destination)


def ensure_model_installed(model_name: str) -> Path:
    canonical_name = normalize_model_name(model_name)
    directory = model_directory(canonical_name)
    if is_model_installed(canonical_name):
        return directory

    root = model_root()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ibus-voice-model-", dir=root) as tmpdir:
        archive_path = Path(tmpdir) / f"{QWEN3_ASR_MODEL.directory_name}.tar.bz2"
        try:
            _download_model_archive(QWEN3_ASR_MODEL, archive_path)
            with tarfile.open(archive_path, mode="r:bz2") as archive:
                _safe_extract(archive, root)
        except Exception as exc:
            raise LocalAsrError(f"failed to install local ASR model: {exc}") from exc

    if not is_model_installed(canonical_name):
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


def pcm16le_to_mono_float32(audio_bytes: bytes, *, channels: int = 1, sample_width: int = 2) -> list[float]:
    if channels < 1:
        raise LocalAsrError("PCM input did not contain any channels")
    if sample_width != 2:
        raise LocalAsrError(f"unsupported PCM sample width: {sample_width * 8}-bit")
    if len(audio_bytes) % 2 != 0:
        raise LocalAsrError("PCM input did not contain aligned 16-bit samples")
    samples = array.array("h")
    samples.frombytes(audio_bytes)
    return [samples[index] / 32768.0 for index in range(0, len(samples), channels)]


def _build_recognizer(sherpa_onnx: object, model_dir: Path) -> object:
    return sherpa_onnx.OfflineRecognizer.from_qwen3_asr(
        conv_frontend=str(model_dir / CONV_FRONTEND_FILE),
        encoder=str(model_dir / ENCODER_FILE),
        decoder=str(model_dir / DECODER_FILE),
        tokenizer=str(model_dir / TOKENIZER_DIRECTORY),
        num_threads=QWEN3_ASR_NUM_THREADS,
        sample_rate=16_000,
        feature_dim=128,
        decoding_method="greedy_search",
        debug=False,
        provider="cpu",
        max_total_len=QWEN3_ASR_MAX_TOKENS,
        max_new_tokens=QWEN3_ASR_MAX_TOKENS,
        temperature=1e-6,
        top_p=0.8,
        seed=42,
        hotwords="",
    )


def _recognizer_for_model(model_name: str) -> object:
    global _cached_recognizer, _cached_recognizer_key

    canonical_name = normalize_model_name(model_name)
    expected_directory = model_directory(canonical_name)
    cache_key = (canonical_name, expected_directory)
    if _cached_recognizer is not None and _cached_recognizer_key == cache_key:
        return _cached_recognizer

    ensure_runtime_dependency()
    model_dir = ensure_model_installed(canonical_name)
    sherpa_onnx = importlib.import_module("sherpa_onnx")
    recognizer = _build_recognizer(sherpa_onnx, model_dir)
    _cached_recognizer = recognizer
    _cached_recognizer_key = (canonical_name, model_dir)
    return recognizer


def _reset_recognizer_cache() -> None:
    global _cached_recognizer, _cached_recognizer_key

    with _RECOGNIZER_LOCK:
        _cached_recognizer = None
        _cached_recognizer_key = None


def _result_text(result: object) -> str:
    if hasattr(result, "text"):
        return str(result.text).strip()
    if isinstance(result, dict):
        return str(result.get("text", "")).strip()
    return str(result).strip()


def _transcribe_samples(samples: list[float], sample_rate: int, model_name: str) -> str:
    with _RECOGNIZER_LOCK:
        recognizer = _recognizer_for_model(model_name)
        stream = recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)
        recognizer.decode_stream(stream)
        return _result_text(stream.result)


def initialize_local_asr(model_name: str) -> None:
    with _RECOGNIZER_LOCK:
        _recognizer_for_model(model_name)


def transcribe_pcm16le_bytes(
    audio_bytes: bytes,
    sample_rate: int,
    model_name: str,
    *,
    channels: int = 1,
    sample_width: int = 2,
) -> str:
    return _transcribe_samples(
        pcm16le_to_mono_float32(
            audio_bytes,
            channels=channels,
            sample_width=sample_width,
        ),
        sample_rate,
        model_name,
    )


def transcribe_wav_file(path: str | os.PathLike[str], model_name: str) -> str:
    sample_rate, samples = _read_wave_mono_float32(Path(path))
    return _transcribe_samples(samples, sample_rate, model_name)


def transcribe_wav_file_with_timeout(
    path: str | os.PathLike[str],
    model_name: str,
    timeout_seconds: float,
) -> str:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(transcribe_wav_file, path, model_name)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as exc:
        future.cancel()
        raise LocalAsrError(f"transcription timed out after {timeout_seconds}s") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
