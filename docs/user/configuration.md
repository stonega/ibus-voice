# Configuration

`ibus-voice` uses a TOML config file.

Default location:

- `~/.config/ibus-voice/config.toml`

Example:

```toml
[provider]
name = "openai"
api_key = "replace-me"
model = "gpt-4o-transcribe"
timeout_seconds = 30

[cleanup]
enabled = false
base_url = "https://api.openai.com/v1"
api_key = "replace-me"
model = "gpt-4o-mini"
timeout_seconds = 8
system_prompt_path = "cleanup-system-prompt.txt"
user_prompt_path = "cleanup-user-prompt.txt"

[audio]
sample_rate = 16000
channels = 1
chunk_size = 1024
sample_width = 2

[hotkey]
key = "space"
modifiers = ["Control"]
```

To switch providers, change `provider.name` to `gemini` and set a Gemini-compatible model and API key.

Supported provider defaults:

- OpenAI: transcription endpoint using multipart audio upload
- Gemini: `generateContent` with inline audio data

Cleanup notes:

- `cleanup.enabled = false` keeps the current ASR-only behavior
- `cleanup.base_url` must be an OpenAI-compatible API base such as `https://api.openai.com/v1`
- `ibus-voice` appends `/chat/completions` internally
- `system_prompt_path` and `user_prompt_path` are resolved relative to the config file directory when they are not absolute paths
- cleanup prompt files are read when a dictation session runs, so prompt edits apply without reinstalling the engine
- if cleanup fails, `ibus-voice` falls back to the raw transcript instead of failing the whole dictation session

Hotkey notes:

- `key` maps to an IBus key constant such as `space`
- `modifiers` maps to IBus modifier masks such as `Control` or `Shift`

Installer behavior:

- `scripts/install-local.sh` installs a local launcher at `~/.local/bin/ibus-engine-voice`
- the IBus component XML is installed at `~/.local/share/ibus-voice/component/ibus-voice.xml`
- the default config is copied to `~/.config/ibus-voice/config.toml` if it does not already exist
- example cleanup prompt files should be copied manually if you enable cleanup

System installer behavior:

- `scripts/install-system.sh` installs the launcher at `/usr/local/bin/ibus-engine-voice`
- the IBus component XML is installed at `/usr/share/ibus/component/ibus-voice.xml`
- the default config is copied into the invoking user's `~/.config/ibus-voice/config.toml`
- the launcher reads config from the runtime user's default config path
