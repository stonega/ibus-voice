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
RPM_ROOT="${ROOT_DIR}/.dist/rpm"
PACKAGE_DIR="${ROOT_DIR}/.dist/packages"
SOURCE_DIR="${RPM_ROOT}/SOURCES/ibus-voice-${VERSION}"
SPEC_PATH="${RPM_ROOT}/SPECS/ibus-voice.spec"
TMP_DIR="${RPM_ROOT}/tmp"
RPM_CHANGELOG_DATE="$(LC_ALL=C date '+%a %b %d %Y')"

if ! command -v rpmbuild >/dev/null 2>&1; then
  echo "error: rpmbuild is required to build RPM packages" >&2
  echo "Install rpm-build tooling and rerun ./scripts/build-rpm.sh" >&2
  exit 1
fi

echo "Building RPM package for version ${VERSION}"
rm -rf "${RPM_ROOT}"
mkdir -p \
  "${RPM_ROOT}/BUILD" \
  "${RPM_ROOT}/BUILDROOT" \
  "${RPM_ROOT}/RPMS" \
  "${RPM_ROOT}/SOURCES" \
  "${RPM_ROOT}/SPECS" \
  "${RPM_ROOT}/SRPMS" \
  "${TMP_DIR}" \
  "${PACKAGE_DIR}" \
  "${SOURCE_DIR}/examples"

cp -R "${ROOT_DIR}/src" "${SOURCE_DIR}/src"
cp "${ROOT_DIR}/README.md" "${SOURCE_DIR}/README.md"
cp "${ROOT_DIR}/LICENSE" "${SOURCE_DIR}/LICENSE"
cp "${ROOT_DIR}/examples/config.toml" "${SOURCE_DIR}/examples/config.toml"
cp "${ROOT_DIR}/examples/dictionary.txt" "${SOURCE_DIR}/examples/dictionary.txt"
cp "${ROOT_DIR}/examples/system_prompt.txt" "${SOURCE_DIR}/examples/system_prompt.txt"
cp "${ROOT_DIR}/examples/user_prompt.txt" "${SOURCE_DIR}/examples/user_prompt.txt"

cat > "${SOURCE_DIR}/ibus-voice" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="/usr/lib/ibus-voice/src${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -m ibus_voice.cli "$@"
EOF
chmod 0755 "${SOURCE_DIR}/ibus-voice"

PYTHONPATH="${ROOT_DIR}/src" /usr/bin/python3 - <<'PY' > "${SOURCE_DIR}/ibus-voice.xml"
from ibus_voice.metadata import render_component_xml

print(render_component_xml("/usr/bin/ibus-voice"), end="")
PY

tar -C "${RPM_ROOT}/SOURCES" -czf "${RPM_ROOT}/SOURCES/ibus-voice-${VERSION}.tar.gz" "ibus-voice-${VERSION}"

cat > "${SPEC_PATH}" <<EOF
Name: ibus-voice
Version: ${VERSION}
Release: 1%{?dist}
Summary: Voice input support for IBus on Linux
License: MIT
BuildArch: noarch
Source0: %{name}-%{version}.tar.gz
Requires: ibus, python3

%description
Voice input support for IBus on Linux.

%prep
%setup -q

%install
mkdir -p %{buildroot}/usr/lib/ibus-voice
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/ibus/component
mkdir -p %{buildroot}/usr/share/doc/%{name}/examples
cp -r src %{buildroot}/usr/lib/ibus-voice/
cp README.md %{buildroot}/usr/lib/ibus-voice/
cp LICENSE %{buildroot}/usr/lib/ibus-voice/
cp ibus-voice %{buildroot}/usr/bin/ibus-voice
cp ibus-voice.xml %{buildroot}/usr/share/ibus/component/ibus-voice.xml
cp examples/config.toml %{buildroot}/usr/share/doc/%{name}/examples/config.toml
cp examples/dictionary.txt %{buildroot}/usr/share/doc/%{name}/examples/dictionary.txt
cp examples/system_prompt.txt %{buildroot}/usr/share/doc/%{name}/examples/system_prompt.txt
cp examples/user_prompt.txt %{buildroot}/usr/share/doc/%{name}/examples/user_prompt.txt

%files
/usr/lib/ibus-voice
/usr/bin/ibus-voice
/usr/share/ibus/component/ibus-voice.xml
/usr/share/doc/%{name}/examples/config.toml
/usr/share/doc/%{name}/examples/dictionary.txt
/usr/share/doc/%{name}/examples/system_prompt.txt
/usr/share/doc/%{name}/examples/user_prompt.txt

%changelog
* ${RPM_CHANGELOG_DATE} ibus-voice contributors - ${VERSION}-1
- Automated package build
EOF

rpmbuild \
  --define "_topdir ${RPM_ROOT}" \
  --define "_tmppath ${TMP_DIR}" \
  -bb "${SPEC_PATH}" >/dev/null
find "${RPM_ROOT}/RPMS" -name '*.rpm' -exec cp {} "${PACKAGE_DIR}/" \;

echo "RPM package created in ${PACKAGE_DIR}"
