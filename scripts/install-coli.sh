#!/usr/bin/env bash
set -euo pipefail

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to install @marswave/coli" >&2
  exit 1
fi

npm install -g @marswave/coli

if ! command -v coli >/dev/null 2>&1; then
  echo "coli was not found on PATH after installation" >&2
  exit 1
fi

cat <<EOF
Installed coli.

Binary:
- $(command -v coli)

Next steps:
1. If you plan to use the ListenHub provider, set provider.name = "listenhub" in your config.
2. Validate the runtime with: PYTHONPATH=src python3 -m ibus_voice.cli --config examples/config.toml --check
EOF
