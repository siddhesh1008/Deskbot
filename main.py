"""
DeskBot - Main Orchestrator

Entry point for DeskBot. Creates the event bus, initializes all modules,
and runs the Qt GUI event loop alongside the asyncio event loop.

The tricky part here: Qt has its own event loop (app.exec()) and we need
asyncio for the event bus and module coroutines. We solve this by running
asyncio in a background thread and using Qt's event loop as the main loop.
Qt signals/slots are thread-safe, so the FaceModule can safely call
eye_controller.set_state() from the asyncio thread.

Usage:
    python3 main.py              # windowed 1080x1080 (development)
    python3 main.py --fullscreen # fullscreen (Raspberry Pi deployment)

Keyboard controls (for testing, handled in QML):
    I = Idle, L = Listening, T = Thinking, S = Speaking
    H = Happy, C = Confused, Z = Sleeping, Esc/Q = Quit
"""

import sys
import asyncio
import threading
import logging
import argparse
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QColor, QGuiApplication
from PyQt6.QtQuick import QQuickView

from event_bus import EventBus
from face_module import EyeController, FaceModule

# ─── Logging Setup ───

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("deskbot.main")


def run_async_loop(loop: asyncio.AbstractEventLoop, bus: EventBus, modules: list):
    """
    Run the asyncio event loop in a background thread.

    This function:
        1. Sets up all modules (calls setup() on each)
        2. Starts all modules as concurrent tasks
        3. Runs until the loop is stopped (when Qt quits)
    """
    asyncio.set_event_loop(loop)

    async def run_modules():
        # Setup all modules
        for module in modules:
            await module.setup()
            logger.info(f"Module '{module.name}' setup complete")

        # Start all modules concurrently
        tasks = [asyncio.create_task(module.start()) for module in modules]
        logger.info(f"All {len(tasks)} modules started")

        # Wait for all tasks (they run until cancelled)
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Modules cancelled, shutting down")

    try:
        loop.run_until_complete(run_modules())
    except RuntimeError as e:
        if "Event loop stopped" in str(e):
            pass  # Expected during shutdown
        else:
            logger.error(f"Async loop error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Async loop error: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="DeskBot - Desk Companion Robot")
    parser.add_argument("--fullscreen", action="store_true",
                        help="Run fullscreen (for Raspberry Pi deployment)")
    args = parser.parse_args()

    # ─── Qt Application ───

    app = QGuiApplication(sys.argv)

    # ─── Event Bus ───

    bus = EventBus()

    # ─── Eye Controller (Qt/QML bridge) ───

    eye_controller = EyeController()

    # ─── Modules ───

    face_module = FaceModule(bus, eye_controller)

    # Future modules will be added here:
    # tts_module = TTSModule(bus)
    # stt_module = STTModule(bus)
    # llm_module = LLMModule(bus)
    # wake_module = WakeWordModule(bus)
    # camera_module = CameraModule(bus)

    all_modules = [face_module]

    # ─── Start Async Loop in Background Thread ───

    async_loop = asyncio.new_event_loop()
    async_thread = threading.Thread(
        target=run_async_loop,
        args=(async_loop, bus, all_modules),
        daemon=True  # Dies when main thread exits
    )
    async_thread.start()

    # ─── Load QML ───

    view = QQuickView()
    view.setTitle("DeskBot")

    # Connect QML Qt.quit() to app shutdown
    view.engine().quit.connect(app.quit)

    # Expose eye controller to QML
    view.rootContext().setContextProperty("eyeController", eye_controller)

    # Load QML file
    qml_path = Path(__file__).parent / "Eyes.qml"
    view.setSource(QUrl.fromLocalFile(str(qml_path)))

    if view.status().value != 1:
        for err in view.errors():
            logger.error(f"QML Error: {err.toString()}")
        sys.exit(1)

    # ─── Window Setup ───

    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setColor(QColor("#000000"))

    if args.fullscreen:
        view.showFullScreen()
    else:
        view.setWidth(1080)
        view.setHeight(1080)
        view.show()

    logger.info("DeskBot started. Press keyboard keys to test face states.")
    logger.info("Modules loaded: " + ", ".join(m.name for m in all_modules))

    # ─── Run Qt Event Loop (blocks until window closes) ───

    exit_code = app.exec()

    # ─── Cleanup ───

    logger.info("Shutting down...")

    # Stop async loop
    for task in asyncio.all_tasks(async_loop):
        async_loop.call_soon_threadsafe(task.cancel)
    async_loop.call_soon_threadsafe(async_loop.stop)
    async_thread.join(timeout=3)

    logger.info("DeskBot stopped.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()