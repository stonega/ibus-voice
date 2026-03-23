# Koe Feature Gap Analysis

This document compares the supplied Koe documentation snapshot against the current `ibus-voice` project.

The goal is not to copy Koe's macOS product shape. The goal is to identify practical gaps that matter for Linux voice input through IBus.

## Current Capability

`ibus-voice` already has:

- microphone capture through a recorder abstraction
- pluggable speech-to-text providers
- a push-to-talk engine state machine
- final text commit through IBus
- local packaging and install scripts

## Missing Features Found In Koe Docs

### Recommended Next

- LLM correction after ASR, with fallback to raw transcript
- dictionary file support for recurring terms
- prompt files for correction behavior
- session history and local usage stats

### Useful, But Secondary

- tap-to-toggle recording in addition to hold-to-talk
- configurable start/stop/error feedback sounds
- richer runtime state reporting than a single `Listening...` auxiliary message
- explicit troubleshooting docs around failure modes

### Not A Direct Linux/IBus Port

- macOS Accessibility and Input Monitoring permissions
- menu bar UI and floating overlay UI
- clipboard write and simulated paste workflow

On Linux with IBus, the engine can commit text directly, so clipboard-driven paste behavior is not a primary design target.

## First Implemented Gap

This repository now implements the first high-value gap:

- optional LLM correction after ASR
- OpenAI-compatible correction endpoint support
- prompt-file driven correction behavior
- fallback to raw ASR text if correction is disabled or fails

## Recommended Follow-Up Order

1. Add dictionary file loading and inject terms into the correction prompt.
2. Add local session history storage and a small stats surface.
3. Add tap-to-toggle recording and optional feedback sounds.
4. Revisit richer runtime status reporting once the session model has more stages.
