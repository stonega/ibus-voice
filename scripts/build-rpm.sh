#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_DIR="${ROOT_DIR}/.dist/rpm"

echo "Preparing RPM spec in ${SPEC_DIR}"
rm -rf "${SPEC_DIR}"
mkdir -p "${SPEC_DIR}"

cat > "${SPEC_DIR}/ibus-voice.spec" <<EOF
Name: ibus-voice
Version: 0.1.0
Release: 1%{?dist}
Summary: Voice input support for IBus on Linux
License: MIT
BuildArch: noarch

%description
Voice input support for IBus on Linux.

%install
mkdir -p %{buildroot}/usr/lib/ibus-voice
cp -r ${ROOT_DIR}/src %{buildroot}/usr/lib/ibus-voice/
cp ${ROOT_DIR}/README.md %{buildroot}/usr/lib/ibus-voice/
cp ${ROOT_DIR}/LICENSE %{buildroot}/usr/lib/ibus-voice/

%files
/usr/lib/ibus-voice
EOF

echo "RPM spec prepared at ${SPEC_DIR}/ibus-voice.spec"
