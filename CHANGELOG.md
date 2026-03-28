# Changelog

## Unreleased

## 0.3.1 - 2026-03-28

- updated GitHub Actions to use newer JavaScript action runtimes and opt into Node 24 now
- added x86_64 and aarch64 package builds in CI and aligned package metadata with the host architecture
- disabled artifact recompression in CI uploads for packaged files
- filtered bundled ListenHub runtime paths out of RPM auto dependency scanning to avoid false solver requirements

## 0.3.0 - 2026-03-28

- made ListenHub the default speech provider with `sensevoice` as the default local model
- added a bundled fixed-width listening indicator so the animated dots render correctly in IBus auxiliary text
- added a dedicated ListenHub provider module and improved provider validation around bundled or PATH-based `coli`
- updated Debian and RPM builds to bundle `@marswave/coli` during packaging and require `nodejs` at runtime
- refreshed user and release documentation for the new default provider and release version

## 0.1.2 - 2026-03-23

- renamed packaged and installed launchers from `ibus-engine-voice` to `ibus-voice` for consistent CLI behavior
- updated Debian and RPM packaging to install `/usr/bin/ibus-voice` and generate matching IBus component XML
- updated local and system uninstall scripts to remove the renamed launcher correctly
- refreshed user documentation to reflect the current launcher name and release version

## 0.1.1 - 2026-03-23

- added SQLite-backed session history persistence and a CLI viewer for completed sessions
- added `dictionary.txt`, `system_prompt.txt`, and `user_prompt.txt` defaults with a cleaner separation between policy and per-session structure
- added configurable history database paths and aligned correction prompt history reads with persisted session history
- added correction token-usage capture when OpenAI-compatible responses return `usage`
- renamed the post-ASR stage to `correction` as the primary config and code path while keeping legacy `cleanup` compatibility

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
