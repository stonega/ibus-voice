# ibus-voice

`ibus-voice` is a Linux voice dictation project for the IBus input framework. It is intended to let users speak into a microphone, transcribe that audio with a local or remote speech-to-text backend, and commit the recognized text into the currently focused application through IBus.

The repository is focused on practical Linux desktop integration: audio capture, backend selection, IBus engine behavior, packaging, and local development workflows.

## Development

Run the test suite with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Validate a config file with:

```bash
PYTHONPATH=src python3 -m ibus_voice.cli --config examples/config.toml --check
```

Install local Python runtime dependencies for development with:

```bash
python3 -m pip install -e '.[runtime,local]'
```

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
- both package builders require `python3 -m pip`

For GNOME or standard desktop integration, prefer the system installer because IBus reads component XML from `/usr/share/ibus/component` by default:

```bash
sudo ./scripts/install-system.sh
```

## Config Files

The installers and first run use `~/.config/ibus-voice/` as the default config directory.

- `config.toml`: main runtime configuration
- `dictionary.txt`: canonical terms used for transcription bias and correction prompting; default entries include `IBus` and `ibus-voice`
- `system_prompt.txt`: stable correction policy
- `user_prompt.txt`: prompt template that inserts transcript, history, and dictionary content

Tip: after changing `config.toml`, restart IBus before testing the new settings so the running `ibus-voice` engine reloads the updated config.
Tip: `dictionary.txt` is currently not used by the `listenhub` provider. Dictionary biasing only applies to the remote providers and correction prompting.

See `docs/user/configuration.md` for the full configuration reference.

Example self-hosted OpenAI-compatible transcription config:

```toml
[provider]
name = "openai_transcriptions"
endpoint = "http://host:port/v1/audio/transcriptions"
model = "whisper-1"
timeout_seconds = 10
dictionary_path = "dictionary.txt"
```

## CLI Usage

The installed launcher is `ibus-voice`.

```bash
ibus-voice --check
ibus-voice --add-word "OpenAI"
ibus-voice --config ~/.config/ibus-voice/config.toml --check
ibus-voice --xml
ibus-voice --version
ibus-voice --history
ibus-voice --history --history-limit 50
ibus-voice --history-path ~/.config/ibus-voice/history.db --history
```

- `--check`: validate the config and provider dependencies
- `--add-word`: append a canonical term to the configured dictionary file if it is not already present
- `--xml`: print the IBus engine XML metadata
- `--version`: print CLI version information
- `--history`: print completed dictation session history
- `--config`: use a specific `config.toml`
- `--history-path`: read history from a specific SQLite database

## Usage

After installing, add `ibus-voice` from your desktop environment's input source settings.

Once `ibus-voice` is selected as an input source, long-press `Ctrl+Space` to get started with voice input.

## Credits

Feature-gap analysis for this phase was informed by the Koe project and its public documentation:

- https://koe.li/docs

Earlier local-provider work in this repository was also informed by the upstream `marswaveai/coli` project:

- https://github.com/marswaveai/coli

`ibus-voice` remains a Linux IBus project with its own architecture and scope.

## License

This project is released under the MIT License. See `LICENSE`.
