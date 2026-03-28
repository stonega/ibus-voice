# Getting Started

`ibus-voice` `v0.3.1` is the current early alpha release.

System install for GNOME and normal desktop use:

1. Review and edit `examples/config.toml` or let the installer copy it to `~/.config/ibus-voice/config.toml`
   If you want transcript correction, also copy the example prompt files into `~/.config/ibus-voice/`.
   If you plan to use the ListenHub provider with the install scripts instead of a package build, install `coli` with `./scripts/install-coli.sh` before the final config check.
2. Run:

```bash
sudo ./scripts/install-system.sh
```

3. Restart IBus:

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
./scripts/install-coli.sh
```

Package builds:

```bash
./scripts/build-deb.sh
./scripts/build-rpm.sh
```

`build-deb.sh` requires `dpkg-deb` and `npm`. `build-rpm.sh` requires `rpmbuild` and `npm`.

The installed CLI launcher is `ibus-voice`.

With correction disabled, `ibus-voice` commits the raw speech-to-text result.

With correction enabled, it sends the transcript to an OpenAI-compatible text model and commits the corrected result. If that second step fails, the raw transcript is still committed.

With `provider.name = "listenhub"`, `--check` validates that `coli` is either bundled with the installed app or available on `PATH`.
