# Configuration

`ibus-voice` uses a TOML config file.

Default location:

- `~/.config/ibus-voice/config.toml`
- if that file does not exist, `ibus-voice` creates it automatically on first run with the default ListenHub-based config shown below
- first run also creates default `dictionary.txt`, `system_prompt.txt`, and `user_prompt.txt` beside the config if they are missing

Example:

```toml
[provider]
name = "listenhub"
model = "sensevoice"
timeout_seconds = 30
dictionary_path = "dictionary.txt"

[history]
path = "history.db"

[correction]
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

To switch providers, change `provider.name` and update the provider-specific fields:

- `listenhub`: install `coli`, omit `api_key`, and optionally set `model = "sensevoice"` or `model = "whisper-tiny.en"`
- `openai`: set `api_key` and an OpenAI transcription model such as `gpt-4o-transcribe`
- `gemini`: set `api_key` and a Gemini model that supports inline audio input

When `[provider]` is omitted entirely, `ibus-voice` defaults to `listenhub` with `model = "sensevoice"`.

Supported provider defaults:

- OpenAI: transcription endpoint using multipart audio upload
- Gemini: `generateContent` with inline audio data
- ListenHub: local `coli asr` command execution with `sensevoice` as the default model
- OpenAI and Gemini always send a built-in transcription prompt that asks the model to keep the spoken language as-is, avoid translation, and preserve mixed-language dictation
- if `dictionary.txt` exists, OpenAI and Gemini append it to that transcription prompt to bias recognition toward canonical terms
- if a remote provider echoes the prompt or returns refusal text instead of a transcript, `ibus-voice` reports a provider failure such as `non_transcript_response` or `audio_not_processed` and does not commit the text

Local ListenHub notes:

- `listenhub` follows the local ASR flow documented at `https://listenhub.ai/docs/zh/skills/asr`
- install the CLI with `./scripts/install-coli.sh` or `npm install -g @marswave/coli`
- Debian and RPM package builds bundle `@marswave/coli` into the package during the build; install `nodejs` if you want to use the bundled local CLI at runtime
- `ffmpeg` is recommended if you want `coli` to accept non-WAV formats directly, but `ibus-voice` records WAV already
- the current integration assumes `coli asr` prints the transcript to stdout
- `dictionary_path` is currently ignored by the local ListenHub provider because the published CLI docs do not describe a dictionary-bias flag
- `ibus-voice.cli --check` fails fast when `provider.name = "listenhub"` and `coli` is neither bundled with the app nor available on `PATH`

Correction notes:

- `correction.enabled = false` keeps the current ASR-only behavior
- `correction.base_url` must be an OpenAI-compatible API base such as `https://api.openai.com/v1`
- `ibus-voice` appends `/chat/completions` internally
- `dictionary_path`, `system_prompt_path`, and `user_prompt_path` are resolved relative to the config file directory when they are not absolute paths
- correction prompt files are read when a dictation session runs, so prompt edits apply without reinstalling the engine
- `user_prompt.txt` supports `{transcript}`, `{history}`, and `{dictionary}`
- if correction fails, `ibus-voice` falls back to the raw transcript instead of failing the whole dictation session
- legacy `[cleanup]` config is still accepted for compatibility, but new configs should use `[correction]`

Prompt authoring notes:

- put stable correction policy in `system_prompt.txt`
- use `system_prompt.txt` for long-term context such as your domain, terminology, punctuation preferences, and casing rules
- keep `user_prompt.txt` mostly structural; it should usually just arrange the transcript, history, and dictionary blocks
- keep long term names and preferred spellings in `dictionary.txt` instead of turning `system_prompt.txt` into a term list
- the default `system_prompt.txt` assumes the output is inserted directly at the cursor, so it forbids chatty responses and markdown
- for multilingual dictation, make the no-translation rule explicit and tell the model to preserve code-switching instead of normalizing everything into one language

History notes:

- set `[history].path` to choose where completed sessions are stored
- when omitted, the default history path is `~/.config/ibus-voice/history.db`
- the history database is created automatically on startup
- a session row stores the provider, final text, raw text, latency, warning, and serialized metadata
- `history.db` is also available to correction prompts through the `{history}` placeholder
- correction usage tokens are stored in session metadata when the correction provider returns `usage`
- `ibus-voice.cli --history` prints human-readable history records and includes correction token usage when available

Hotkey notes:

- `key` maps to an IBus key constant such as `space`
- `modifiers` maps to IBus modifier masks such as `Control` or `Shift`
- recording stays active only while the full hotkey chord is held and stops when the key or any required modifier is released

Installer behavior:

- `scripts/install-local.sh` installs a local launcher at `~/.local/bin/ibus-voice`
- the IBus component XML is installed at `~/.local/share/ibus-voice/component/ibus-voice.xml`
- the installer copies the default config to `~/.config/ibus-voice/config.toml` if it does not already exist
- example `dictionary.txt`, `system_prompt.txt`, and `user_prompt.txt` should be copied into `~/.config/ibus-voice/`

System installer behavior:

- `scripts/install-system.sh` installs the launcher at `/usr/local/bin/ibus-voice`
- the IBus component XML is installed at `/usr/share/ibus/component/ibus-voice.xml`
- the installer copies the default config into the invoking user's `~/.config/ibus-voice/config.toml`
- the launcher reads config from the runtime user's default config path
