from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class EngineMetadata:
    name: str
    longname: str
    language: str
    description: str = ENGINE_DESCRIPTION
    icon: str = ENGINE_ICON
    layout: str = ENGINE_LAYOUT
    symbol: str = ENGINE_SYMBOL
    rank: int = 0


ENGINE_METADATA = (
    EngineMetadata(
        name=ENGINE_NAME,
        longname=ENGINE_LONGNAME,
        language=ENGINE_LANGUAGE,
    ),
    EngineMetadata(
        name="ibus-voice-zh",
        longname=ENGINE_LONGNAME,
        language="zh",
    ),
)


def render_engines_xml() -> str:
    engines_xml = "\n".join(
        f"""  <engine>
    <name>{engine.name}</name>
    <language>{engine.language}</language>
    <license>{LICENSE}</license>
    <author>{AUTHOR}</author>
    <icon>{engine.icon}</icon>
    <layout>{engine.layout}</layout>
    <layout_variant></layout_variant>
    <layout_option></layout_option>
    <longname translatable="no">{engine.longname}</longname>
    <description>{engine.description}</description>
    <rank>{engine.rank}</rank>
    <symbol>{engine.symbol}</symbol>
    <version>{VERSION}</version>
    <textdomain>{TEXTDOMAIN}</textdomain>
  </engine>"""
        for engine in ENGINE_METADATA
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<engines>
{engines_xml}
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
