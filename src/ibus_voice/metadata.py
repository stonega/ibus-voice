from __future__ import annotations

from xml.sax.saxutils import escape

from ibus_voice import __version__


PACKAGE_NAME = "ibus-voice"
COMPONENT_NAME = "org.freedesktop.IBus.ibus_voice"
VERSION = __version__
AUTHOR = "ibus-voice contributors"
HOMEPAGE = "https://github.com/stonega/ibus-voice"
REPOSITORY = HOMEPAGE
ISSUES = f"{HOMEPAGE}/issues"
LICENSE = "MIT"
ENGINE_NAME = "ibus-voice"
ENGINE_LONGNAME = "ibus-voice"
ENGINE_DESCRIPTION = "Voice input for IBus"
ENGINE_LANGUAGE = "en"
ENGINE_LAYOUT = "default"
ENGINE_ICON = "audio-input-microphone"
ENGINE_SYMBOL = "V"
TEXTDOMAIN = "ibus-voice"
CLI_AUTHOR = "Stone"


def render_engines_xml() -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<engines>
  <engine>
    <name>ibus-voice</name>
    <language>en</language>
    <license>MIT</license>
    <author>ibus-voice contributors</author>
    <icon>audio-input-microphone</icon>
    <layout>default</layout>
    <layout_variant></layout_variant>
    <layout_option></layout_option>
    <longname translatable="no">ibus-voice</longname>
    <description>Voice input for IBus</description>
    <rank>0</rank>
    <symbol>V</symbol>
    <version>{VERSION}</version>
    <textdomain>ibus-voice</textdomain>
  </engine>
</engines>
"""


def render_component_xml(exec_path: str) -> str:
    exec_escaped = escape(exec_path)
    return f"""<?xml version='1.0' encoding='utf-8'?>
<component>
  <name>{COMPONENT_NAME}</name>
  <description>ibus-voice component</description>
  <exec>{exec_escaped} --ibus</exec>
  <version>{VERSION}</version>
  <author>{AUTHOR}</author>
  <license>{LICENSE}</license>
  <homepage>{HOMEPAGE}</homepage>
  <textdomain>{TEXTDOMAIN}</textdomain>
  <engines exec='{exec_escaped} --xml'/>
</component>
"""


def render_version_text() -> str:
    return (
        f"version: {VERSION}\n"
        f"created by: {CLI_AUTHOR}\n"
        f"repository: {REPOSITORY}\n"
        f"issues: {ISSUES}"
    )
