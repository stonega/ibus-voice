# Changelog

## 0.1.0 - 2026-03-23

Initial alpha release.

- added a Python-based IBus voice engine with push-to-talk dictation flow
- added PyAudio recording support and WAV payload preparation
- added pluggable speech-to-text providers for OpenAI and Gemini
- added optional OpenAI-compatible transcript cleanup with raw-text fallback
- added IBus component and engine metadata generation
- added local and system install scripts for Linux desktop testing
- added Debian and RPM packaging scripts
- added unit test coverage for config parsing, metadata, providers, audio, engine, cleanup, and IBus hotkey handling
