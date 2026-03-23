# Runtime Design

## Python Package Layout

- `config.py`: config loading and validation
- `audio.py`: recorder abstractions and PyAudio integration
- `audio.py`: recorder abstractions, PCM capture, and WAV payload encoding
- `engine.py`: state machine for push-to-talk dictation
- `providers/`: normalized speech backend adapters
- `ibus_service.py`: IBus engine registration, hotkey matching, and commit boundary

## Runtime Behavior

- `ibus-voice` is active only when the engine is selected in IBus
- recording starts on push-to-talk press
- IBus auxiliary text shows `Listening...` while push-to-talk is held
- recording stops on release
- audio is sent to the selected provider
- only final text is committed
- OpenAI receives multipart file uploads
- Gemini receives inline audio data through `generateContent`

## Current Gaps

- IBus registration is implemented, but desktop packaging and engine XML integration still need distro-level testing
- packaging scripts prepare artifacts but do not publish packages
