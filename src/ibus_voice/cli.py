from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from ibus_voice.audio import PyAudioRecorder
from ibus_voice.correction import build_corrector
from ibus_voice.config import load_config, load_history_path
from ibus_voice.engine import VoiceEngine
from ibus_voice.history import DEFAULT_HISTORY_PATH, SQLiteSessionHistory, format_completed_sessions
from ibus_voice.ibus_service import IBusVoiceService, TextCommitter
from ibus_voice.metadata import render_engines_xml, render_version_text
from ibus_voice.providers.listenhub import ensure_coli_available
from ibus_voice.providers import build_provider
from ibus_voice.types import ProviderFailure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ibus-voice")
    parser.add_argument("--config", help="Path to config.toml")
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
        if config.provider.name.lower() == "listenhub":
            try:
                coli_path = ensure_coli_available()
            except ProviderFailure as exc:
                print(f"config check failed: {exc}", file=sys.stderr)
                return 1
            dependency_status = f" coli={coli_path}"
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


if __name__ == "__main__":
    sys.exit(main())
