"""
DeskBot - Face Module

Bridges the event bus to the Qt/QML eye rendering.
"""

import asyncio
import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty

from core.base_module import BaseModule
from core.event_bus import EventBus, Event

logger = logging.getLogger("deskbot.face")


class EyeController(QObject):
    stateChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._state = "idle"

    @pyqtProperty(str, notify=stateChanged)
    def state(self):
        return self._state

    @pyqtSlot(str)
    def set_state(self, new_state):
        valid_states = {
            "idle", "listening", "thinking",
            "speaking", "happy", "confused", "sleeping"
        }
        if new_state in valid_states and new_state != self._state:
            self._state = new_state
            self.stateChanged.emit(self._state)
            logger.info(f"Face state -> {self._state}")


class FaceModule(BaseModule):
    def __init__(self, bus: EventBus, eye_controller: EyeController):
        super().__init__(bus, "face")
        self.eye_controller = eye_controller

    async def setup(self) -> None:
        self.subscribe("face.set_state", self._on_set_state)
        self.subscribe("audio.wake_word_detected", self._on_wake_word)
        self.subscribe("audio.speech_ready", self._on_speech_ready)
        self.subscribe("llm.response_ready", self._on_response_ready)
        self.subscribe("llm.tool_call", self._on_tool_call)
        self.subscribe("tts.started", self._on_tts_started)
        self.subscribe("tts.finished", self._on_tts_finished)
        self.subscribe("system.error", self._on_error)

    async def _on_set_state(self, event: Event) -> None:
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
        pass

    async def _on_tool_call(self, event: Event) -> None:
        self.eye_controller.set_state("thinking")

    async def _on_tts_started(self, event: Event) -> None:
        self.eye_controller.set_state("speaking")
        await self.publish("face.state_changed", {"state": "speaking"})

    async def _on_tts_finished(self, event: Event) -> None:
        self.eye_controller.set_state("happy")
        await self.publish("face.state_changed", {"state": "happy"})
        await asyncio.sleep(1.5)
        self.eye_controller.set_state("idle")
        await self.publish("face.state_changed", {"state": "idle"})

    async def _on_error(self, event: Event) -> None:
        self.eye_controller.set_state("confused")
        await self.publish("face.state_changed", {"state": "confused"})
        await asyncio.sleep(2.0)
        self.eye_controller.set_state("idle")
        await self.publish("face.state_changed", {"state": "idle"})