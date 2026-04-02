import QtQuick
import QtQuick.Shapes

/*
 * DeskPod Robot Face - QML Visual Layer
 *
 * Coordinate system:
 *   Canvas is 1080x1080 with a circular clip mask (simulates round display).
 *   Face center: x=540, y=540
 *   Eyes centered at y=430 (slightly above center for natural face proportions).
 *   Left eye center:  x=370, y=430
 *   Right eye center: x=710, y=430
 *   Mouth center:     x=540, y=700
 */

Rectangle {
    id: root
    anchors.fill: parent
    color: "#000000"
    focus: true

    property string currentState: eyeController ? eyeController.state : "idle"

    // ─── Eye Configuration ───

    readonly property int eyeY: 430
    readonly property int leftEyeX: 370
    readonly property int rightEyeX: 710
    readonly property int eyeWidth: 120                 // sclera half-width
    readonly property int eyeHeight: 100                // sclera half-height
    readonly property int irisRadius: 45                // iris size
    readonly property int pupilRadius: 22               // pupil size
    readonly property color irisColor: "#4FC3F7"
    readonly property color irisDark: "#0288D1"

    // ─── Mouth Configuration ───

    readonly property int mouthCenterX: 540
    readonly property int mouthCenterY: 700

    // ─── Animated Eye Properties ───

    property real pupilOffsetX: 0
    property real pupilOffsetY: 0
    property real pupilScale: 1.0
    property real eyeOpenness: 1.0
    property real leftEyeOpenness: 1.0
    property real rightEyeOpenness: 1.0
    property real eyeSquish: 0.0
    property real breatheScale: 1.0

    // ─── Animated Mouth Properties ───

    property real mouthWidth: 130
    property real mouthCurve: 0.1
    property real mouthOpenAmount: 0
    property real mouthOffsetX: 0

    // ─── Keyboard Input ───

    Keys.onPressed: function(event) {
        switch (event.key) {
            case Qt.Key_I: eyeController.set_state("idle"); break;
            case Qt.Key_L: eyeController.set_state("listening"); break;
            case Qt.Key_T: eyeController.set_state("thinking"); break;
            case Qt.Key_S: eyeController.set_state("speaking"); break;
            case Qt.Key_H: eyeController.set_state("happy"); break;
            case Qt.Key_C: eyeController.set_state("confused"); break;
            case Qt.Key_Z: eyeController.set_state("sleeping"); break;
            case Qt.Key_Escape:
            case Qt.Key_Q: Qt.quit(); break;
        }
    }

    // ─── State Handling ───

    Connections {
        target: eyeController
        function onStateChanged(newState) {
            applyState(newState);
        }
    }

    function applyState(state) {
        idleLookTimer.stop();
        blinkTimer.stop();
        speakTimer.stop();
        breatheAnimation.stop();
        thinkAnimation.stop();
        speakMouthAnimation.stop();

        switch (state) {
            case "idle":
                resetFace();
                blinkTimer.start();
                idleLookTimer.start();
                breatheAnimation.start();
                break;

            case "listening":
                resetFace();
                pupilScale = 1.4;
                mouthCurve = 0.0;
                mouthOpenAmount = 0.25;
                mouthWidth = 100;
                blinkTimer.interval = 4000;
                blinkTimer.start();
                break;

            case "thinking":
                resetFace();
                pupilScale = 0.7;
                pupilOffsetX = 0.4;
                pupilOffsetY = -0.3;
                eyeOpenness = 0.6;
                leftEyeOpenness = 0.6;
                rightEyeOpenness = 0.6;
                mouthCurve = -0.15;
                mouthOpenAmount = 0.05;
                mouthOffsetX = 30;
                mouthWidth = 80;
                thinkAnimation.start();
                break;

            case "speaking":
                resetFace();
                pupilScale = 1.0;
                eyeOpenness = 0.9;
                leftEyeOpenness = 0.9;
                rightEyeOpenness = 0.9;
                mouthCurve = 0.05;
                speakTimer.start();
                speakMouthAnimation.start();
                blinkTimer.interval = 3000;
                blinkTimer.start();
                break;

            case "happy":
                resetFace();
                eyeSquish = 0.55;
                pupilScale = 1.1;
                eyeOpenness = 0.85;
                leftEyeOpenness = 0.85;
                rightEyeOpenness = 0.85;
                mouthCurve = 1.0;
                mouthWidth = 160;
                mouthOpenAmount = 0.15;
                break;

            case "confused":
                resetFace();
                leftEyeOpenness = 0.5;
                rightEyeOpenness = 1.0;
                pupilScale = 0.9;
                pupilOffsetX = -0.2;
                mouthCurve = -0.3;
                mouthOffsetX = -20;
                mouthWidth = 95;
                mouthOpenAmount = 0.1;
                break;

            case "sleeping":
                resetFace();
                eyeOpenness = 0.0;
                leftEyeOpenness = 0.0;
                rightEyeOpenness = 0.0;
                mouthCurve = 0.05;
                mouthWidth = 70;
                mouthOpenAmount = 0.0;
                breatheAnimation.start();
                break;
        }
    }

    function resetFace() {
        pupilOffsetX = 0;
        pupilOffsetY = 0;
        pupilScale = 1.0;
        eyeOpenness = 1.0;
        leftEyeOpenness = 1.0;
        rightEyeOpenness = 1.0;
        eyeSquish = 0.0;
        breatheScale = 1.0;
        mouthWidth = 130;
        mouthCurve = 0.1;
        mouthOpenAmount = 0.0;
        mouthOffsetX = 0;
    }

    // ─── Timers and Animations ───

    Timer {
        id: blinkTimer
        interval: 3000
        repeat: true
        running: true
        onTriggered: {
            interval = 2000 + Math.random() * 3000;
            blinkAnimation.start();
        }
    }

    SequentialAnimation {
        id: blinkAnimation
        NumberAnimation {
            target: root; property: "leftEyeOpenness"
            to: 0.05; duration: 80; easing.type: Easing.InQuad
        }
        NumberAnimation {
            target: root; property: "leftEyeOpenness"
            to: root.currentState === "sleeping" ? 0.0 :
                root.currentState === "thinking" ? 0.6 :
                root.currentState === "happy" ? 0.85 : 1.0
            duration: 120; easing.type: Easing.OutQuad
        }
        NumberAnimation {
            target: root; property: "rightEyeOpenness"
            to: 0.05; duration: 1
        }
        NumberAnimation {
            target: root; property: "rightEyeOpenness"
            to: root.currentState === "sleeping" ? 0.0 :
                root.currentState === "confused" ? 1.0 :
                root.currentState === "thinking" ? 0.6 :
                root.currentState === "happy" ? 0.85 : 1.0
            duration: 120; easing.type: Easing.OutQuad
        }
    }

    Timer {
        id: idleLookTimer
        interval: 4000
        repeat: true
        running: true
        onTriggered: {
            interval = 3000 + Math.random() * 4000;
            idleLookX.to = (Math.random() - 0.5) * 0.6;
            idleLookY.to = (Math.random() - 0.5) * 0.3;
            idleLookAnim.start();
        }
    }

    ParallelAnimation {
        id: idleLookAnim
        NumberAnimation {
            id: idleLookX
            target: root; property: "pupilOffsetX"
            duration: 600; easing.type: Easing.InOutQuad
        }
        NumberAnimation {
            id: idleLookY
            target: root; property: "pupilOffsetY"
            duration: 600; easing.type: Easing.InOutQuad
        }
    }

    SequentialAnimation {
        id: breatheAnimation
        loops: Animation.Infinite
        NumberAnimation {
            target: root; property: "breatheScale"
            from: 1.0; to: 1.01; duration: 2000
            easing.type: Easing.InOutSine
        }
        NumberAnimation {
            target: root; property: "breatheScale"
            from: 1.01; to: 1.0; duration: 2000
            easing.type: Easing.InOutSine
        }
    }

    SequentialAnimation {
        id: thinkAnimation
        loops: Animation.Infinite
        NumberAnimation {
            target: root; property: "pupilOffsetX"
            to: 0.5; duration: 2000; easing.type: Easing.InOutSine
        }
        NumberAnimation {
            target: root; property: "pupilOffsetX"
            to: 0.3; duration: 2000; easing.type: Easing.InOutSine
        }
    }

    Timer {
        id: speakTimer
        interval: 300
        repeat: true
        onTriggered: {
            interval = 200 + Math.random() * 400;
            pupilOffsetX = (Math.random() - 0.5) * 0.2;
            pupilOffsetY = (Math.random() - 0.5) * 0.1;
        }
    }

    SequentialAnimation {
        id: speakMouthAnimation
        loops: Animation.Infinite
        NumberAnimation {
            target: root; property: "mouthOpenAmount"
            to: 0.5; duration: 150; easing.type: Easing.InOutQuad
        }
        NumberAnimation {
            target: root; property: "mouthOpenAmount"
            to: 0.1; duration: 120; easing.type: Easing.InOutQuad
        }
        NumberAnimation {
            target: root; property: "mouthOpenAmount"
            to: 0.65; duration: 180; easing.type: Easing.InOutQuad
        }
        NumberAnimation {
            target: root; property: "mouthOpenAmount"
            to: 0.0; duration: 100; easing.type: Easing.InOutQuad
        }
        PauseAnimation { duration: 80 }
        NumberAnimation {
            target: root; property: "mouthOpenAmount"
            to: 0.4; duration: 140; easing.type: Easing.InOutQuad
        }
        NumberAnimation {
            target: root; property: "mouthOpenAmount"
            to: 0.15; duration: 160; easing.type: Easing.InOutQuad
        }
    }

    // ─── Smooth Transitions ───

    Behavior on pupilOffsetX {
        NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
    }
    Behavior on pupilOffsetY {
        NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
    }
    Behavior on pupilScale {
        NumberAnimation { duration: 400; easing.type: Easing.InOutQuad }
    }
    Behavior on eyeOpenness {
        NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
    }
    Behavior on eyeSquish {
        NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
    }
    Behavior on mouthWidth {
        NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
    }
    Behavior on mouthCurve {
        NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
    }
    Behavior on mouthOffsetX {
        NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
    }

    // ─── Circular Display Mask ───
    // Clips everything to a circle, simulating the round display.
    // On the actual Waveshare display, the physical bezel does this.
    // For development on a normal monitor, this gives the same effect.

    Rectangle {
        id: circularMask
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height)
        height: width
        radius: width / 2
        color: "#000000"
        clip: true

        // Subtle circular border to show display edge
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.color: "#222222"
            border.width: 3
            z: 100
        }

        // ─── Face Container (inside the circle) ───
        Item {
            id: faceContainer
            anchors.centerIn: parent
            width: parent.width
            height: parent.height
            scale: root.breatheScale

            // ════════════════════════
            //       LEFT EYE
            // ════════════════════════
            Item {
                id: leftEye
                x: root.leftEyeX - root.eyeWidth
                y: root.eyeY - root.eyeHeight
                width: root.eyeWidth * 2
                height: root.eyeHeight * 2
                clip: true

                Rectangle {
                    anchors.centerIn: parent
                    width: root.eyeWidth * 2
                    height: root.eyeHeight * 2
                    radius: width / 2
                    color: "#F5F5F5"
                }

                Rectangle {
                    anchors.centerIn: parent
                    anchors.horizontalCenterOffset: root.pupilOffsetX * (root.eyeWidth - root.irisRadius)
                    anchors.verticalCenterOffset: root.pupilOffsetY * (root.eyeHeight - root.irisRadius)
                    width: root.irisRadius * 2
                    height: root.irisRadius * 2
                    radius: root.irisRadius
                    color: root.irisColor

                    Rectangle {
                        anchors.fill: parent
                        radius: parent.radius
                        color: "transparent"
                        border.color: root.irisDark
                        border.width: 3
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: root.pupilRadius * 2 * root.pupilScale
                        height: root.pupilRadius * 2 * root.pupilScale
                        radius: width / 2
                        color: "#000000"

                        Rectangle {
                            x: parent.width * 0.5
                            y: parent.height * 0.15
                            width: parent.width * 0.25
                            height: width
                            radius: width / 2
                            color: "#FFFFFF"
                            opacity: 0.9
                        }
                    }
                }

                // Upper eyelid
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width + 20
                    height: parent.height
                    color: "#000000"
                    y: -height + (parent.height * (1.0 - root.leftEyeOpenness))
                }

                // Lower eyelid
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width + 20
                    height: parent.height
                    color: "#000000"
                    y: parent.height - (parent.height * (1.0 - root.leftEyeOpenness))
                       + (parent.height * (1.0 - root.eyeSquish))
                }
            }

            // ════════════════════════
            //       RIGHT EYE
            // ════════════════════════
            Item {
                id: rightEye
                x: root.rightEyeX - root.eyeWidth
                y: root.eyeY - root.eyeHeight
                width: root.eyeWidth * 2
                height: root.eyeHeight * 2
                clip: true

                Rectangle {
                    anchors.centerIn: parent
                    width: root.eyeWidth * 2
                    height: root.eyeHeight * 2
                    radius: width / 2
                    color: "#F5F5F5"
                }

                Rectangle {
                    anchors.centerIn: parent
                    anchors.horizontalCenterOffset: root.pupilOffsetX * (root.eyeWidth - root.irisRadius)
                    anchors.verticalCenterOffset: root.pupilOffsetY * (root.eyeHeight - root.irisRadius)
                    width: root.irisRadius * 2
                    height: root.irisRadius * 2
                    radius: root.irisRadius
                    color: root.irisColor

                    Rectangle {
                        anchors.fill: parent
                        radius: parent.radius
                        color: "transparent"
                        border.color: root.irisDark
                        border.width: 3
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: root.pupilRadius * 2 * root.pupilScale
                        height: root.pupilRadius * 2 * root.pupilScale
                        radius: width / 2
                        color: "#000000"

                        Rectangle {
                            x: parent.width * 0.5
                            y: parent.height * 0.15
                            width: parent.width * 0.25
                            height: width
                            radius: width / 2
                            color: "#FFFFFF"
                            opacity: 0.9
                        }
                    }
                }

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width + 20
                    height: parent.height
                    color: "#000000"
                    y: -height + (parent.height * (1.0 - root.rightEyeOpenness))
                }

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width + 20
                    height: parent.height
                    color: "#000000"
                    y: parent.height - (parent.height * (1.0 - root.rightEyeOpenness))
                       + (parent.height * (1.0 - root.eyeSquish))
                }
            }

            // ════════════════════════
            //        MOUTH
            // ════════════════════════

            Shape {
                id: mouthShape
                x: root.mouthCenterX - root.mouthWidth + root.mouthOffsetX
                y: root.mouthCenterY - 30
                width: root.mouthWidth * 2
                height: 100
                antialiasing: true

                // Upper lip
                ShapePath {
                    strokeColor: "#F5F5F5"
                    strokeWidth: 8
                    fillColor: root.mouthOpenAmount > 0.05 ? "#3A0A0A" : "transparent"
                    capStyle: ShapePath.RoundCap

                    startX: 0
                    startY: 30

                    PathQuad {
                        controlX: root.mouthWidth
                        controlY: 30 + (root.mouthCurve * 45)
                        x: root.mouthWidth * 2
                        y: 30
                    }
                }

                // Lower lip
                ShapePath {
                    strokeColor: root.mouthOpenAmount > 0.05 ? "#F5F5F5" : "transparent"
                    strokeWidth: root.mouthOpenAmount > 0.05 ? 8 : 0
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap

                    startX: 0
                    startY: 30

                    PathQuad {
                        controlX: root.mouthWidth
                        controlY: 30 + (root.mouthCurve * 45)
                               + (root.mouthOpenAmount * 80)
                        x: root.mouthWidth * 2
                        y: 30
                    }
                }
            }
        }
    }

    // ─── State Label (outside the circle, dev only) ───
    Text {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        anchors.horizontalCenter: parent.horizontalCenter
        text: "State: " + root.currentState + "  |  Keys: I L T S H C Z  |  Esc=Quit"
        color: "#555555"
        font.pixelSize: 18
        font.family: "monospace"
    }

    Component.onCompleted: {
        applyState("idle");
    }
}
