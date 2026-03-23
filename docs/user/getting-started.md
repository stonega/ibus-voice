# Getting Started

This project is in an early stage.

System install for GNOME and normal desktop use:

1. Review and edit `examples/config.toml` or let the installer copy it to `~/.config/ibus-voice/config.toml`
   If you want transcript cleanup, also copy the example prompt files into `~/.config/ibus-voice/`.
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
6. Switch to the `ibus-voice` engine and use the configured push-to-talk hotkey

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
```

With cleanup disabled, `ibus-voice` commits the raw speech-to-text result.

With cleanup enabled, it sends the transcript to an OpenAI-compatible text model and commits the cleaned result. If that second step fails, the raw transcript is still committed.
