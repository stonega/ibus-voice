# Examples

This directory contains the baseline local config and prompt files for `ibus-voice`.

- `config.toml`: example runtime config with optional cleanup stage settings
- `cleanup-system-prompt.txt`: default correction rules for the cleanup model
- `cleanup-user-prompt.txt`: template used to pass the raw transcript into cleanup

Copy these files into `~/.config/ibus-voice/` and edit credentials before running the engine.
