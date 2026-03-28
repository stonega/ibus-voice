# ibus-voice

`ibus-voice` is a Linux project that adds voice input support to the IBus input framework.

The goal is to make spoken dictation available as a normal input method so text can be entered into desktop applications through IBus, similar to switching to any other keyboard or IME.

## Goals

- Integrate voice input with the Linux desktop through IBus
- Support dictation into standard text fields and applications
- Provide a practical path for local or remote speech-to-text backends
- Keep the user workflow simple: enable the engine, start speaking, and insert text

## Scope

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

## v0.3.3 Status

`v0.3.3` is the current packaged alpha milestone. It includes:

- config loading
- a push-to-talk engine state machine
- PyAudio-based recorder integration
- OpenAI and Gemini provider adapters
- a local ListenHub `coli asr` provider adapter
- dictionary-aware OpenAI and Gemini transcription prompting
- optional OpenAI-compatible correction after transcription with transcript history context
- an IBus engine registration and hotkey handling layer
- SQLite history for completed sessions at `~/.config/ibus-voice/history.db`
- local and system install scripts
- Debian and RPM packaging scripts
- unit tests for core behavior

The IBus desktop wiring is present in the codebase, but desktop and distro validation is still limited. This release should be treated as an alpha milestone for Linux users who are comfortable testing an early IBus engine.

Recent design work in this repository has also started closing feature gaps identified by reviewing the Koe voice input project and its public documentation, adapted for Linux and IBus rather than copied directly.

## Release Notes

For the `v0.3.3` milestone:

- supported runtime shape is Python 3.11+ on Linux with IBus
- the interaction model is hold-to-talk dictation: recording runs only while the configured hotkey chord is held
- speech recognition backends are pluggable and currently include OpenAI, Gemini, and ListenHub adapters
- new installs default to the local ListenHub provider with the `sensevoice` model
- transcript correction is optional and falls back to raw text if correction fails
- package artifacts can be built locally as `.deb` and `.rpm`

Known limitations for `v0.3.3`:

- desktop integration has unit coverage but limited live distro validation
- local speech support depends on an installed `coli` binary for the ListenHub provider
- only final text commit is implemented; partial transcript display is not

## Development

Run the test suite with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Validate a config file with:

```bash
PYTHONPATH=src python3 -m ibus_voice.cli --config examples/config.toml --check
```

Install the ListenHub CLI dependency when using the local provider:

```bash
./scripts/install-coli.sh
```

Debian and RPM package builds bundle the ListenHub CLI into the package at build time and require `nodejs` on the target system to run it.

If correction is configured and enabled, `ibus-voice` will:

1. send recorded audio to the configured speech-to-text provider
2. optionally send the raw transcript to a text correction model
3. commit the cleaned text through IBus

If the correction step is disabled or fails, the raw transcript is still committed.

Example prompt files are provided in `examples/system_prompt.txt`, `examples/user_prompt.txt`, and `examples/dictionary.txt`. The intended split is simple: `system_prompt.txt` carries stable correction policy, `user_prompt.txt` stays structural, and `dictionary.txt` holds canonical terms.

Print IBus engine metadata XML with:

```bash
PYTHONPATH=src python3 -m ibus_voice.cli --xml
```

Show recent completed dictation history with:

```bash
PYTHONPATH=src python3 -m ibus_voice.cli --history
PYTHONPATH=src python3 -m ibus_voice.cli --history --history-limit 50
PYTHONPATH=src python3 -m ibus_voice.cli --history --config ~/.config/ibus-voice/config.toml
```

Install a local development copy with:

```bash
./scripts/install-local.sh
```

Build Linux packages locally with:

```bash
./scripts/build-deb.sh
./scripts/build-rpm.sh
```

Artifacts are written to `.dist/packages/`.

Packaging prerequisites:

- `./scripts/build-deb.sh` requires `dpkg-deb`
- `./scripts/build-rpm.sh` requires `rpmbuild`

The packaged launcher is:

- `ibus-voice`

For GNOME or standard desktop integration, prefer the system installer because IBus reads component XML from `/usr/share/ibus/component` by default:

```bash
sudo ./scripts/install-system.sh
ibus restart
```

If `ibus-voice` still does not appear in GNOME Settings after installation, log out and log back in.

## Credits

Feature-gap analysis for this phase was informed by the Koe project and its public documentation:

- https://koe.li/docs

`ibus-voice` remains a Linux IBus project with its own architecture and scope.

## License

This project is released under the MIT License. See `LICENSE`.
