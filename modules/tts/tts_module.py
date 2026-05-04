"""
DeskBot - TTS Module (Piper)

Local text-to-speech using Piper TTS. Completely offline, no cloud.

Events this module LISTENS to:
    tts.speak              - Direct speak request (data: {"text": "..."})
    llm.response_ready     - Speak LLM response (data: {"text": "..."})

Events this module PUBLISHES:
    tts.started            - Audio playback beginning
    tts.finished           - Audio playback done
"""

import io
import wave
import subprocess
import logging
import tempfile
import os

from core.base_module import BaseModule
from core.event_bus import EventBus, Event
from core.configs import config

logger = logging.getLogger("deskbot.tts")

VOICES_DIR = os.path.expanduser("~/.local/share/piper_voices")


class TTSModule(BaseModule):

    def __init__(self, bus: EventBus):
        super().__init__(bus, "tts")
        self.voice = config.TTS_VOICE
        self.speaker_device = config.SPEAKER_DEVICE
        self._piper = None

    async def setup(self) -> None:
        self.subscribe("tts.speak", self._on_speak)
        self.subscribe("llm.response_ready", self._on_llm_response)

        try:
            from piper import PiperVoice

            model_path = os.path.join(VOICES_DIR, f"{self.voice}.onnx")
            config_path = os.path.join(VOICES_DIR, f"{self.voice}.onnx.json")

            if not os.path.exists(model_path):
                logger.error(f"Voice model not found: {model_path}")
                logger.error(f"Download it to {VOICES_DIR}")
                return

            logger.info(f"Loading Piper voice: {self.voice}")
            self._piper = PiperVoice.load(model_path, config_path=config_path)
            logger.info(f"Piper TTS ready (voice: {self.voice}, device: {self.speaker_device})")

        except Exception as e:
            logger.error(f"Failed to initialize Piper TTS: {e}", exc_info=True)

    async def _on_llm_response(self, event: Event) -> None:
        if isinstance(event.data, dict) and "text" in event.data:
            await self._speak(event.data["text"])

    async def _on_speak(self, event: Event) -> None:
        if isinstance(event.data, dict) and "text" in event.data:
            await self._speak(event.data["text"])
        elif isinstance(event.data, str):
            await self._speak(event.data)

    async def _speak(self, text: str) -> None:
        if not self._piper:
            logger.error("Piper not initialized, cannot speak")
            return

        if not text.strip():
            return

        logger.info(f"Speaking: {text[:80]}...")

        try:
            await self.publish("tts.started")

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                self._piper.synthesize(text, wav_file)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_buffer.getvalue())
                tmp_path = tmp.name

            subprocess.run(
                ["aplay", "-D", self.speaker_device, "-q", tmp_path],
                check=True,
                timeout=60
            )

            os.unlink(tmp_path)
            await self.publish("tts.finished")

        except subprocess.TimeoutExpired:
            logger.error("Audio playback timed out")
            await self.publish("tts.finished")
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
            await self.publish("tts.finished")