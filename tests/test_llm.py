"""
DeskBot - LLM Module Test
Run: python3 tests/test_llm.py  (from project root)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from core.event_bus import EventBus
from llm.llm_module import LLMModule
from core.configs import config

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("test_llm")


async def test_connection():
    print("\n=== Test 1: Ollama Connection ===")
    bus = EventBus()
    llm = LLMModule(bus)
    await llm.setup()
    print("PASSED\n")


async def test_direct_query():
    print("=== Test 2: Direct Query ===")
    bus = EventBus()
    llm = LLMModule(bus)
    await llm.setup()

    responses = []

    async def on_response(event):
        responses.append(event.data)

    bus.subscribe("llm.response_ready", on_response, name="test")
    await bus.publish("llm.query", {"text": "What are you?"})

    assert len(responses) == 1
    assert "text" in responses[0]
    print(f"Response: {responses[0]['text']}")
    print("PASSED\n")


async def test_speech_event():
    print("=== Test 3: Speech Event ===")
    bus = EventBus()
    llm = LLMModule(bus)
    await llm.setup()

    responses = []

    async def on_response(event):
        responses.append(event.data)

    bus.subscribe("llm.response_ready", on_response, name="test")
    await bus.publish("audio.speech_ready", {"text": "Say hello"})

    assert len(responses) == 1
    print(f"Response: {responses[0]['text']}")
    print("PASSED\n")


async def test_thinking_event():
    print("=== Test 4: Thinking Event ===")
    bus = EventBus()
    llm = LLMModule(bus)
    await llm.setup()

    events_received = []

    async def on_any(event):
        events_received.append(event.name)

    bus.subscribe("llm.*", on_any, name="test")
    await bus.publish("llm.query", {"text": "Hi"})

    assert "llm.thinking" in events_received
    assert "llm.response_ready" in events_received
    print(f"Events: {events_received}")
    print("PASSED\n")


async def test_conversation_history():
    print("=== Test 5: Conversation History ===")
    bus = EventBus()
    llm = LLMModule(bus)
    await llm.setup()

    responses = []

    async def on_response(event):
        responses.append(event.data["text"])

    bus.subscribe("llm.response_ready", on_response, name="test")

    await bus.publish("llm.query", {"text": "My name is Sid. Remember that."})
    print(f"Response 1: {responses[-1]}")

    await bus.publish("llm.query", {"text": "What is my name?"})
    print(f"Response 2: {responses[-1]}")

    assert "sid" in responses[-1].lower(), \
        f"LLM should remember 'Sid', got: {responses[-1]}"
    print("PASSED\n")


async def test_interactive():
    print("=== Interactive Mode ===")
    print("Type messages to chat. Type 'quit' to exit.\n")

    bus = EventBus()
    llm = LLMModule(bus)
    await llm.setup()

    async def on_response(event):
        print(f"\nDeskBot: {event.data['text']}\n")

    bus.subscribe("llm.response_ready", on_response, name="display")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if user_input:
                await bus.publish("llm.query", {"text": user_input})
        except (KeyboardInterrupt, EOFError):
            break


async def run_all_tests():
    print("=" * 50)
    print(f"DeskBot LLM Module Tests")
    print(f"Ollama: {config.OLLAMA_HOST}")
    print(f"Model:  {config.OLLAMA_MODEL}")
    print("=" * 50)

    await test_connection()
    await test_direct_query()
    await test_speech_event()
    await test_thinking_event()
    await test_conversation_history()

    print("=" * 50)
    print("ALL 5 TESTS PASSED")
    print("=" * 50)

    try:
        choice = input("\nEnter interactive chat mode? (y/n): ").strip().lower()
        if choice == "y":
            await test_interactive()
    except (KeyboardInterrupt, EOFError):
        pass


if __name__ == "__main__":
    asyncio.run(run_all_tests())