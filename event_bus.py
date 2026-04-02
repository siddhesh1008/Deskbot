"""
DeskBot - Event Bus

The central nervous system of DeskBot. Every module communicates through
this bus instead of importing each other directly.

How it works:
    - Modules subscribe to event names they care about
    - Modules publish events when something happens
    - The bus routes events to all matching subscribers
    - Everything is async (asyncio) for non-blocking operation

Why this matters:
    Decoupling. The eye controller doesn't import the LLM. The LLM
    doesn't import TTS. They all just publish and subscribe to events.
    This means:
        - Any module can be tested alone by faking events
        - Any module can be swapped without touching others
        - New modules (camera, servos, sensors) plug in with zero rewiring
        - The system stays clean as it grows

Event naming convention:
    Use dot-separated namespaces so we can do wildcard matching later.
    Examples:
        audio.wake_word_detected
        audio.speech_ready
        llm.response_ready
        llm.tool_call
        tts.started
        tts.finished
        face.state_changed
        system.error
        system.shutdown
        camera.frame_ready
        servo.position_reached

Usage:
    bus = EventBus()

    # Subscribe to a specific event
    bus.subscribe("audio.wake_word_detected", my_callback)

    # Subscribe to all events in a namespace
    bus.subscribe("audio.*", my_callback)

    # Subscribe to everything (useful for logging/debugging)
    bus.subscribe("*", my_logger)

    # Publish an event (with optional data payload)
    await bus.publish("audio.speech_ready", {"text": "hello world"})

    # Callbacks receive an Event object:
    async def my_callback(event):
        print(event.name)     # "audio.speech_ready"
        print(event.data)     # {"text": "hello world"}
        print(event.timestamp)
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine
from collections import defaultdict
import fnmatch

logger = logging.getLogger("deskbot.bus")


@dataclass
class Event:
    """
    A single event flowing through the bus.

    Attributes:
        name:       Dot-separated event name (e.g. "audio.speech_ready")
        data:       Arbitrary payload. Can be dict, string, None, whatever
                    the publisher wants to send.
        timestamp:  When the event was created (monotonic clock).
        source:     Optional string identifying which module published this.
    """
    name: str
    data: Any = None
    timestamp: float = field(default_factory=time.monotonic)
    source: str = ""


# Type alias for subscriber callbacks.
# They must be async functions that accept an Event.
Subscriber = Callable[[Event], Coroutine]


class EventBus:
    """
    Async publish/subscribe event bus.

    This is intentionally simple. No priorities, no complex routing,
    no message queues. Just:
        1. Subscribe a callback to an event pattern
        2. Publish an event
        3. All matching callbacks get called

    The simplicity is the point. For a desk robot running on a Pi 5,
    we don't need RabbitMQ. We need something fast, predictable, and
    easy to debug.
    """

    def __init__(self):
        # Pattern -> list of (callback, subscriber_name) tuples
        # Using a regular dict so we preserve insertion order
        self._subscribers: dict[str, list[tuple[Subscriber, str]]] = defaultdict(list)

        # Event history for debugging. Keeps last N events.
        self._history: list[Event] = []
        self._history_limit = 100

        # Flag to track if bus is running
        self._running = False

    def subscribe(self, pattern: str, callback: Subscriber, name: str = "") -> None:
        """
        Register a callback for events matching the pattern.

        Args:
            pattern:  Event name or glob pattern.
                      "audio.speech_ready" - exact match
                      "audio.*"            - all audio events
                      "*"                  - everything
            callback: Async function that takes an Event argument.
            name:     Optional name for debugging (e.g. "eye_controller").

        The callback must be an async function. If you pass a sync function,
        it will be wrapped automatically but that's not ideal for performance.
        """
        if not asyncio.iscoroutinefunction(callback):
            # Wrap sync callbacks so the bus stays fully async
            sync_fn = callback
            async def async_wrapper(event: Event):
                sync_fn(event)
            async_wrapper.__name__ = getattr(sync_fn, '__name__', 'wrapped')
            callback = async_wrapper
            logger.warning(
                f"Subscriber '{name}' registered sync callback for '{pattern}'. "
                f"Wrapped it as async, but consider making it async natively."
            )

        self._subscribers[pattern].append((callback, name))
        logger.debug(f"Subscribed '{name}' to '{pattern}'")

    def unsubscribe(self, pattern: str, callback: Subscriber) -> None:
        """Remove a specific callback from a pattern."""
        if pattern in self._subscribers:
            self._subscribers[pattern] = [
                (cb, n) for cb, n in self._subscribers[pattern]
                if cb is not callback
            ]
            # Clean up empty lists
            if not self._subscribers[pattern]:
                del self._subscribers[pattern]

    async def publish(self, event_name: str, data: Any = None, source: str = "") -> None:
        """
        Publish an event to all matching subscribers.

        Args:
            event_name: Dot-separated event name (e.g. "audio.speech_ready")
            data:       Any payload to send with the event
            source:     Which module is publishing (for debugging)

        All matching subscribers are called concurrently using asyncio.gather.
        If any subscriber raises an exception, it's logged but doesn't kill
        other subscribers or the bus itself. This is critical for robustness:
        a buggy camera module should never crash the eye animations.
        """
        event = Event(name=event_name, data=data, source=source)

        # Store in history
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit:]

        logger.debug(f"Event: {event_name} (source={source}, data={data})")

        # Find all matching subscribers
        tasks = []
        for pattern, subscribers in self._subscribers.items():
            if self._matches(pattern, event_name):
                for callback, sub_name in subscribers:
                    tasks.append(self._safe_call(callback, event, sub_name))

        # Run all matched callbacks concurrently
        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_call(self, callback: Subscriber, event: Event, name: str) -> None:
        """
        Call a subscriber callback with error isolation.

        If the callback throws, we log the error and move on.
        One broken module must never take down the whole system.
        """
        try:
            await callback(event)
        except Exception as e:
            logger.error(
                f"Subscriber '{name}' crashed handling '{event.name}': {e}",
                exc_info=True
            )

    @staticmethod
    def _matches(pattern: str, event_name: str) -> bool:
        """
        Check if an event name matches a subscription pattern.

        Supports:
            "audio.speech_ready"  matches exactly "audio.speech_ready"
            "audio.*"             matches "audio.speech_ready", "audio.wake_word"
            "*"                   matches everything
            "*.error"             matches "llm.error", "tts.error", etc.
        """
        return fnmatch.fnmatch(event_name, pattern)

    def get_history(self, pattern: str = "*", limit: int = 20) -> list[Event]:
        """Get recent events matching a pattern. Useful for debugging."""
        matching = [e for e in self._history if self._matches(pattern, e.name)]
        return matching[-limit:]

    def get_subscribers(self) -> dict[str, list[str]]:
        """Get a map of patterns to subscriber names. For debugging."""
        return {
            pattern: [name for _, name in subs]
            for pattern, subs in self._subscribers.items()
        }

    def clear(self) -> None:
        """Remove all subscribers and history. Mainly for testing."""
        self._subscribers.clear()
        self._history.clear()