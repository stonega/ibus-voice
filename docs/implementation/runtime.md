# Runtime Design

## Python Package Layout

- `config.py`: config loading and validation
- `audio.py`: recorder abstractions and PyAudio integration
- `audio.py`: recorder abstractions, PCM capture, and WAV payload encoding
- `correction.py`: optional OpenAI-compatible transcript correction
- `engine.py`: state machine for push-to-talk dictation
- `history.py`: SQLite persistence for completed dictation sessions
- `providers/`: normalized speech backend adapters
- `ibus_service.py`: IBus engine registration, hotkey matching, and commit boundary

## Runtime Behavior

- `ibus-voice` is active only when the engine is selected in IBus
- recording starts only while the configured push-to-talk chord is held
- IBus auxiliary text shows an animated `🎙...` listening indicator while push-to-talk is held
- recording stops as soon as the trigger key or one of its required modifiers is released
- audio is sent to the selected provider
- OpenAI and Gemini send a built-in ASR prompt that preserves spoken language and mixed-language dictation without translation
- if `dictionary.txt` exists, provider-specific ASR prompts also bias transcription toward canonical terms
- OpenAI and Gemini reject prompt-echo and audio-refusal text such as "unable to process audio" as provider failures instead of committing that text
- if configured, the raw transcript is sent to a correction model before commit
- correction templates can use transcript text, recent session history, and dictionary content
- correction failures fall back to the raw transcript
- only final text is committed
- successful committed sessions are appended to the configured history database path
- correction token usage is persisted in session metadata when the correction response includes `usage`
- OpenAI receives multipart file uploads
- Gemini receives inline audio data through `generateContent`
- ListenHub shells out to the local `coli asr` CLI with a temporary WAV file

## Current Gaps

- IBus registration is implemented, but installed-engine behavior still needs distro-level testing
- package build scripts produce `.deb` and `.rpm` artifacts, but installation and desktop integration still need distro-level validation
