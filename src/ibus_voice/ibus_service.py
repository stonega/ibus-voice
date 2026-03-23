from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable

from ibus_voice.config import AppConfig
from ibus_voice.engine import VoiceEngine
from ibus_voice.metadata import (
    AUTHOR,
    COMPONENT_NAME,
    ENGINE_DESCRIPTION,
    ENGINE_ICON,
    ENGINE_LANGUAGE,
    ENGINE_LAYOUT,
    ENGINE_LONGNAME,
    ENGINE_NAME,
    ENGINE_SYMBOL,
    HOMEPAGE,
    LICENSE,
    TEXTDOMAIN,
    VERSION,
)


LOGGER = logging.getLogger(__name__)


try:  # pragma: no cover - depends on host desktop libraries
    import gi

    gi.require_version("IBus", "1.0")
    gi.require_version("GLib", "2.0")
    from gi.repository import GLib, IBus  # type: ignore
except Exception:  # pragma: no cover - exercised by runtime import fallback
    IBus = None
    GLib = None


@dataclass(slots=True)
class TextCommitter:
    engine: object | None = None

    def commit_text(self, text: str) -> None:
        if IBus is None or self.engine is None:
            LOGGER.info("commit_text fallback: %s", text)
            return
        self.engine.commit_text(IBus.Text.new_from_string(text))


def _set_auxiliary_status(engine: object, text: str, *, visible: bool) -> None:
    if IBus is None:
        return
    update = getattr(engine, "update_auxiliary_text", None)
    if update is None:
        return
    update(IBus.Text.new_from_string(text), visible)


def _hide_auxiliary_status(engine: object) -> None:
    hide = getattr(engine, "hide_auxiliary_text", None)
    if callable(hide):
        hide()
        return
    _set_auxiliary_status(engine, "", visible=False)


@dataclass(slots=True)
class HotkeyMatcher:
    key: str
    modifiers: tuple[str, ...]

    def matches(self, keyval: int, state: int, *, released: bool) -> bool:
        if IBus is None:
            return False
        if keyval != _key_name_to_value(self.key):
            return False
        expected_state = 0
        for modifier in self.modifiers:
            expected_state |= _modifier_name_to_mask(modifier)
        release_mask = int(IBus.ModifierType.RELEASE_MASK)
        handled_mask = int(IBus.ModifierType.HANDLED_MASK)
        normalized_state = int(state) & ~(release_mask | handled_mask)
        has_release = bool(int(state) & release_mask)
        return normalized_state == expected_state and has_release == released

    def matches_release_key(self, keyval: int, state: int) -> bool:
        if IBus is None:
            return False
        release_mask = int(IBus.ModifierType.RELEASE_MASK)
        return keyval == _key_name_to_value(self.key) and bool(int(state) & release_mask)


if IBus is not None:  # pragma: no branch
    class VoiceIBusEngine(IBus.Engine):  # pragma: no cover - hard to instantiate in isolated tests
        def __init__(self, bus, object_path: str, voice_engine: VoiceEngine, matcher: HotkeyMatcher):
            super().__init__(
                connection=bus.get_connection(),
                object_path=object_path,
                engine_name="ibus-voice",
            )
            self._voice_engine = voice_engine
            self._matcher = matcher
            committer = self._voice_engine.committer
            if isinstance(committer, TextCommitter):
                committer.engine = self

        def do_focus_out(self) -> None:
            if self._voice_engine.state == "recording":
                self._voice_engine.handle_release()
            _hide_auxiliary_status(self)
            super().do_focus_out()

        def do_process_key_event(self, keyval: int, keycode: int, state: int) -> bool:
            del keycode
            if self._matcher.matches(keyval, state, released=False):
                self._voice_engine.handle_press()
                if self._voice_engine.state == "recording":
                    _set_auxiliary_status(self, "Listening...", visible=True)
                return True
            if self._voice_engine.state == "recording" and self._matcher.matches_release_key(keyval, state):
                self._voice_engine.handle_release()
                if self._voice_engine.last_error:
                    _set_auxiliary_status(self, f"Voice input failed: {self._voice_engine.last_error}", visible=True)
                else:
                    _hide_auxiliary_status(self)
                return True
            return False


    class VoiceEngineFactory(IBus.Factory):  # pragma: no cover - depends on live IBus
        ENGINE_PATH = "/org/freedesktop/IBus/Engine/ibus_voice"

        def __init__(self, bus, engine_builder: Callable[[], VoiceEngine], matcher: HotkeyMatcher):
            super().__init__(connection=bus.get_connection(), object_path=IBus.PATH_FACTORY)
            self._bus = bus
            self._engine_builder = engine_builder
            self._matcher = matcher
            self._engine_id = 0

        def do_create_engine(self, engine_name: str):
            if engine_name != "ibus-voice":
                return super().do_create_engine(engine_name)
            self._engine_id += 1
            object_path = f"{self.ENGINE_PATH}/{self._engine_id}"
            return VoiceIBusEngine(
                self._bus,
                object_path=object_path,
                voice_engine=self._engine_builder(),
                matcher=self._matcher,
            )


class IBusVoiceService:
    def __init__(self, config: AppConfig, voice_engine: VoiceEngine) -> None:
        self.config = config
        self.voice_engine = voice_engine

    def run(self) -> int:
        if IBus is None or GLib is None:
            LOGGER.warning("IBus GI bindings are unavailable; service cannot attach to the bus")
            return 1
        component = IBus.Component(
            name=COMPONENT_NAME,
            description="ibus-voice component",
            version=VERSION,
            license=LICENSE,
            author=AUTHOR,
            homepage=HOMEPAGE,
            command_line="ibus-voice --ibus",
            textdomain=TEXTDOMAIN,
        )
        component.add_engine(
            IBus.EngineDesc(
                name=ENGINE_NAME,
                longname=ENGINE_LONGNAME,
                description=ENGINE_DESCRIPTION,
                language=ENGINE_LANGUAGE,
                license=LICENSE,
                author=AUTHOR,
                icon=ENGINE_ICON,
                layout=ENGINE_LAYOUT,
                symbol=ENGINE_SYMBOL,
                rank=0,
            )
        )
        bus = IBus.Bus()
        bus.connect("disconnected", self._on_bus_disconnected)
        matcher = HotkeyMatcher(
            key=self.config.hotkey.key,
            modifiers=self.config.hotkey.modifiers,
        )
        self._mainloop = GLib.MainLoop()
        self._factory = VoiceEngineFactory(bus, self._build_engine, matcher)
        if "--ibus" in __import__("sys").argv:
            bus.request_name(COMPONENT_NAME, 0)
        else:
            bus.register_component(component)
        LOGGER.info("ibus-voice service ready")
        self._mainloop.run()
        return 0

    def _build_engine(self) -> VoiceEngine:
        return self.voice_engine

    def _on_bus_disconnected(self, bus) -> None:
        del bus
        if hasattr(self, "_mainloop"):
            self._mainloop.quit()


def _key_name_to_value(key: str) -> int:
    if IBus is None:
        raise RuntimeError("IBus is unavailable")
    value = getattr(IBus, f"KEY_{key}", None)
    if value is None:
        raise ValueError(f"unsupported hotkey key: {key}")
    return int(value)


def _modifier_name_to_mask(name: str) -> int:
    if IBus is None:
        raise RuntimeError("IBus is unavailable")
    attribute = f"{name.upper()}_MASK"
    value = getattr(IBus.ModifierType, attribute, None)
    if value is None:
        raise ValueError(f"unsupported modifier: {name}")
    return int(value)
