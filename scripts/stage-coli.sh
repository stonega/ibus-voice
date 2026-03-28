#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <staging-dir> <app-root>" >&2
  exit 1
fi

STAGING_DIR="$1"
APP_ROOT="$2"

if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm is required to bundle @marswave/coli during package builds" >&2
  exit 1
fi

rm -rf "${STAGING_DIR}"
mkdir -p "${STAGING_DIR}" "${APP_ROOT}/bin" "${APP_ROOT}/vendor"

npm_config_platform="${NPM_CONFIG_PLATFORM:-linux}" \
npm_config_arch="${NPM_CONFIG_ARCH:-}" \
  npm install --prefix "${STAGING_DIR}" @marswave/coli >/dev/null

cp -a "${STAGING_DIR}/node_modules" "${APP_ROOT}/vendor/"

cat > "${APP_ROOT}/bin/coli" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
if ! command -v node >/dev/null 2>&1; then
  echo "error: node is required to run the bundled coli CLI; install nodejs or install coli separately on PATH" >&2
  exit 127
fi
exec /usr/bin/env node "${APP_ROOT}/vendor/node_modules/.bin/coli" "$@"
EOF
chmod 0755 "${APP_ROOT}/bin/coli"
