"""
DeskBot - Event Bus Test

Run this standalone to verify the event bus works correctly.
No Qt, no display needed. Pure Python async test.

Usage:
    python3 test_event_bus.py

What it tests:
    1. Basic publish/subscribe
    2. Wildcard pattern matching
    3. Error isolation (one bad subscriber doesn't kill others)
    4. Event history
    5. A simulated full voice interaction cycle
"""

import asyncio
import logging
from event_bus import EventBus, Event

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

# Track received events for assertions
received = []


async def test_basic_pubsub():
    """Test basic publish and subscribe."""
    print("\n=== Test 1: Basic pub/sub ===")
    bus = EventBus()
    received.clear()

    async def handler(event: Event):
        received.append(event.name)

    bus.subscribe("test.hello", handler, name="test_handler")
    await bus.publish("test.hello", data="world")

    assert received == ["test.hello"], f"Expected ['test.hello'], got {received}"
    print("PASSED: Basic pub/sub works")


async def test_wildcard():
    """Test wildcard pattern matching."""
    print("\n=== Test 2: Wildcard matching ===")
    bus = EventBus()
    received.clear()

    async def handler(event: Event):
        received.append(event.name)

    # Subscribe to all audio events
    bus.subscribe("audio.*", handler, name="audio_handler")

    await bus.publish("audio.wake_word_detected")
    await bus.publish("audio.speech_ready", data={"text": "hello"})
    await bus.publish("llm.response_ready")  # Should NOT match

    assert received == ["audio.wake_word_detected", "audio.speech_ready"], \
        f"Expected 2 audio events, got {received}"
    print("PASSED: Wildcard matching works")


async def test_catch_all():
    """Test * subscribes to everything."""
    print("\n=== Test 3: Catch-all subscriber ===")
    bus = EventBus()
    received.clear()

    async def handler(event: Event):
        received.append(event.name)

    bus.subscribe("*", handler, name="catch_all")

    await bus.publish("audio.test")
    await bus.publish("llm.test")
    await bus.publish("face.test")

    assert len(received) == 3, f"Expected 3 events, got {len(received)}"
    print("PASSED: Catch-all works")


async def test_error_isolation():
    """Test that one broken subscriber doesn't kill others."""
    print("\n=== Test 4: Error isolation ===")
    bus = EventBus()
    received.clear()

    async def bad_handler(event: Event):
        raise RuntimeError("I am broken!")

    async def good_handler(event: Event):
        received.append(event.name)

    bus.subscribe("test.event", bad_handler, name="bad_handler")
    bus.subscribe("test.event", good_handler, name="good_handler")

    await bus.publish("test.event")

    assert received == ["test.event"], \
        f"Good handler should still receive event despite bad handler"
    print("PASSED: Error isolation works (bad subscriber logged, good one unaffected)")


async def test_event_history():
    """Test event history tracking."""
    print("\n=== Test 5: Event history ===")
    bus = EventBus()

    await bus.publish("event.one")
    await bus.publish("event.two")
    await bus.publish("event.three")

    history = bus.get_history()
    assert len(history) == 3, f"Expected 3 events in history, got {len(history)}"
    assert history[0].name == "event.one"
    assert history[2].name == "event.three"

    # Filter history
    await bus.publish("audio.test")
    audio_history = bus.get_history("audio.*")
    assert len(audio_history) == 1
    print("PASSED: Event history works")


async def test_data_payload():
    """Test that event data is passed correctly."""
    print("\n=== Test 6: Data payload ===")
    bus = EventBus()
    received.clear()
    payloads = []

    async def handler(event: Event):
        received.append(event.name)
        payloads.append(event.data)

    bus.subscribe("test.data", handler, name="data_handler")

    await bus.publish("test.data", data={"text": "hello", "confidence": 0.95})
    await bus.publish("test.data", data="simple string")
    await bus.publish("test.data", data=None)

    assert payloads[0] == {"text": "hello", "confidence": 0.95}
    assert payloads[1] == "simple string"
    assert payloads[2] is None
    print("PASSED: Data payloads work correctly")


async def test_unsubscribe():
    """Test removing a subscriber."""
    print("\n=== Test 7: Unsubscribe ===")
    bus = EventBus()
    received.clear()

    async def handler(event: Event):
        received.append(event.name)

    bus.subscribe("test.unsub", handler, name="unsub_handler")
    await bus.publish("test.unsub")
    assert len(received) == 1

    bus.unsubscribe("test.unsub", handler)
    await bus.publish("test.unsub")
    assert len(received) == 1, "Should not receive after unsubscribe"
    print("PASSED: Unsubscribe works")


async def test_full_interaction_cycle():
    """
    Simulate a complete voice interaction:
        wake word -> listening -> speech -> thinking -> LLM -> speaking -> idle

    This is exactly what happens when you talk to DeskBot.
    """
    print("\n=== Test 8: Full interaction cycle ===")
    bus = EventBus()
    state_log = []

    # Simulate the face module tracking states
    async def face_handler(event: Event):
        state_map = {
            "audio.wake_word_detected": "listening",
            "audio.speech_ready": "thinking",
            "tts.started": "speaking",
            "tts.finished": "idle",
        }
        if event.name in state_map:
            state_log.append(state_map[event.name])

    bus.subscribe("audio.*", face_handler, name="face")
    bus.subscribe("tts.*", face_handler, name="face")

    # Simulate the interaction
    print("  [1] Wake word detected...")
    await bus.publish("audio.wake_word_detected", source="wake_word")

    print("  [2] User speaks, speech transcribed...")
    await bus.publish("audio.speech_ready",
                      data={"text": "What time is it?"},
                      source="stt")

    print("  [3] LLM processes and responds...")
    await bus.publish("llm.response_ready",
                      data={"text": "It is 3:42 PM."},
                      source="llm")

    print("  [4] TTS starts speaking...")
    await bus.publish("tts.started", source="tts")

    print("  [5] TTS finishes...")
    await bus.publish("tts.finished", source="tts")

    expected = ["listening", "thinking", "speaking", "idle"]
    assert state_log == expected, f"Expected {expected}, got {state_log}"
    print(f"  State transitions: {' -> '.join(state_log)}")
    print("PASSED: Full interaction cycle works")


async def test_multiple_subscribers():
    """Test that multiple modules can listen to the same event."""
    print("\n=== Test 9: Multiple subscribers ===")
    bus = EventBus()
    results = {"face": False, "logger": False, "analytics": False}

    async def face_handler(event: Event):
        results["face"] = True

    async def log_handler(event: Event):
        results["logger"] = True

    async def analytics_handler(event: Event):
        results["analytics"] = True

    bus.subscribe("audio.wake_word_detected", face_handler, name="face")
    bus.subscribe("audio.wake_word_detected", log_handler, name="logger")
    bus.subscribe("audio.*", analytics_handler, name="analytics")

    await bus.publish("audio.wake_word_detected")

    assert all(results.values()), f"Not all subscribers triggered: {results}"
    print("PASSED: Multiple subscribers all receive the same event")


async def run_all_tests():
    """Run all tests."""
    print("=" * 50)
    print("DeskBot Event Bus Tests")
    print("=" * 50)

    await test_basic_pubsub()
    await test_wildcard()
    await test_catch_all()
    await test_error_isolation()
    await test_event_history()
    await test_data_payload()
    await test_unsubscribe()
    await test_full_interaction_cycle()
    await test_multiple_subscribers()

    print("\n" + "=" * 50)
    print("ALL 9 TESTS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())