# Runtime Design

## Python Package Layout

- `config.py`: config loading and validation
- `audio.py`: recorder abstractions and PyAudio integration
- `audio.py`: recorder abstractions, PCM capture, and WAV payload encoding
- `cleanup.py`: optional OpenAI-compatible transcript cleanup
- `engine.py`: state machine for push-to-talk dictation
- `history.py`: SQLite persistence for completed dictation sessions
- `providers/`: normalized speech backend adapters
- `ibus_service.py`: IBus engine registration, hotkey matching, and commit boundary

## Runtime Behavior

- `ibus-voice` is active only when the engine is selected in IBus
- recording starts on push-to-talk press
- IBus auxiliary text shows `Listening...` while push-to-talk is held
- recording stops on release
- audio is sent to the selected provider
- if `dictionary.txt` exists, provider-specific ASR prompts bias transcription toward canonical terms
- if configured, the raw transcript is sent to a cleanup model before commit
- cleanup templates can use transcript text, recent session history, and dictionary content
- cleanup failures fall back to the raw transcript
- only final text is committed
- successful committed sessions are appended to the configured history database path
- cleanup token usage is persisted in session metadata when the cleanup response includes `usage`
- OpenAI receives multipart file uploads
- Gemini receives inline audio data through `generateContent`

## Current Gaps

- IBus registration is implemented, but installed-engine behavior still needs distro-level testing
- package build scripts produce `.deb` and `.rpm` artifacts, but installation and desktop integration still need distro-level validation
