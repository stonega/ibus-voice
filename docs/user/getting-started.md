# Getting Started

`ibus-voice` `v0.6.0` is the current early alpha release.

System install for GNOME and normal desktop use:

1. Review and edit `examples/config.toml` or let the installer copy it to `~/.config/ibus-voice/config.toml`
   If you want transcript correction, also copy the example prompt files into `~/.config/ibus-voice/`.
   If you plan to use the ListenHub provider from source, install the local Python dependencies before the final config check.
2. Run:

```bash
sudo ./scripts/install-system.sh
```

3. The installer refreshes IBus automatically. If the engine still does not appear, restart IBus manually:

```bash
ibus restart
```

4. If `ibus-voice` still does not appear in GNOME Settings, log out and log back in
5. Open IBus Preferences and add `ibus-voice` as an input method
   `ibus-voice` is exposed under both English and Chinese language groups so it can be added from either list.
6. Switch to the `ibus-voice` engine and hold the configured push-to-talk hotkey while speaking, then release it to stop recording

Local install is only for development runs where you control how `ibus-daemon` starts. IBus reads component XML from `/usr/share/ibus/component` by default; custom component directories require `IBUS_COMPONENT_PATH`.

For a local development session:

```bash
./scripts/install-local.sh
IBUS_COMPONENT_PATH="$HOME/.local/share/ibus-voice/component" ibus-daemon -rdx
```

Useful commands:

```bash
PYTHONPATH=src python3 -m ibus_voice.cli --xml
PYTHONPATH=src python3 -m ibus_voice.cli --config examples/config.toml --check
PYTHONPATH=src python3 -m ibus_voice.cli --history
python3 -m pip install -e '.[runtime,local]'
```

If `--check` says `install the Python package 'sherpa-onnx'` even though you already installed it, install it into the same interpreter that runs `ibus-voice`. The packaged launchers use `/usr/bin/python3`:

```bash
/usr/bin/python3 -m pip install sherpa-onnx
```

Packaged installs also include an offline `sherpa-onnx` wheel bundle. If the vendored runtime does not match the target machine's Python minor version, `ibus-voice` will try to reinstall the matching wheel into `~/.local/share/ibus-voice/runtime/` on first local-provider use.

Package builds:

```bash
./scripts/build-deb.sh
./scripts/build-rpm.sh
```

`build-deb.sh` requires `dpkg-deb` and `python3 -m pip`. `build-rpm.sh` requires `rpmbuild` and `python3 -m pip`.

The installed CLI launcher is `ibus-voice`.

With correction disabled, `ibus-voice` commits the raw speech-to-text result.

With correction enabled, it sends the transcript to an OpenAI-compatible text model and commits the corrected result. If that second step fails, the raw transcript is still committed.

With `provider.name = "listenhub"`, `--check` validates that the local Python ASR runtime is available and reports whether the SenseVoice model is already installed or will auto-download on first use.
