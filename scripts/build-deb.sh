#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(
  cd "${ROOT_DIR}"
  python3 - <<'PY'
import tomllib
from pathlib import Path

data = tomllib.loads(Path("pyproject.toml").read_text())
print(data["project"]["version"])
PY
)"
BUILD_DIR="${ROOT_DIR}/.dist/deb"
PACKAGE_DIR="${ROOT_DIR}/.dist/packages"
PACKAGE_ROOT="${BUILD_DIR}/ibus-voice_${VERSION}"
COLI_STAGE_DIR="${BUILD_DIR}/coli-stage"

HOST_ARCH="$(uname -m)"
case "${HOST_ARCH}" in
  x86_64)
    DEB_ARCH="amd64"
    ;;
  aarch64|arm64)
    DEB_ARCH="arm64"
    ;;
  *)
    echo "error: unsupported architecture '${HOST_ARCH}' for Debian packaging" >&2
    exit 1
    ;;
esac

ARTIFACT_PATH="${PACKAGE_DIR}/ibus-voice_${VERSION}_${DEB_ARCH}.deb"

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "error: dpkg-deb is required to build Debian packages" >&2
  echo "Install dpkg tooling and rerun ./scripts/build-deb.sh" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm is required to bundle @marswave/coli into Debian packages" >&2
  echo "Install npm and rerun ./scripts/build-deb.sh" >&2
  exit 1
fi

echo "Building Debian package ${ARTIFACT_PATH}"
rm -rf "${BUILD_DIR}"
mkdir -p \
  "${PACKAGE_ROOT}/DEBIAN" \
  "${PACKAGE_ROOT}/usr/bin" \
  "${PACKAGE_ROOT}/usr/lib/ibus-voice" \
  "${PACKAGE_ROOT}/usr/share/doc/ibus-voice/examples" \
  "${PACKAGE_ROOT}/usr/share/ibus/component" \
  "${PACKAGE_DIR}"

cp -R "${ROOT_DIR}/src" "${PACKAGE_ROOT}/usr/lib/ibus-voice/"
cp "${ROOT_DIR}/README.md" "${PACKAGE_ROOT}/usr/lib/ibus-voice/"
cp "${ROOT_DIR}/LICENSE" "${PACKAGE_ROOT}/usr/lib/ibus-voice/"
cp "${ROOT_DIR}/examples/config.toml" "${PACKAGE_ROOT}/usr/share/doc/ibus-voice/examples/config.toml"
cp "${ROOT_DIR}/examples/dictionary.txt" "${PACKAGE_ROOT}/usr/share/doc/ibus-voice/examples/dictionary.txt"
cp "${ROOT_DIR}/examples/system_prompt.txt" "${PACKAGE_ROOT}/usr/share/doc/ibus-voice/examples/system_prompt.txt"
cp "${ROOT_DIR}/examples/user_prompt.txt" "${PACKAGE_ROOT}/usr/share/doc/ibus-voice/examples/user_prompt.txt"
"${ROOT_DIR}/scripts/stage-coli.sh" "${COLI_STAGE_DIR}" "${PACKAGE_ROOT}/usr/lib/ibus-voice"

cat > "${PACKAGE_ROOT}/usr/bin/ibus-voice" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="/usr/lib/ibus-voice/src${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -m ibus_voice.cli "$@"
EOF
chmod 0755 "${PACKAGE_ROOT}/usr/bin/ibus-voice"

PYTHONPATH="${ROOT_DIR}/src" /usr/bin/python3 - <<'PY' > "${PACKAGE_ROOT}/usr/share/ibus/component/ibus-voice.xml"
from ibus_voice.metadata import render_component_xml

print(render_component_xml("/usr/bin/ibus-voice"), end="")
PY

cat > "${PACKAGE_ROOT}/DEBIAN/control" <<EOF
Package: ibus-voice
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${DEB_ARCH}
Maintainer: ibus-voice contributors
Depends: python3, ibus, nodejs
Description: Voice input support for IBus on Linux
EOF

dpkg-deb --build --root-owner-group "${PACKAGE_ROOT}" "${ARTIFACT_PATH}" >/dev/null

echo "Debian package created at ${ARTIFACT_PATH}"
