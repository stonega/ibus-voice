# Runtime Design

## Python Package Layout

- `config.py`: config loading and validation
- `audio.py`: recorder abstractions and PyAudio integration
- `audio.py`: recorder abstractions, PCM capture, and WAV payload encoding
- `correction.py`: optional OpenAI-compatible transcript correction
- `engine.py`: state machine for push-to-talk dictation
- `history.py`: SQLite persistence for completed dictation sessions
- `local_asr.py`: built-in Qwen3-ASR model management and offline decoding
- `provider_initialization.py`: background provider setup state and desktop notifications
- `providers/`: normalized speech backend adapters
- `ibus_service.py`: IBus engine registration, hotkey matching, and commit boundary

## Runtime Behavior

- `ibus-voice` is active only when the engine is selected in IBus
- recording starts only while the configured push-to-talk chord is held
- IBus auxiliary text shows an animated fixed-width `🎙 Listening...` indicator while push-to-talk is held
- when the selected provider supports streaming partials, recognized text is surfaced through IBus preedit while the user is still speaking
- when local setup is needed, model download and recognizer preparation run on a daemon worker instead of blocking the IBus event handler
- desktop notifications report when local setup starts, succeeds, or fails; the IBus auxiliary area is reserved for active listening and transcription failures
- the dictation hotkey is consumed without recording while setup is running, and pressing it after a failed setup starts a retry
- recording stops as soon as the trigger key or one of its required modifiers is released
- audio is sent to the selected provider
- OpenAI and Gemini send a built-in ASR prompt that preserves spoken language and mixed-language dictation without translation
- if `dictionary.txt` exists, provider-specific ASR prompts also bias transcription toward canonical terms
- OpenAI and Gemini reject prompt-echo and audio-refusal text such as "unable to process audio" as provider failures instead of committing that text
- if configured, the raw transcript is sent to a correction model before commit
- correction templates can use transcript text, recent session history, and dictionary content
- correction failures fall back to the raw transcript
- partial text remains preedit-only until release; only the final corrected text is committed
- successful committed sessions are appended to the configured history database path
- correction token usage is persisted in session metadata when the correction response includes `usage`
- OpenAI receives multipart file uploads
- Gemini receives inline audio data through `generateContent`
- ListenHub uses the sherpa-onnx Qwen3-ASR 0.6B INT8 runtime and auto-downloads a SHA-256-verified model archive on first use when needed
- the local Qwen recognizer is preloaded by background setup, cached for the process lifetime, and serialized because streaming partials and final transcription share it
- legacy `sensevoice` model configuration is normalized to `qwen3-asr-0.6b` before provider construction

## Current Gaps

- IBus registration is implemented, but installed-engine behavior still needs distro-level testing
- package build scripts produce `.deb` and `.rpm` artifacts, but installation and desktop integration still need distro-level validation
