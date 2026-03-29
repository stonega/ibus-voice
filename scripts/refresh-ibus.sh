#!/usr/bin/env bash
set -euo pipefail

TARGET_USER="${1:-${SUDO_USER:-${USER:-}}}"

detect_active_user() {
  local session_id session_user

  if command -v loginctl >/dev/null 2>&1; then
    while IFS=: read -r session_id session_user; do
      if [[ -z "${session_id}" || -z "${session_user}" || "${session_user}" == "root" ]]; then
        continue
      fi
      if [[ "$(loginctl show-session "${session_id}" -p Active --value 2>/dev/null)" == "yes" ]]; then
        echo "${session_user}"
        return 0
      fi
    done < <(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1 ":" $3}')
  fi

  for runtime_dir in /run/user/*; do
    local target_uid target_user
    if [[ ! -S "${runtime_dir}/bus" ]]; then
      continue
    fi
    target_uid="${runtime_dir##*/}"
    if [[ "${target_uid}" == "0" ]]; then
      continue
    fi
    target_user="$(id -nu "${target_uid}" 2>/dev/null || true)"
    if [[ -n "${target_user}" ]]; then
      echo "${target_user}"
      return 0
    fi
  done

  return 1
}

resolve_target_user() {
  local requested_user="$1"

  if [[ -n "${requested_user}" ]] && id "${requested_user}" >/dev/null 2>&1 && [[ "${requested_user}" != "root" ]]; then
    echo "${requested_user}"
    return 0
  fi

  detect_active_user
}

write_ibus_cache() {
  if ! command -v ibus >/dev/null 2>&1; then
    return 1
  fi
  if ibus write-cache --system >/dev/null 2>&1; then
    return 0
  fi
  ibus write-cache >/dev/null 2>&1
}

restart_ibus_for_user() {
  local target_user="$1"
  local target_uid runtime_dir bus_address

  if [[ -z "${target_user}" ]] || ! id "${target_user}" >/dev/null 2>&1; then
    return 1
  fi

  target_uid="$(id -u "${target_user}")"
  runtime_dir="/run/user/${target_uid}"
  bus_address="unix:path=${runtime_dir}/bus"

  if [[ ! -S "${runtime_dir}/bus" ]]; then
    return 1
  fi

  if [[ "$(id -u)" == "${target_uid}" ]]; then
    env \
      DBUS_SESSION_BUS_ADDRESS="${bus_address}" \
      XDG_RUNTIME_DIR="${runtime_dir}" \
      ibus restart >/dev/null 2>&1
    return 0
  fi

  if command -v runuser >/dev/null 2>&1; then
    runuser -u "${target_user}" -- env \
      DBUS_SESSION_BUS_ADDRESS="${bus_address}" \
      XDG_RUNTIME_DIR="${runtime_dir}" \
      ibus restart >/dev/null 2>&1
    return 0
  fi

  if command -v sudo >/dev/null 2>&1; then
    sudo -u "${target_user}" env \
      DBUS_SESSION_BUS_ADDRESS="${bus_address}" \
      XDG_RUNTIME_DIR="${runtime_dir}" \
      ibus restart >/dev/null 2>&1
    return 0
  fi

  return 1
}

cache_status="warning: unable to refresh the IBus component cache automatically."
TARGET_USER="$(resolve_target_user "${TARGET_USER}" || true)"
restart_status="warning: unable to restart IBus automatically for ${TARGET_USER:-the active desktop user}."

if write_ibus_cache; then
  cache_status="Refreshed the IBus component cache."
fi

if restart_ibus_for_user "${TARGET_USER}"; then
  restart_status="Restarted IBus for ${TARGET_USER}."
fi

echo "${cache_status}"
echo "${restart_status}"

if [[ "${restart_status}" == warning:* ]]; then
  echo "Run 'ibus restart' in the desktop session for ${TARGET_USER:-the active desktop user}, then reopen Input Sources if needed."
fi

exit 0
