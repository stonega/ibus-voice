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
dictionary_path = "dictionary.txt"

[history]
path = "history.db"

[cleanup]
enabled = false
base_url = "https://api.openai.com/v1"
api_key = "replace-me"
model = "gpt-4o-mini"
timeout_seconds = 8
dictionary_path = "dictionary.txt"
system_prompt_path = "system_prompt.txt"
user_prompt_path = "user_prompt.txt"

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
- if `dictionary.txt` exists, both providers use it to bias transcription toward canonical terms

Cleanup notes:

- `cleanup.enabled = false` keeps the current ASR-only behavior
- `cleanup.base_url` must be an OpenAI-compatible API base such as `https://api.openai.com/v1`
- `ibus-voice` appends `/chat/completions` internally
- `dictionary_path`, `system_prompt_path`, and `user_prompt_path` are resolved relative to the config file directory when they are not absolute paths
- cleanup prompt files are read when a dictation session runs, so prompt edits apply without reinstalling the engine
- `user_prompt.txt` supports `{transcript}`, `{history}`, and `{dictionary}`
- if cleanup fails, `ibus-voice` falls back to the raw transcript instead of failing the whole dictation session

Prompt authoring notes:

- put stable correction policy in `system_prompt.txt`
- use `system_prompt.txt` for long-term context such as your domain, terminology, punctuation preferences, and casing rules
- keep `user_prompt.txt` mostly structural; it should usually just arrange the transcript, history, and dictionary blocks
- keep long term names and preferred spellings in `dictionary.txt` instead of turning `system_prompt.txt` into a term list
- the default `system_prompt.txt` assumes the output is inserted directly at the cursor, so it forbids chatty responses and markdown

History notes:

- set `[history].path` to choose where completed sessions are stored
- when omitted, the default history path is `~/.config/ibus-voice/history.db`
- the history database is created automatically on startup
- a session row stores the provider, final text, raw text, latency, warning, and serialized metadata
- `history.db` is also available to cleanup prompts through the `{history}` placeholder
- cleanup usage tokens are stored in session metadata when the cleanup provider returns `usage`
- `ibus-voice.cli --history` prints human-readable history records and includes cleanup token usage when available

Hotkey notes:

- `key` maps to an IBus key constant such as `space`
- `modifiers` maps to IBus modifier masks such as `Control` or `Shift`

Installer behavior:

- `scripts/install-local.sh` installs a local launcher at `~/.local/bin/ibus-engine-voice`
- the IBus component XML is installed at `~/.local/share/ibus-voice/component/ibus-voice.xml`
- the default config is copied to `~/.config/ibus-voice/config.toml` if it does not already exist
- example `dictionary.txt`, `system_prompt.txt`, and `user_prompt.txt` should be copied into `~/.config/ibus-voice/`

System installer behavior:

- `scripts/install-system.sh` installs the launcher at `/usr/local/bin/ibus-engine-voice`
- the IBus component XML is installed at `/usr/share/ibus/component/ibus-voice.xml`
- the default config is copied into the invoking user's `~/.config/ibus-voice/config.toml`
- the launcher reads config from the runtime user's default config path
