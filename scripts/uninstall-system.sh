#!/usr/bin/env bash
set -euo pipefail

PREFIX="/usr/local"
LAUNCHER_PATH="${PREFIX}/bin/ibus-voice"
APP_DIR="${PREFIX}/share/ibus-voice"
COMPONENT_PATH="/usr/share/ibus/component/ibus-voice.xml"
REFRESH_SCRIPT_PATH="${APP_DIR}/refresh-ibus.sh"

rm -f "${LAUNCHER_PATH}" "${COMPONENT_PATH}"
if [[ -x "${REFRESH_SCRIPT_PATH}" ]]; then
  "${REFRESH_SCRIPT_PATH}" "${SUDO_USER:-${USER}}"
fi
rm -rf "${APP_DIR}"

cat <<EOF
Removed system-wide ibus-voice files.

Remaining user config, if any:
- ${HOME}/.config/ibus-voice
EOF
