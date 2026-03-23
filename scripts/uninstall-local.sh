#!/usr/bin/env bash
set -euo pipefail

PREFIX="${HOME}/.local"
BIN_DIR="${PREFIX}/bin"
APP_DIR="${PREFIX}/share/ibus-voice"
COMPONENT_PATH="${PREFIX}/share/ibus/component/ibus-voice.xml"
LAUNCHER_PATH="${BIN_DIR}/ibus-voice"

rm -f "${LAUNCHER_PATH}" "${COMPONENT_PATH}"
rm -rf "${APP_DIR}"

cat <<EOF
Removed local ibus-voice installation files.

Remaining user config, if any:
- ${HOME}/.config/ibus-voice
EOF
