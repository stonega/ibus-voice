# ibus-voice

`ibus-voice` is a Linux project intended to add voice input support to the IBus input framework.

The goal is to make spoken dictation available as a normal input method so text can be entered into desktop applications through IBus, similar to switching to any other keyboard or IME.

## Goals

- Integrate voice input with the Linux desktop through IBus
- Support dictation into standard text fields and applications
- Provide a practical path for local or remote speech-to-text backends
- Keep the user workflow simple: enable the engine, start speaking, and insert text

## Planned Scope

This repository is expected to contain:

- An IBus engine or bridge process
- Audio capture integration for Linux
- Speech-to-text backend integration
- Text commit and candidate handling through IBus APIs
- Configuration for language, trigger keys, and backend selection

## High-Level Design

A typical architecture for this project would look like this:

1. Capture microphone audio from the Linux desktop
2. Stream or batch that audio to a speech recognition backend
3. Convert recognition results into committed or preedit text
4. Send the text into the active application through IBus

Depending on the implementation, the backend may be:

- Fully local, for privacy and offline use
- Remote, for higher accuracy or lower local CPU usage
- Pluggable, so users can choose either option

## Use Cases

- Dictation in editors, browsers, chat apps, and terminals
- Hands-free text entry
- Accessibility support for users who prefer speech over typing
- Mixed workflows where users switch between keyboard input and voice input

## Expected Features

- Start and stop voice dictation
- Insert recognized text at the cursor
- Support multiple languages
- Optional punctuation commands
- Configurable hotkeys or triggers
- Error handling for microphone and backend failures

## Development Notes

If you are building this project, useful implementation areas will likely include:

- `ibus` engine integration
- D-Bus communication
- Microphone capture on Linux
- Speech recognition backend adapters
- Packaging and installation for desktop environments

## Current Status

The repository now contains an initial Python implementation skeleton for:

- config loading
- a push-to-talk engine state machine
- PyAudio-based recorder integration
- OpenAI and Gemini provider adapters
- an IBus engine registration and hotkey handling layer
- unit tests for core behavior

The IBus desktop wiring is now present at the code level and still needs live end-to-end validation with an installed engine on a Linux desktop.

## Development

Run the test suite with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Validate a config file with:

```bash
PYTHONPATH=src python3 -m ibus_voice.cli --config examples/config.toml --check
```

Print IBus engine metadata XML with:

```bash
PYTHONPATH=src python3 -m ibus_voice.cli --xml
```

Install a local development copy with:

```bash
./scripts/install-local.sh
```

For GNOME or standard desktop integration, prefer the system installer because IBus reads component XML from `/usr/share/ibus/component` by default:

```bash
sudo ./scripts/install-system.sh
ibus restart
```

If `ibus-voice` still does not appear in GNOME Settings after installation, log out and log back in.

## License

Add a license file before distribution.
