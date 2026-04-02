"""
DeskBot - Main Orchestrator

Entry point for DeskBot. Creates the event bus, initializes all modules,
and runs the Qt GUI event loop alongside the asyncio event loop.

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

# Ensure project root is on sys.path so all imports work
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QColor, QGuiApplication
from PyQt6.QtQuick import QQuickView

from core.event_bus import EventBus
from core.configs import config
from modules.face.face_module import EyeController, FaceModule
from llm.llm_module import LLMModule

# ─── Logging Setup ───

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("deskbot.main")


def run_async_loop(loop: asyncio.AbstractEventLoop, bus: EventBus, modules: list):
    asyncio.set_event_loop(loop)

    async def run_modules():
        for module in modules:
            await module.setup()
            logger.info(f"Module '{module.name}' setup complete")

        tasks = [asyncio.create_task(module.start()) for module in modules]
        logger.info(f"All {len(tasks)} modules started")

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Modules cancelled, shutting down")

    try:
        loop.run_until_complete(run_modules())
    except RuntimeError as e:
        if "Event loop stopped" in str(e):
            pass
        else:
            logger.error(f"Async loop error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Async loop error: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="DeskBot - Desk Companion Robot")
    parser.add_argument("--fullscreen", action="store_true",
                        help="Run fullscreen (for Raspberry Pi deployment)")
    args = parser.parse_args()

    app = QGuiApplication(sys.argv)

    bus = EventBus()

    eye_controller = EyeController()

    face_module = FaceModule(bus, eye_controller)
    llm_module = LLMModule(bus)

    all_modules = [face_module, llm_module]

    async_loop = asyncio.new_event_loop()
    async_thread = threading.Thread(
        target=run_async_loop,
        args=(async_loop, bus, all_modules),
        daemon=True
    )
    async_thread.start()

    view = QQuickView()
    view.setTitle("DeskBot")
    view.engine().quit.connect(app.quit)
    view.rootContext().setContextProperty("eyeController", eye_controller)

    qml_path = PROJECT_ROOT / "modules" / "face" / "Eyes.qml"
    view.setSource(QUrl.fromLocalFile(str(qml_path)))

    if view.status().value != 1:
        for err in view.errors():
            logger.error(f"QML Error: {err.toString()}")
        sys.exit(1)

    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setColor(QColor("#000000"))

    if args.fullscreen or config.FULLSCREEN:
        view.showFullScreen()
    else:
        view.setWidth(config.DISPLAY_WIDTH)
        view.setHeight(config.DISPLAY_HEIGHT)
        view.show()

    logger.info("DeskBot started. Press keyboard keys to test face states.")
    logger.info("Modules loaded: " + ", ".join(m.name for m in all_modules))

    exit_code = app.exec()

    logger.info("Shutting down...")
    for task in asyncio.all_tasks(async_loop):
        async_loop.call_soon_threadsafe(task.cancel)
    async_loop.call_soon_threadsafe(async_loop.stop)
    async_thread.join(timeout=3)

    logger.info("DeskBot stopped.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()