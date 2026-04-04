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

## Credits

Feature-gap analysis for this phase was informed by the Koe project and its public documentation:

- https://koe.li/docs

`ibus-voice` remains a Linux IBus project with its own architecture and scope.

## License

This project is released under the MIT License. See `LICENSE`.
