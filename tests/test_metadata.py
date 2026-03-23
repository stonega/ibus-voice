from __future__ import annotations

import unittest
from pathlib import Path
import tomllib

from ibus_voice import __version__
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

    def test_rendered_xml_uses_package_version(self) -> None:
        rendered = render_engines_xml()

        self.assertIn(f"<version>{__version__}</version>", rendered)

    def test_package_version_matches_pyproject_version(self) -> None:
        pyproject = tomllib.loads(Path("pyproject.toml").read_text())

        self.assertEqual(pyproject["project"]["version"], __version__)
