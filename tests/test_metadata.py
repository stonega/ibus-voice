from __future__ import annotations

import unittest

from ibus_voice.metadata import render_component_xml, render_engines_xml


class MetadataTests(unittest.TestCase):
    def test_render_engines_xml_contains_engine_name(self) -> None:
        rendered = render_engines_xml()

        self.assertIn("<name>ibus-voice</name>", rendered)
        self.assertIn("<symbol>V</symbol>", rendered)

    def test_render_component_xml_contains_exec_commands(self) -> None:
        rendered = render_component_xml("/home/test/.local/bin/ibus-engine-voice")

        self.assertIn("<exec>/home/test/.local/bin/ibus-engine-voice --ibus</exec>", rendered)
        self.assertIn("engines exec='/home/test/.local/bin/ibus-engine-voice --xml'", rendered)
