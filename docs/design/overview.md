# Design Overview

## Purpose

`ibus-voice` is intended to provide voice input for Linux through the IBus framework.

## Core Flow

1. Capture microphone audio
2. Send audio to a speech-to-text backend
3. Optionally run a text correction step on the final transcript
4. Receive partial or final recognition results
5. Convert results into preedit or committed text
6. Deliver text to the focused application through IBus

## Main Components

- IBus engine or bridge layer
- Audio capture layer
- Speech backend adapter
- Optional text correction adapter
- Configuration layer

## Design Priorities

- low-latency text input
- reliable Linux desktop integration
- support for local or remote backends
- clear separation between IBus logic and speech backend logic

## Open Questions

- Should the first implementation use a local backend, remote backend, or both?
- Should dictation be push-to-talk, toggle-based, or always-listening?
- How should punctuation and command phrases be handled?
