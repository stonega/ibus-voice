from __future__ import annotations

import argparse
import logging
import sys

from ibus_voice.audio import PyAudioRecorder
from ibus_voice.cleanup import build_cleaner
from ibus_voice.config import load_config
from ibus_voice.engine import VoiceEngine
from ibus_voice.history import SQLiteSessionHistory
from ibus_voice.ibus_service import IBusVoiceService, TextCommitter
from ibus_voice.metadata import render_engines_xml
from ibus_voice.providers import build_provider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ibus-voice")
    parser.add_argument("--config", help="Path to config.toml")
    parser.add_argument("--check", action="store_true", help="Validate config and dependencies")
    parser.add_argument("--ibus", action="store_true", help="Run as an IBus engine process")
    parser.add_argument("--xml", action="store_true", help="Print IBus engine XML")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.xml:
        print(render_engines_xml(), end="")
        return 0
    config = load_config(args.config)
    provider = build_provider(config.provider)
    cleaner = build_cleaner(config.cleanup)
    recorder = PyAudioRecorder(config.audio)
    history = SQLiteSessionHistory()
    engine = VoiceEngine(
        recorder=recorder,
        provider=provider,
        committer=TextCommitter(),
        cleaner=cleaner,
        history=history,
    )
    if args.check:
        cleanup_status = "enabled" if config.cleanup and config.cleanup.enabled else "disabled"
        print(
            "config ok: "
            f"provider={config.provider.name} model={config.provider.model} cleanup={cleanup_status}"
        )
        return 0
    service = IBusVoiceService(config=config, voice_engine=engine)
    return service.run()


if __name__ == "__main__":
    sys.exit(main())
