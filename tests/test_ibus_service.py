from __future__ import annotations

import unittest
from unittest.mock import Mock

from ibus_voice.ibus_service import (
    TextCommitter,
    HotkeyMatcher,
    _hide_auxiliary_status,
    _initializing_status_text,
    _listening_status_text,
    _provider_status_text,
)


class FakeEngine:
    def __init__(self) -> None:
        self.hidden = False
        self.updated: list[tuple[str, bool]] = []
        self.preedit_hidden = False
        self.preedit_updates: list[tuple[str, int, bool]] = []

    def hide_auxiliary_text(self) -> None:
        self.hidden = True

    def update_auxiliary_text(self, text, visible: bool) -> None:
        self.updated.append((str(text), visible))

    def update_preedit_text(self, text, cursor_pos: int, visible: bool) -> None:
        self.preedit_updates.append((str(text), cursor_pos, visible))

    def hide_preedit_text(self) -> None:
        self.preedit_hidden = True


class HotkeyMatcherTests(unittest.TestCase):
    def test_matches_press_with_modifiers(self) -> None:
        matcher = HotkeyMatcher(key="space", modifiers=("Control",))

        self.assertTrue(matcher.matches(32, 4, released=False))
        self.assertFalse(matcher.matches(32, 4, released=True))

    def test_matches_release_with_release_mask(self) -> None:
        matcher = HotkeyMatcher(key="space", modifiers=("Control",))

        self.assertTrue(matcher.matches(32, 4 | 1073741824, released=True))

    def test_matches_release_key_without_modifier_state(self) -> None:
        matcher = HotkeyMatcher(key="space", modifiers=("Control",))

        self.assertTrue(matcher.matches_release_key(32, 1073741824))

    def test_matches_release_for_primary_key(self) -> None:
        matcher = HotkeyMatcher(key="space", modifiers=("Control",))

        self.assertTrue(matcher.matches_release(32, 1073741824))

    def test_matches_release_for_modifier_key(self) -> None:
        matcher = HotkeyMatcher(key="space", modifiers=("Control",))

        self.assertTrue(matcher.matches_release(65507, 1073741824))

    def test_non_hotkey_modifier_release_does_not_match(self) -> None:
        matcher = HotkeyMatcher(key="space", modifiers=("Control",))

        self.assertFalse(matcher.matches_release(65505, 1073741824))

    def test_wrong_modifier_does_not_match(self) -> None:
        matcher = HotkeyMatcher(key="space", modifiers=("Control",))

        self.assertFalse(matcher.matches(32, 1, released=False))


class AuxiliaryStatusTests(unittest.TestCase):
    def test_hide_auxiliary_status_prefers_hide_method(self) -> None:
        engine = FakeEngine()

        _hide_auxiliary_status(engine)

        self.assertTrue(engine.hidden)

    def test_listening_status_text_cycles_animated_dots(self) -> None:
        self.assertEqual(_listening_status_text(0), "🎙 Listening...")
        self.assertEqual(_listening_status_text(1), "🎙 Listening.. ")
        self.assertEqual(_listening_status_text(2), "🎙 Listening.  ")
        self.assertEqual(_listening_status_text(3), "🎙 Listening...")

    def test_initializing_status_text_uses_initing_label(self) -> None:
        self.assertEqual(_initializing_status_text(), "🎙 Initing...")

    def test_provider_status_text_maps_auto_download_to_initing(self) -> None:
        provider = Mock()
        provider.readiness_status.return_value = "auto-download"

        self.assertEqual(_provider_status_text(provider), "🎙 Initing...")

    def test_provider_status_text_ignores_other_statuses(self) -> None:
        provider = Mock()
        provider.readiness_status.return_value = "installed"

        self.assertIsNone(_provider_status_text(provider))

    def test_text_committer_queues_preedit_updates_on_glib_main_loop(self) -> None:
        engine = FakeEngine()
        committer = TextCommitter(engine=engine)
        fake_glib = Mock()
        queued: list[object] = []

        def idle_add(callback):
            queued.append(callback)
            return 1

        fake_glib.idle_add.side_effect = idle_add

        from ibus_voice import ibus_service

        with unittest.mock.patch.object(ibus_service, "GLib", fake_glib):
            with unittest.mock.patch.object(
                ibus_service,
                "IBus",
                Mock(Text=Mock(new_from_string=lambda text: text)),
            ):
                committer.update_preedit("hello")
                self.assertEqual(engine.preedit_updates, [])
                queued[0]()

        self.assertEqual(engine.preedit_updates, [("hello", 5, True)])
