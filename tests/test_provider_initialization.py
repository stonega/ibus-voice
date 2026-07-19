from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from ibus_voice.provider_initialization import (
    DesktopNotifier,
    ProviderInitializer,
    SETUP_FAILED_TITLE,
    SETUP_READY_TITLE,
    SETUP_STARTED_TITLE,
)


class FakeNotifier:
    def __init__(self) -> None:
        self.notifications: list[tuple[str, str, str]] = []

    def send(self, title: str, body: str, *, urgency: str = "normal") -> None:
        self.notifications.append((title, body, urgency))


class FakeInitializableProvider:
    def __init__(self, status: str = "auto-download", failures: int = 0) -> None:
        self.status = status
        self.failures = failures
        self.initialize_calls = 0

    def readiness_status(self) -> str:
        return self.status

    def initialize(self) -> None:
        self.initialize_calls += 1
        if self.failures > 0:
            self.failures -= 1
            raise RuntimeError("download failed")


class ProviderInitializerTests(unittest.TestCase):
    def test_missing_model_initializes_in_background_with_notifications(self) -> None:
        provider = FakeInitializableProvider(status="auto-download")
        notifier = FakeNotifier()
        initializer = ProviderInitializer(provider, notifier)

        self.assertTrue(initializer.start())
        initializer.wait(1)

        self.assertEqual(initializer.state, "ready")
        self.assertEqual(provider.initialize_calls, 1)
        self.assertEqual(
            [notification[0] for notification in notifier.notifications],
            [SETUP_STARTED_TITLE, SETUP_READY_TITLE],
        )

    def test_installed_model_preloads_silently(self) -> None:
        provider = FakeInitializableProvider(status="installed")
        notifier = FakeNotifier()
        initializer = ProviderInitializer(provider, notifier)

        initializer.start()
        initializer.wait(1)

        self.assertTrue(initializer.ready)
        self.assertEqual(provider.initialize_calls, 1)
        self.assertEqual(notifier.notifications, [])

    def test_failed_initialization_notifies_and_can_retry(self) -> None:
        provider = FakeInitializableProvider(status="auto-download", failures=1)
        notifier = FakeNotifier()
        initializer = ProviderInitializer(provider, notifier)

        initializer.start()
        initializer.wait(1)

        self.assertEqual(initializer.state, "failed")
        self.assertEqual(initializer.error, "download failed")
        self.assertEqual(notifier.notifications[-1][0], SETUP_FAILED_TITLE)
        self.assertEqual(notifier.notifications[-1][2], "critical")

        self.assertTrue(initializer.start())
        initializer.wait(1)

        self.assertTrue(initializer.ready)
        self.assertEqual(provider.initialize_calls, 2)
        self.assertEqual(notifier.notifications[-1][0], SETUP_READY_TITLE)

    def test_provider_without_initializer_is_immediately_ready(self) -> None:
        initializer = ProviderInitializer(object(), FakeNotifier())

        self.assertFalse(initializer.start())

        self.assertTrue(initializer.ready)


class DesktopNotifierTests(unittest.TestCase):
    def test_falls_back_to_notify_send(self) -> None:
        notifier = DesktopNotifier()
        completed = Mock(returncode=0, stderr="")

        with patch(
            "ibus_voice.provider_initialization._send_freedesktop_notification",
            return_value=False,
        ):
            with patch(
                "ibus_voice.provider_initialization.shutil.which",
                return_value="/usr/bin/notify-send",
            ):
                with patch(
                    "ibus_voice.provider_initialization.subprocess.run",
                    return_value=completed,
                ) as run:
                    notifier.send("Voice input is ready", "You can start dictating.")

        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["Voice input is ready", "You can start dictating."])
        self.assertIn("--app-name=ibus-voice", command)

    def test_does_not_spawn_notify_send_when_dbus_succeeds(self) -> None:
        notifier = DesktopNotifier()

        with patch(
            "ibus_voice.provider_initialization._send_freedesktop_notification",
            return_value=True,
        ):
            with patch("ibus_voice.provider_initialization.subprocess.run") as run:
                notifier.send("Voice input is ready", "You can start dictating.")

        run.assert_not_called()
