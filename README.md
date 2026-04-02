# DeskBot

A fully local, zero-cloud AI desk companion robot built on Raspberry Pi 5 with a round display. DeskBot features an expressive animated face, voice interaction, and task execution — all running on-device with no subscriptions, no API keys, and no internet dependency.

## Why Local?

Most hobby AI assistants are thin wrappers around cloud APIs. DeskBot takes the harder path: every component runs locally on a Raspberry Pi 5. Speech recognition, language model inference, text-to-speech, and the animated display all operate on-device. This demonstrates real embedded systems engineering — working within hardware constraints, managing real-time pipelines, and building robust modular software — not just gluing APIs together.

## Hardware

| Component | Details |
|-----------|---------|
| Compute | Raspberry Pi 5 (8GB) |
| Display | Waveshare 5" Round Capacitive Touch (1080x1080, HDMI) |
| Audio In | USB Microphone |
| Audio Out | USB / 3.5mm Speaker |

## Architecture

DeskBot uses an event-driven architecture built on an async publish/subscribe bus. Modules communicate exclusively through events — no module imports another directly. This means any module can be tested in isolation, swapped without side effects, or new modules (camera, servos, sensors) can be added without touching existing code.

```
┌─────────────────────────────────────────────────────┐
│                    Event Bus                         │
│              (async pub/sub backbone)                │
├──────────┬──────────┬──────────┬──────────┬─────────┤
│  Wake    │  Speech  │  LLM    │  Text to │  Face   │
│  Word    │  to Text │  Engine │  Speech  │  Module │
│  Module  │  Module  │  Module │  Module  │         │
└──────────┴──────────┴──────────┴──────────┴─────────┘
                                                │
                                          ┌─────┴─────┐
                                          │  Qt6/QML  │
                                          │  Renderer │
                                          └───────────┘
```

**Interaction flow:**

1. Wake word detected → eyes switch to **listening**
2. Speech transcribed → eyes switch to **thinking**
3. LLM generates response → TTS begins → eyes switch to **speaking**, mouth animates
4. TTS finishes → eyes switch to **happy** briefly → return to **idle**

## Current Features

### Animated Robot Face (Module 1)
- Two expressive eyes with iris, pupil, and highlight rendering
- Animated mouth using quadratic bezier curves
- Circular display mask matching the round Waveshare screen
- Seven emotional states with smooth transitions:
  - **Idle** — random blinks, subtle look-around, gentle breathing
  - **Listening** — wide eyes, dilated pupils, slightly open mouth
  - **Thinking** — squinted eyes looking up-right, mouth shifted to side
  - **Speaking** — engaged eyes, rhythmic mouth animation simulating speech
  - **Happy** — anime-style smile eyes, wide grin
  - **Confused** — asymmetric eyes, uncertain mouth
  - **Sleeping** — eyes closed, breathing animation
- Built with Qt6/QML for GPU-accelerated 60fps rendering
- Keyboard controls for testing all states

### Event Bus Architecture
- Async publish/subscribe system using Python asyncio
- Dot-separated event namespaces (e.g., `audio.wake_word_detected`)
- Wildcard pattern matching (`audio.*`, `*`)
- Error isolation — one crashed module never takes down others
- Event history for debugging
- Base module class with lifecycle management (setup → start → run → stop)
- Thread-safe bridge between asyncio event loop and Qt GUI loop

## Project Structure

```
Deskbot/
├── main.py             # Orchestrator — creates bus, initializes modules, runs event loops
├── event_bus.py        # Core pub/sub event bus
├── base_module.py      # Base class all modules inherit from
├── face_module.py      # Face module — translates bus events to eye/mouth states
├── Eyes.qml            # QML rendering — all face visuals and animations
├── test_event_bus.py   # Standalone bus tests (9 tests, no Qt needed)
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- Qt6 with QML support

### Install Dependencies

```bash
# Qt6 system packages (required — QML modules are native C++ libraries)
sudo apt update
sudo apt install -y python3-pyqt6 python3-pyqt6.qtquick \
    qml6-module-qtquick qml6-module-qtquick-window \
    qml6-module-qtquick-controls qml6-module-qtquick-layouts \
    qml6-module-qtquick-shapes qml6-module-qtqml-workerscript

# Create virtual environment with access to system Qt6 packages
python3 -m venv venv --system-site-packages
source venv/bin/activate
```

### Run

```bash
# Test the event bus (no display needed)
python3 test_event_bus.py

# Run DeskBot (windowed, for development)
python3 main.py

# Run fullscreen (for Raspberry Pi with round display)
python3 main.py --fullscreen
```

### Keyboard Controls (Development)

| Key | State |
|-----|-------|
| I | Idle |
| L | Listening |
| T | Thinking |
| S | Speaking |
| H | Happy |
| C | Confused |
| Z | Sleeping |
| Esc / Q | Quit |

## Roadmap

### Upcoming Modules

**Ollama — Local LLM Inference**
Run a language model (Llama 3.1 / Phi-3 / Mistral) locally on the Pi 5 using Ollama. Structured tool/function calling so the LLM can execute actions, not just chat. Conversation memory stored in local SQLite.

**Faster-Whisper — Local Speech-to-Text**
Real-time speech recognition running on-device. Voice activity detection to know when the user starts and stops speaking. Optimized for Pi 5 with INT8 quantized models.

**Piper TTS — Local Text-to-Speech**
High-quality neural voice synthesis running locally. Multiple voice options. Mouth animation synced to audio output duration.

**OpenWakeWord — Wake Word Detection**
Always-on, low-power wake word listening. Custom wake word training. Triggers the full voice pipeline without needing a button press.

**Tool System — Function Calling**
Timer and stopwatch with display countdown. Weather from free APIs. Quick math and unit conversions. Pomodoro timer. Note taking with local storage. Desktop notifications over local network.

### Planned Features

**Camera Module**
USB camera with pan/tilt servo control. Face detection and tracking. Visual context for the LLM (describe what it sees).

**Home Assistant Integration**
MQTT bridge to control smart home devices. Desk light control. Room sensor monitoring.

**Enclosure**
3D printed housing designed for the round display. Cable management. Mounting for mic and speaker.

## Design Principles

- **Local first.** No cloud dependencies. No API keys. No subscriptions. Everything runs on-device.
- **Modular.** Every component is an independent module communicating through the event bus. Add, remove, or swap modules without side effects.
- **Testable.** Each module can be tested standalone by publishing fake events. The bus test suite runs without any hardware.
- **Incremental.** Built one module at a time, tested standalone, then integrated. No big bang deployments.

## 🧊 License

This project is licensed under the **MIT License**.  
Feel free to use, modify, and expand this project — just credit the original creator.
