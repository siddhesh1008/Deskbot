"""
DeskPod - Module 1: Animated Robot Eyes
Standalone test: python3 main.py
Keyboard controls:
    I = Idle, L = Listening, T = Thinking, S = Speaking
    H = Happy, C = Confused, Z = Sleeping, Esc/Q = Quit
"""

import sys
import os
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty, QUrl
from PyQt6.QtGui import QColor, QGuiApplication
from PyQt6.QtQuick import QQuickView
from PyQt6.QtQml import QQmlContext


class EyeController(QObject):
    """
    Controls eye state from Python side.
    
    This is the bridge between the future audio/LLM pipeline and the QML
    eye rendering. Right now we drive it from keyboard input for testing.
    Later, other modules will call set_state() directly.
    
    States:
        idle      - default, random blinks and subtle movement
        listening - eyes widen, pupils dilate, attentive look
        thinking  - eyes squint, look up-right, pupils shrink
        speaking  - engaged look, subtle movement synced to output
        happy     - curved lower eyelids (anime smile)
        confused  - asymmetric eyes, one eyebrow raised
        sleeping  - eyes closed, gentle breathing animation
    """

    stateChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._state = "idle"

    @pyqtProperty(str, notify=stateChanged)
    def state(self):
        return self._state

    @pyqtSlot(str)
    def set_state(self, new_state):
        valid_states = {
            "idle", "listening", "thinking",
            "speaking", "happy", "confused", "sleeping"
        }
        if new_state in valid_states and new_state != self._state:
            self._state = new_state
            self.stateChanged.emit(self._state)
            print(f"[EyeController] State -> {self._state}")


def main():
    app = QGuiApplication(sys.argv)

    # Create the eye controller (Python -> QML bridge)
    controller = EyeController()

    # Load QML
    view = QQuickView()
    view.setTitle("DeskPod Eyes")

    # Expose controller to QML as 'eyeController'
    view.rootContext().setContextProperty("eyeController", controller)

    # Load QML file from same directory as this script
    qml_path = Path(__file__).parent / "Eyes.qml"
    view.setSource(QUrl.fromLocalFile(str(qml_path)))

    if view.status().value != 1:  # 1 = QQuickView.Status.Ready
        errors = view.errors()
        for err in errors:
            print(f"QML Error: {err.toString()}")
        sys.exit(1)

    # Size to match round display (1080x1080)
    view.setWidth(1080)
    view.setHeight(1080)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setColor(QColor("#000000"))  # Black background hides square corners

    view.show()

    # Keyboard state mapping for testing
    # We handle this via QML's Keys since QQuickView forwards input there.
    # But we also need a way to bridge key events. QML will call
    # eyeController.set_state() directly on keypress.

    sys.exit(app.exec())


if __name__ == "__main__":
    main()