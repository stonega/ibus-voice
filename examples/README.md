# Examples

This directory contains the baseline local config and prompt files for `ibus-voice`.

- `config.toml`: example runtime config with optional cleanup stage settings
- `dictionary.txt`: canonical terms shared by ASR prompting and cleanup prompting
- `system_prompt.txt`: default correction rules for the cleanup model
- `user_prompt.txt`: template used to pass transcript, history, and dictionary into cleanup

Copy these files into `~/.config/ibus-voice/` and edit credentials before running the engine.
