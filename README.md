# DeskBot

A fully local, zero-cloud AI desk companion robot built on Raspberry Pi 5 with a round display. DeskBot features an expressive animated face, voice interaction, and task execution — all running on-device with no subscriptions, no API keys, and no internet dependency.

## Why Local?

Most hobby AI assistants are thin wrappers around cloud APIs. DeskBot takes the harder path: every component runs locally. Speech recognition, language model inference, text-to-speech, and the animated display all operate on-device. This demonstrates real embedded systems engineering — working within hardware constraints, managing real-time pipelines, and building robust modular software — not just gluing APIs together.

## Hardware

| Component | Details |
|-----------|---------|
| Compute | Raspberry Pi 5 (8GB) |
| Display | Waveshare 5" Round Capacitive Touch (1080x1080, HDMI) |
| Audio In | USB Microphone |
| Audio Out | USB / 3.5mm Speaker |
| LLM Server (optional) | Any machine on local network running Ollama via Docker |

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

### Animated Robot Face
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

### Local LLM via Ollama
- Connects to Ollama running in Docker (local machine or remote server on same network)
- Llama 3.1 8B for server deployment, Llama 3.2 3B for on-Pi standalone
- System prompt tuned for concise desk assistant behavior
- Conversation history maintained across interactions
- Publishes thinking/response events that drive face animations
- Configurable endpoint via `.env` — switch between local and remote with one line

### Event Bus Architecture
- Async publish/subscribe system using Python asyncio
- Dot-separated event namespaces (e.g., `audio.wake_word_detected`)
- Wildcard pattern matching (`audio.*`, `*`)
- Error isolation — one crashed module never takes down others
- Event history for debugging
- Base module class with lifecycle management (setup → start → run → stop)
- Thread-safe bridge between asyncio event loop and Qt GUI loop

### Configuration
- All settings in `.env` file (git-ignored)
- `.env.example` provided as template
- Supports: Ollama host/model, display dimensions, fullscreen toggle, log level

## Project Structure

```
Deskbot/
├── main.py                        # Entry point — orchestrator
├── .env                           # Local config (git-ignored)
├── .env.example                   # Config template
├── .gitignore
├── README.md
│
├── core/                          # Framework
│   ├── __init__.py
│   ├── configs.py                 # .env loader and config object
│   ├── event_bus.py               # Async pub/sub event bus
│   └── base_module.py             # Base class for all modules
│
├── modules/                       # Pluggable modules
│   ├── __init__.py
│   └── face/                      # Face rendering module
│       ├── __init__.py
│       ├── face_module.py         # Event bus → eye/mouth state bridge
│       └── Eyes.qml               # QML rendering and animations
│
├── llm/                           # Language model module
│   ├── __init__.py
│   └── llm_module.py              # Ollama HTTP client + conversation history
│
└── tests/                         # Standalone tests
    ├── __init__.py
    ├── test_event_bus.py           # 9 event bus tests
    └── test_llm.py                # 5 LLM tests + interactive chat mode
```

## Setup

### Prerequisites

- Python 3.11+
- Qt6 with QML support
- Docker (for Ollama)

### Install Qt6 Dependencies

```bash
sudo apt update
sudo apt install -y python3-pyqt6 python3-pyqt6.qtquick \
    qml6-module-qtquick qml6-module-qtquick-window \
    qml6-module-qtquick-controls qml6-module-qtquick-layouts \
    qml6-module-qtquick-shapes qml6-module-qtqml-workerscript
```

### Create Virtual Environment

```bash
cd Deskbot
python3 -m venv venv --system-site-packages
source venv/bin/activate
```

### Set Up Ollama (Docker)

```bash
docker run -d \
  --name ollama \
  -v ollama_data:/root/.ollama \
  -p 11434:11434 \
  --restart unless-stopped \
  ollama/ollama

# Pull a model
docker exec -it ollama ollama pull llama3.1:8b
```

### Configure

```bash
cp .env.example .env
# Edit .env with your settings (Ollama host, model, display size, etc.)
```

If Ollama runs on a different machine, update `OLLAMA_HOST` in `.env`:
```
OLLAMA_HOST=http://192.168.1.100:11434
```

### Run

```bash
# Test the event bus (no display, no Ollama needed)
python3 tests/test_event_bus.py

# Test LLM module (requires Ollama running)
python3 tests/test_llm.py

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

- **Local first.** No cloud dependencies. No API keys. No subscriptions. Everything runs on-device or on the local network.
- **Modular.** Every component is an independent module communicating through the event bus. Add, remove, or swap modules without side effects.
- **Testable.** Each module can be tested standalone by publishing fake events. The bus test suite runs without any hardware.
- **Incremental.** Built one module at a time, tested standalone, then integrated. No big bang deployments.
- **Configurable.** All settings in `.env`. Switch between Pi-local and server-offloaded LLM with one line change.

## License

This project is licensed under the **MIT License**.
Feel free to use, modify, and expand this project — just credit the original creator.