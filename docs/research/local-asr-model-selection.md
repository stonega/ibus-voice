# Local ASR Model Selection

Date: 2026-07-19

## Requirements

The built-in local model must:

- run fully offline on Linux after installation
- support both Chinese and English, including code-switching
- integrate without replacing the existing sherpa-onnx runtime and packaging flow
- remain practical for desktop CPU inference

## Selection

The selected model is Qwen3-ASR 0.6B INT8 through sherpa-onnx. The application-facing model name is `qwen3-asr-0.6b`.

Qwen's model card reports support for 30 languages and 22 Chinese dialects, including Chinese and English, and describes code-switching and punctuation support. Sherpa-onnx publishes an INT8 offline package with separate convolution frontend, encoder, decoder, and tokenizer files. This fits the existing local Python runtime without introducing another inference framework.

The Qwen model is published under Apache-2.0. It is downloaded on demand rather than redistributed inside the application package.

At the selection date, sherpa-onnx 1.13.4 is the current PyPI release. The dependency keeps `1.12.36` as its lower bound because that is the first release line containing the Qwen support and fixes required here; normal installation resolves the newest compatible release.

Upstream references:

- [Qwen3-ASR 0.6B model card](https://huggingface.co/Qwen/Qwen3-ASR-0.6B)
- [Sherpa-onnx Qwen3-ASR pretrained models](https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/pretrained.html)
- [Sherpa-onnx Python Qwen3-ASR adapter](https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/python/sherpa_onnx/offline_recognizer.py)
- [Sherpa-onnx on PyPI](https://pypi.org/project/sherpa-onnx/)

## Operational Decisions

- Use the upstream `sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25` archive.
- Require `sherpa-onnx >= 1.12.36`, which includes Qwen3-ASR fixes for this model generation.
- Verify the 878,702,423-byte archive against the upstream SHA-256 digest before extraction.
- Validate all three ONNX components and the tokenizer files before treating installation as complete.
- Cache one recognizer per process and serialize decoding to avoid repeated model initialization and unsafe concurrent access.
- Preserve the `listenhub` provider name and accept `sensevoice` as a legacy model alias so existing user configs continue to load.

The previous SenseVoice model remains historically documented in the changelog, but it is no longer selected or downloaded by the runtime.
