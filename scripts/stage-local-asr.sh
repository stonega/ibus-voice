#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <staging-dir> <app-root>" >&2
  exit 1
fi

STAGING_DIR="$1"
APP_ROOT="$2"
LOCAL_ASR_PACKAGE="${LOCAL_ASR_PACKAGE:-sherpa-onnx>=1.12.0}"

if ! /usr/bin/python3 -m pip --version >/dev/null 2>&1; then
  echo "error: python3 -m pip is required to bundle the local ASR runtime" >&2
  exit 1
fi

rm -rf "${STAGING_DIR}" "${APP_ROOT}/vendor"
mkdir -p "${STAGING_DIR}" "${APP_ROOT}/vendor"

/usr/bin/python3 -m pip install \
  --disable-pip-version-check \
  --no-compile \
  --target "${STAGING_DIR}" \
  "${LOCAL_ASR_PACKAGE}" >/dev/null

cp -a "${STAGING_DIR}/." "${APP_ROOT}/vendor/"
