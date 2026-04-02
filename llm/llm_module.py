"""
DeskBot - LLM Module

Connects to Ollama over HTTP for local language model inference.

Events this module LISTENS to:
    llm.query              - Direct query (data: {"text": "..."})
    audio.speech_ready     - Transcribed user speech (data: {"text": "..."})

Events this module PUBLISHES:
    llm.thinking           - Started processing
    llm.response_ready     - Response generated (data: {"text": "..."})
    llm.error              - Something went wrong (data: {"error": "..."})
"""

import json
import logging
import urllib.request
import urllib.error
from core.base_module import BaseModule
from core.event_bus import EventBus, Event
from core.configs import config

logger = logging.getLogger("deskbot.llm")

SYSTEM_PROMPT = """You are DeskBot, a small desk companion robot with an expressive face on a round display. You sit on the user's desk and help with quick tasks.

Personality:
- Friendly but concise. You are not a chatbot, you are an assistant.
- Keep responses SHORT. One to three sentences max unless asked for more.
- You have a face with eyes and a mouth that shows emotions. Mention this naturally if relevant.
- You are running fully locally with no cloud dependencies. You are proud of this if asked.

Capabilities:
- Answer quick questions
- Set timers and reminders (coming soon)
- Give weather updates (coming soon)
- Do quick math and conversions
- Have brief conversations

Rules:
- Never give long explanations unless explicitly asked.
- If you don't know something, say so briefly.
- Be helpful, not verbose."""


class LLMModule(BaseModule):
    def __init__(self, bus: EventBus):
        super().__init__(bus, "llm")
        self.host = config.OLLAMA_HOST
        self.model = config.OLLAMA_MODEL
        self._history: list[dict] = []
        self._max_history = 20

    async def setup(self) -> None:
        self.subscribe("llm.query", self._on_query)
        self.subscribe("audio.speech_ready", self._on_speech_ready)

        if self._check_connection():
            logger.info(f"Connected to Ollama at {self.host} (model: {self.model})")
        else:
            logger.error(f"Cannot reach Ollama at {self.host}. Is it running?")

    def _check_connection(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                logger.info(f"Available models: {models}")
                return True
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False

    async def _on_speech_ready(self, event: Event) -> None:
        if isinstance(event.data, dict) and "text" in event.data:
            await self._generate_response(event.data["text"])

    async def _on_query(self, event: Event) -> None:
        if isinstance(event.data, dict) and "text" in event.data:
            await self._generate_response(event.data["text"])
        elif isinstance(event.data, str):
            await self._generate_response(event.data)

    async def _generate_response(self, user_text: str) -> None:
        logger.info(f"User: {user_text}")
        await self.publish("llm.thinking")

        self._history.append({"role": "user", "content": user_text})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self._history)

        try:
            response_text = self._call_ollama(messages)
            logger.info(f"DeskBot: {response_text}")

            self._history.append({"role": "assistant", "content": response_text})

            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            await self.publish("llm.response_ready", {"text": response_text})

        except Exception as e:
            logger.error(f"LLM error: {e}")
            await self.publish("llm.error", {"error": str(e)})

    def _call_ollama(self, messages: list[dict]) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 256,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["message"]["content"]

    def clear_history(self) -> None:
        self._history.clear()
        logger.info("Conversation history cleared")