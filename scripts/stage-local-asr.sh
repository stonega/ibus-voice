#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <staging-dir> <app-root>" >&2
  exit 1
fi

STAGING_DIR="$1"
APP_ROOT="$2"
LOCAL_ASR_PACKAGE="${LOCAL_ASR_PACKAGE:-sherpa-onnx>=1.12.36}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
WHEELHOUSE_DIR="${APP_ROOT}/wheelhouse"
WHEEL_PLATFORM="${WHEEL_PLATFORM:-}"

if ! "${PYTHON_BIN}" -m pip --version >/dev/null 2>&1; then
  echo "error: ${PYTHON_BIN} -m pip is required to bundle the local ASR runtime" >&2
  exit 1
fi

if [[ -z "${WHEEL_PLATFORM}" ]]; then
  case "$(uname -m)" in
    x86_64)
      WHEEL_PLATFORM="manylinux2014_x86_64"
      ;;
    aarch64|arm64)
      WHEEL_PLATFORM="manylinux2014_aarch64"
      ;;
    *)
      echo "error: unsupported architecture '$(uname -m)' for sherpa-onnx wheel staging" >&2
      exit 1
      ;;
  esac
fi

rm -rf "${STAGING_DIR}" "${APP_ROOT}/vendor" "${WHEELHOUSE_DIR}"
mkdir -p "${STAGING_DIR}" "${APP_ROOT}/vendor" "${WHEELHOUSE_DIR}"

"${PYTHON_BIN}" -m pip install \
  --disable-pip-version-check \
  --no-compile \
  --target "${STAGING_DIR}" \
  "${LOCAL_ASR_PACKAGE}" >/dev/null

for PYTHON_VERSION in 311 312 313 314; do
  "${PYTHON_BIN}" -m pip download \
    --disable-pip-version-check \
    --only-binary=:all: \
    --implementation cp \
    --python-version "${PYTHON_VERSION}" \
    --abi "cp${PYTHON_VERSION}" \
    --platform "${WHEEL_PLATFORM}" \
    --dest "${WHEELHOUSE_DIR}" \
    "${LOCAL_ASR_PACKAGE}" >/dev/null
done

cp -a "${STAGING_DIR}/." "${APP_ROOT}/vendor/"
