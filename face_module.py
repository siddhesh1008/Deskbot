"""
DeskBot - Face Module

Bridges the event bus to the Qt/QML eye rendering.

Listens for events on the bus and translates them into eye/mouth
state changes. This is the only module that touches Qt directly.

Events this module LISTENS to:
    face.set_state          - Direct state change (data: {"state": "happy"})
    audio.wake_word_detected - Switch to listening
    audio.speech_ready      - Switch to thinking (user finished speaking)
    llm.response_ready      - Switch to speaking (LLM has a reply)
    tts.finished            - Switch back to idle
    system.error            - Switch to confused
    system.shutdown         - Clean exit

Events this module PUBLISHES:
    face.state_changed      - After state transitions (data: {"state": "idle"})
"""

import asyncio
import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty

from base_module import BaseModule
from event_bus import EventBus, Event

logger = logging.getLogger("deskbot.face")


class EyeController(QObject):
    """
    Qt/QML bridge for eye state.

    This is a QObject so QML can bind to its properties. It does NOT
    contain any business logic. It just holds the current state and
    emits a signal when it changes. The FaceModule below decides
    WHEN to change state based on bus events.
    """

    stateChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._state = "idle"

    @pyqtProperty(str, notify=stateChanged)
    def state(self):
        return self._state

    @pyqtSlot(str)
    def set_state(self, new_state):
        """Called from QML (keyboard input) or from FaceModule."""
        valid_states = {
            "idle", "listening", "thinking",
            "speaking", "happy", "confused", "sleeping"
        }
        if new_state in valid_states and new_state != self._state:
            self._state = new_state
            self.stateChanged.emit(self._state)
            logger.info(f"Face state -> {self._state}")


class FaceModule(BaseModule):
    """
    Event bus module that controls the face.

    Translates bus events into eye/mouth state changes via the
    EyeController. This is the glue between the async event world
    and the Qt/QML rendering world.
    """

    def __init__(self, bus: EventBus, eye_controller: EyeController):
        super().__init__(bus, "face")
        self.eye_controller = eye_controller

    async def setup(self) -> None:
        """Wire up event subscriptions."""

        # Direct state control (any module can request a face state)
        self.subscribe("face.set_state", self._on_set_state)

        # Audio pipeline events
        self.subscribe("audio.wake_word_detected", self._on_wake_word)
        self.subscribe("audio.speech_ready", self._on_speech_ready)

        # LLM events
        self.subscribe("llm.response_ready", self._on_response_ready)
        self.subscribe("llm.tool_call", self._on_tool_call)

        # TTS events
        self.subscribe("tts.started", self._on_tts_started)
        self.subscribe("tts.finished", self._on_tts_finished)

        # System events
        self.subscribe("system.error", self._on_error)

    async def _on_set_state(self, event: Event) -> None:
        """Direct state change request."""
        if isinstance(event.data, dict) and "state" in event.data:
            self.eye_controller.set_state(event.data["state"])
            await self.publish("face.state_changed", {"state": event.data["state"]})

    async def _on_wake_word(self, event: Event) -> None:
        self.eye_controller.set_state("listening")
        await self.publish("face.state_changed", {"state": "listening"})

    async def _on_speech_ready(self, event: Event) -> None:
        self.eye_controller.set_state("thinking")
        await self.publish("face.state_changed", {"state": "thinking"})

    async def _on_response_ready(self, event: Event) -> None:
        # Response is ready but TTS hasn't started yet, stay thinking
        # TTS will trigger speaking state when it starts
        pass

    async def _on_tool_call(self, event: Event) -> None:
        # Stay in thinking while tools execute
        self.eye_controller.set_state("thinking")

    async def _on_tts_started(self, event: Event) -> None:
        self.eye_controller.set_state("speaking")
        await self.publish("face.state_changed", {"state": "speaking"})

    async def _on_tts_finished(self, event: Event) -> None:
        self.eye_controller.set_state("happy")
        await self.publish("face.state_changed", {"state": "happy"})
        # Brief happy moment, then back to idle
        await asyncio.sleep(1.5)
        self.eye_controller.set_state("idle")
        await self.publish("face.state_changed", {"state": "idle"})

    async def _on_error(self, event: Event) -> None:
        self.eye_controller.set_state("confused")
        await self.publish("face.state_changed", {"state": "confused"})
        await asyncio.sleep(2.0)
        self.eye_controller.set_state("idle")
        await self.publish("face.state_changed", {"state": "idle"})