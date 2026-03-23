#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/.dist/deb"

echo "Preparing Debian package layout in ${BUILD_DIR}"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/usr/lib/ibus-voice" "${BUILD_DIR}/DEBIAN"

cp -R "${ROOT_DIR}/src" "${BUILD_DIR}/usr/lib/ibus-voice/"
cp "${ROOT_DIR}/README.md" "${BUILD_DIR}/usr/lib/ibus-voice/"
cp "${ROOT_DIR}/LICENSE" "${BUILD_DIR}/usr/lib/ibus-voice/"

cat > "${BUILD_DIR}/DEBIAN/control" <<'EOF'
Package: ibus-voice
Version: 0.1.0
Section: utils
Priority: optional
Architecture: all
Maintainer: ibus-voice contributors
Description: Voice input support for IBus on Linux
EOF

echo "Debian package tree prepared. Build with: dpkg-deb --build ${BUILD_DIR}"
