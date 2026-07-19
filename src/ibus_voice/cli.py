from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from ibus_voice.audio import PyAudioRecorder
from ibus_voice.correction import build_corrector
from ibus_voice.config import AppConfig, load_config, load_history_path
from ibus_voice.engine import VoiceEngine
from ibus_voice.history import DEFAULT_HISTORY_PATH, SQLiteSessionHistory, format_completed_sessions
from ibus_voice.ibus_service import IBusVoiceService, TextCommitter
from ibus_voice.local_asr import MODEL_NAME as DEFAULT_LOCAL_MODEL
from ibus_voice.metadata import render_engines_xml, render_version_text
from ibus_voice.providers.listenhub import ensure_local_provider_ready
from ibus_voice.providers import build_provider
from ibus_voice.types import ProviderFailure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ibus-voice")
    parser.add_argument("--config", help="Path to config.toml")
    parser.add_argument("--add-word", help="Add a canonical term to configured dictionary files")
    parser.add_argument("--check", action="store_true", help="Validate config and dependencies")
    parser.add_argument("--ibus", action="store_true", help="Run as an IBus engine process")
    parser.add_argument("--xml", action="store_true", help="Print IBus engine XML")
    parser.add_argument("--version", action="store_true", help="Print CLI version information")
    parser.add_argument("--history", action="store_true", help="Print completed session history")
    parser.add_argument("--history-limit", type=int, default=20, help="Number of history records to print")
    parser.add_argument("--history-path", help="Path to history.db")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.xml:
        print(render_engines_xml(), end="")
        return 0
    if args.version:
        print(render_version_text())
        return 0
    if args.add_word is not None:
        try:
            config = load_config(args.config)
            updated_paths = add_dictionary_word(config, args.add_word)
        except ValueError as exc:
            print(f"failed to add dictionary word: {exc}", file=sys.stderr)
            return 1
        for path, added in updated_paths:
            status = "added" if added else "already present"
            print(f"{status}: {path}")
        return 0
    if args.history:
        history_path = Path(args.history_path).expanduser() if args.history_path else None
        if history_path is None and args.config:
            history_path = load_history_path(args.config)
        if history_path is None:
            history_path = DEFAULT_HISTORY_PATH
        try:
            history = SQLiteSessionHistory(history_path)
            print(format_completed_sessions(history.list_completed_sessions(limit=max(args.history_limit, 1))))
            return 0
        except Exception as exc:
            print(f"failed to read history: {history_path}: {exc}", file=sys.stderr)
            return 1
    config = load_config(args.config)
    provider = build_provider(config.provider)
    if args.check:
        correction_status = "enabled" if config.correction and config.correction.enabled else "disabled"
        dependency_status = ""
        provider_name = config.provider.name.lower()
        local_model = None
        if provider_name == "listenhub":
            local_model = config.provider.model
        elif provider_name == "openai_transcriptions":
            local_model = DEFAULT_LOCAL_MODEL
        if local_model is not None:
            try:
                local_runtime = ensure_local_provider_ready(local_model)
            except ProviderFailure as exc:
                print(f"config check failed: {exc}", file=sys.stderr)
                return 1
            dependency_status = f" local_asr={local_runtime}"
        print(
            "config ok: "
            f"provider={config.provider.name} model={config.provider.model} correction={correction_status}{dependency_status}"
        )
        return 0
    corrector = build_corrector(config.correction)
    recorder = PyAudioRecorder(config.audio)
    history = SQLiteSessionHistory(config.history.path)
    engine = VoiceEngine(
        recorder=recorder,
        provider=provider,
        committer=TextCommitter(),
        corrector=corrector,
        history=history,
    )
    service = IBusVoiceService(config=config, voice_engine=engine)
    return service.run()


def add_dictionary_word(config: AppConfig, word: str) -> list[tuple[Path, bool]]:
    normalized_word = word.strip()
    if not normalized_word:
        raise ValueError("word must not be empty")

    dictionary_paths: list[Path] = []
    seen_paths: set[Path] = set()

    for path in _iter_dictionary_paths(config):
        if path in seen_paths:
            continue
        seen_paths.add(path)
        dictionary_paths.append(path)

    if not dictionary_paths:
        raise ValueError("no dictionary_path configured")

    results: list[tuple[Path, bool]] = []
    for path in dictionary_paths:
        results.append((path, _append_dictionary_word(path, normalized_word)))
    return results


def _iter_dictionary_paths(config: AppConfig) -> list[Path]:
    paths: list[Path] = []
    if config.provider.dictionary_path is not None:
        paths.append(config.provider.dictionary_path)
    if config.correction and config.correction.dictionary_path is not None:
        paths.append(config.correction.dictionary_path)
    return paths


def _append_dictionary_word(path: Path, word: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_text = ""
    existing_words = []
    if path.exists():
        existing_text = path.read_text(encoding="utf-8")
        existing_words = [line.strip() for line in existing_text.splitlines()]
    if word in existing_words:
        return False

    prefix = ""
    if existing_text and not existing_text.endswith("\n"):
        prefix = "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}{word}\n")
    return True


if __name__ == "__main__":
    sys.exit(main())
