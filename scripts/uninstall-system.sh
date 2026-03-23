#!/usr/bin/env bash
set -euo pipefail

PREFIX="/usr/local"
LAUNCHER_PATH="${PREFIX}/bin/ibus-engine-voice"
APP_DIR="${PREFIX}/share/ibus-voice"
COMPONENT_PATH="/usr/share/ibus/component/ibus-voice.xml"

rm -f "${LAUNCHER_PATH}" "${COMPONENT_PATH}"
rm -rf "${APP_DIR}"

cat <<EOF
Removed system-wide ibus-voice files.

Remaining user config, if any:
- ${HOME}/.config/ibus-voice
EOF
