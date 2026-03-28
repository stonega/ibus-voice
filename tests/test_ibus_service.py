from __future__ import annotations

import unittest

from ibus_voice.ibus_service import HotkeyMatcher, _hide_auxiliary_status, _listening_status_text


class FakeEngine:
    def __init__(self) -> None:
        self.hidden = False
        self.updated: list[tuple[str, bool]] = []

    def hide_auxiliary_text(self) -> None:
        self.hidden = True

    def update_auxiliary_text(self, text, visible: bool) -> None:
        self.updated.append((str(text), visible))


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
        self.assertEqual(_listening_status_text(0), "🎙...")
        self.assertEqual(_listening_status_text(1), "🎙.. ")
        self.assertEqual(_listening_status_text(2), "🎙.  ")
        self.assertEqual(_listening_status_text(3), "🎙...")
