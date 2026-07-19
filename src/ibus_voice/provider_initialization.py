from __future__ import annotations

from dataclasses import dataclass, field
import logging
import shutil
import subprocess
from threading import Lock, Thread
from typing import Callable, Protocol


LOGGER = logging.getLogger(__name__)

NOTIFICATION_APP_NAME = "ibus-voice"
NOTIFICATION_ICON = "audio-input-microphone-symbolic"
NOTIFICATION_TIMEOUT_MS = 8_000
SETUP_STARTED_TITLE = "Setting up voice input"
SETUP_READY_TITLE = "Voice input is ready"
SETUP_FAILED_TITLE = "Voice input setup failed"


try:  # pragma: no cover - depends on host desktop libraries
    import gi

    gi.require_version("Gio", "2.0")
    gi.require_version("GLib", "2.0")
    from gi.repository import Gio, GLib  # type: ignore
except Exception:  # pragma: no cover - exercised by runtime import fallback
    Gio = None
    GLib = None


class NotificationSink(Protocol):
    def send(self, title: str, body: str, *, urgency: str = "normal") -> None: ...


@dataclass(slots=True)
class DesktopNotifier:
    application_name: str = NOTIFICATION_APP_NAME
    icon: str = NOTIFICATION_ICON

    def send(self, title: str, body: str, *, urgency: str = "normal") -> None:
        try:
            if _send_freedesktop_notification(
                self.application_name,
                self.icon,
                title,
                body,
                urgency=urgency,
            ):
                return
        except Exception as exc:  # pragma: no cover - depends on the desktop session
            LOGGER.debug("freedesktop notification failed: %s", exc)

        notify_send = shutil.which("notify-send")
        if notify_send is None:
            LOGGER.warning("desktop notification unavailable: %s: %s", title, body)
            return
        try:
            result = subprocess.run(
                [
                    notify_send,
                    f"--app-name={self.application_name}",
                    f"--icon={self.icon}",
                    f"--urgency={urgency}",
                    f"--expire-time={NOTIFICATION_TIMEOUT_MS}",
                    title,
                    body,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            LOGGER.warning("desktop notification failed: %s", exc)
            return
        if result.returncode != 0:
            message = result.stderr.strip() or f"notify-send exited with {result.returncode}"
            LOGGER.warning("desktop notification failed: %s", message)


def _send_freedesktop_notification(
    application_name: str,
    icon: str,
    title: str,
    body: str,
    *,
    urgency: str,
) -> bool:
    if Gio is None or GLib is None:
        return False
    urgency_value = {"low": 0, "normal": 1, "critical": 2}.get(urgency, 1)
    proxy = Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION,
        Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
        None,
        "org.freedesktop.Notifications",
        "/org/freedesktop/Notifications",
        "org.freedesktop.Notifications",
        None,
    )
    parameters = GLib.Variant(
        "(susssasa{sv}i)",
        (
            application_name,
            0,
            icon,
            title,
            body,
            [],
            {"urgency": GLib.Variant("y", urgency_value)},
            NOTIFICATION_TIMEOUT_MS,
        ),
    )
    response = proxy.call_sync(
        "Notify",
        parameters,
        Gio.DBusCallFlags.NONE,
        5_000,
        None,
    )
    return response is not None


@dataclass(slots=True)
class ProviderInitializer:
    provider: object
    notifier: NotificationSink = field(default_factory=DesktopNotifier)
    _state: str = field(default="idle", init=False)
    _error: str | None = field(default=None, init=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _thread: Thread | None = field(default=None, init=False, repr=False)

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def error(self) -> str | None:
        with self._lock:
            return self._error

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    def start(self) -> bool:
        initialize = getattr(self.provider, "initialize", None)
        if not callable(initialize):
            with self._lock:
                self._state = "ready"
                self._error = None
            return False

        with self._lock:
            if self._state in {"initializing", "ready"}:
                return False
            self._state = "initializing"
            self._error = None
            thread = Thread(
                target=self._run,
                args=(initialize,),
                name="ibus-voice-provider-init",
                daemon=True,
            )
            self._thread = thread
        thread.start()
        return True

    def wait(self, timeout: float | None = None) -> None:
        with self._lock:
            thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def _run(self, initialize: Callable[[], None]) -> None:
        setup_notification_sent = False
        try:
            readiness_status = getattr(self.provider, "readiness_status", None)
            status = readiness_status() if callable(readiness_status) else None
            if status == "auto-download":
                setup_notification_sent = True
                self._notify(
                    SETUP_STARTED_TITLE,
                    "Qwen3-ASR is downloading and preparing in the background (about 879 MB).",
                )
            initialize()
        except Exception as exc:
            error = (str(exc).strip() or exc.__class__.__name__)[:400]
            with self._lock:
                self._state = "failed"
                self._error = error
            self._notify(
                SETUP_FAILED_TITLE,
                f"Qwen3-ASR could not be prepared: {error}. Use the dictation hotkey to retry.",
                urgency="critical",
            )
            return

        with self._lock:
            self._state = "ready"
            self._error = None
        if setup_notification_sent:
            self._notify(
                SETUP_READY_TITLE,
                "Qwen3-ASR is installed and ready for local dictation.",
            )

    def _notify(self, title: str, body: str, *, urgency: str = "normal") -> None:
        try:
            self.notifier.send(title, body, urgency=urgency)
        except Exception as exc:  # pragma: no cover - notification failure must not break setup
            LOGGER.warning("desktop notification failed: %s", exc)
