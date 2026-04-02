"""
DeskBot - Base Module

Every module in DeskBot inherits from this class. It provides:
    - Automatic connection to the event bus
    - Lifecycle management (setup -> start -> run -> stop)
    - Convenience methods for publishing and subscribing
    - A consistent interface so any new module (camera, servo, sensor)
      plugs in the same way

Creating a new module:
    1. Inherit from BaseModule
    2. Override setup() to subscribe to events you care about
    3. Override run() if you need a continuous loop (e.g. reading a sensor)
    4. Publish events when things happen

Example:
    class CameraModule(BaseModule):
        def __init__(self, bus):
            super().__init__(bus, "camera")

        async def setup(self):
            # Subscribe to events
            self.subscribe("system.shutdown", self.on_shutdown)

        async def run(self):
            # Continuous loop (optional)
            while self.running:
                frame = await self.capture_frame()
                await self.publish("camera.frame_ready", {"frame": frame})
                await asyncio.sleep(0.033)  # ~30fps

        async def on_shutdown(self, event):
            self.running = False
"""

import asyncio
import logging
from event_bus import EventBus, Event

logger = logging.getLogger("deskbot.module")


class BaseModule:
    """
    Base class for all DeskBot modules.

    Lifecycle:
        1. __init__()  - Store bus reference, set module name
        2. setup()     - Subscribe to events, initialize resources
        3. start()     - Called by the orchestrator, kicks off run()
        4. run()       - Override for continuous operation (loops)
        5. stop()      - Clean shutdown, release resources

    The orchestrator (main.py) creates all modules, calls setup() on
    each, then starts them all concurrently with asyncio.
    """

    def __init__(self, bus: EventBus, name: str):
        """
        Args:
            bus:  The shared EventBus instance
            name: Human-readable module name (e.g. "eye_controller", "tts")
                  Used in logs and event source fields.
        """
        self.bus = bus
        self.name = name
        self.running = False
        self._logger = logging.getLogger(f"deskbot.{name}")

    async def setup(self) -> None:
        """
        Initialize the module. Subscribe to events here.

        Override this in your module. Called once before start().
        Do NOT start loops here. Just wire up subscriptions and
        initialize any resources (open files, load models, etc).
        """
        pass

    async def start(self) -> None:
        """
        Start the module. Called by the orchestrator.

        You usually don't need to override this. It sets the running
        flag and calls run(). Override run() instead.
        """
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
        """
        Main loop for the module. Override for continuous operation.

        If your module only reacts to events (like the eye controller),
        you don't need to override this. The default just waits until
        stop() is called.

        If your module needs a loop (sensor polling, audio capture),
        override this with your loop. Check self.running to know when
        to exit:

            async def run(self):
                while self.running:
                    data = await self.read_sensor()
                    await self.publish("sensor.reading", data)
                    await asyncio.sleep(0.1)
        """
        # Default: just stay alive until stopped
        while self.running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """
        Clean shutdown. Override to release resources.

        Called automatically when start() exits (normally or from error).
        Release hardware, close files, disconnect from APIs here.
        """
        self.running = False
        self._logger.info(f"Module '{self.name}' stopped")

    # ─── Convenience Methods ───

    def subscribe(self, pattern: str, callback) -> None:
        """Subscribe to an event pattern. Shortcut for bus.subscribe."""
        self.bus.subscribe(pattern, callback, name=self.name)

    async def publish(self, event_name: str, data=None) -> None:
        """Publish an event. Shortcut for bus.publish with source auto-set."""
        await self.bus.publish(event_name, data=data, source=self.name)