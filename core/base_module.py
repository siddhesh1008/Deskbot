"""
DeskBot - Base Module

Every module in DeskBot inherits from this class. It provides:
    - Automatic connection to the event bus
    - Lifecycle management (setup -> start -> run -> stop)
    - Convenience methods for publishing and subscribing
"""

import asyncio
import logging
from core.event_bus import EventBus, Event

logger = logging.getLogger("deskbot.module")


class BaseModule:
    def __init__(self, bus: EventBus, name: str):
        self.bus = bus
        self.name = name
        self.running = False
        self._logger = logging.getLogger(f"deskbot.{name}")

    async def setup(self) -> None:
        pass

    async def start(self) -> None:
        self.running = True
        self._logger.info(f"Module '{self.name}' starting")
        try:
            await self.run()
        except asyncio.CancelledError:
            self._logger.info(f"Module '{self.name}' cancelled")
        except Exception as e:
            self._logger.error(f"Module '{self.name}' crashed: {e}", exc_info=True)
        finally:
            await self.stop()

    async def run(self) -> None:
        while self.running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self.running = False
        self._logger.info(f"Module '{self.name}' stopped")

    def subscribe(self, pattern: str, callback) -> None:
        self.bus.subscribe(pattern, callback, name=self.name)

    async def publish(self, event_name: str, data=None) -> None:
        await self.bus.publish(event_name, data=data, source=self.name)