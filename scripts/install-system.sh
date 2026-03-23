#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="/usr/local"
BIN_DIR="${PREFIX}/bin"
APP_DIR="${PREFIX}/share/ibus-voice"
COMPONENT_DIR="/usr/share/ibus/component"
TARGET_USER="${SUDO_USER:-${USER}}"
TARGET_HOME="$(getent passwd "${TARGET_USER}" | cut -d: -f6)"
if [[ -z "${TARGET_HOME}" ]]; then
  TARGET_HOME="${HOME}"
fi
CONFIG_DIR="${TARGET_HOME}/.config/ibus-voice"
LAUNCHER_PATH="${BIN_DIR}/ibus-voice"
COMPONENT_PATH="${COMPONENT_DIR}/ibus-voice.xml"

mkdir -p "${BIN_DIR}" "${APP_DIR}" "${COMPONENT_DIR}" "${CONFIG_DIR}"

rm -rf "${APP_DIR}/src"
cp -R "${ROOT_DIR}/src" "${APP_DIR}/src"
cp "${ROOT_DIR}/README.md" "${APP_DIR}/README.md"
cp "${ROOT_DIR}/LICENSE" "${APP_DIR}/LICENSE"

if [[ ! -f "${CONFIG_DIR}/config.toml" ]]; then
  cp "${ROOT_DIR}/examples/config.toml" "${CONFIG_DIR}/config.toml"
fi
if [[ ! -f "${CONFIG_DIR}/dictionary.txt" ]]; then
  cp "${ROOT_DIR}/examples/dictionary.txt" "${CONFIG_DIR}/dictionary.txt"
fi
if [[ ! -f "${CONFIG_DIR}/system_prompt.txt" ]]; then
  cp "${ROOT_DIR}/examples/system_prompt.txt" "${CONFIG_DIR}/system_prompt.txt"
fi
if [[ ! -f "${CONFIG_DIR}/user_prompt.txt" ]]; then
  cp "${ROOT_DIR}/examples/user_prompt.txt" "${CONFIG_DIR}/user_prompt.txt"
fi

cat > "${LAUNCHER_PATH}" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${APP_DIR}/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec /usr/bin/python3 -m ibus_voice.cli "\$@"
EOF
chmod +x "${LAUNCHER_PATH}"

PYTHONPATH="${ROOT_DIR}/src" /usr/bin/python3 - <<PY > "${COMPONENT_PATH}"
from ibus_voice.metadata import render_component_xml
print(render_component_xml(${LAUNCHER_PATH@Q}), end="")
PY

cat <<EOF
Installed ibus-voice system-wide.

Files:
- launcher: ${LAUNCHER_PATH}
- component: ${COMPONENT_PATH}
- app: ${APP_DIR}
- config: ${CONFIG_DIR}/config.toml
- dictionary: ${CONFIG_DIR}/dictionary.txt
- system prompt: ${CONFIG_DIR}/system_prompt.txt
- user prompt: ${CONFIG_DIR}/user_prompt.txt

Next steps:
1. Run: ibus restart
2. Open IBus Preferences
3. Add the "ibus-voice" input method
4. If GNOME Settings still does not list it, log out and log back in
EOF
